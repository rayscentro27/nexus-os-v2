/**
 * Nexus automation status registry — per-category live status that powers the Command Center
 * Automation Control surface and future UI. Derived deterministically from the category matrix so
 * it never drifts. No live activation here: schedule_ready means "candidate exists", not "running".
 *
 * Pure / deterministic. No I/O.
 */
import type { AutomationLevelId } from './nexusAutomationLevels';
import type { AutomationCategoryId } from './nexusAutomationCategories';
import { AUTOMATION_CATEGORY_MATRIX } from './nexusAutomationCategoryMatrix';

export type AutomationLevelStatus = 'enabled_internal' | 'manual_only' | 'gated' | 'blocked' | 'not_applicable';

export interface AutomationCategoryStatus {
  category_id: AutomationCategoryId;
  category_name: string;
  owner_department: string;
  current_level_allowed: AutomationLevelId;
  level_1_status: AutomationLevelStatus;
  level_2_status: AutomationLevelStatus;
  level_3_status: AutomationLevelStatus;
  approved_internal_actions: string[];
  approval_gated_actions: string[];
  blocked_actions: string[];
  last_checked_at: string | null;
  proof_event_id: string | null;
  report_path: string | null;
  next_recommended_action: string;
  owner: string;
  risk_notes: string;
  schedule_ready: boolean;
  scheduler_approval_required: boolean;
  connector_required: boolean;
  external_api_required: boolean;
  high_risk_guard_required: boolean;
}

const SCHEDULE_READY_CATEGORIES = new Set<AutomationCategoryId>([
  'research_source_intake',
  'youtube_research',
  'seo_marketing',
  'affiliate_marketing',
  'content_opportunity_lab',
  'goclear_revenue_hub',
  'trading_lab',
  'monitoring_health',
]);

const CONNECTOR_CATEGORIES = new Set<AutomationCategoryId>([
  'youtube_research',
  'integrations',
  'notebooklm_research_library',
  'email_sms_dm_social',
  'goclear_revenue_hub',
]);

const EXTERNAL_API_CATEGORIES = new Set<AutomationCategoryId>([
  'youtube_research',
  'integrations',
  'email_sms_dm_social',
  'ads_spend',
  'trading_lab',
]);

function levelStatus(actions: string[], gated: boolean, blocked: boolean): AutomationLevelStatus {
  if (actions.length === 0) return 'not_applicable';
  if (blocked) return 'blocked';
  if (gated) return 'gated';
  return 'enabled_internal';
}

export const NEXUS_AUTOMATION_STATUS_REGISTRY: AutomationCategoryStatus[] = AUTOMATION_CATEGORY_MATRIX.map((e) => {
  const highRisk = e.level_3_blocked_actions.length > 0;
  return {
    category_id: e.category_id,
    category_name: e.category_name,
    owner_department: e.owner_department,
    current_level_allowed: 'autonomous_internal' as AutomationLevelId,
    level_1_status: levelStatus(e.level_1_allowed_actions, false, false),
    level_2_status: levelStatus(e.level_2_approval_gated_actions, true, false),
    level_3_status: levelStatus(e.level_3_blocked_actions, false, true),
    approved_internal_actions: e.level_1_allowed_actions,
    approval_gated_actions: e.level_2_approval_gated_actions,
    blocked_actions: e.level_3_blocked_actions,
    last_checked_at: null,
    proof_event_id: null,
    report_path: 'reports/manual_publish/nexus_automation_control_center_latest.md',
    next_recommended_action: e.next_recommended_action,
    owner: e.owner_department,
    risk_notes: e.risk_notes,
    schedule_ready: SCHEDULE_READY_CATEGORIES.has(e.category_id),
    scheduler_approval_required: e.level_2_approval_gated_actions.some((a) => /scheduler/i.test(a)) || SCHEDULE_READY_CATEGORIES.has(e.category_id),
    connector_required: CONNECTOR_CATEGORIES.has(e.category_id),
    external_api_required: EXTERNAL_API_CATEGORIES.has(e.category_id),
    high_risk_guard_required: highRisk,
  };
});

export function getAutomationCategoryStatus(id: AutomationCategoryId): AutomationCategoryStatus | undefined {
  return NEXUS_AUTOMATION_STATUS_REGISTRY.find((s) => s.category_id === id);
}
