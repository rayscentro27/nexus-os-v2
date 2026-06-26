/**
 * Nexus universal action policy — the single source of truth for how EVERY tab classifies an
 * action: is it safe to queue automatically, does it need Ray review, must it appear in Approvals,
 * or is it disabled? Tabs must use these helpers instead of inventing per-tab rules.
 *
 * Pure / deterministic. No external AI, no I/O. Never weakens publish/send/trade/deploy gates.
 */

export type ActionCategory =
  | 'safe_read'            // read-only data
  | 'safe_queue'           // safe work that may queue automatically (no approval)
  | 'safe_draft'           // produces a draft, not published
  | 'safe_internal_route'  // routes to an internal/non-client destination
  | 'needs_review'         // Ray should review internally (does NOT imply Approvals)
  | 'approval_required'    // hard approval gate (publish/send/trade/deploy/etc.)
  | 'disabled'             // not connected yet
  | 'dangerous_blocked';   // never allowed from the UI

export type RiskTrigger =
  | 'uncategorized' | 'low_confidence' | 'high_compliance_risk' | 'risky_destination'
  | 'client_facing' | 'publish_send_trade_deploy' | 'scheduler_or_local_command'
  | 'raw_v1_worker' | 'sensitive_data' | 'external_ai_sensitive_text' | 'broad_scrape'
  | 'missing_connection';

export type ActionOutcome =
  | 'auto_routed' | 'queued_safe_work' | 'needs_ray_review' | 'approval_required'
  | 'parked' | 'rejected' | 'disabled_not_connected';

export interface NexusAction {
  category: ActionCategory;
  triggers?: RiskTrigger[];
  disabledReason?: string;
}

export const ACTION_COPY = {
  safeQueue: 'Safe work can queue automatically.',
  approvalRequired: 'Ray approval is required for risky actions.',
  hermesRecommends: 'Hermes can recommend, but Ray approves risky actions.',
  disabled: 'Disabled — not connected yet.',
  queuedRunner: 'Queued — waiting for local runner.',
  needsReview: 'Needs Ray review.',
} as const;

/** Triggers that ALWAYS force an approval gate (never auto-queue). */
const HARD_TRIGGERS: RiskTrigger[] = [
  'publish_send_trade_deploy', 'scheduler_or_local_command', 'raw_v1_worker',
  'sensitive_data', 'external_ai_sensitive_text', 'broad_scrape', 'client_facing',
];

const SAFE_SOURCE_TYPES = new Set(['youtube_video', 'manual_idea', 'transcript_file']);

/** Safe destinations that do NOT require approval. */
export const SAFE_DESTINATIONS = new Set([
  'Source Intake & Review', 'Ops & Improvements', 'Research Only', 'Knowledge/Memory',
  'Creative Ideas (draft)', 'Opportunity Lab',
]);

export function isSafeAdminSubmittedSourceCapture(payload: Record<string, unknown>): boolean {
  if (payload?.sensitive === true) return false;
  if (payload?.requested_by_admin !== true) return false;
  return SAFE_SOURCE_TYPES.has(String(payload?.source_type ?? ''));
}

/** Deterministic risk triggers for a submission payload. */
export function getReviewTriggers(payload: Record<string, unknown>): RiskTrigger[] {
  const t: RiskTrigger[] = [];
  const type = String(payload?.source_type ?? '');
  if (payload?.sensitive) t.push('sensitive_data');
  if (type === 'website_url') t.push('risky_destination');             // crawl
  else if (type && !SAFE_SOURCE_TYPES.has(type)) t.push('uncategorized');
  if (payload?.client_facing) t.push('client_facing');
  if (payload?.publish || payload?.send || payload?.trade || payload?.deploy) t.push('publish_send_trade_deploy');
  if (payload?.low_confidence) t.push('low_confidence');
  if (payload?.high_compliance_risk) t.push('high_compliance_risk');
  if (payload?.external_ai_on_sensitive) t.push('external_ai_sensitive_text');
  return t;
}

export function getApprovalRequirement(action: NexusAction): boolean {
  if (action.category === 'approval_required') return true;
  return (action.triggers ?? []).some((x) => HARD_TRIGGERS.includes(x));
}

