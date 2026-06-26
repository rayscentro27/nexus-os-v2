/**
 * Nexus automation policy — the single source of truth for classifying an automation action into
 * Level 1 (autonomous internal), Level 2 (approval-gated), or Level 3 (blocked / high-risk).
 *
 * Tabs, feeders, Hermes, Ray Review Queue, Approvals, and Scheduler Approval Center must use these
 * helpers instead of inventing per-area rules.
 *
 * Pure / deterministic. No I/O, no external AI. Never weakens publish/send/trade/deploy gates.
 */
import {
  AUTOMATION_LEVELS,
  getAutomationLevel,
  type AutomationLevel,
  type AutomationLevelId,
} from '../config/nexusAutomationLevels';
import {
  AUTOMATION_CATEGORY_MATRIX,
  getCategoryMatrixEntry,
  type AutomationCategoryMatrixEntry,
} from '../config/nexusAutomationCategoryMatrix';
import type { AutomationCategoryId } from '../config/nexusAutomationCategories';

/** Level 3 — high-risk actions that are BLOCKED by default unless a separate contract is approved. */
const BLOCKED_HIGH_RISK = [
  /\blive[ _-]?trad/i,
  /\bbroker\b/i,
  /\bfunded[ _-]?account/i,
  /\bauto_executor\b/i,
  /\bpayment\b/i,
  /\bcharge\b/i,
  /\brefund\b/i,
  /\bad[ _-]?spend\b/i,
  /\bproduction[ _-]?deploy/i,
  /\brls\b/i,
  /\bdestructive\b/i,
  /\bdrop[ _-]?table\b/i,
  /\bsecret/i,
  /\.env\b/i,
  /\bbroad[ _-]?scrap/i,
  /\bmedia[ _-]?download/i,
  /youtube.*download|download.*youtube/i,
  /\bbulk[ _-]?send\b/i,
  /\bspam\b/i,
  /tenant[ _-]?isolation[ _-]?bypass/i,
  /client[ _-]?data[ _-]?exposure/i,
  /external[ _-]?ai.*(sensitive|private|customer)|(sensitive|private|customer).*external[ _-]?ai/i,
];

/** Level 2 — actions that can be prepared automatically but require Ray approval to execute. */
const APPROVAL_GATED = [
  /\bpublish/i,
  /\bsend\b/i,
  /\bemail\b/i,
  /\bsms\b/i,
  /\bdm\b/i,
  /\bsocial\b/i,
  /\bpost\b/i,
  /\bcampaign\b/i,
  /\bcontact\b/i,
  /\blead\b/i,
  /\bclient\b/i,
  /\bdeploy\b/i,
  /\bproduction\b/i,
  /\bscheduler\b/i,
  /\bcron\b/i,
  /\blaunchd\b/i,
  /\bsystemd\b/i,
  /\bconnector\b/i,
  /\boauth\b/i,
  /\bactivate\b/i,
  /\bspend\b/i,
];

export type AutomationActionInput =
  | string
  | { action?: string; category_id?: AutomationCategoryId; sensitive?: boolean; [k: string]: unknown };

function actionText(input: AutomationActionInput): string {
  if (typeof input === 'string') return input;
  return `${input.action ?? ''} ${input.category_id ?? ''} ${input.sensitive ? 'sensitive customer data' : ''}`.trim();
}

/** Classify any automation action into its level. Deterministic, keyword-based. */
export function classifyAutomationLevel(input: AutomationActionInput): AutomationLevelId {
  const text = actionText(input);
  if (BLOCKED_HIGH_RISK.some((re) => re.test(text))) return 'blocked_high_risk';
  if (APPROVAL_GATED.some((re) => re.test(text))) return 'approval_gated';
  return 'autonomous_internal';
}

export interface AutomationApprovalRequirement {
  level: AutomationLevelId;
  approval_required: boolean;
  ray_review_required: boolean;
  special_contract_required: boolean;
}

export function getAutomationApprovalRequirement(input: AutomationActionInput): AutomationApprovalRequirement {
  const level = typeof input === 'string' || !('level' in (input as object)) ? classifyAutomationLevel(input) : (input as { level: AutomationLevelId }).level;
  const def = getAutomationLevel(level);
  return {
    level,
    approval_required: def.approval_required,
    ray_review_required: def.ray_review_required,
    special_contract_required: def.special_contract_required,
  };
}

