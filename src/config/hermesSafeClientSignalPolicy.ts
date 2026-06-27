/**
 * Nexus OS v2 — Hermes-safe client signal policy.
 *
 * The allow-list of sanitized, aggregate signals Hermes may read, and the deny-list of raw fields
 * Hermes must never see. Pure / deterministic. No I/O.
 */

/** Aggregate signal keys Hermes may read. */
export const HERMES_SAFE_SIGNAL_KEYS = [
  'total_clients_by_stage',
  'stuck_clients_count',
  'credit_reports_pending_count',
  'smartcredit_selected_count',
  'annualcreditreport_selected_count',
  'no_score_available_count',
  'business_setup_incomplete_count',
  'letters_ready_count',
  'mailing_pending_count',
  'mailing_proof_missing_count',
  'funding_ready_count',
  'ray_review_needed_count',
  'affiliate_opportunity_count',
  'revenue_risk_count',
  'estimated_commission_delayed',
  'recommended_next_actions',
] as const;

export type HermesSafeSignalKey = (typeof HERMES_SAFE_SIGNAL_KEYS)[number];

/** Raw fields Hermes must NEVER receive. */
export const HERMES_FORBIDDEN_FIELDS = [
  'full_client_name',
  'full_credit_report',
  'smartcredit_file',
  'smartcredit_import',
  'ssn',
  'dob',
  'address',
  'account_number',
  'creditor_account_detail',
  'bank_statement',
  'raw_letter',
  'private_funding_document',
] as const;

export type HermesForbiddenField = (typeof HERMES_FORBIDDEN_FIELDS)[number];

const FORBIDDEN = new Set<string>(HERMES_FORBIDDEN_FIELDS);
const SAFE = new Set<string>(HERMES_SAFE_SIGNAL_KEYS);

export function isHermesSafeSignalKey(key: string): boolean {
  return SAFE.has(key);
}

export function isHermesForbiddenField(key: string): boolean {
  return FORBIDDEN.has(key);
}

/** Example Hermes-safe signals (illustrative, no PII). */
export const HERMES_SAFE_SIGNAL_EXAMPLES = [
  '4 clients are stuck at credit report upload.',
  '2 clients selected AnnualCreditReport.com and have no score.',
  '5 clients are missing business bank accounts.',
  '3 clients have letters ready but no mailing proof.',
  '1 client is nearly funding-ready but has high utilization.',
  'Estimated commission opportunity delayed: $X.',
] as const;
