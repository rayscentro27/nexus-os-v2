/**
 * Nexus OS v2 — Client workflow monetization mapping.
 *
 * Connects workflow tasks/stages to revenue paths: revenue opportunity score, affiliate opportunity
 * score, subscription retention reason, and funding commission potential. Internal-only and
 * deterministic. All client-facing recommendations remain approval-gated.
 */
import type { ClientWorkflowStage } from '../config/clientWorkflow';

export interface TaskMonetization {
  task_key: string;
  revenue_path: string;
  recommended_partner: string | null;
  diy_option: string | null;
  revenue_opportunity_score: number; // 0-100
  affiliate_opportunity_score: number; // 0-100
  subscription_retention_reason: string;
  funding_commission_potential: 'none' | 'low' | 'medium' | 'high';
  approval_gated: true;
}

function t(
  task_key: string,
  revenue_path: string,
  recommended_partner: string | null,
  diy_option: string | null,
  revenue: number,
  affiliate: number,
  retention: string,
  funding: TaskMonetization['funding_commission_potential'] = 'none',
): TaskMonetization {
  return {
    task_key,
    revenue_path,
    recommended_partner,
    diy_option,
    revenue_opportunity_score: revenue,
    affiliate_opportunity_score: affiliate,
    subscription_retention_reason: retention,
    funding_commission_potential: funding,
    approval_gated: true,
  };
}

/** Task → monetization mapping (mirrors the workflow task templates). */
export const TASK_MONETIZATION: TaskMonetization[] = [
  t('choose_credit_report_source', 'credit_monitoring affiliate', 'SmartCredit', 'AnnualCreditReport.com (free)', 70, 80, 'Score tracking keeps clients subscribed for monthly progress.', 'low'),
  t('connect_smartcredit_or_upload_report', 'credit_monitoring affiliate', 'SmartCredit', 'Manual upload', 70, 80, 'Ongoing monitoring is the core monthly value.', 'low'),
  t('enter_credit_scores_if_missing', 'subscription value', null, 'Manual score entry', 30, 20, 'Score visibility drives monthly engagement.', 'low'),
  t('review_credit_analysis', 'readiness review + subscription', null, null, 60, 10, 'Monthly action plans keep clients on track.', 'low'),
  t('approve_dispute_letters', 'mailing affiliate', 'DocuPost', 'USPS Certified Mail', 55, 55, 'Letter tracking is a recurring convenience.', 'low'),
  t('choose_mailing_method', 'mailing affiliate', 'DocuPost', 'USPS Certified Mail', 55, 55, 'Mailing + deadline tracking retains clients.', 'low'),
  t('confirm_business_entity', 'business_formation affiliate', 'Formation partner', 'State SoS (DIY)', 70, 70, 'Business setup extends the relationship past credit.', 'medium'),
  t('add_ein', 'business_formation affiliate', 'Formation partner', 'IRS.gov (free)', 40, 40, 'Guided setup adds convenience value.', 'low'),
  t('add_business_bank_account', 'online_business_bank affiliate', 'Bluevine (primary)', 'Client’s own bank/credit union', 75, 70, 'Bank statements are required for funding; ongoing tracking retains clients.', 'high'),
  t('add_duns_profile', 'business_credit_profile affiliate', 'Business credit tool', 'Free DUNS from D&B', 60, 65, 'Business credit building is a long-term subscription driver.', 'medium'),
  t('add_vendor_accounts', 'vendor_credit affiliate', 'Vendor credit partner', 'Net-30 vendors (DIY)', 60, 60, 'Vendor tradelines build over months — recurring value.', 'medium'),
  t('upload_bank_statements', 'funding readiness', null, 'From client bank', 50, 0, 'Funding readiness tracking retains clients toward funding.', 'high'),
  t('complete_funding_readiness_review', 'funding commission pipeline', null, null, 80, 0, 'Funding-ready clients move to the post-funding tier.', 'high'),
  t('review_recommended_funding_path', 'funding commission pipeline', null, null, 85, 0, 'Approved funding path is the highest-value moment.', 'high'),
  t('book_funding_strategy_call', 'funding commission pipeline', null, null, 70, 0, 'Strategy call deepens retention and funding outcomes.', 'high'),
];

const BY_TASK = new Map(TASK_MONETIZATION.map((m) => [m.task_key, m]));

export function monetizationForTask(taskKey: string): TaskMonetization | undefined {
  return BY_TASK.get(taskKey);
}

/** Stage → headline monetization signal for the workflow card. */
export const STAGE_MONETIZATION: Partial<Record<ClientWorkflowStage, string>> = {
  credit_report_source_needed: 'SmartCredit (affiliate) vs AnnualCreditReport.com (free).',
  credit_report_pending: 'SmartCredit recommendation if no score.',
  business_setup_needed: 'Formation / online bank / DUNS partner vs DIY options.',
  business_setup_in_progress: 'Online business bank account (Bluevine) vs client’s own bank.',
  letters_ready: 'DocuPost (affiliate) vs USPS certified mail (DIY).',
  funding_readiness_pending: 'Funding readiness → commission pipeline (Ray-approved).',
  ray_review_needed: 'Approve client-facing plan + funding path.',
  funding_ready: 'Funding commission opportunity + post-funding subscription tier.',
};

export function summarizeMonetization(): { total_tasks: number; avg_revenue_score: number; high_funding_tasks: number } {
  const total = TASK_MONETIZATION.length;
  const avg = Math.round(TASK_MONETIZATION.reduce((s, m) => s + m.revenue_opportunity_score, 0) / total);
  const highFunding = TASK_MONETIZATION.filter((m) => m.funding_commission_potential === 'high').length;
  return { total_tasks: total, avg_revenue_score: avg, high_funding_tasks: highFunding };
}
