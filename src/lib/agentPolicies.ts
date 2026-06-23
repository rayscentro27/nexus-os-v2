import type { Row } from '../services/db';

/**
 * Agent permission helpers (frontend). The UI uses these for SUMMARIES/labels only — actual
 * enforcement happens server-side (scripts/agent_policy.py + nexus_runner + approvals + RLS).
 */

export function isClientAgent(a: Row): boolean { return a.agent_class === 'client_agent'; }
export function isHermesAdvisor(a: Row): boolean { return a.agent_class === 'hermes_advisor'; }
export function canUseWeb(a: Row): boolean { return !!a.web_access_allowed; }
export function canUseExternalApi(a: Row): boolean { return !!a.external_api_allowed; }
export function canCreateJob(a: Row): boolean { return !!a.can_create_jobs; }
export function canCreateApproval(a: Row): boolean { return !!a.can_create_approvals; }
export function canExecuteAction(a: Row): boolean { return !!a.can_execute_actions; }
export function requiresApproval(a: Row, actionType: string): boolean {
  const needs: string[] = a.requires_approval_for ?? [];
  return needs.includes(actionType) || needs.includes('any_external_action') || needs.includes('any_public_claim');
}

export function explainAgentBoundary(a: Row): string {
  if (isHermesAdvisor(a)) return "Ray's private advisor: can research, recommend, and queue jobs/approvals — cannot publish, send, trade, or deploy without approvals + runner gates.";
  if (isClientAgent(a)) return 'Client-facing: answers only from Supabase-approved knowledge. No web, no external API, no public claims.';
  if (a.agent_class === 'runner') return 'Execution layer: runs only allowlisted job handlers; risky/real actions require explicit flags + approvals.';
  return 'Internal worker: reads job payloads + Supabase tables; cannot execute external actions.';
}
