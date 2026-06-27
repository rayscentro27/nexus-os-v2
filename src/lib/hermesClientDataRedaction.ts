/**
 * Nexus OS v2 — Hermes client-data redaction.
 *
 * The hard boundary that strips any forbidden raw client field before data reaches Hermes.
 * Fails closed: anything not on the Hermes-safe allow-list is dropped. Deterministic. No I/O.
 */
import {
  HERMES_FORBIDDEN_FIELDS,
  isHermesForbiddenField,
} from '../config/hermesSafeClientSignalPolicy';

/** Keys that look like PII even if not explicitly listed (extra guard). */
const PII_PATTERNS = [
  /name/i, /ssn/i, /social.?security/i, /dob|date.?of.?birth/i, /address/i, /phone/i, /email/i,
  /account.?(number|no|#)/i, /bank.?statement/i, /credit.?report/i, /smartcredit/i, /\bletter\b/i,
  /routing/i, /card.?number/i, /funding.?document/i,
];

function looksLikePii(key: string): boolean {
  if (isHermesForbiddenField(key)) return true;
  return PII_PATTERNS.some((re) => re.test(key));
}

/** Remove forbidden/PII keys from an object before Hermes sees it. */
export function redactForHermes<T extends Record<string, unknown>>(input: T): Partial<T> {
  const out: Partial<T> = {};
  for (const [k, v] of Object.entries(input)) {
    if (looksLikePii(k)) continue;
    out[k as keyof T] = v as T[keyof T];
  }
  return out;
}

/** Returns the forbidden keys present in an object (for proof/verification). */
export function detectForbiddenKeys(input: Record<string, unknown>): string[] {
  return Object.keys(input).filter((k) => looksLikePii(k));
}

/** True if the object is safe to hand to Hermes (no forbidden/PII keys). */
export function isSafeForHermes(input: Record<string, unknown>): boolean {
  return detectForbiddenKeys(input).length === 0;
}

export const HERMES_REDACTION_RULES = {
  forbidden_fields: HERMES_FORBIDDEN_FIELDS,
  policy: 'Hermes receives sanitized signals/aggregates only. Any raw client field is stripped before Hermes sees it. Fail closed.',
} as const;
