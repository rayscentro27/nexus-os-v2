/**
 * Nexus OS v2 — AI agent access policy (declarative).
 *
 * Combines AI department roles with tool access and client-data access. The enforcement helpers
 * live in src/lib/nexusAIAccessPolicy.ts. Pure / deterministic. No I/O.
 */
import type { AIDepartmentRole } from './nexusAIDepartmentRoles';

export type AITool =
  | 'internet'
  | 'web_browse'
  | 'youtube'
  | 'external_ai_api'
  | 'supabase_system_reports'
  | 'sanitized_client_signals'
  | 'client_vault_adapter'
  | 'approved_knowledge'
  | 'unapproved_research';

export interface AIToolAccess {
  role: AIDepartmentRole;
  allowed_tools: AITool[];
  blocked_tools: AITool[];
}

/** Per-role tool allow/block lists. Least-privilege. */
export const AI_TOOL_ACCESS: Record<AIDepartmentRole, AIToolAccess> = {
  hermes_ceo_advisor: {
    role: 'hermes_ceo_advisor',
    allowed_tools: ['internet', 'web_browse', 'supabase_system_reports', 'sanitized_client_signals', 'approved_knowledge'],
    blocked_tools: ['client_vault_adapter', 'external_ai_api'],
  },
  researcher_ai: {
    role: 'researcher_ai',
    allowed_tools: ['internet', 'web_browse', 'youtube', 'supabase_system_reports', 'approved_knowledge'],
    blocked_tools: ['client_vault_adapter', 'sanitized_client_signals'],
  },
  credit_specialist_ai: {
    role: 'credit_specialist_ai',
    allowed_tools: ['supabase_system_reports', 'sanitized_client_signals', 'client_vault_adapter', 'approved_knowledge'],
    blocked_tools: ['internet', 'web_browse', 'youtube', 'external_ai_api', 'unapproved_research'],
  },
  funding_specialist_ai: {
    role: 'funding_specialist_ai',
    allowed_tools: ['supabase_system_reports', 'sanitized_client_signals', 'client_vault_adapter', 'approved_knowledge'],
    blocked_tools: ['internet', 'web_browse', 'youtube', 'external_ai_api', 'unapproved_research'],
  },
  business_setup_specialist_ai: {
    role: 'business_setup_specialist_ai',
    allowed_tools: ['supabase_system_reports', 'sanitized_client_signals', 'client_vault_adapter', 'approved_knowledge'],
    blocked_tools: ['internet', 'web_browse', 'youtube', 'external_ai_api', 'unapproved_research'],
  },
  client_chat_ai: {
    role: 'client_chat_ai',
    allowed_tools: ['client_vault_adapter', 'approved_knowledge'],
    blocked_tools: ['internet', 'web_browse', 'youtube', 'external_ai_api', 'supabase_system_reports', 'unapproved_research'],
  },
};

/** Tools that can reach the open internet — these may NEVER also touch the Client Vault. */
export const INTERNET_TOOLS: AITool[] = ['internet', 'web_browse', 'youtube', 'external_ai_api'];

export const AI_ACCESS_COPY = {
  hermesNoRaw: 'Hermes works from sanitized signals and system reports only — never raw client data.',
  specialistSupabaseOnly: 'Specialist AIs are Supabase-only: no internet/web tools, approved knowledge + vault adapter only.',
  internetVaultSeparation: 'Internet-enabled tools can never access Client Vault data.',
  clientFacingGated: 'All client-facing recommendations remain approval-gated.',
} as const;
