export type RayDecisionType =
  | 'campaign_publish'
  | 'email_send'
  | 'social_post'
  | 'lead_contact'
  | 'client_action'
  | 'scheduler_activation'
  | 'production_change'
  | 'trading_live_execution_blocked'
  | 'high_value_strategy_choice'
  | 'compliance_review'
  | 'revenue_decision'
  | 'connector_setup'
  | 'experiment_selection'
  | 'report_review';

export type RayReviewStatus =
  | 'pending_review'
  | 'reviewed'
  | 'approved'
  | 'rejected'
  | 'changes_requested'
  | 'parked'
  | 'escalated'
  | 'completed';

export type RayReviewPriority = 'low' | 'medium' | 'high' | 'urgent';
export type RayReviewRiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface RayReviewQueueItem {
  review_id: string;
  title: string;
  decision_type: RayDecisionType;
  department: string;
  source_table: string;
  source_id: string;
  source_url: string | null;
  status: RayReviewStatus;
  priority: RayReviewPriority;
  risk_level: RayReviewRiskLevel;
  approval_required: boolean;
  ray_decision_required: boolean;
  due_at: string | null;
  summary: string;
  hermes_recommendation: string;
  options: string[];
  pros: string[];
  cons: string[];
  expected_outcome: string;
  risk_notes: string[];
  proof_event_id: string | null;
  report_path: string | null;
  created_at: string;
  updated_at: string;
}

export const RAY_DECISION_TYPES: RayDecisionType[] = [
  'campaign_publish',
  'email_send',
  'social_post',
  'lead_contact',
  'client_action',
  'scheduler_activation',
  'production_change',
  'trading_live_execution_blocked',
  'high_value_strategy_choice',
  'compliance_review',
  'revenue_decision',
  'connector_setup',
  'experiment_selection',
  'report_review',
];
