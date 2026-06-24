/**
 * Hermes data firewall — single source of truth for sensitivity labels and access rules.
 *
 * Hermes (Conversation + Report Reader) may ONLY ever read `public` and `internal_summary`.
 * Everything more sensitive is handled exclusively by private/internal (non-internet) workers,
 * which return redacted status/summaries. Hermes must never read it or send it to a public
 * provider/search. This module is pure (no I/O) so it can guard both the UI and any caller.
 */

export type Sensitivity =
  | 'public'
  | 'internal_summary'
  | 'customer_private'
  | 'credit_sensitive'
  | 'funding_sensitive'
  | 'auth_sensitive'
  | 'secrets'
  | 'trading_sensitive';

/** The ONLY scopes Hermes may read directly. */
export const HERMES_VISIBLE: readonly Sensitivity[] = ['public', 'internal_summary'];

export function hermesCanRead(s: Sensitivity): boolean {
  return HERMES_VISIBLE.includes(s);
}

/**
 * Patterns for data Hermes must never read or forward to a public provider/search.
 * Order does not matter; the first match is returned for labelling.
 */
const SENSITIVE_PATTERNS: { re: RegExp; label: Sensitivity }[] = [
  { re: /\bssn\b|social security (number|#|no\b)/i, label: 'customer_private' },
  { re: /credit report|full credit (file|report)|fico (file|report|details)/i, label: 'credit_sensitive' },
  { re: /bank statement|account number|routing number|bank balance/i, label: 'customer_private' },
  { re: /tax (return|document|transcript)|w-?2\b|1099\b/i, label: 'customer_private' },
  { re: /funding (document|packet|application file)|loan documents/i, label: 'funding_sensitive' },
  { re: /\bpassword\b|reset token|one[- ]time (code|password)|\botp\b|2fa code/i, label: 'auth_sensitive' },
  { re: /service[- ]?role( key)?|service_role|secret key|api[_ ]?key|private key|access token|bearer token/i, label: 'secrets' },
  { re: /open positions|live (trade|position) details|brokerage balance/i, label: 'trading_sensitive' },
];

/** Returns the sensitivity label if `text` references private data, else null. */
export function containsSensitive(text: string): Sensitivity | null {
  const t = text || '';
  for (const p of SENSITIVE_PATTERNS) if (p.re.test(t)) return p.label;
  return null;
}
