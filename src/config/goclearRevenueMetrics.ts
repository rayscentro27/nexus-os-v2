export type GoClearMetricKey =
  | 'readiness_review_leads'
  | 'readiness_review_purchases_97'
  | 'upgrade_purchases_297_497'
  | 'subscription_prospects'
  | 'monthly_recurring_revenue'
  | 'funding_applications'
  | 'commission_opportunities'
  | 'affiliate_referral_clicks'
  | 'affiliate_referral_conversions'
  | 'nav_business_credit_partner_referrals'
  | 'beehiiv_newsletter_growth'
  | 'pictory_content_affiliate'
  | 'seo_content_leads'
  | 'booked_calls'
  | 'estimated_revenue_potential'
  | 'actual_revenue';

export type GoClearPipelineStage =
  | 'source_detected'
  | 'lead'
  | 'readiness_review'
  | 'upgrade_candidate'
  | 'partner_referral'
  | 'booked_call'
  | 'converted'
  | 'needs_connector';

export interface GoClearRevenueMetric {
  metric_key: GoClearMetricKey;
  label: string;
  value: number | null;
  unit: 'count' | 'usd' | 'percent' | 'status';
  conversion_stage: GoClearPipelineStage;
  estimated_revenue_potential: number | null;
  actual_revenue: number | null;
  proof_event_id?: string | null;
  source_department: string;
  updated_at: string;
}

export interface GoClearAffiliateStats {
  partner: 'Nav' | 'Beehiiv' | 'Pictory' | 'Other';
  clicks: number | null;
  conversions: number | null;
  estimated_commission: number | null;
  actual_commission: number | null;
  source: string;
  updated_at: string;
}

export const GOCLEAR_REVENUE_METRIC_DEFINITIONS: Record<GoClearMetricKey, {
  label: string;
  unit: GoClearRevenueMetric['unit'];
  defaultStage: GoClearPipelineStage;
}> = {
  readiness_review_leads: { label: 'Readiness review leads', unit: 'count', defaultStage: 'lead' },
  readiness_review_purchases_97: { label: '$97 readiness review purchases', unit: 'count', defaultStage: 'converted' },
  upgrade_purchases_297_497: { label: '$297/$497 upgrades', unit: 'count', defaultStage: 'converted' },
  subscription_prospects: { label: 'Subscription prospects', unit: 'count', defaultStage: 'upgrade_candidate' },
  monthly_recurring_revenue: { label: 'Monthly recurring revenue', unit: 'usd', defaultStage: 'converted' },
  funding_applications: { label: 'Funding applications', unit: 'count', defaultStage: 'readiness_review' },
  commission_opportunities: { label: 'Commission opportunities', unit: 'usd', defaultStage: 'partner_referral' },
  affiliate_referral_clicks: { label: 'Affiliate/referral clicks', unit: 'count', defaultStage: 'partner_referral' },
  affiliate_referral_conversions: { label: 'Affiliate/referral conversions', unit: 'count', defaultStage: 'converted' },
  nav_business_credit_partner_referrals: { label: 'Nav/business credit partner referrals', unit: 'count', defaultStage: 'partner_referral' },
  beehiiv_newsletter_growth: { label: 'Beehiiv/newsletter growth', unit: 'count', defaultStage: 'lead' },
  pictory_content_affiliate: { label: 'Pictory/content affiliate', unit: 'count', defaultStage: 'partner_referral' },
  seo_content_leads: { label: 'SEO/content leads', unit: 'count', defaultStage: 'lead' },
  booked_calls: { label: 'Booked calls', unit: 'count', defaultStage: 'booked_call' },
  estimated_revenue_potential: { label: 'Estimated revenue potential', unit: 'usd', defaultStage: 'source_detected' },
  actual_revenue: { label: 'Actual revenue', unit: 'usd', defaultStage: 'converted' },
};
