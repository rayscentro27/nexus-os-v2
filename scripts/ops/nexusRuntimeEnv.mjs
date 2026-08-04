import fs from 'node:fs';

export const CANONICAL_RUNTIME_ENV = '/Users/raymonddavis/.config/nexus/runtime.env';

export const ALIASES = {
  NEXUS_TELEGRAM_BOT_TOKEN: 'TELEGRAM_BOT_TOKEN',
  OANDA_API_KEY: 'OANDA_API_TOKEN',
  RESEND_FROM: 'RESEND_FROM_EMAIL',
  EMAIL_FROM: 'RESEND_FROM_EMAIL',
  SUPABASE_ANON_KEY: 'VITE_SUPABASE_ANON_KEY',
  META_ACCESS_TOKEN: 'META_PAGE_ACCESS_TOKEN',
};

function unquote(value) {
  const trimmed = String(value || '').trim();
  if ((trimmed.startsWith("'") && trimmed.endsWith("'")) || (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

export function readEnvFile(file = CANONICAL_RUNTIME_ENV) {
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const [key, ...rest] = line.split('=');
    out[key.trim().replace(/^export\s+/, '')] = unquote(rest.join('='));
  }
  return out;
}

export function applyAliases(values) {
  const merged = { ...values };
  for (const [alias, canonical] of Object.entries(ALIASES)) {
    if (!merged[canonical] && merged[alias]) merged[canonical] = merged[alias];
  }
  return merged;
}

export function loadRuntimeEnv({ override = false } = {}) {
  const values = applyAliases(readEnvFile(CANONICAL_RUNTIME_ENV));
  for (const [key, value] of Object.entries(values)) {
    if (override || !process.env[key]) process.env[key] = value;
  }
  return values;
}

export function presenceReport(required) {
  const values = loadRuntimeEnv();
  return required.map((variable) => ({ variable, configured: Boolean(values[variable] || process.env[variable]) }));
}
