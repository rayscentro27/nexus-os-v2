/**
 * Nexus OS v2 — AI Agent Runtime.
 *
 * Turns the static AI access contracts into RUNTIME-enforced behavior. Every Specialist/agent reads
 * the Client Vault ONLY through this runtime, which at call time:
 *   1. enforces canUseTool(role, tool)
 *   2. enforces canAccessData(role, dataCategory)
 *   3. enforces own-client scoping (Client Chat AI)
 *   4. records a ClientAuditEvent (allowed OR denied) to the audit sink + the vault adapter
 *
 * Fails closed: a denied read returns no data. v1 uses the mock Client Vault adapter only.
 * Deterministic except for event ids / timestamps. No network beyond the (mock) adapter.
 */
import type {
  ClientVaultAdapter,
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
  VaultSanitizedSignalExport,
} from '../config/clientVaultContract';
import { getClientVaultAdapter } from './clientVaultAdapter';
import { canUseTool, canAccessData } from './nexusAIAccessPolicy';
import type { AIDepartmentRole } from '../config/nexusAIDepartmentRoles';
import type { AITool } from '../config/nexusAIAgentAccessPolicy';
import type { ClientDataCategory } from '../config/nexusClientDataSensitivityPolicy';
import type {
  ClientAuditEvent,
  AuditAccessType,
  AuditActorType,
  AuditDataCategory,
} from '../config/nexusClientAuditContract';

export type VaultMethod =
  | 'listClientProfiles'
  | 'getCreditReport'
  | 'getCreditScoreSnapshots'
  | 'getBusinessProfile'
  | 'listBusinessSetupItems'
  | 'listProofUploads'
  | 'listLetterPackets'
  | 'listMailingRecords'
  | 'listWorkflowTasks'
  | 'listReminderTasks'
  | 'getFundingReadiness'
  | 'listAffiliateAttribution'
  | 'listConsentEvents'
  | 'exportSanitizedSignals';

interface MethodSpec {
  tool: AITool;
  dataCategory: ClientDataCategory;
  auditCategory: AuditDataCategory;
  accessType: AuditAccessType;
  clientScoped: boolean; // requires a clientId and is subject to own-client scoping
}

/** Per-method access + audit classification. */
export const VAULT_METHOD_SPECS: Record<VaultMethod, MethodSpec> = {
  listClientProfiles: { tool: 'client_vault_adapter', dataCategory: 'client_name', auditCategory: 'client_profile', accessType: 'read', clientScoped: false },
  getCreditReport: { tool: 'client_vault_adapter', dataCategory: 'raw_credit_report', auditCategory: 'raw_credit_report', accessType: 'read', clientScoped: true },
  getCreditScoreSnapshots: { tool: 'client_vault_adapter', dataCategory: 'credit_score_raw', auditCategory: 'credit_score', accessType: 'read', clientScoped: true },
  getBusinessProfile: { tool: 'client_vault_adapter', dataCategory: 'business_profile', auditCategory: 'business_profile', accessType: 'read', clientScoped: true },
  listBusinessSetupItems: { tool: 'client_vault_adapter', dataCategory: 'business_setup_item', auditCategory: 'business_setup_item', accessType: 'read', clientScoped: true },
  listProofUploads: { tool: 'client_vault_adapter', dataCategory: 'proof_upload', auditCategory: 'proof_upload', accessType: 'read', clientScoped: true },
  listLetterPackets: { tool: 'client_vault_adapter', dataCategory: 'raw_letter', auditCategory: 'raw_letter', accessType: 'read', clientScoped: true },
  listMailingRecords: { tool: 'client_vault_adapter', dataCategory: 'mailing_record', auditCategory: 'mailing_record', accessType: 'read', clientScoped: true },
  listWorkflowTasks: { tool: 'client_vault_adapter', dataCategory: 'workflow_task', auditCategory: 'workflow_task', accessType: 'read', clientScoped: true },
  listReminderTasks: { tool: 'client_vault_adapter', dataCategory: 'reminder_task', auditCategory: 'reminder_task', accessType: 'read', clientScoped: true },
  getFundingReadiness: { tool: 'client_vault_adapter', dataCategory: 'funding_readiness', auditCategory: 'funding_readiness', accessType: 'read', clientScoped: true },
  listAffiliateAttribution: { tool: 'client_vault_adapter', dataCategory: 'affiliate_attribution', auditCategory: 'affiliate_attribution', accessType: 'read', clientScoped: true },
  listConsentEvents: { tool: 'client_vault_adapter', dataCategory: 'client_consent_record', auditCategory: 'consent_event', accessType: 'read', clientScoped: true },
  exportSanitizedSignals: { tool: 'sanitized_client_signals', dataCategory: 'sanitized_signal', auditCategory: 'sanitized_signal', accessType: 'export', clientScoped: false },
};

