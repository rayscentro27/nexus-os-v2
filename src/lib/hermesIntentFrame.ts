export type IntentType =
  | 'greeting'
  | 'trace_question'
  | 'status_question'
  | 'record_lookup'
  | 'domain_review'
  | 'business_advice'
  | 'advisory_followup'
  | 'selection_followup'
  | 'approval_action_draft'
  | 'specialist_handoff'
  | 'build_planning'
  | 'page_context'
  | 'brain_capability_status'
  | 'general_advisor'
  | 'casual_common'
  | 'external_current_info'
  | 'unknown';

export type IntentDomain =
  | 'business_opportunities'
  | 'approvals'
  | 'clients'
  | 'monetization'
  | 'research'
  | 'trading'
  | 'credit_funding'
  | 'nexus_product_build'
  | 'system_health'
  | 'reports'
  | 'ray_review'
  | 'current_page'
  | 'specialist_agents'
  | 'trace'
  | 'general_conversation'
  | 'external_info'
  | 'unknown';

export type IntentTarget = {
  type?: 'record' | 'ranked_item' | 'named_offer' | 'page' | 'report' | 'last_answer' | 'active_session_item' | 'none';
  label?: string;
  rank?: number;
  id?: string;
  confidence: number;
};

export type IntentAction =
  | 'answer'
  | 'review'
  | 'compare'
  | 'recommend'
  | 'improve'
  | 'explain_score'
  | 'draft_ray_review'
  | 'prepare_handoff'
  | 'explain_source'
  | 'block_or_gate'
  | 'list_inventory'
  | 'none';

export type SourceNeed =
  | 'live_records_required'
  | 'report_preferred'
  | 'local_trace'
  | 'session_context'
  | 'page_context'
  | 'general_reasoning'
  | 'none';

export type FollowupType = 'selection' | 'advisory' | 'trace' | 'domain_review' | 'active_session';

export type SafetyDisposition = 'safe' | 'approval_required' | 'blocked';

export interface HermesIntentFrame {
  rawMessage: string;
  normalizedMessage: string;

  intent: IntentType;
  domain: IntentDomain;
  target: IntentTarget;
  action: IntentAction;
  sourceNeed: SourceNeed;

  isFollowup: boolean;
  followupType?: FollowupType;

  safetyDisposition: SafetyDisposition;
  confidence: number;

  signals: string[];
}