export function getAutomationAllowedActions(level: AutomationLevelId): string[] {
  return getAutomationLevel(level).allowed_outputs;
}

export function getAutomationForbiddenActions(level: AutomationLevelId): string[] {
  return getAutomationLevel(level).forbidden_outputs;
}

/**
 * Level 1 actions do NOT enter the Ray Review Queue. Level 2 enter when execution-ready.
 * Level 3 enter only as blocked/escalation items.
 */
export function shouldEnterRayReviewQueue(input: AutomationActionInput): boolean {
  return classifyAutomationLevel(input) !== 'autonomous_internal';
}

/** Only Level 2 execution-ready items create an Approvals row. Level 3 does NOT (separate contract). */
export function shouldEnterApprovals(input: AutomationActionInput): boolean {
  return classifyAutomationLevel(input) === 'approval_gated';
}

export function isBlockedHighRiskAutomation(input: AutomationActionInput): boolean {
  return classifyAutomationLevel(input) === 'blocked_high_risk';
}

export function getAutomationRiskReason(input: AutomationActionInput): string {
  const level = classifyAutomationLevel(input);
  if (level === 'blocked_high_risk') {
    return 'Blocked / high-risk: this can spend, trade, deploy, expose sensitive data, scrape broadly, or damage production. Requires a separate design doc, explicit Ray approval, proof plan, rollback plan, and hard guard tests.';
  }
  if (level === 'approval_gated') {
    return 'Approval-gated: this would leave the building (publish, send, contact, deploy, scheduler/connector activation, or spend). Nexus may prepare it, but Ray must approve before execution.';
  }
  return 'Autonomous internal: research, scoring, routing, internal cards/reports, and Hermes prep only. Nothing leaves the building.';
}

export function getAutomationRollbackRequirement(input: AutomationActionInput): string {
  const level = classifyAutomationLevel(input);
  const def = getAutomationLevel(level);
  if (!def.rollback_required) return 'No rollback required — internal-only output, no external side effects.';
  if (level === 'blocked_high_risk') {
    return 'Rollback plan REQUIRED before any execution: documented disable/undo command, proof log, and hard guard test that fails closed.';
  }
  return 'Rollback plan required: a documented disable/undo command and proof event before execution is approved.';
}

export interface AutomationCategorySummary {
  category_id: AutomationCategoryId;
  category_name: string;
  owner_department: string;
  level_1_allowed_actions: string[];
  level_2_approval_gated_actions: string[];
  level_3_blocked_actions: string[];
  current_level_allowed: AutomationLevelId;
  risk_notes: string;
  next_recommended_action: string;
}

export function getAutomationCategorySummary(id: AutomationCategoryId): AutomationCategorySummary | undefined {
  const e = getCategoryMatrixEntry(id);
  if (!e) return undefined;
  return toSummary(e);
}

export function getAllAutomationCategorySummaries(): AutomationCategorySummary[] {
  return AUTOMATION_CATEGORY_MATRIX.map(toSummary);
}

function toSummary(e: AutomationCategoryMatrixEntry): AutomationCategorySummary {
  // The highest level a category is currently allowed to run autonomously is always Level 1.
  // Level 2/3 actions exist but are gated/blocked, so the "currently allowed" lane is Level 1.
  return {
    category_id: e.category_id,
    category_name: e.category_name,
    owner_department: e.owner_department,
    level_1_allowed_actions: e.level_1_allowed_actions,
    level_2_approval_gated_actions: e.level_2_approval_gated_actions,
    level_3_blocked_actions: e.level_3_blocked_actions,
    current_level_allowed: 'autonomous_internal',
    risk_notes: e.risk_notes,
    next_recommended_action: e.next_recommended_action,
  };
}

export const AUTOMATION_LEVEL_DEFS: AutomationLevel[] = [
  AUTOMATION_LEVELS.autonomous_internal,
  AUTOMATION_LEVELS.approval_gated,
  AUTOMATION_LEVELS.blocked_high_risk,
];