export type VaultReadResult<T> =
  | { allowed: true; data: T; audit: ClientAuditEvent }
  | { allowed: false; data: null; denied_reason: string; audit: ClientAuditEvent };

/** Collects audit events. In-memory in v1; a live impl would persist append-only. */
export class AuditSink {
  private events: ClientAuditEvent[] = [];
  record(e: ClientAuditEvent): void {
    this.events.push(e);
  }
  all(): ClientAuditEvent[] {
    return this.events;
  }
  allowed(): ClientAuditEvent[] {
    return this.events.filter((e) => e.allowed);
  }
  denied(): ClientAuditEvent[] {
    return this.events.filter((e) => !e.allowed);
  }
  clear(): void {
    this.events = [];
  }
}

export interface AgentRuntimeConfig {
  role: AIDepartmentRole;
  actorId: string;
  tenantId?: string;
  /** Client Chat AI is scoped to a single client; reads of any other client are denied. */
  allowedClientId?: string | null;
  sink?: AuditSink;
  adapter?: ClientVaultAdapter;
  /** Deterministic id/clock hooks for testing. */
  idFactory?: () => string;
  clock?: () => string;
}

const ACTOR_TYPE: AuditActorType = 'ai_agent';

/**
 * The runtime an agent uses to read the Client Vault. Every method enforces access + logs an audit
 * event. Construct one per (agent, request) scope.
 */
export class NexusAgentRuntime {
  readonly role: AIDepartmentRole;
  private readonly actorId: string;
  private readonly tenantId: string;
  private readonly allowedClientId: string | null;
  private readonly sink: AuditSink;
  private readonly adapter: ClientVaultAdapter;
  private readonly idFactory: () => string;
  private readonly clock: () => string;
  private seq = 0;

  constructor(cfg: AgentRuntimeConfig) {
    this.role = cfg.role;
    this.actorId = cfg.actorId;
    this.tenantId = cfg.tenantId ?? 'dev';
    this.allowedClientId = cfg.allowedClientId ?? null;
    this.sink = cfg.sink ?? new AuditSink();
    this.adapter = cfg.adapter ?? getClientVaultAdapter();
    this.idFactory = cfg.idFactory ?? (() => `audit-${this.role}-${++this.seq}`);
    this.clock = cfg.clock ?? (() => new Date().toISOString());
  }

  auditLog(): ClientAuditEvent[] {
    return this.sink.all();
  }

  private buildEvent(
    spec: MethodSpec,
    clientId: string,
    allowed: boolean,
    reason: string,
    deniedReason: string | null,
  ): ClientAuditEvent {
    return {
      event_id: this.idFactory(),
      tenant_id: this.tenantId,
      client_id: clientId,
      actor_type: ACTOR_TYPE,
      actor_id: this.actorId,
      agent_role: this.role,
      access_type: allowed ? spec.accessType : 'denied',
      data_category: spec.auditCategory,
      reason,
      allowed,
      denied_reason: deniedReason,
      created_at: this.clock(),
    };
  }

  /** Core guard: tool gate → data gate → scope gate → audit → adapter call (fail closed). */
  private async guard<T>(
    method: VaultMethod,
    clientId: string,
    invoke: (a: ClientVaultAdapter) => Promise<T>,
  ): Promise<VaultReadResult<T>> {
    const spec = VAULT_METHOD_SPECS[method];

    const toolDecision = canUseTool(this.role, spec.tool);
    if (!toolDecision.allowed) return this.deny<T>(spec, clientId, toolDecision.reason);

    const dataDecision = canAccessData(this.role, spec.dataCategory);
    if (!dataDecision.allowed) return this.deny<T>(spec, clientId, dataDecision.reason);

    if (spec.clientScoped && this.role === 'client_chat_ai') {
      if (!this.allowedClientId || this.allowedClientId !== clientId) {
        return this.deny<T>(spec, clientId, `Client Chat AI is scoped to ${this.allowedClientId ?? 'no client'}; cannot read ${clientId}.`);
      }
    }

    const audit = this.buildEvent(spec, clientId, true, `${this.role} read ${method} via vault adapter.`, null);
    this.sink.record(audit);
    await this.adapter.recordAuditEvent(audit);
    const data = await invoke(this.adapter);
    return { allowed: true, data, audit };
  }

