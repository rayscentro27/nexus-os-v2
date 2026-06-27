/**
 * Nexus OS v2 — Credit Specialist Supabase-only access contract.
 * Pure / deterministic. No I/O.
 */

export const CREDIT_SPECIALIST_MAY_USE = [
  'approved_credit_knowledge',
  'approved_dispute_rules',
  'approved_funding_readiness_rules',
  'approved_compliance_language',
  'mock_client_credit_report_via_vault_adapter',
  'mock_client_business_setup_via_vault_adapter',
  'client_workflow_tasks_via_adapter',
  'client_action_plan_drafts',
] as const;

export const CREDIT_SPECIALIST_MUST_NOT_USE = [
  'internet',
  'web_browsing',
  'youtube',
  'unapproved_research',
  'external_ai_on_client_data',
  'raw_client_vault_production_connection',
  'production_smartcredit_files',
] as const;

export const CREDIT_SPECIALIST_CONTRACT = {
  role: 'credit_specialist_ai',
  supabase_only: true,
  internet_allowed: false,
  approved_knowledge_only: true,
  vault_access: 'mock_adapter_only_v1',
  client_facing_output: 'approval_gated',
  may_use: CREDIT_SPECIALIST_MAY_USE,
  must_not_use: CREDIT_SPECIALIST_MUST_NOT_USE,
  notes: 'Reads client credit/business data only through the Client Vault adapter (mock in v1). No web tools. No external AI on client data. Client-facing output is approval-gated.',
} as const;