export function getActionStatusLabel(action: NexusAction): string {
  switch (action.category) {
    case 'safe_read': return 'Live';
    case 'safe_queue': return 'Safe capture';
    case 'safe_draft': return 'Draft only';
    case 'safe_internal_route': return 'Auto-routed';
    case 'needs_review': return 'Needs Ray review';
    case 'approval_required': return 'Approval required';
    case 'disabled': return 'Disabled';
    case 'dangerous_blocked': return 'Blocked';
  }
}

export function getActionSafetyCopy(action: NexusAction): string {
  if (action.category === 'disabled') return action.disabledReason || ACTION_COPY.disabled;
  if (getApprovalRequirement(action)) return ACTION_COPY.approvalRequired;
  if (action.category === 'safe_queue') return ACTION_COPY.queuedRunner;
  return ACTION_COPY.safeQueue;
}

/** approval_required items must show in the Approvals tab. */
export function shouldShowInApprovals(action: NexusAction): boolean {
  return getApprovalRequirement(action);
}

/** Safe queue items show in the owning tab queue (NOT Approvals). */
export function shouldShowInOwningQueue(action: NexusAction): boolean {
  return !getApprovalRequirement(action) && action.category !== 'disabled' && action.category !== 'dangerous_blocked';
}

/** Trigger → Approvals item_type. */
export const TRIGGER_ITEM_TYPE: Record<string, string> = {
  risky_destination: 'risky_destination_review',
  uncategorized: 'uncategorized_source_review',
  low_confidence: 'low_confidence_source_review',
  high_compliance_risk: 'high_risk_source_review',
  client_facing: 'high_risk_source_review',
  sensitive_data: 'source_capture_review',
  publish_send_trade_deploy: 'high_risk_source_review',
};

export interface CaptureClassification {
  category: ActionCategory; triggers: RiskTrigger[]; approvalRequired: boolean;
  outcome: ActionOutcome; itemType: string | null; statusLabel: string; safetyCopy: string;
}

// ---- Automation-level approval bridge ---------------------------------------
// Ties the universal action policy to the three-level automation model:
//   Level 1 (autonomous_internal)  → no approval row.
//   Level 2 (approval_gated)        → approval row ONLY when execution-ready.
//   Level 3 (blocked_high_risk)     → NO direct execution approval; separate contract/escalation.

import { classifyAutomationLevel, type AutomationActionInput } from '../lib/nexusAutomationPolicy';

export type AutomationApprovalDisposition =
  | 'no_approval_needed'
  | 'approval_when_execution_ready'
  | 'blocked_separate_contract';

export function getAutomationApprovalDisposition(input: AutomationActionInput): AutomationApprovalDisposition {
  const level = classifyAutomationLevel(input);
  if (level === 'blocked_high_risk') return 'blocked_separate_contract';
  if (level === 'approval_gated') return 'approval_when_execution_ready';
  return 'no_approval_needed';
}

/** Should this action create an Approvals row now? Only Level 2 AND execution-ready. */
export function shouldCreateApprovalRow(input: AutomationActionInput, executionReady = false): boolean {
  return getAutomationApprovalDisposition(input) === 'approval_when_execution_ready' && executionReady;
}

/** Level 3 must never become a direct execution approval. */
export function isBlockedFromDirectApproval(input: AutomationActionInput): boolean {
  return getAutomationApprovalDisposition(input) === 'blocked_separate_contract';
}

/** Actions that must NEVER create approvals (pure internal Level 1 work). */
export const NO_APPROVAL_ACTIONS = [
  'research', 'scoring', 'routing', 'internal report', 'watched resource update',
  'transcript review', 'paper-only trading research', 'hermes internal recommendation',
] as const;

/** The keystone: classify a source-capture submission. Used by Source Intake (and any tab). */
export function classifyCaptureSubmission(payload: Record<string, unknown>): CaptureClassification {
  const triggers = getReviewTriggers(payload);
  const approvalRequired = triggers.some((x) => HARD_TRIGGERS.includes(x));
  const category: ActionCategory = approvalRequired ? 'needs_review' : 'safe_queue';
  const action: NexusAction = { category, triggers };
  const firstTrigger = triggers[0];
  return {
    category, triggers, approvalRequired,
    outcome: approvalRequired ? 'needs_ray_review' : 'queued_safe_work',
    itemType: approvalRequired ? (TRIGGER_ITEM_TYPE[firstTrigger] ?? 'source_capture_review') : null,
    statusLabel: getActionStatusLabel(action),
    safetyCopy: getActionSafetyCopy(action),
  };
}
