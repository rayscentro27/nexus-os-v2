export interface AffiliateOpportunity {
  program_name: string;
  category: string;
  affiliate_url: string;
  dashboard_url: string | null;
  commission_type: string;
  payout_amount: string | null;
  cookie_window: string | null;
  offer_relevance: number;
  SEO_keyword_tie_in: string;
  content_angle: string;
  GoClear_offer_tie_in: string;
  status: 'candidate' | 'reviewing' | 'approved' | 'parked' | 'blocked';
  compliance_risk: 'low' | 'medium' | 'high';
  notes: string;
  last_checked_at: string | null;
  proof_source: string;
}

export const AFFILIATE_CATEGORIES = [
  'business_credit',
  'funding_tools',
  'business_formation',
  'website_builders',
  'email_newsletter',
  'ai_tools',
  'seo_tools',
  'bookkeeping_accounting',
  'credit_monitoring',
  'trading_education_tools',
] as const;
