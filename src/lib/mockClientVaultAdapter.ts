/**
 * Nexus OS v2 — Mock Client Vault adapter (dev/fake data only).
 *
 * Implements ClientVaultAdapter with deterministic FAKE data. No real client data, no network, no
 * second Supabase. This is the only adapter available in v1.
 */
import type {
  ClientVaultAdapter,
  ClientVaultConnectionStatus,
  VaultClientProfile,
  VaultClientCreditReport,
  VaultCreditScoreSnapshot,
  VaultBusinessProfile,
  VaultBusinessSetupItem,
  VaultProofUpload,
  VaultLetterPacket,
  VaultMailingRecord,
  VaultWorkflowTask,
  VaultReminderTask,
  VaultFundingReadinessSummary,
  VaultAffiliateAttributionEvent,
  VaultConsentEvent,
  VaultAuditEvent,
  VaultSanitizedSignalExport,
} from '../config/clientVaultContract';

const NOW = '2026-06-26T00:00:00.000Z';

const PROFILES: VaultClientProfile[] = [
  { client_id: 'dev-c1', tenant_id: 'dev', client_label: 'Dev Client A', current_stage: 'credit_report_pending' },
  { client_id: 'dev-c2', tenant_id: 'dev', client_label: 'Dev Client B', current_stage: 'business_setup_in_progress' },
  { client_id: 'dev-c3', tenant_id: 'dev', client_label: 'Dev Client C', current_stage: 'ray_review_needed' },
];

export class MockClientVaultAdapter implements ClientVaultAdapter {
  private auditLog: VaultAuditEvent[] = [];

  connectionStatus(): ClientVaultConnectionStatus {
    return 'mock_dev';
  }
  isMock(): boolean {
    return true;
  }
  async listClientProfiles(): Promise<VaultClientProfile[]> {
    return PROFILES;
  }
  async getCreditReport(clientId: string): Promise<VaultClientCreditReport | null> {
    return { client_id: clientId, source: 'smartcredit', report_received: false, imported_at: null };
  }
  async getCreditScoreSnapshots(clientId: string): Promise<VaultCreditScoreSnapshot[]> {
    return [{ client_id: clientId, bureau: 'experian', score: null, score_source: 'unavailable', reported_at: NOW }];
  }
  async getBusinessProfile(clientId: string): Promise<VaultBusinessProfile | null> {
    return { client_id: clientId, entity_type: 'LLC', bankability_score: 55 };
  }
  async listBusinessSetupItems(clientId: string): Promise<VaultBusinessSetupItem[]> {
    return [
      { client_id: clientId, setup_item_key: 'business_bank_account', completion_status: 'not_started', client_selected_path: 'undecided' },
      { client_id: clientId, setup_item_key: 'duns_profile', completion_status: 'not_started', client_selected_path: 'undecided' },
    ];
  }
  async listProofUploads(clientId: string): Promise<VaultProofUpload[]> {
    return [{ client_id: clientId, proof_type: 'llc_proof', file_ref: 'dev-ref-llc', uploaded_at: NOW }];
  }
  async listLetterPackets(clientId: string): Promise<VaultLetterPacket[]> {
    return [{ client_id: clientId, letter_type: 'bureau_dispute', approval_status: 'draft' }];
  }
  async listMailingRecords(clientId: string): Promise<VaultMailingRecord[]> {
    return [{ client_id: clientId, mailing_method: 'usps_certified', mailing_status: 'not_started' }];
  }
  async listWorkflowTasks(clientId: string): Promise<VaultWorkflowTask[]> {
    return [{ client_id: clientId, task_key: 'upload_credit_report', status: 'pending' }];
  }
  async listReminderTasks(clientId: string): Promise<VaultReminderTask[]> {
    return [{ client_id: clientId, task_key: 'upload_credit_report', reminder_status: 'pending', days_stuck: 9 }];
  }
  async getFundingReadiness(clientId: string): Promise<VaultFundingReadinessSummary | null> {
    return { client_id: clientId, funding_readiness_score: 50, blockers: ['High credit utilization (>30%)'] };
  }
  async listAffiliateAttribution(clientId: string): Promise<VaultAffiliateAttributionEvent[]> {
    return [{ client_id: clientId, category: 'credit_monitoring', conversion_status: 'clicked' }];
  }
  async listConsentEvents(clientId: string): Promise<VaultConsentEvent[]> {
    return [{ client_id: clientId, consent_type: 'affiliate_disclosure', accepted: true, recorded_at: NOW }];
  }
  async exportSanitizedSignals(): Promise<VaultSanitizedSignalExport> {
    const byStage: Record<string, number> = {};
    for (const p of PROFILES) byStage[p.current_stage] = (byStage[p.current_stage] ?? 0) + 1;
    return {
      total_clients_by_stage: byStage,
      stuck_clients_count: 1,
      ray_review_needed_count: 1,
      revenue_risk_count: 1,
      recommended_next_actions: ['1 client stuck at credit report upload — follow up.', '1 client ready for Ray review.'],
    };
  }
  async recordAuditEvent(event: VaultAuditEvent): Promise<void> {
    // Mock: append in-memory only. No persistence, no real client data.
    this.auditLog.push(event);
  }
  getAuditLog(): VaultAuditEvent[] {
    return this.auditLog;
  }
}
