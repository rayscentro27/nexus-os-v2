/**
 * Nexus OS v2 — Client data access audit logging contract.
 *
 * Defines the audit event shape for FUTURE client data access. Mock events only in v1 — no real
 * production client data. Pure / deterministic. No I/O.
 */

export type AuditActorType = 'ai_agent' | 'admin' | 'system' | 'client';
export type AuditAccessType = 'read' | 'write' | 'export' | 'denied';
export type AuditDataCategory =
  | 'sanitized_signal'
  | 'workflow_status_internal'
  | 'raw_credit_report'
  | 'smartcredit_file'
  | 'bank_statement'
  | 'raw_letter'
  | 'funding_document'
  | 'client_profile';

export interface ClientAuditEvent {
  event_id: string;
  tenant_id: string;
  client_id: string;
  actor_type: AuditActorType;
  actor_id: string;
  agent_role: string;
  access_type: AuditAccessType;
  data_category: AuditDataCategory;
  reason: string;
  allowed: boolean;
  denied_reason: string | null;
  created_at: string;
}

const NOW = '2026-06-26T00:00:00.000Z';

/** Mock audit events (dev only — no real client data). Demonstrates allowed + denied paths. */
export const MOCK_AUDIT_EVENTS: ClientAuditEvent[] = [
  {
    event_id: 'audit-1', tenant_id: 'dev', client_id: 'dev-c1',
    actor_type: 'ai_agent', actor_id: 'credit_specialist', agent_role: 'credit_specialist_ai',
    access_type: 'read', data_category: 'raw_credit_report',
    reason: 'Credit analysis via vault adapter (mock).', allowed: true, denied_reason: null, created_at: NOW,
  },
  {
    event_id: 'audit-2', tenant_id: 'dev', client_id: 'dev-c1',
    actor_type: 'ai_agent', actor_id: 'hermes', agent_role: 'hermes_ceo_advisor',
    access_type: 'denied', data_category: 'raw_credit_report',
    reason: 'Hermes attempted raw credit report read.', allowed: false,
    denied_reason: 'Hermes is blocked from raw client data (sanitized signals only).', created_at: NOW,
  },
  {
    event_id: 'audit-3', tenant_id: 'dev', client_id: 'dev-c2',
    actor_type: 'ai_agent', actor_id: 'researcher', agent_role: 'researcher_ai',
    access_type: 'denied', data_category: 'client_profile',
    reason: 'Researcher attempted client record read.', allowed: false,
    denied_reason: 'Researcher AI has no client PII access.', created_at: NOW,
  },
  {
    event_id: 'audit-4', tenant_id: 'dev', client_id: 'dev-c3',
    actor_type: 'ai_agent', actor_id: 'hermes', agent_role: 'hermes_ceo_advisor',
    access_type: 'read', data_category: 'sanitized_signal',
    reason: 'Hermes read sanitized department signals.', allowed: true, denied_reason: null, created_at: NOW,
  },
];

export const AUDIT_CONTRACT_NOTE =
  'Audit events are contract + mock only in v1. When the live Client Vault is connected later, every client data access (allowed or denied) must be recorded with these fields.';
