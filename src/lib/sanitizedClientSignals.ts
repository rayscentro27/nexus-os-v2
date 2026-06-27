/**
 * Nexus OS v2 — Sanitized client signals model.
 *
 * Converts raw client workflow profiles into the aggregate, PII-free signal set that Hermes is
 * allowed to read. Deterministic. No raw names, credit data, account numbers, statements, or letters.
 */
import type { ClientWorkflowProfile } from '../config/clientWorkflow';
import { HERMES_SAFE_SIGNAL_KEYS } from '../config/hermesSafeClientSignalPolicy';

export interface SanitizedClientSignals {
  total_clients_by_stage: Record<string, number>;
  stuck_clients_count: number;
  credit_reports_pending_count: number;
  smartcredit_selected_count: number;
  annualcreditreport_selected_count: number;
  no_score_available_count: number;
  business_setup_incomplete_count: number;
  letters_ready_count: number;
  mailing_pending_count: number;
  mailing_proof_missing_count: number;
  funding_ready_count: number;
  ray_review_needed_count: number;
  affiliate_opportunity_count: number;
  revenue_risk_count: number;
  estimated_commission_delayed: number;
  recommended_next_actions: string[];
}

export interface ClientWorkflowSignalInputs {
  business_incomplete?: boolean;
  letters_ready?: boolean;
  mailing_pending?: boolean;
  mailing_proof_missing?: boolean;
  affiliate_opportunity?: boolean;
  estimated_commission?: number;
}

/**
 * Build sanitized signals. `profiles` carry NO raw PII into the output — only stages/flags/counts.
 * `inputsByClient` is optional per-client boolean flags computed elsewhere (also PII-free).
 */
export function buildSanitizedClientSignals(
  profiles: ClientWorkflowProfile[],
  inputsByClient: Record<string, ClientWorkflowSignalInputs> = {},
): SanitizedClientSignals {
  const byStage: Record<string, number> = {};
  let stuck = 0, pending = 0, smartcredit = 0, acr = 0, noScore = 0, businessIncomplete = 0;
  let lettersReady = 0, mailingPending = 0, mailingProofMissing = 0, fundingReady = 0, rayReview = 0;
  let affiliate = 0, revenueRisk = 0, commissionDelayed = 0;

  for (const p of profiles) {
    byStage[p.current_stage] = (byStage[p.current_stage] ?? 0) + 1;
    const ins = inputsByClient[p.client_id] ?? {};
    if (p.days_stuck >= 7) stuck += 1;
    if (p.current_stage === 'credit_report_pending') pending += 1;
    if (p.selected_credit_report_source === 'smartcredit') smartcredit += 1;
    if (p.selected_credit_report_source === 'annualcreditreport') acr += 1;
    if (!p.score_available) noScore += 1;
    if (ins.business_incomplete) businessIncomplete += 1;
    if (ins.letters_ready) lettersReady += 1;
    if (ins.mailing_pending) mailingPending += 1;
    if (ins.mailing_proof_missing) mailingProofMissing += 1;
    if (p.current_stage === 'funding_ready') fundingReady += 1;
    if (p.current_stage === 'ray_review_needed' || p.ray_review_status === 'pending_review') rayReview += 1;
    if (ins.affiliate_opportunity) affiliate += 1;
    if (p.revenue_risk_level === 'high' || p.revenue_risk_level === 'critical') revenueRisk += 1;
    commissionDelayed += ins.estimated_commission ?? 0;
  }

  const recommended: string[] = [];
  if (pending > 0) recommended.push(`${pending} client(s) stuck at credit report upload — follow up.`);
  if (noScore > 0) recommended.push(`${noScore} client(s) have no score — recommend SmartCredit or manual entry.`);
  if (businessIncomplete > 0) recommended.push(`${businessIncomplete} client(s) missing business setup items.`);
  if (mailingProofMissing > 0) recommended.push(`${mailingProofMissing} client(s) have letters but no mailing proof.`);
  if (rayReview > 0) recommended.push(`${rayReview} client(s) ready for Ray review.`);
  if (recommended.length === 0) recommended.push('No urgent client workflow actions.');

  return {
    total_clients_by_stage: byStage,
    stuck_clients_count: stuck,
    credit_reports_pending_count: pending,
    smartcredit_selected_count: smartcredit,
    annualcreditreport_selected_count: acr,
    no_score_available_count: noScore,
    business_setup_incomplete_count: businessIncomplete,
    letters_ready_count: lettersReady,
    mailing_pending_count: mailingPending,
    mailing_proof_missing_count: mailingProofMissing,
    funding_ready_count: fundingReady,
    ray_review_needed_count: rayReview,
    affiliate_opportunity_count: affiliate,
    revenue_risk_count: revenueRisk,
    estimated_commission_delayed: commissionDelayed,
    recommended_next_actions: recommended,
  };
}

/** Defense-in-depth: assert the signal object exposes only allow-listed keys. */
export function assertSignalsArePiiFree(signals: Record<string, unknown>): boolean {
  const allowed = new Set<string>(HERMES_SAFE_SIGNAL_KEYS);
  return Object.keys(signals).every((k) => allowed.has(k));
}
