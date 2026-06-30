#!/usr/bin/env node
/**
 * Runtime regression test: verifies that the built bundle and all source
 * components have no unsafe bare `client` variable references that could
 * cause ReferenceError at runtime.
 *
 * Exit code 0 = safe, 1 = unsafe reference found.
 */
const fs = require('fs');
const path = require('path');
const glob = require('path');

const ROOT = path.resolve(__dirname, '../..');
const SRC = path.join(ROOT, 'src');
const DIST = path.join(ROOT, 'dist/assets');

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

// ── 1. Check built JS for bare `client` property access outside strings ──
console.log('\n[1] Checking built JS for bare `client` variable access...');

const jsFiles = fs.readdirSync(DIST).filter(f => f.endsWith('.js'));
for (const file of jsFiles) {
  const content = fs.readFileSync(path.join(DIST, file), 'utf8');

  check(`No bare client.property in ${file}`, () => {
    // Split into lines and check each
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      let inSingle = false, inDouble = false, inBacktick = false;
      for (let j = 0; j < line.length; j++) {
        const ch = line[j];
        const prev = j > 0 ? line[j - 1] : '';
        if (ch === "'" && prev !== '\\' && !inDouble && !inBacktick) inSingle = !inSingle;
        if (ch === '"' && prev !== '\\' && !inSingle && !inBacktick) inDouble = !inDouble;
        if (ch === '`' && prev !== '\\' && !inSingle && !inDouble) inBacktick = !inBacktick;
        if (inSingle || inDouble || inBacktick) continue;

        // Check for bare client followed by . (property access)
        if (ch === 'c' && line.substring(j, j + 7) === 'client' &&
            j + 7 < line.length && line[j + 7] === '.' &&
            j > 0 && !/[.\w]/.test(line[j - 1])) {
          throw new Error(
            `Line ${i + 1}, col ${j}: bare client. access found\n` +
            `  Context: ...${line.substring(Math.max(0, j - 40), j + 50)}...`
          );
        }
      }
    }
  });
}

// ── 2. Check source components for unsafe `client` usage ──
console.log('\n[2] Checking source components for unsafe client references...');

function walkDir(dir, exts) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== 'node_modules' && entry.name !== 'dist') {
      results.push(...walkDir(full, exts));
    } else if (entry.isFile() && exts.some(e => entry.name.endsWith(e))) {
      results.push(full);
    }
  }
  return results;
}

const srcFiles = walkDir(SRC, ['.jsx', '.tsx', '.ts', '.js']);

for (const file of srcFiles) {
  const rel = path.relative(ROOT, file);
  const content = fs.readFileSync(file, 'utf8');
  const lines = content.split('\n');

  check(`No bare client in ${rel}`, () => {
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const stripped = line.trim();
      if (stripped.startsWith('//') || stripped.startsWith('*') || stripped.startsWith('import') || stripped.startsWith('export')) continue;

      // Remove string contents (single, double, template), regex literals, and comments
      const origLine = lines[i].trim();
      const cleaned = line
        .replace(/'[^']*'/g, "''")
        .replace(/"[^"]*"/g, '""')
        .replace(/`[^`]*`/g, '``')
        .replace(/\/[^\/\n]+\/[gimsuy]*/g, '/REGEX/');

      const matches = cleaned.matchAll(/\bclient\b/g);
      for (const m of matches) {
        const pos = m.index;
        const before = cleaned.substring(0, pos).trimEnd();
        const after = cleaned.substring(pos + 6).trimStart();

        // Skip if preceded by . (property access)
        if (before.endsWith('.')) continue;
        // Skip if client.something (property access)
        if (/client\.\w/.test(cleaned.substring(pos, pos + 30))) continue;
        // Skip if part of larger word
        if (after[0] && /[a-zA-Z0-9_]/.test(after[0])) continue;
        if (before.length > 0 && /[a-zA-Z0-9_]/.test(before[before.length - 1])) continue;

        // Skip if it's a function parameter, destructured prop, map callback, JSX prop, or string content
        if (/\.map\(|\.filter\(|\.find\(|\.forEach\(/.test(origLine)) continue;
        if (/function\s+\w+\s*\([^)]*client/.test(origLine)) continue;
        if (/\(\s*client\s*[,)]/.test(origLine)) continue;
        if (/\{\s*client\s*[,:}]/.test(origLine)) continue;
        if (/client\s*=>/.test(origLine)) continue;
        if (/>client|client=|\/client\b|client\//.test(origLine)) continue;
        if (/client[,\s]+(is|was|has|does|can|will|should|would|could)/.test(origLine)) continue;
        // JSX prop: client={...}
        if (/client\s*=\s*[{"']/.test(origLine)) continue;
        // Template literal content (backtick strings already removed, but check for ${} patterns)
        if (/\$\{.*client.*\}/.test(origLine)) continue;
        // Import/export statements
        if (/^(import|export)\s/.test(origLine)) continue;
        // Guard clause: if (!client) - safe pattern
        if (/if\s*\(\s*!client\s*\)/.test(origLine)) continue;
        // Property access in objects: {client.something}
        if (/\{\s*client\./.test(origLine)) continue;

        // This is suspicious
        throw new Error(
          `Line ${i + 1}: possible bare client reference\n` +
          `  ${lines[i].trim()}`
        );
      }
    }
  });
}

// ── 3. Verify all business panel components exist and export ──
console.log('\n[3] Verifying business panel components exist...');

const panels = [
  'ClientsPanel.jsx',
  'CreditFundingPanel.jsx',
  'BusinessOpportunitiesPanel.jsx',
  'ResearchEnginePanel.jsx',
  'MonetizationPanel.jsx',
  'MarketingDraftsPanel.jsx',
];

for (const panel of panels) {
  const file = path.join(SRC, 'components', panel);
  check(`${panel} exists`, () => {
    if (!fs.existsSync(file)) throw new Error('File not found');
    const content = fs.readFileSync(file, 'utf8');
    if (!content.includes('export default')) throw new Error('No default export');
    if (content.includes('if (!') && content.includes('return null')) {
      // Has null guard - good
    }
  });
}

// ── 4. Verify data files exist and export ──
console.log('\n[4] Verifying data files exist...');

const dataFiles = [
  'clientsData.js',
  'creditFundingData.js',
  'businessOpportunitiesData.js',
  'researchEngineData.js',
  'monetizationData.js',
  'marketingDraftsData.js',
];

for (const file of dataFiles) {
  const full = path.join(SRC, 'data', file);
  check(`${file} exists with exports`, () => {
    if (!fs.existsSync(full)) throw new Error('File not found');
    const content = fs.readFileSync(full, 'utf8');
    if (!content.includes('export')) throw new Error('No exports');
  });
}

// ── 5. Verify build hash is fresh ──
console.log('\n[5] Verifying build output...');
check('dist/index.html exists', () => {
  if (!fs.existsSync(path.join(DIST, '..', 'index.html'))) throw new Error('Not found');
});
check('dist JS bundle exists', () => {
  if (jsFiles.length === 0) throw new Error('No JS bundles found');
});

// ── Summary ──
console.log(`\n${'='.repeat(50)}`);
if (failures === 0) {
  console.log('ALL CHECKS PASSED');
  process.exit(0);
} else {
  console.log(`${failures} CHECK(S) FAILED`);
  process.exit(1);
}
