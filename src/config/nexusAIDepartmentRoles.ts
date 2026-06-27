/**
 * Nexus OS v2 — AI Department roles.
 *
 * Separates the AI agents so each has a distinct, least-privilege capability profile.
 * Pure / deterministic. No I/O.
 */

export type AIDepartmentRole =
  | 'hermes_ceo_advisor'
  | 'researcher_ai'
  | 'credit_specialist_ai'
  | 'funding_specialist_ai'
  | 'business_setup_specialist_ai'
  | 'client_chat_ai';

export interface AIDepartmentRoleDef {
  role: AIDepartmentRole;
  label: string;
  internet_allowed: boolean;
  public_research_allowed: boolean;
  supabase_system_reports_allowed: boolean;
  sanitized_client_signals_allowed: boolean;
  raw_client_data_allowed: boolean;
  vault_adapter_allowed: boolean; // may read client data ONLY through the Client Vault adapter
  approved_knowledge_only: boolean;
  client_facing_output: 'blocked' | 'approval_gated';
  description: string;
}

export const AI_DEPARTMENT_ROLES: Record<AIDepartmentRole, AIDepartmentRoleDef> = {
  hermes_ceo_advisor: {
    role: 'hermes_ceo_advisor',
    label: 'Hermes (CEO / Advisor)',
    internet_allowed: true,
    public_research_allowed: true,
    supabase_system_reports_allowed: true,
    sanitized_client_signals_allowed: true,
    raw_client_data_allowed: false,
    vault_adapter_allowed: false,
    approved_knowledge_only: false,
    client_facing_output: 'approval_gated',
    description: 'Strategy + public research + system reports + sanitized client metrics. Never raw client data, credit reports, SmartCredit files, SSN/DOB/account numbers/bank statements.',
  },
  researcher_ai: {
    role: 'researcher_ai',
    label: 'Researcher AI',
    internet_allowed: true,
    public_research_allowed: true,
    supabase_system_reports_allowed: true,
    sanitized_client_signals_allowed: false,
    raw_client_data_allowed: false,
    vault_adapter_allowed: false,
    approved_knowledge_only: false,
    client_facing_output: 'blocked',
    description: 'Public research only. Creates PROPOSED knowledge records that must be approved before the Credit Specialist may use them. No client PII, no client-specific recommendations.',
  },
  credit_specialist_ai: {
    role: 'credit_specialist_ai',
    label: 'Credit Specialist AI',
    internet_allowed: false,
    public_research_allowed: false,
    supabase_system_reports_allowed: true,
    sanitized_client_signals_allowed: true,
    raw_client_data_allowed: false, // only via vault adapter
    vault_adapter_allowed: true,
    approved_knowledge_only: true,
    client_facing_output: 'approval_gated',
    description: 'Supabase-approved knowledge only. Reads client credit/business data ONLY through the Client Vault adapter (mock in v1). No web tools, no external AI on client data. Client-facing output approval-gated.',
  },
  funding_specialist_ai: {
    role: 'funding_specialist_ai',
    label: 'Funding Specialist AI',
    internet_allowed: false,
    public_research_allowed: false,
    supabase_system_reports_allowed: true,
    sanitized_client_signals_allowed: true,
    raw_client_data_allowed: false,
    vault_adapter_allowed: true,
    approved_knowledge_only: true,
    client_facing_output: 'approval_gated',
    description: 'Supabase-approved funding rules only. Reads client funding readiness data ONLY through the vault adapter. Internet blocked by default. Client-facing output approval-gated.',
  },
  business_setup_specialist_ai: {
    role: 'business_setup_specialist_ai',
    label: 'Business Setup Specialist AI',
    internet_allowed: false,
    public_research_allowed: false,
    supabase_system_reports_allowed: true,
    sanitized_client_signals_allowed: true,
    raw_client_data_allowed: false,
    vault_adapter_allowed: true,
    approved_knowledge_only: true,
    client_facing_output: 'approval_gated',
    description: 'Supabase-approved business setup rules only. Reads client business setup data ONLY through the vault adapter. Internet blocked by default. Client-facing output approval-gated.',
  },
  client_chat_ai: {
    role: 'client_chat_ai',
    label: 'Client Chat AI',
    internet_allowed: false,
    public_research_allowed: false,
    supabase_system_reports_allowed: false,
    sanitized_client_signals_allowed: false,
    raw_client_data_allowed: false,
    vault_adapter_allowed: true, // own-client scoped/sanitized only
    approved_knowledge_only: true,
    client_facing_output: 'approval_gated',
    description: 'Approved knowledge only. Own-client scoped/sanitized data only via the vault adapter. No internet. No final recommendations unless approved.',
  },
};

export const AI_DEPARTMENT_ROLE_LIST: AIDepartmentRoleDef[] = Object.values(AI_DEPARTMENT_ROLES);

export function getAIRole(role: AIDepartmentRole): AIDepartmentRoleDef {
  return AI_DEPARTMENT_ROLES[role];
}
