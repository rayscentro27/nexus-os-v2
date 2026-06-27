/**
 * Nexus OS v2 — Hermes Client Workflow recommendation layer.
 *
 * When Ray enters the Client Workflow department, Hermes proactively generates internal-only
 * recommendations from client workflow data: stuck clients, missing tasks, mailing gaps, funding
 * blockers, Ray-Review-ready clients, upsell/affiliate opportunities, and revenue risk.
 *
 * Deterministic. Output is INTERNAL ONLY unless approved. Never contacts clients, never sends.
 */
import type { ClientWorkflowProfile } from '../config/clientWorkflow';
import { REMINDER_TIMINGS } from '../config/clientWorkflowReminders';

export type HermesRecommendationKind =
  | 'stuck_client'
  | 'missing_task'
  | 'credit_report_pending'
  | 'smartcredit_incomplete'
  | 'no_score_available'
  | 'business_setup_incomplete'
  | 'letters_unmailed'
  | 'mailing_proof_missing'
  | 'funding_blocker'
  | 'ready_for_ray_review'
  | 'upsell_opportunity'
  | 'near_funding_ready'
  | 'revenue_risk'
  | 'affiliate_opportunity'
  | 'do_not_send_to_lenders';

export interface HermesClientRecommendation {
  kind: HermesRecommendationKind;
  client_id: string;
  client_label: string;
  message: string;
  internal_only: true;
  approval_required: boolean;
  revenue_risk_level: ClientWorkflowProfile['revenue_risk_level'];
}

export interface ClientWorkflowSignals {
  letters_ready_not_mailed?: boolean;
  mailing_proof_missing?: boolean;
  business_missing_items?: string[];
  funding_readiness_score?: number;
  funding_blockers?: string[];
  high_utilization?: boolean;
}

/** Generate Hermes recommendations for a single client. Internal-only. */
export function recommendForClient(p: ClientWorkflowProfile, s: ClientWorkflowSignals = {}): HermesClientRecommendation[] {
  const out: HermesClientRecommendation[] = [];
  const base = { client_id: p.client_id, client_label: p.client_label, internal_only: true as const, revenue_risk_level: p.revenue_risk_level };

  if (p.days_stuck >= REMINDER_TIMINGS.stuck_task_days) {
    out.push({ ...base, kind: 'stuck_client', message: `${p.client_label} has been stuck ${p.days_stuck} days at "${p.current_stage}".`, approval_required: false });
  }
  if (p.current_stage === 'credit_report_pending') {
    out.push({ ...base, kind: 'credit_report_pending', message: `${p.client_label} still needs to provide a credit report.`, approval_required: false });
  }
  if (p.selected_credit_report_source === 'smartcredit' && p.report_upload_status !== 'received' && p.report_import_status !== 'received') {
    out.push({ ...base, kind: 'smartcredit_incomplete', message: `${p.client_label} selected SmartCredit but hasn't completed signup/import.`, approval_required: false });
  }
  if (p.selected_credit_report_source === 'annualcreditreport' && !p.score_available) {
    out.push({ ...base, kind: 'no_score_available', message: `${p.client_label} used AnnualCreditReport.com (no score). Recommend SmartCredit for score tracking, or enter a score manually.`, approval_required: false });
  }
  if (s.business_missing_items && s.business_missing_items.length > 0) {
    out.push({ ...base, kind: 'business_setup_incomplete', message: `${p.client_label} is missing: ${s.business_missing_items.slice(0, 3).join(', ')}.`, approval_required: false });
  }
  if (s.letters_ready_not_mailed) {
    out.push({ ...base, kind: 'letters_unmailed', message: `${p.client_label} has approved letters not yet mailed.`, approval_required: false });
  }
  if (s.mailing_proof_missing) {
    out.push({ ...base, kind: 'mailing_proof_missing', message: `${p.client_label} mailed letters but no proof/receipt was uploaded.`, approval_required: false });
  }
  if (s.funding_blockers && s.funding_blockers.length > 0) {
    out.push({ ...base, kind: 'funding_blocker', message: `${p.client_label} funding blockers: ${s.funding_blockers.slice(0, 3).join(', ')}.`, approval_required: false });
  }
  if (p.current_stage === 'ray_review_needed' || p.ray_review_status === 'pending_review') {
    out.push({ ...base, kind: 'ready_for_ray_review', message: `${p.client_label} has a full action plan ready for Ray review.`, approval_required: true });
  }
  const score = s.funding_readiness_score ?? p.funding_readiness_impact;
  if (score >= 60 && score < 75) {
    out.push({ ...base, kind: 'near_funding_ready', message: `${p.client_label} is near funding-ready (${score}/100)${s.high_utilization ? ' but has high utilization' : ''}.`, approval_required: false });
    out.push({ ...base, kind: 'upsell_opportunity', message: `${p.client_label} is a future commission opportunity once remaining blockers clear.`, approval_required: false });
  }
  if (score < 60 && (p.current_stage === 'funding_readiness_pending' || p.current_stage === 'funding_ready')) {
    out.push({ ...base, kind: 'do_not_send_to_lenders', message: `${p.client_label} is NOT funding-ready (${score}/100). Do not route to lenders yet.`, approval_required: false });
  }
  if (p.revenue_risk_level === 'high' || p.revenue_risk_level === 'critical') {
    out.push({ ...base, kind: 'revenue_risk', message: `${p.client_label} is a ${p.revenue_risk_level} revenue risk (stuck ${p.days_stuck} days).`, approval_required: false });
  }
  return out;
}

export interface HermesWorkflowDigest {
  total_clients: number;
  stuck_clients: number;
  credit_reports_pending: number;
  smartcredit_incomplete: number;
  no_score: number;
  business_incomplete: number;
  letters_unmailed: number;
  mailing_proof_missing: number;
  ready_for_ray_review: number;
  upsell_opportunities: number;
  near_funding_ready: number;
  revenue_risk_clients: number;
  recommendations: HermesClientRecommendation[];
  top_recommendation: string;
}

/** Aggregate digest across all clients — the proactive department briefing. */
export function buildHermesWorkflowDigest(
  profiles: ClientWorkflowProfile[],
  signalsByClient: Record<string, ClientWorkflowSignals> = {},
): HermesWorkflowDigest {
  const all: HermesClientRecommendation[] = [];
  for (const p of profiles) all.push(...recommendForClient(p, signalsByClient[p.client_id] ?? {}));
  const count = (k: HermesRecommendationKind) => all.filter((r) => r.kind === k).length;
  const stuck = count('stuck_client');
  const rayReady = count('ready_for_ray_review');
  const top = rayReady > 0
    ? `${rayReady} client(s) ready for Ray review.`
    : stuck > 0
      ? `${stuck} client(s) stuck — follow up to protect revenue.`
      : 'No urgent client workflow actions. Keep advancing setup tasks.';
  return {
    total_clients: profiles.length,
    stuck_clients: stuck,
    credit_reports_pending: count('credit_report_pending'),
    smartcredit_incomplete: count('smartcredit_incomplete'),
    no_score: count('no_score_available'),
    business_incomplete: count('business_setup_incomplete'),
    letters_unmailed: count('letters_unmailed'),
    mailing_proof_missing: count('mailing_proof_missing'),
    ready_for_ray_review: rayReady,
    upsell_opportunities: count('upsell_opportunity'),
    near_funding_ready: count('near_funding_ready'),
    revenue_risk_clients: count('revenue_risk'),
    recommendations: all,
    top_recommendation: top,
  };
}
