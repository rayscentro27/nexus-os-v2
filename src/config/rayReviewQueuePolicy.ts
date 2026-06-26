import type { RayDecisionType, RayReviewPriority, RayReviewRiskLevel } from './rayReviewQueueTypes';

const AUTONOMOUS_RESEARCH_TYPES = new Set([
  'watched_resource',
  'watched_resource_update',
  'youtube_transcript_review',
  'affiliate_opportunity',
  'seo_keyword_opportunity',
  'seo_affiliate_content_plan',
  'research_experiment',
  'content_opportunity',
  'content_test_result',
  'trading_lab_research_project',
  'trading_lab_backtest_import',
  'hermes_decision_memory',
]);

const OUTBOUND_TERMS = /\b(publish|send|email|sms|dm|social|post|ad|spend|contact|client|lead|deploy|production|scheduler|cron|launchd|systemd|connector|oauth|live trading|broker|auto_executor)\b/i;

export function classifyRayDecisionType(input: Record<string, unknown>): RayDecisionType {
  const text = `${input.task_type ?? ''} ${input.item_type ?? ''} ${input.title ?? ''} ${input.summary ?? ''} ${JSON.stringify(input.payload ?? {})}`.toLowerCase();
  if (/scheduler|cron|launchd|systemd/.test(text)) return 'scheduler_activation';
  if (/live trading|broker|auto_executor|funded/.test(text)) return 'trading_live_execution_blocked';
  if (/deploy|production/.test(text)) return 'production_change';
  if (/connector|oauth|integration|credential/.test(text)) return 'connector_setup';
  if (/email/.test(text)) return 'email_send';
  if (/social|facebook|instagram|tiktok|post|publish/.test(text)) return /campaign/.test(text) ? 'campaign_publish' : 'social_post';
  if (/lead|client|contact|dm|sms/.test(text)) return /client/.test(text) ? 'client_action' : 'lead_contact';
  if (/revenue|funding|goclear|apex|upgrade|purchase/.test(text)) return 'revenue_decision';
  if (/compliance|claim|guarantee|legal/.test(text)) return 'compliance_review';
  if (/experiment|test/.test(text)) return 'experiment_selection';
  if (/report/.test(text)) return 'report_review';
  return 'high_value_strategy_choice';
}

export function shouldCreateRayReviewItem(input: Record<string, unknown>): boolean {
  const payload = (input.payload && typeof input.payload === 'object') ? input.payload as Record<string, unknown> : {};
  const taskType = String(input.task_type ?? payload.task_type ?? payload.project_type ?? '');
  if (AUTONOMOUS_RESEARCH_TYPES.has(taskType) && payload.ray_decision_required !== true && payload.approval_required !== true) return false;
  if (input.approval_required === true || payload.approval_required === true) return true;
  if (input.ray_decision_required === true || payload.ray_decision_required === true) return true;
  if (payload.strategic_decision === true || payload.hermes_strategic_decision === true) return true;
  if (payload.ready_for_publish === true || payload.ready_to_send === true || payload.ready_for_scheduler === true) return true;
  return OUTBOUND_TERMS.test(`${input.task_type ?? ''} ${input.item_type ?? ''} ${input.title ?? ''} ${input.summary ?? ''} ${JSON.stringify(payload)}`);
}

export function getRayReviewPriority(input: Record<string, unknown>): RayReviewPriority {
  const decision = classifyRayDecisionType(input);
  if (['trading_live_execution_blocked', 'production_change', 'scheduler_activation'].includes(decision)) return 'urgent';
  if (input.approval_required === true || (input.payload as Record<string, unknown> | undefined)?.approval_required === true) return 'high';
  if (decision === 'revenue_decision' || decision === 'high_value_strategy_choice') return 'high';
  return 'medium';
}

export function getRayReviewRisk(input: Record<string, unknown>): RayReviewRiskLevel {
  const decision = classifyRayDecisionType(input);
  if (decision === 'trading_live_execution_blocked') return 'critical';
  if (['production_change', 'scheduler_activation', 'campaign_publish', 'email_send', 'social_post'].includes(decision)) return 'high';
  if (['lead_contact', 'client_action', 'compliance_review', 'connector_setup'].includes(decision)) return 'medium';
  return 'low';
}

