export type HermesUiActionType = 'open_report' | 'open_approval' | 'view_source' | 'open_access_map' | 'draft_ray_review' | 'prepare_specialist_handoff' | 'open_intake' | 'open_scorecard' | 'open_report_template' | 'open_checklist' | 'draft_client_report' | 'draft_upgrade_recommendation';

export interface HermesUiAction {
  title: string;
  summary?: string;
  category?: string;
  status?: string;
  priority?: string;
  actionLabel: string;
  actionType: HermesUiActionType;
  href?: string;
  reportPath?: string;
  approvalId?: string;
  taskRequestId?: string;
  source: string;
  freshness?: string;
  approvalRequired?: boolean;
}

export const SAFE_HERMES_ACTION_TYPES: ReadonlySet<HermesUiActionType> = new Set([
  'open_report', 'open_approval', 'view_source', 'open_access_map', 'draft_ray_review', 'prepare_specialist_handoff', 'open_intake', 'open_scorecard', 'open_report_template', 'open_checklist', 'draft_client_report', 'draft_upgrade_recommendation',
]);

export function isSafeHermesUiAction(action: HermesUiAction): boolean {
  return SAFE_HERMES_ACTION_TYPES.has(action.actionType)
    && (!action.href || /^#\/?(?:reports|rayreview|hermes|system|research|monetization|clients|opportunity|automation|trading)/.test(action.href));
}
