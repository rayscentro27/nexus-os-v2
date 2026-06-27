/**
 * Nexus OS v2 — Client Workflow status + scoring engine.
 *
 * Deterministic, internal-only. Computes stage progress, days_stuck, credit/business/funding
 * readiness scores, blockers, and next actions. Produces NO client-facing output and NEVER exposes
 * a recommendation until Ray-approves (callers must gate on ray_review_status).
 */
import {
  CLIENT_WORKFLOW_STAGES,
  STAGE_NEXT_ACTION,
  CLIENT_VISIBLE_STAGE_LABEL,
  BUSINESS_SETUP_ITEMS,
  type ClientWorkflowStage,
  type ClientWorkflowProfile,
  type BusinessSetupPath,
  type CompletionStatus,
  type RevenueRiskLevel,
} from '../config/clientWorkflow';
import { revenueRiskForDaysStuck } from '../config/clientWorkflowReminders';

export function stageIndex(stage: ClientWorkflowStage): number {
  return Math.max(0, CLIENT_WORKFLOW_STAGES.indexOf(stage));
}

export function progressPercentage(stage: ClientWorkflowStage): number {
  const idx = stageIndex(stage);
  const last = CLIENT_WORKFLOW_STAGES.length - 1;
  return Math.round((idx / last) * 100);
}

export function nextRequiredAction(stage: ClientWorkflowStage): string {
  return STAGE_NEXT_ACTION[stage];
}

export function clientVisibleStatus(stage: ClientWorkflowStage): string {
  return CLIENT_VISIBLE_STAGE_LABEL[stage];
}

/** Whole-day difference between two ISO timestamps (>= 0). */
export function daysBetween(fromIso: string, toIso: string): number {
  const from = Date.parse(fromIso);
  const to = Date.parse(toIso);
  if (!Number.isFinite(from) || !Number.isFinite(to)) return 0;
  return Math.max(0, Math.floor((to - from) / 86_400_000));
}

export function daysStuck(lastActivityIso: string, nowIso = new Date().toISOString()): number {
  return daysBetween(lastActivityIso, nowIso);
}

// ---- Credit analysis --------------------------------------------------------

export interface CreditAnalysisInput {
  scores?: number[]; // any bureau scores available
  utilization_percent?: number;
  negative_accounts?: number;
  collections?: number;
  charge_offs?: number;
  late_payments?: number;
  inquiries?: number;
  account_age_years?: number;
  open_tradelines?: number;
  public_records?: number;
}

export interface CreditAnalysisResult {
  credit_readiness_score: number; // 0-100
  funding_readiness_contribution: number; // 0-100
  top_blockers: string[];
  next_actions: string[];
  dispute_candidates: number;
  score_available: boolean;
}

export function analyzeCredit(input: CreditAnalysisInput): CreditAnalysisResult {
  const scoreAvailable = Array.isArray(input.scores) && input.scores.length > 0;
  const avgScore = scoreAvailable ? input.scores!.reduce((a, b) => a + b, 0) / input.scores!.length : 0;
  let readiness = scoreAvailable ? Math.max(0, Math.min(100, ((avgScore - 300) / 550) * 100)) : 40;

  const blockers: string[] = [];
  const negatives = (input.negative_accounts ?? 0) + (input.collections ?? 0) + (input.charge_offs ?? 0);
  if ((input.utilization_percent ?? 0) > 30) { readiness -= 15; blockers.push('High credit utilization (>30%).'); }
  if ((input.collections ?? 0) > 0) { readiness -= 12; blockers.push(`${input.collections} collection account(s).`); }
  if ((input.charge_offs ?? 0) > 0) { readiness -= 12; blockers.push(`${input.charge_offs} charge-off(s).`); }
  if ((input.late_payments ?? 0) > 0) { readiness -= 8; blockers.push(`${input.late_payments} late payment(s).`); }
  if ((input.inquiries ?? 0) > 4) { readiness -= 5; blockers.push('Many recent inquiries.'); }
  if ((input.public_records ?? 0) > 0) { readiness -= 15; blockers.push('Public record(s) present.'); }
  if ((input.account_age_years ?? 0) < 2) { readiness -= 5; blockers.push('Thin/young credit history.'); }

  readiness = Math.max(0, Math.min(100, Math.round(readiness)));
  const disputeCandidates = negatives + Math.min(input.inquiries ?? 0, 3);

  const nextActions: string[] = [];
  if ((input.utilization_percent ?? 0) > 30) nextActions.push('Pay down revolving balances below 30%.');
  if (disputeCandidates > 0) nextActions.push('Prepare disputes for inaccurate negative items.');
  if (!scoreAvailable) nextActions.push('Add scores via SmartCredit or manual entry for sharper analysis.');
  while (nextActions.length < 3) nextActions.push('Maintain on-time payments and low utilization.');

  return {
    credit_readiness_score: readiness,
    funding_readiness_contribution: Math.round(readiness * 0.5),
    top_blockers: blockers.slice(0, 3),
    next_actions: nextActions.slice(0, 3),
    dispute_candidates: disputeCandidates,
    score_available: scoreAvailable,
  };
}