export function getRayReviewReason(input: Record<string, unknown>): string {
  const decision = classifyRayDecisionType(input).replaceAll('_', ' ');
  return `Ray decision required: ${decision}. Autonomous research can continue, but this item affects execution, risk, spend, public/client accounts, or strategic direction.`;
}

export function summarizeRayDecisionOptions(input: Record<string, unknown>): string[] {
  const decision = classifyRayDecisionType(input);
  if (decision === 'trading_live_execution_blocked') return ['Keep blocked', 'Convert to paper-only research', 'Request more risk review'];
  if (decision === 'scheduler_activation') return ['Keep manual only', 'Approve scheduler plan later', 'Request narrower schedule'];
  if (decision === 'campaign_publish' || decision === 'social_post' || decision === 'email_send') return ['Approve prep only', 'Request changes', 'Park', 'Create formal approval item'];
  return ['Proceed with internal prep', 'Request changes', 'Park', 'Escalate to Approvals'];
}

/**
 * Automation-level decision reasons. Level 1 items never reach the queue; Level 2 enter as
 * execution-ready approvals; Level 3 enter ONLY as blocked/escalation (never executable approval).
 */
export type RayReviewDecisionReason =
  | 'approval_gated_execution'
  | 'blocked_high_risk_escalation'
  | 'scheduler_activation_request'
  | 'connector_activation_request'
  | 'campaign_ready'
  | 'send_ready'
  | 'client_contact_ready'
  | 'trading_live_blocked'
  | 'production_change_request'
  | 'spend_request'
  | 'sensitive_data_request';

const DECISION_TYPE_TO_REASON: Partial<Record<RayDecisionType, RayReviewDecisionReason>> = {
  trading_live_execution_blocked: 'trading_live_blocked',
  scheduler_activation: 'scheduler_activation_request',
  connector_setup: 'connector_activation_request',
  production_change: 'production_change_request',
  campaign_publish: 'campaign_ready',
  social_post: 'campaign_ready',
  email_send: 'send_ready',
  lead_contact: 'client_contact_ready',
  client_action: 'client_contact_ready',
  revenue_decision: 'spend_request',
};

/** Map a queue item to its automation-level decision reason. Level 3 escalates, never executes. */
export function getRayReviewDecisionReason(input: Record<string, unknown>): RayReviewDecisionReason {
  const decision = classifyRayDecisionType(input);
  const risk = getRayReviewRisk(input);
  if (decision === 'trading_live_execution_blocked') return 'trading_live_blocked';
  const blob = `${input.task_type ?? ''} ${input.item_type ?? ''} ${input.title ?? ''} ${input.summary ?? ''} ${JSON.stringify(input.payload ?? {})}`.toLowerCase();
  if (/auto_executor|broker|funded|destructive|rls|broad scrape|media download|external ai.*(sensitive|private|customer)/.test(blob)) {
    return 'blocked_high_risk_escalation';
  }
  if (/sensitive|private|customer data|credit-sensitive/.test(blob)) return 'sensitive_data_request';
  if (risk === 'critical') return 'blocked_high_risk_escalation';
  return DECISION_TYPE_TO_REASON[decision] ?? 'approval_gated_execution';
}

/** Level 3 items are escalation-only: they must never be presented as an executable approval. */
export function isBlockedEscalationOnly(input: Record<string, unknown>): boolean {
  const reason = getRayReviewDecisionReason(input);
  return reason === 'blocked_high_risk_escalation' || reason === 'trading_live_blocked';
}

export const RAY_REVIEW_QUEUE_EXCLUSIONS = [
  'reviewed transcripts',
  'scored videos',
  'scored SEO keywords',
  'scored affiliate pages',
  'watched resource updates',
  'internal department routing',
  'internal experiment cards',
  'internal reports',
  'paper-only trading research cards',
  'Hermes internal recommendations',
] as const;
