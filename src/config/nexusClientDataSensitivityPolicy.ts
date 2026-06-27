/**
 * Nexus OS v2 — Client data sensitivity policy.
 *
 * Classifies every data category an AI agent might touch, and what may leave the building.
 * Pure / deterministic. No I/O. This is the vocabulary the AI access policy enforces.
 */

export type ClientDataCategory =
  // sanitized / aggregate (safe for Hermes)
  | 'sanitized_signal'
  | 'aggregate_metric'
  | 'stage_count'
  | 'workflow_status_internal'
  // identifying / private (NOT for Hermes; vault-only via adapter)
  | 'client_name'
  | 'client_contact'
  | 'address'
  | 'dob'
  | 'ssn'
  | 'account_number'
  | 'creditor_account_detail'
  | 'bank_statement'
  | 'raw_credit_report'
  | 'smartcredit_file'
  | 'credit_score_raw'
  | 'raw_letter'
  | 'funding_document'
  | 'client_consent_record'
  // client-scoped business / workflow records (vault-only via adapter)
  | 'business_profile'
  | 'business_setup_item'
  | 'workflow_task'
  | 'reminder_task'
  | 'funding_readiness'
  | 'proof_upload'
  | 'mailing_record'
  | 'affiliate_attribution';

export type DataSensitivity =
  | 'public'
  | 'internal_summary'
  | 'sanitized_aggregate'
  | 'client_private'
  | 'credit_sensitive'
  | 'funding_sensitive'
  | 'auth_sensitive';

export interface DataCategoryDef {
  category: ClientDataCategory;
  sensitivity: DataSensitivity;
  hermes_allowed: boolean;
  internet_tool_allowed: boolean; // may an internet-enabled tool ever see this? (always false for private)
  vault_only: boolean; // only reachable through the Client Vault adapter
}

function def(
  category: ClientDataCategory,
  sensitivity: DataSensitivity,
  hermes_allowed: boolean,
  internet_tool_allowed: boolean,
  vault_only: boolean,
): DataCategoryDef {
  return { category, sensitivity, hermes_allowed, internet_tool_allowed, vault_only };
}

export const CLIENT_DATA_CATEGORIES: DataCategoryDef[] = [
  def('sanitized_signal', 'sanitized_aggregate', true, false, false),
  def('aggregate_metric', 'sanitized_aggregate', true, false, false),
  def('stage_count', 'sanitized_aggregate', true, false, false),
  def('workflow_status_internal', 'internal_summary', true, false, false),
  def('client_name', 'client_private', false, false, true),
  def('client_contact', 'client_private', false, false, true),
  def('address', 'client_private', false, false, true),
  def('dob', 'auth_sensitive', false, false, true),
  def('ssn', 'auth_sensitive', false, false, true),
  def('account_number', 'auth_sensitive', false, false, true),
  def('creditor_account_detail', 'credit_sensitive', false, false, true),
  def('bank_statement', 'funding_sensitive', false, false, true),
  def('raw_credit_report', 'credit_sensitive', false, false, true),
  def('smartcredit_file', 'credit_sensitive', false, false, true),
  def('credit_score_raw', 'credit_sensitive', false, false, true),
  def('raw_letter', 'credit_sensitive', false, false, true),
  def('funding_document', 'funding_sensitive', false, false, true),
  def('client_consent_record', 'client_private', false, false, true),
  def('business_profile', 'client_private', false, false, true),
  def('business_setup_item', 'client_private', false, false, true),
  def('workflow_task', 'client_private', false, false, true),
  def('reminder_task', 'client_private', false, false, true),
  def('funding_readiness', 'funding_sensitive', false, false, true),
  def('proof_upload', 'client_private', false, false, true),
  def('mailing_record', 'client_private', false, false, true),
  def('affiliate_attribution', 'client_private', false, false, true),
];

const BY_CATEGORY = new Map(CLIENT_DATA_CATEGORIES.map((d) => [d.category, d]));

export function getDataCategory(category: ClientDataCategory): DataCategoryDef | undefined {
  return BY_CATEGORY.get(category);
}

/** Categories Hermes may read. */
export const HERMES_ALLOWED_CATEGORIES: ClientDataCategory[] = CLIENT_DATA_CATEGORIES.filter((d) => d.hermes_allowed).map((d) => d.category);

/** Categories that are vault-only private client data (never for Hermes / internet tools). */
export const PRIVATE_VAULT_CATEGORIES: ClientDataCategory[] = CLIENT_DATA_CATEGORIES.filter((d) => d.vault_only).map((d) => d.category);

export function isPrivateClientData(category: ClientDataCategory): boolean {
  return !!BY_CATEGORY.get(category)?.vault_only;
}

export function isHermesSafe(category: ClientDataCategory): boolean {
  return !!BY_CATEGORY.get(category)?.hermes_allowed;
}
