/**
 * Nexus automation status helpers — derived counts and summaries for the Command Center.
 * Pure / deterministic. No I/O.
 */
import {
  NEXUS_AUTOMATION_STATUS_REGISTRY,
  type AutomationCategoryStatus,
} from '../config/nexusAutomationStatusRegistry';

export interface AutomationStatusCounts {
  total_categories: number;
  level_1_internal: number;
  level_2_gated: number;
  level_3_blocked: number;
  schedule_ready: number;
  scheduler_approval_required: number;
  connector_required: number;
  external_api_required: number;
  high_risk_guard_required: number;
}

export function automationStatusCounts(
  registry: AutomationCategoryStatus[] = NEXUS_AUTOMATION_STATUS_REGISTRY,
): AutomationStatusCounts {
  return {
    total_categories: registry.length,
    level_1_internal: registry.filter((s) => s.level_1_status === 'enabled_internal').length,
    level_2_gated: registry.filter((s) => s.approval_gated_actions.length > 0).length,
    level_3_blocked: registry.filter((s) => s.blocked_actions.length > 0).length,
    schedule_ready: registry.filter((s) => s.schedule_ready).length,
    scheduler_approval_required: registry.filter((s) => s.scheduler_approval_required).length,
    connector_required: registry.filter((s) => s.connector_required).length,
    external_api_required: registry.filter((s) => s.external_api_required).length,
    high_risk_guard_required: registry.filter((s) => s.high_risk_guard_required).length,
  };
}

/** The single highest-priority safe automation Ray could enable next (a schedule-ready Level 1). */
export function nextRecommendedSafeAutomation(
  registry: AutomationCategoryStatus[] = NEXUS_AUTOMATION_STATUS_REGISTRY,
): AutomationCategoryStatus | null {
  return (
    registry.find((s) => s.schedule_ready && !s.connector_required && s.level_1_status === 'enabled_internal') ??
    registry.find((s) => s.schedule_ready) ??
    registry[0] ??
    null
  );
}

/** The single top automation risk to surface (a high-risk-guarded category). */
export function topAutomationRisk(
  registry: AutomationCategoryStatus[] = NEXUS_AUTOMATION_STATUS_REGISTRY,
): AutomationCategoryStatus | null {
  return (
    registry.find((s) => s.category_id === 'trading_lab') ??
    registry.find((s) => s.high_risk_guard_required) ??
    null
  );
}

export function categoriesNeedingRayApproval(
  registry: AutomationCategoryStatus[] = NEXUS_AUTOMATION_STATUS_REGISTRY,
): AutomationCategoryStatus[] {
  return registry.filter((s) => s.approval_gated_actions.length > 0);
}

export function categoriesNexusCanRunInternally(
  registry: AutomationCategoryStatus[] = NEXUS_AUTOMATION_STATUS_REGISTRY,
): AutomationCategoryStatus[] {
  return registry.filter((s) => s.level_1_status === 'enabled_internal');
}

export function blockedCategories(
  registry: AutomationCategoryStatus[] = NEXUS_AUTOMATION_STATUS_REGISTRY,
): AutomationCategoryStatus[] {
  return registry.filter((s) => s.blocked_actions.length > 0);
}
