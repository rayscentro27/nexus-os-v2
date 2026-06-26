export type ResearchAutonomyLane = 'autonomous_internal_research' | 'approval_gated_execution';

export const AUTONOMOUS_INTERNAL_RESEARCH_ACTIONS = [
  'watch_approved_resource',
  'backfill_approved_resource',
  'detect_new_content',
  'review_transcript',
  'score_research',
  'score_seo_keyword',
  'score_affiliate_opportunity',
  'route_to_department',
  'create_internal_project_card',
  'create_internal_experiment_card',
  'generate_internal_report',
  'update_hermes_memory',
  'paper_only_trading_research',
] as const;

export const APPROVAL_GATED_EXECUTION_ACTIONS = [
  'publish_campaign',
  'send_email_sms_dm_or_social',
  'launch_ads',
  'contact_leads_or_clients',
  'spend_money',
  'live_trade_or_broker_execution',
  'enable_persistent_scheduler',
  'change_production_system',
  'use_sensitive_data_in_external_tool',
  'run_action_outside_nexus',
] as const;

const AUTONOMOUS = new Set<string>(AUTONOMOUS_INTERNAL_RESEARCH_ACTIONS);
const GATED = new Set<string>(APPROVAL_GATED_EXECUTION_ACTIONS);

export function getResearchAutonomyLane(action: string): ResearchAutonomyLane {
  return GATED.has(action) ? 'approval_gated_execution' : 'autonomous_internal_research';
}

export function isApprovalRequiredForResearchAction(action: string): boolean {
  if (AUTONOMOUS.has(action)) return false;
  return GATED.has(action);
}

export const RESEARCH_AUTONOMY_COPY = {
  internal:
    'Approved resources can be watched, scored, routed, reported, and converted into internal experiment cards without Ray approving every item.',
  gated:
    'Publishing, sending, contacting, spending, live trading, scheduler activation, production changes, and sensitive external-tool use require Ray approval.',
} as const;
