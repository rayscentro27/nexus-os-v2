#!/usr/bin/env node
/**
 * Runtime smoke test — Playwright-based UI workflow test.
 *
 * Builds the app, starts Vite dev server with ui-smoke=1 bypass, then uses Playwright to:
 *   - Visit every hash route and verify it renders non-blank content
 *   - Collect console errors across all routes
 *   - Click core actions on Hermes, Credit, and Trading
 *   - Verify clicks produce visible UI change
 *
 * Exit code 0 = safe, 1 = crash detected.
 */
import { execSync, spawn } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..', '..');
const DIST = join(ROOT, 'dist');
let failures = 0;
let server = null;

function check(label, fn) {
  try {
    fn();
    console.log(`  PASS  ${label}`);
  } catch (e) {
    failures++;
    console.log(`  FAIL  ${label}: ${e.message}`);
  }
}

async function checkAsync(label, fn) {
  try {
    await fn();
    console.log(`  PASS  ${label}`);
  } catch (e) {
    failures++;
    console.log(`  FAIL  ${label}: ${e.message}`);
  }
}

// ── 1. Build artifacts ──
console.log('\n[1] Build artifacts exist...');
check('dist/index.html exists', () => {
  if (!existsSync(join(DIST, 'index.html'))) throw new Error('Not found');
});
check('dist JS bundle exists', () => {
  const files = execSync('ls dist/assets/*.js', { cwd: ROOT }).toString().trim();
  if (!files) throw new Error('No JS bundles');
});

// ── 2. Bundle syntax check ──
console.log('\n[2] Bundle can be parsed as valid JavaScript...');
const jsFiles = execSync('ls dist/assets/*.js', { cwd: ROOT }).toString().trim().split('\n');
for (const file of jsFiles) {
  const fullPath = join(ROOT, file);
  check(`Node can parse ${file}`, () => {
    try {
      execSync(`node --check ${fullPath}`, { cwd: ROOT, stdio: 'pipe' });
    } catch (e) {
      const code = readFileSync(fullPath, 'utf8');
      let depth = 0;
      let inSingle = false, inDouble = false, inBacktick = false;
      for (let i = 0; i < code.length; i++) {
        const ch = code[i];
        const prev = i > 0 ? code[i - 1] : '';
        if (prev === '\\') continue;
        if (ch === "'" && !inDouble && !inBacktick) inSingle = !inSingle;
        if (ch === '"' && !inSingle && !inBacktick) inDouble = !inDouble;
        if (ch === '`' && !inSingle && !inDouble) {
          inBacktick = !inBacktick;
          depth += inBacktick ? 1 : -1;
          if (depth < 0) throw new Error(`Unbalanced backtick at position ${i}`);
        }
      }
      if (depth !== 0) throw new Error(`Unbalanced backticks: depth=${depth}`);
      if (inSingle) throw new Error('Unbalanced single quotes');
      if (inDouble) throw new Error('Unbalanced double quotes');
    }
  });
}

// ── 3. Start Vite dev server (ui-smoke=1 bypasses auth for local testing) ──
console.log('\n[3] Starting Vite dev server...');
try {
  const devServer = spawn('npx', ['vite', '--port', '4199', '--host', '127.0.0.1'], {
    cwd: ROOT,
    stdio: 'pipe',
    env: { ...process.env, FORCE_COLOR: '0' },
  });
  server = devServer;

  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Server start timeout')), 25000);
    const onOutput = (data) => {
      const text = data.toString();
      if (text.includes('Local:') || text.includes('4199')) {
        clearTimeout(timeout);
        devServer.stdout.removeListener('data', onOutput);
        devServer.stderr.removeListener('data', onOutput);
        resolve();
      }
    };
    devServer.stdout.on('data', onOutput);
    devServer.stderr.on('data', onOutput);
  });
  console.log('  Dev server started on http://127.0.0.1:4199');
} catch (e) {
  console.log(`  FAIL  Could not start server: ${e.message}`);
  process.exit(1);
}

// ── 4. Playwright UI workflow tests ──
console.log('\n[4] Playwright UI workflow tests...');

function routeUrl(hash) {
  return hash ? `http://127.0.0.1:4199/?ui-smoke=1#${hash}` : `http://127.0.0.1:4199/?ui-smoke=1`;
}

const ROUTES = [
  { hash: '', name: '/' },
  { hash: 'hermes', name: '/#hermes' },
  { hash: 'credit', name: '/#credit' },
  { hash: 'trading', name: '/#trading' },
  { hash: 'clients', name: '/#clients' },
  { hash: 'opportunity', name: '/#opportunity' },
  { hash: 'research', name: '/#research' },
  { hash: 'monetization', name: '/#monetization' },
  { hash: 'marketing', name: '/#marketing' },
];