  private deny<T>(spec: MethodSpec, clientId: string, deniedReason: string): VaultReadResult<T> {
    const audit = this.buildEvent(spec, clientId, false, `${this.role} blocked from ${spec.auditCategory}.`, deniedReason);
    this.sink.record(audit);
    // best-effort: also record denial on the adapter audit log
    void this.adapter.recordAuditEvent(audit);
    return { allowed: false, data: null, denied_reason: deniedReason, audit };
  }

  // ---- Wrapped vault reads (each enforced + audited) ----

  listClientProfiles(): Promise<VaultReadResult<VaultClientProfile[]>> {
    return this.guard('listClientProfiles', 'aggregate', (a) => a.listClientProfiles());
  }
  getCreditReport(clientId: string): Promise<VaultReadResult<VaultClientCreditReport | null>> {
    return this.guard('getCreditReport', clientId, (a) => a.getCreditReport(clientId));
  }
  getCreditScoreSnapshots(clientId: string): Promise<VaultReadResult<VaultCreditScoreSnapshot[]>> {
    return this.guard('getCreditScoreSnapshots', clientId, (a) => a.getCreditScoreSnapshots(clientId));
  }
  getBusinessProfile(clientId: string): Promise<VaultReadResult<VaultBusinessProfile | null>> {
    return this.guard('getBusinessProfile', clientId, (a) => a.getBusinessProfile(clientId));
  }
  listBusinessSetupItems(clientId: string): Promise<VaultReadResult<VaultBusinessSetupItem[]>> {
    return this.guard('listBusinessSetupItems', clientId, (a) => a.listBusinessSetupItems(clientId));
  }
  listProofUploads(clientId: string): Promise<VaultReadResult<VaultProofUpload[]>> {
    return this.guard('listProofUploads', clientId, (a) => a.listProofUploads(clientId));
  }
  listLetterPackets(clientId: string): Promise<VaultReadResult<VaultLetterPacket[]>> {
    return this.guard('listLetterPackets', clientId, (a) => a.listLetterPackets(clientId));
  }
  listMailingRecords(clientId: string): Promise<VaultReadResult<VaultMailingRecord[]>> {
    return this.guard('listMailingRecords', clientId, (a) => a.listMailingRecords(clientId));
  }
  listWorkflowTasks(clientId: string): Promise<VaultReadResult<VaultWorkflowTask[]>> {
    return this.guard('listWorkflowTasks', clientId, (a) => a.listWorkflowTasks(clientId));
  }
  listReminderTasks(clientId: string): Promise<VaultReadResult<VaultReminderTask[]>> {
    return this.guard('listReminderTasks', clientId, (a) => a.listReminderTasks(clientId));
  }
  getFundingReadiness(clientId: string): Promise<VaultReadResult<VaultFundingReadinessSummary | null>> {
    return this.guard('getFundingReadiness', clientId, (a) => a.getFundingReadiness(clientId));
  }
  listAffiliateAttribution(clientId: string): Promise<VaultReadResult<VaultAffiliateAttributionEvent[]>> {
    return this.guard('listAffiliateAttribution', clientId, (a) => a.listAffiliateAttribution(clientId));
  }
  listConsentEvents(clientId: string): Promise<VaultReadResult<VaultConsentEvent[]>> {
    return this.guard('listConsentEvents', clientId, (a) => a.listConsentEvents(clientId));
  }
  /** Sanitized signals — the only path that may feed Hermes. */
  exportSanitizedSignals(): Promise<VaultReadResult<VaultSanitizedSignalExport>> {
    return this.guard('exportSanitizedSignals', 'aggregate', (a) => a.exportSanitizedSignals());
  }
}

/** Factory: create a runtime for an agent role. */
export function createAgentRuntime(cfg: AgentRuntimeConfig): NexusAgentRuntime {
  return new NexusAgentRuntime(cfg);
}

/** Convenience for the Credit Specialist (Supabase-only, vault via adapter). */
export function createCreditSpecialistRuntime(actorId = 'credit_specialist', sink?: AuditSink): NexusAgentRuntime {
  return new NexusAgentRuntime({ role: 'credit_specialist_ai', actorId, sink });
}