// ---- Business bankability ---------------------------------------------------

export interface BusinessSetupState {
  setup_item_key: string;
  client_selected_path: BusinessSetupPath;
  completion_status: CompletionStatus;
}

export interface BankabilityResult {
  business_foundation_score: number;
  bankability_score: number;
  business_funding_readiness_score: number;
  missing_items: string[];
  high_risk_flags: string[];
  next_actions: string[];
}

export function scoreBankability(states: BusinessSetupState[], highRiskFlags: string[] = []): BankabilityResult {
  const byKey = new Map(states.map((s) => [s.setup_item_key, s]));
  let bankabilityEarned = 0;
  let bankabilityTotal = 0;
  let fundingEarned = 0;
  let fundingTotal = 0;
  const missing: string[] = [];

  for (const item of BUSINESS_SETUP_ITEMS) {
    bankabilityTotal += item.bankability_score_impact;
    fundingTotal += item.funding_readiness_score_impact;
    const state = byKey.get(item.setup_item_key);
    const done = state && (state.completion_status === 'completed' || state.completion_status === 'verified' || state.client_selected_path === 'already_completed');
    if (done) {
      bankabilityEarned += item.bankability_score_impact;
      fundingEarned += item.funding_readiness_score_impact;
    } else if (item.required_for_bankability) {
      missing.push(item.setup_item_name);
    }
  }

  const foundation = bankabilityTotal ? Math.round((bankabilityEarned / bankabilityTotal) * 100) : 0;
  const bankability = foundation;
  const fundingReadiness = fundingTotal ? Math.round((fundingEarned / fundingTotal) * 100) : 0;

  const nextActions = missing.slice(0, 3).map((m) => `Complete: ${m}.`);
  while (nextActions.length < 3) nextActions.push('Maintain consistent business identity across all records.');

  return {
    business_foundation_score: foundation,
    bankability_score: bankability,
    business_funding_readiness_score: fundingReadiness,
    missing_items: missing,
    high_risk_flags: highRiskFlags,
    next_actions: nextActions.slice(0, 3),
  };
}

// ---- Overall funding readiness ----------------------------------------------

export function fundingReadinessScore(credit: CreditAnalysisResult, business: BankabilityResult): number {
  return Math.round(credit.funding_readiness_contribution * 0.5 + business.business_funding_readiness_score * 0.5);
}

export function isFundingReady(credit: CreditAnalysisResult, business: BankabilityResult): boolean {
  return fundingReadinessScore(credit, business) >= 75 && business.missing_items.length === 0;
}

// ---- Profile recompute (status engine) --------------------------------------

export function recomputeProfile(
  profile: ClientWorkflowProfile,
  lastActivityIso: string,
  nowIso = new Date().toISOString(),
): ClientWorkflowProfile {
  const stuck = daysStuck(lastActivityIso, nowIso);
  const risk: RevenueRiskLevel = revenueRiskForDaysStuck(stuck);
  return {
    ...profile,
    progress_percentage: progressPercentage(profile.current_stage),
    next_required_action: nextRequiredAction(profile.current_stage),
    client_visible_status: clientVisibleStatus(profile.current_stage),
    days_stuck: stuck,
    revenue_risk_level: risk,
    updated_at: nowIso,
  };
}

/** A client-facing plan may only be exposed when Ray has approved it. */
export function canExposeClientPlan(profile: ClientWorkflowProfile): boolean {
  return profile.ray_review_status === 'approved' &&
    (profile.current_stage === 'approved_client_plan_ready' ||
      profile.current_stage === 'client_plan_visible' ||
      profile.current_stage === 'funding_ready');
}
