/**
 * Nexus OS v2 — Client Vault contract (CONTRACT ONLY — no live connection in v1).
 *
 * Ray approved the Client Vault architecture, but the real vault is NOT connected yet:
 *  - no second live Supabase project
 *  - no real Client Vault credentials
 *  - no real client data
 *  - mock/dev adapter only
 *
 * This file defines the adapter interface + data model contract so a future backend can be wired
 * without changing callers. Pure / deterministic types. No I/O.
 */

export type ClientVaultConnectionStatus = 'not_connected_by_design' | 'mock_dev' | 'live';

/** Future backend options the contract must support (decision deferred). */
export type ClientVaultBackendKind =
  | 'separate_supabase_project'
  | 'separate_schema'
  | 'self_hosted_supabase'
  | 'plain_postgres_vault'
  | 'other_backend';

export const CLIENT_VAULT_CONNECTION_STATUS: ClientVaultConnectionStatus = 'not_connected_by_design';

export const CLIENT_VAULT_CONTRACT_META = {
  connection_status: CLIENT_VAULT_CONNECTION_STATUS,
  adapter_in_use: 'mock' as 'mock' | 'live',
  second_supabase_connected: false,
  real_credentials_present: false,
  real_client_data_present: false,
  supported_future_backends: [
    'separate_supabase_project',
    'separate_schema',
    'self_hosted_supabase',
    'plain_postgres_vault',
    'other_backend',
  ] as ClientVaultBackendKind[],
  note: 'Contract + mock adapter only. Production vault connection happens later via a manual, separately approved step.',
} as const;

// ---- Data model contract (fake/dev examples only — never real client data) ----

export interface VaultClientProfile {
  client_id: string;
  tenant_id: string;
  client_label: string; // dev label, not a real name
  current_stage: string;
}

export interface VaultClientCreditReport {
  client_id: string;
  source: 'smartcredit' | 'annualcreditreport' | 'manual_upload' | 'other';
  report_received: boolean;
  imported_at: string | null;
}

export interface VaultCreditScoreSnapshot {
  client_id: string;
  bureau: string;
  score: number | null;
  score_source: string;
  reported_at: string;
}

export interface VaultBusinessProfile {
  client_id: string;
  entity_type: string | null;
  bankability_score: number;
}

export interface VaultBusinessSetupItem {
  client_id: string;
  setup_item_key: string;
  completion_status: string;
  client_selected_path: string;
}

export interface VaultProofUpload {
  client_id: string;
  proof_type: string;
  file_ref: string; // opaque ref, never a real file
  uploaded_at: string;
}

export interface VaultLetterPacket {
  client_id: string;
  letter_type: string;
  approval_status: string;
}

export interface VaultMailingRecord {
  client_id: string;
  mailing_method: string;
  mailing_status: string;
}

export interface VaultWorkflowTask {
  client_id: string;
  task_key: string;
  status: string;
}

export interface VaultReminderTask {
  client_id: string;
  task_key: string;
  reminder_status: string;
  days_stuck: number;
}

export interface VaultFundingReadinessSummary {
  client_id: string;
  funding_readiness_score: number;
  blockers: string[];
}

export interface VaultAffiliateAttributionEvent {
  client_id: string;
  category: string;
  conversion_status: string;
}

export interface VaultConsentEvent {
  client_id: string;
  consent_type: string;
  accepted: boolean;
  recorded_at: string;
}

export interface VaultAuditEvent {
  event_id: string;
  tenant_id: string;
  client_id: string;
  actor_type: string;
  actor_id: string;
  agent_role: string;
  access_type: string;
  data_category: string;
  reason: string;
  allowed: boolean;
  denied_reason: string | null;
  created_at: string;
}

/** Sanitized signal export — the ONLY shape that may leave the vault toward Hermes. */
export interface VaultSanitizedSignalExport {
  total_clients_by_stage: Record<string, number>;
  stuck_clients_count: number;
  ray_review_needed_count: number;
  revenue_risk_count: number;
  recommended_next_actions: string[];
}

/** The adapter every caller uses. Mock implementation only in v1. */
export interface ClientVaultAdapter {
  connectionStatus(): ClientVaultConnectionStatus;
  isMock(): boolean;
  listClientProfiles(): Promise<VaultClientProfile[]>;
  getCreditReport(clientId: string): Promise<VaultClientCreditReport | null>;
  getCreditScoreSnapshots(clientId: string): Promise<VaultCreditScoreSnapshot[]>;
  getBusinessProfile(clientId: string): Promise<VaultBusinessProfile | null>;
  listBusinessSetupItems(clientId: string): Promise<VaultBusinessSetupItem[]>;
  listProofUploads(clientId: string): Promise<VaultProofUpload[]>;
  listLetterPackets(clientId: string): Promise<VaultLetterPacket[]>;
  listMailingRecords(clientId: string): Promise<VaultMailingRecord[]>;
  listWorkflowTasks(clientId: string): Promise<VaultWorkflowTask[]>;
  listReminderTasks(clientId: string): Promise<VaultReminderTask[]>;
  getFundingReadiness(clientId: string): Promise<VaultFundingReadinessSummary | null>;
  listAffiliateAttribution(clientId: string): Promise<VaultAffiliateAttributionEvent[]>;
  listConsentEvents(clientId: string): Promise<VaultConsentEvent[]>;
  /** Sanitized export is the only path toward Hermes. */
  exportSanitizedSignals(): Promise<VaultSanitizedSignalExport>;
  /** Append-only audit (mock events only in v1). */
  recordAuditEvent(event: VaultAuditEvent): Promise<void>;
}
