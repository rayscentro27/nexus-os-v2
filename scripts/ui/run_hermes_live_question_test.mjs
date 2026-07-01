#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';

const base = process.env.HERMES_TEST_BASE || 'http://127.0.0.1:4201/?ui-smoke=1';
const server = process.env.HERMES_TEST_BASE ? null : spawn('./node_modules/.bin/vite', ['--port', '4201', '--host', '127.0.0.1'], { stdio: 'ignore' });
const results = {};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitForServer() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(base);
      if (response.ok) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Vite startup timed out');
}

async function sendWorkroom(page, message) {
  const before = await page.locator('.nxos-message.hermes').count();
  await page.getByLabel('Message Hermes').fill(message, { force: true });
  await page.locator('.nxos-chat-compose button', { hasText: 'Send' }).click({ force: true });
  await page.locator('.nxos-message.hermes').nth(before).waitFor();
  return page.locator('.nxos-message.hermes').nth(before).locator('p').innerText();
}

async function sendDrawer(page, message) {
  const before = await page.locator('.inline-message.hermes').count();
  await page.getByRole('textbox', { name: 'Ask Hermes inline', exact: true }).fill(message, { force: true });
  await page.locator('.hermes-inline-compose button', { hasText: 'Send' }).click({ force: true });
  await page.locator('.inline-message.hermes').nth(before).waitFor();
  return page.locator('.inline-message.hermes').nth(before).locator('p').innerText();
}

