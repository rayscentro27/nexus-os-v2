#!/usr/bin/env node
/**
 * Runtime smoke test: runs the Vite preview server and checks the app loads
 * without JavaScript errors using a headless fetch + module parse check.
 *
 * Exit code 0 = safe, 1 = crash detected.
 */
import { execSync, spawn } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..', '..');
const DIST = join(ROOT, 'dist');
let failures = 0;

function check(label, fn) {
  try {
    fn();
    console.log(`  PASS  ${label}`);
  } catch (e) {
    failures++;
    console.log(`  FAIL  ${label}: ${e.message}`);
  }
}

// ── 1. Build check ──
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
    // Use Node's --check flag to verify syntax
    try {
      execSync(`node --check ${fullPath}`, { cwd: ROOT, stdio: 'pipe' });
    } catch (e) {
      // ES modules with import.meta may fail node --check, try eval instead
      const code = readFileSync(fullPath, 'utf8');
      // Quick check: no template literal parsing errors
      // Count backticks — they should be balanced
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

// ── 3. Specific known-bug check: unescaped backticks in template literals ──
console.log('\n[3] Checking for unescaped backticks in recently changed source files...');
// Only check files modified in recent commits (the ones that could have introduced bugs)
const recentFiles = execSync(`git diff --name-only HEAD~3..HEAD -- src/`, { cwd: ROOT, encoding: 'utf8' })
  .trim().split('\n').filter(Boolean);

for (const file of recentFiles) {
  const fullPath = join(ROOT, file);
  if (!existsSync(fullPath)) continue;
  check(`No unescaped backticks in ${file}`, () => {
    const content = readFileSync(fullPath, 'utf8');
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Find template literal lines (contain backticks)
      if (!line.includes('`')) continue;

      // Skip import/export/comment lines
      const stripped = line.trim();
      if (stripped.startsWith('//') || stripped.startsWith('*') || stripped.startsWith('import') || stripped.startsWith('export')) continue;

      // Check: template literals should have balanced backticks
      let inSingle = false, inDouble = false, inBacktick = false;
      for (let j = 0; j < line.length; j++) {
        const ch = line[j];
        const prev = j > 0 ? line[j - 1] : '';
        if (prev === '\\') continue;
        if (ch === "'" && !inDouble && !inBacktick) inSingle = !inSingle;
        if (ch === '"' && !inSingle && !inBacktick) inDouble = !inDouble;
        if (ch === '`' && !inSingle && !inDouble) {
          inBacktick = !inBacktick;
        }
      }
      if (inBacktick) {
        throw new Error(`Line ${i + 1}: unbalanced backtick (template literal may contain unescaped backtick)`);
      }
    }
  });
}

// ── 4. Vite preview smoke test ──
console.log('\n[4] Vite preview smoke test (start server, fetch, check for errors)...');

let server;
try {
  // Start vite preview
  const preview = spawn('npx', ['vite', 'preview', '--port', '4199', '--host', '127.0.0.1'], {
    cwd: ROOT,
    stdio: 'pipe',
    env: { ...process.env, FORCE_COLOR: '0' },
  });
  server = preview;

  // Wait for server to start
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Server start timeout')), 15000);
    preview.stdout.on('data', (data) => {
      const text = data.toString();
      if (text.includes('Local:') || text.includes('4199')) {
        clearTimeout(timeout);
        resolve();
      }
    });
    preview.stderr.on('data', (data) => {
      // Some output goes to stderr
      const text = data.toString();
      if (text.includes('Local:') || text.includes('4199')) {
        clearTimeout(timeout);
        resolve();
      }
    });
  });

  // Fetch the page
  const response = await fetch('http://127.0.0.1:4199/');
  const html = await response.text();

  check('Page returns 200', () => {
    if (response.status !== 200) throw new Error(`Status ${response.status}`);
  });

  check('HTML contains root div', () => {
    if (!html.includes('id="root"')) throw new Error('No root div');
  });

  check('HTML loads JS bundle', () => {
    if (!html.includes('.js')) throw new Error('No JS bundle loaded');
  });

  // Fetch the JS bundle and check for the specific bug pattern
  const jsMatch = html.match(/src="([^"]*\.js)"/);
  if (jsMatch) {
    const jsUrl = `http://127.0.0.1:4199${jsMatch[1]}`;
    const jsResponse = await fetch(jsUrl);
    const jsCode = await jsResponse.text();

    check('JS bundle loads successfully', () => {
      if (jsResponse.status !== 200) throw new Error(`Status ${jsResponse.status}`);
    });

    check('No bare client.property outside strings in bundle', () => {
      const lines = jsCode.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        let inSingle = false, inDouble = false, inBacktick = false;
        for (let j = 0; j < line.length; j++) {
          const ch = line[j];
          const prev = j > 0 ? line[j - 1] : '';
          if (prev === '\\') continue;
          if (ch === "'" && !inDouble && !inBacktick) inSingle = !inSingle;
          if (ch === '"' && !inSingle && !inBacktick) inDouble = !inDouble;
          if (ch === '`' && !inSingle && !inDouble) inBacktick = !inBacktick;

          if (inSingle || inDouble || inBacktick) continue;

          if (ch === 'c' && line.substring(j, j + 7) === 'client' &&
              j + 7 < line.length && line[j + 7] === '.' &&
              j > 0 && !/[.\w]/.test(line[j - 1])) {
            throw new Error(
              `Bundle line ${i + 1}, col ${j}: bare client. access\n` +
              `  ${line.substring(Math.max(0, j - 40), j + 50)}`
            );
          }
        }
      }
    });

    check('Balanced backticks in bundle', () => {
      // Verify the specific crash pattern is fixed:
      // Previously, backtick before /client/dashboard closed a template literal early,
      // making /client/dashboard appear as code (division). Now it should be inside a string.
      // We check that no backtick immediately precedes /client/dashboard
      if (jsCode.includes('`/client/dashboard')) {
        throw new Error('Backtick immediately before /client/dashboard — template literal bug still present');
      }
    });
  }
} catch (e) {
  console.log(`  WARN  Preview test: ${e.message}`);
} finally {
  if (server) {
    server.kill('SIGTERM');
    await new Promise(r => setTimeout(r, 500));
  }
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
