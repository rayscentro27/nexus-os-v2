export type HermesDecisionMemoryKind =
  | 'preferred_topic'
  | 'rejected_idea'
  | 'winning_angle'
  | 'preferred_format'
  | 'prioritized_offer'
  | 'scoring_adjustment'
  | 'repeated_recommendation'
  | 'successful_experiment'
  | 'trading_strategy_pattern'
  | 'compliance_concern'
  | 'ray_feedback';

export interface HermesDecisionMemory {
  memory_id: string;
  kind: HermesDecisionMemoryKind;
  title: string;
  summary: string;
  source_type: 'report' | 'project_card' | 'ray_feedback' | 'experiment_outcome' | 'recommendation';
  source_id: string | null;
  department: string | null;
  confidence: number;
  weight: number;
  safe_visibility: 'internal_summary';
  created_at: string;
  updated_at: string;
}

export interface HermesRecommendationHistory {
  recommendation_id: string;
  report_id: string | null;
  project_id: string | null;
  recommendation: string;
  rationale: string;
  decision: 'pending' | 'approved' | 'rejected' | 'changed' | 'parked';
  outcome_summary: string | null;
  created_at: string;
  updated_at: string;
}

export const HERMES_MEMORY_ALLOWED_DATA = [
  'safe internal summaries',
  'Ray feedback summaries',
  'decision outcomes',
  'experiment result summaries',
  'paper-only trading research summaries',
] as const;

export const HERMES_MEMORY_BLOCKED_DATA = [
  'secrets',
  'cookies',
  'tokens',
  'raw private customer data',
  'broker credentials',
  'unredacted sensitive credit/funding files',
] as const;