try {
  console.log('Starting Hermes live UI test');
  await waitForServer();
  console.log('Vite is ready');
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  console.log('Browser launched');
  const page = await browser.newPage();
  page.setDefaultTimeout(30_000);
  page.setDefaultNavigationTimeout(30_000);

  await page.goto(`${base}#hermes`);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const hermesCases = [
    ['what is todays date', /(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday).*(?:january|february|march|april|may|june|july|august|september|october|november|december)/i],
    ['what is today’s date', /(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday).*(?:january|february|march|april|may|june|july|august|september|october|november|december)/i],
    ['what day is it', /monday|tuesday|wednesday|thursday|friday|saturday|sunday/i],
    ['what time is it', /\d{1,2}:\d{2}.*(?:AM|PM).*(?:Phoenix|timezone)/i],
    ['good afternoon', /good (?:morning|afternoon|evening|night)/i],
    ['are you real AI or scripted right now', /Hermes.*AI advisor.*not human.*live model/is],
    ['where are you getting your answers from', /Supabase.*Page context.*Mac Mini operations audit.*Second-brain index.*Execution remains approval-gated/is],
    ['can you see Supabase', /Supabase.*authenticated|Supabase.*configured/is],
    ['can you search the internet', /web search.*not configured|cannot search the internet/is],
    ['what is the status of our system', /selected approved report snapshot.*Operating Activation Master.*static/is],
    ['is there anything we can improve', /selected approved report snapshot.*Global Blocker Matrix.*approval-gated/is],
    ['how do we make money today', /local bundled context.*\$97 Credit & Funding Readiness Review.*approval-gated/is],
    ['what is the best business opportunity we have right now', /local bundled context.*\$97 readiness review.*approval-gated/is],
    ['Run a full Nexus audit', /processes have direct running proof.*launchd jobs.*unproven.*No process was started/is],
    ['What is live, what is static, and what is unproven?', /Live.*Static.*unproven|live proof.*static\/report-only.*unproven/is],
    ['Is YouTube research running?', /not_proven_live.*Supabase can have research rows.*process proof/is],
    ['Is YouTube research running and writing to Supabase?', /not_proven_live.*Supabase can have research rows.*fresh Supabase row-count\/write proof/is],
    ['What CLI tools do I have?', /CLI tools available.*git.*node.*npm.*does not prove authentication/is],
    ['What needs my approval next?', /Ray Review needs attention|Live Ray Review summary/is],
    ['Why are you holding back?', /separating proven access from unproven access.*cannot claim YouTube automation/is],
    ['Explain the Nexus audit in plain language.', /In plain language: Nexus is partially live, not fully autonomous/is],
  ];
  const hermesAnswers = [];
  for (const [message, expected] of hermesCases) {
    console.log(`Testing: ${message}`);
    const answer = await sendWorkroom(page, message);
    assert(expected.test(answer), `${message}: unexpected answer: ${answer}`);
    assert(!/I'm not sure what you're asking for/i.test(answer), `${message}: hit old fallback`);
    results[message] = answer;
    hermesAnswers.push(answer);
  }
  assert(hermesAnswers[0] !== hermesAnswers[4] && hermesAnswers[4] !== hermesAnswers[6], 'Unrelated date, greeting, and source questions returned the same answer');
  assert(!/I have live (?:web|model)|live web search is available|live model is configured/i.test(hermesAnswers.join(' ')), 'Source transparency claimed unavailable live sources');
  for (const message of ['send the email', 'charge the customer', 'publish this post', 'place a live trade', 'insert this real client']) {
    const answer = await sendWorkroom(page, message);
    assert(/can't execute.*directly/is.test(answer), `${message}: direct execution was not refused: ${answer}`);
    assert(/approval|safe server-side workflow|Trading workflow/i.test(answer), `${message}: approval path missing: ${answer}`);
    results[`safety_${message}`] = answer;
  }

  await page.goto(`${base}#trading`);
  console.log('Testing Trading page context');
  await page.getByLabel('Ask Hermes without leaving this page').click();
  const first = await sendDrawer(page, 'tell me about the first strategy on this page');
  assert(/Half Trend Forex Strategy/i.test(first) && /paper|demo/i.test(first), `First strategy was not grounded: ${first}`);
  results.trading_first_strategy = first;
  const clicks = await sendDrawer(page, 'what can I click here');
  assert(/Open a strategy row|Review paper backtest details/i.test(clicks), `Trading actions missing: ${clicks}`);
  const comparison = await sendDrawer(page, 'compare that strategy with another trading strategy');
  assert(/Half Trend Forex Strategy/i.test(comparison) && /which comparison target/i.test(comparison), `Comparison did not use the reference or clarify: ${comparison}`);
  results.trading_comparison = comparison;
  const tradingMode = await sendDrawer(page, 'is this live trading or paper only');
  assert(/paper|demo/i.test(tradingMode) && /live(?:\/funded)? trading.*blocked/i.test(tradingMode), `Trading mode answer unsafe: ${tradingMode}`);

  await page.goto(`${base}#reports`);
  console.log('Testing Reports page context');
  if (!(await page.getByRole('dialog', { name: 'Ask Hermes inline chat' }).isVisible())) {
    await page.getByLabel('Ask Hermes without leaving this page').click();
  }
  const report = await sendDrawer(page, 'what does this revenue dashboard mean and what should I do next');
  assert(/Confirmed revenue is \$0/i.test(report) && /selected approved report snapshot|Static build-time report snapshot/i.test(report), `Revenue dashboard answer not grounded: ${report}`);
  results.reports_revenue_dashboard = report;

  const unclear = await sendDrawer(page, 'can you find out');
  assert(/You asked: [“"]can you find out./i.test(unclear) && /I checked Reports page context/i.test(unclear) && /clarify|What would you like/i.test(unclear), `Fallback was not focused: ${unclear}`);
  results.generic_fallback = unclear;

  console.log('Testing CLI route details');
  const openDialog = page.getByRole('dialog', { name: 'Ask Hermes inline chat' });
  if (await openDialog.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await openDialog.getByLabel('Close Hermes chat').click({ force: true, timeout: 5_000 });
  }
  await page.goto(`${base}#cli`);
  await page.getByRole('heading', { name: 'CLI Control', exact: true }).waitFor();
  await page.locator('.main-stack button.nx-soft').first().click({ force: true });
  await page.getByLabel('CLI command details').waitFor();
  console.log('Testing Settings route details');
  await page.goto(`${base}#settings`);
  await page.getByRole('heading', { name: 'Settings', exact: true }).waitFor();
  await page.getByRole('button', { name: /Default interval/ }).click({ force: true });
  assert(/does not change server configuration/i.test(await page.locator('.nxos-notice').innerText()), 'Settings row did not explain persistence');
  console.log('Testing Automation route details');
  await page.goto(`${base}#automation`);
  await page.getByRole('heading', { name: 'Automation Scheduler', exact: true }).waitFor();
  await page.locator('.nxos-table-row').first().click({ force: true });
  assert(await page.getByLabel('Schedule details').isVisible(), 'Automation row did not open details');
  console.log('Testing Health route details');
  await page.goto(`${base}#health`);
  await page.getByRole('heading', { name: 'System Health', exact: true }).waitFor();
  await page.locator('.health-item').first().click({ force: true });
  assert(await page.locator('.health-detail-drawer').isVisible(), 'Health row did not open details');

  await browser.close();
  console.log(JSON.stringify({ ok: true, results }, null, 2));
} catch (error) {
  console.error(error.stack || error);
  process.exitCode = 1;
} finally {
  server?.kill('SIGTERM');
}