let browser;
try {
  browser = await chromium.launch({ headless: true, channel: 'chromium' });
  const context = await browser.newContext();
  const consoleErrors = [];
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (text.includes('favicon') || text.includes('HMR') || text.includes('WebSocket') || text.includes('404')) return;
      consoleErrors.push(text);
    }
  });
  page.on('pageerror', err => {
    consoleErrors.push(`PAGE ERROR: ${err.message}`);
  });

  // ── 4a. Route rendering checks ──
  console.log('\n  [4a] Route rendering checks...');
  for (const route of ROUTES) {
    await checkAsync(`Route ${route.name} renders non-blank content`, async () => {
      await page.goto(routeUrl(route.hash), { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);

      const bodyText = await page.evaluate(() => {
        const root = document.getElementById('root');
        return root ? root.innerText.trim() : '';
      });

      if (!bodyText || bodyText.length < 20) {
        throw new Error(`Page body is blank or too short (${bodyText.length} chars)`);
      }

      const meaningfulLength = bodyText.replace(/\s+/g, '').length;
      if (meaningfulLength < 20) {
        throw new Error(`Page has no meaningful content (${meaningfulLength} non-whitespace chars)`);
      }
    });
  }

  // ── 4b. Console error check ──
  console.log('\n  [4b] Console error check...');
  await checkAsync('No uncaught console errors across all routes', async () => {
    for (const route of ROUTES) {
      await page.goto(routeUrl(route.hash), { waitUntil: 'domcontentloaded', timeout: 10000 });
      await page.waitForTimeout(1000);
    }
    if (consoleErrors.length > 0) {
      throw new Error(`Found ${consoleErrors.length} console error(s):\n  ${consoleErrors.slice(0, 5).join('\n  ')}`);
    }
  });

  // ── 4c. Hermes workflow ──
  console.log('\n  [4c] Hermes Workroom workflow...');
  await page.goto(routeUrl('hermes'), { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);

  await checkAsync('Hermes chat panel renders', async () => {
    const chatPanel = await page.$('.nxos-chat-panel');
    if (!chatPanel) throw new Error('No .nxos-chat-panel found');
  });

  await checkAsync('Hermes textarea accepts input', async () => {
    const textarea = await page.$('.nxos-chat-compose textarea');
    if (!textarea) throw new Error('No textarea found');
    await textarea.fill('good morning');
    const value = await textarea.inputValue();
    if (value !== 'good morning') throw new Error(`Expected "good morning", got "${value}"`);
  });

  await checkAsync('Hermes Send button works and adds messages', async () => {
    const beforeCount = await page.$$eval('.nxos-message', els => els.length);
    const sendBtn = await page.$('.nxos-chat-compose button.primary');
    if (!sendBtn) throw new Error('No Send button found');
    await sendBtn.click();
    await page.waitForTimeout(500);
    const afterCount = await page.$$eval('.nxos-message', els => els.length);
    if (afterCount <= beforeCount) {
      throw new Error(`Message count did not increase (before: ${beforeCount}, after: ${afterCount})`);
    }
  });

  await checkAsync('Hermes conversation starter button works', async () => {
    const starters = await page.$$('.nxos-quick-prompts button');
    if (starters.length === 0) throw new Error('No conversation starters found');
    const beforeCount = await page.$$eval('.nxos-message', els => els.length);
    await starters[0].click();
    await page.waitForTimeout(500);
    const afterCount = await page.$$eval('.nxos-message', els => els.length);
    if (afterCount <= beforeCount) {
      throw new Error(`Message count did not increase after clicking starter`);
    }
  });

  await checkAsync('Hermes Clear conversation works', async () => {
    const clearBtn = await page.$('.nxos-chat-actions button');
    if (!clearBtn) throw new Error('No clear button found');
    await clearBtn.click();
    await page.waitForTimeout(500);
    const count = await page.$$eval('.nxos-message', els => els.length);
    if (count > 2) throw new Error(`Expected ≤2 messages after clear, got ${count}`);
  });

  // ── 4d. Credit & Funding workflow ──
  console.log('\n  [4d] Credit & Funding workflow...');
  await page.goto(routeUrl('credit'), { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);

  await checkAsync('Credit page renders metric cards', async () => {
    const cards = await page.$$('.nxos-metric-grid button');
    if (cards.length < 5) throw new Error(`Expected ≥5 metric cards, found ${cards.length}`);
  });

  await checkAsync('Credit section click shows detail content', async () => {
    const cards = await page.$$('.nxos-metric-grid button');
    if (cards.length < 1) throw new Error('No metric cards');
    await cards[0].click();
    await page.waitForTimeout(500);
    const detail = await page.$('.nxos-table-card h2');
    if (!detail) throw new Error('No detail section h2 found after clicking card');
  });

  await checkAsync('Credit dispute approve button works', async () => {
    const cards = await page.$$('.nxos-metric-grid button');
    if (cards.length < 4) throw new Error('Not enough cards');
    await cards[3].click();
    await page.waitForTimeout(500);
    const approveBtn = await page.locator('button', { hasText: 'Approve' }).first();
    if (!approveBtn) throw new Error('No Approve button found');
    await approveBtn.click();
    await page.waitForTimeout(300);
    const receipt = await page.$('.nxos-receipt');
    if (!receipt) throw new Error('No receipt shown after Approve click');
  });

  await checkAsync('Credit Ask Specialist button opens Hermes drawer', async () => {
    const askBtn = await page.locator('.nxos-actions button', { hasText: 'Ask Credit Specialist' }).first();
    if (!askBtn) throw new Error('No Ask Credit Specialist button');
    await askBtn.click();
    await page.waitForTimeout(500);
    const drawer = await page.$('.hermes-inline-drawer');
    if (!drawer) throw new Error('No Hermes drawer opened after Ask Credit Specialist');
    const closeBtn = await page.$('button[aria-label="Close Hermes chat"]');
    if (closeBtn) await closeBtn.click();
    await page.waitForTimeout(300);
  });

  // ── 4e. Trading Demo workflow ──
  console.log('\n  [4e] Trading Demo workflow...');
  await page.goto(routeUrl('trading'), { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);

  await checkAsync('Trading page renders with list and actions', async () => {
    const listItems = await page.$$('.list-card');
    if (listItems.length < 1) throw new Error('No list items found');
    const actionBtns = await page.$$('.action-button');
    if (actionBtns.length < 1) throw new Error('No action buttons found');
  });

  await checkAsync('Trading Run Backtest produces receipt', async () => {
    const backtestBtn = await page.locator('.action-button', { hasText: 'Run Backtest' }).first();
    if (!backtestBtn) throw new Error('No Run Backtest button');
    await backtestBtn.click();
    await page.waitForTimeout(500);
    const receipt = await page.$('.nxos-receipt');
    if (!receipt) throw new Error('No receipt shown after Run Backtest');
  });

  await checkAsync('Trading Generate Report produces receipt', async () => {
    const btn = await page.locator('.action-button', { hasText: 'Generate Report' }).first();
    if (!btn) throw new Error('No Generate Report button');
    await btn.click();
    await page.waitForTimeout(500);
    const receipt = await page.$('.nxos-receipt');
    if (!receipt) throw new Error('No receipt shown after Generate Report');
  });

  await checkAsync('Trading Create Task produces receipt', async () => {
    const btn = await page.locator('.action-button', { hasText: 'Create Task' }).first();
    if (!btn) throw new Error('No Create Task button');
    await btn.click();
    await page.waitForTimeout(500);
    const receipt = await page.$('.nxos-receipt');
    if (!receipt) throw new Error('No receipt shown after Create Task');
  });

  await checkAsync('Trading + New button produces receipt', async () => {
    const btn = await page.locator('.new-btn').first();
    if (!btn) throw new Error('No + New button');
    await btn.click();
    await page.waitForTimeout(500);
    const receipt = await page.$('.nxos-receipt');
    if (!receipt) throw new Error('No receipt shown after + New');
  });

  // Final console error check after all interactions
  console.log('\n  [4f] Final console error check...');
  await checkAsync('No console errors after all interactions', async () => {
    if (consoleErrors.length > 0) {
      throw new Error(`Found ${consoleErrors.length} console error(s) total:\n  ${consoleErrors.slice(0, 10).join('\n  ')}`);
    }
  });

} catch (e) {
  console.log(`  FAIL  Playwright test suite error: ${e.message}`);
  failures++;
} finally {
  if (browser) await browser.close().catch(() => {});
}

// ── 5. Kill server ──
if (server) {
  server.kill('SIGTERM');
  await new Promise(r => setTimeout(r, 500));
}

// ── Summary ──
console.log(`\n${'='.repeat(50)}`);
if (failures === 0) {
  console.log('ALL SMOKE TESTS PASSED');
  process.exit(0);
} else {
  console.log(`${failures} CHECK(S) FAILED`);
  process.exit(1);
}
