/**
 * Nexus OS v2 — Client Workflow affiliate recommendation model.
 *
 * Maps each client workflow need to a recommended partner AND a DIY/free/official option.
 * Reuses the partner_offers / client_recommendations tables at runtime. Pure / deterministic.
 *
 * Rules: always show a DIY/free option; never say the affiliate option is required; always
 * disclose affiliate/referral; never guarantee outcomes. Hermes recommends affiliate paths only
 * when relevant to a client's missing task/stage.
 */

export type AffiliateRecommendationCategory =
  | 'credit_monitoring'
  | 'business_formation'
  | 'registered_agent'
  | 'business_address'
  | 'business_phone'
  | 'website_domain_email'
  | 'business_credit_profile'
  | 'business_bank_account'
  | 'bookkeeping_accounting'
  | 'vendor_credit_accounts'
  | 'online_mailing'
  | 'funding_readiness_services';

export type ClientSelectedPath = 'partner' | 'diy' | 'already_completed' | 'not_applicable' | 'undecided';
export type ConversionStatus = 'none' | 'clicked' | 'signup_started' | 'converted' | 'declined';

export interface AffiliateRecommendation {
  category: AffiliateRecommendationCategory;
  partner_name: string | null;
  affiliate_url: string | null;
  disclosure_text: string;
  recommended_reason: string;
  diy_option_name: string;
  diy_option_url: string | null;
  client_selected_path: ClientSelectedPath;
  conversion_status: ConversionStatus;
  revenue_opportunity_score: number; // 0-100
  compliance_notes: string;
  /** workflow tie-in: setup_item_key or workflow need this maps to. */
  maps_to: string;
}

const DISCLOSURE = 'This is a recommended partner; we may earn a commission if you sign up. It is optional — a free/DIY option is always available.';
const NO_GUARANTEE = 'Educational/planning recommendation only. No guarantee of approval, deletion, score increase, or funding.';

function rec(
  category: AffiliateRecommendationCategory,
  partner_name: string | null,
  recommended_reason: string,
  diy_option_name: string,
  maps_to: string,
  revenue_opportunity_score: number,
): AffiliateRecommendation {
  return {
    category,
    partner_name,
    affiliate_url: null, // populated from partner_offers at runtime when approved
    disclosure_text: DISCLOSURE,
    recommended_reason,
    diy_option_name,
    diy_option_url: null,
    client_selected_path: 'undecided',
    conversion_status: 'none',
    revenue_opportunity_score,
    compliance_notes: NO_GUARANTEE,
    maps_to,
  };
}

export const AFFILIATE_RECOMMENDATIONS: AffiliateRecommendation[] = [
  rec('credit_monitoring', 'SmartCredit', 'Supports score visibility, monitoring, and smoother analysis.', 'AnnualCreditReport.com (free reports only)', 'credit_report_source', 80),
  rec('business_formation', 'Formation partner', 'Faster, guided LLC/EIN setup.', 'State Secretary of State + IRS.gov (free EIN)', 'llc_entity', 70),
  rec('registered_agent', 'Registered agent partner', 'Keeps your address private and compliant.', 'Act as your own registered agent', 'registered_agent', 40),
  rec('business_address', 'Virtual address partner', 'Real commercial address improves bankability.', 'Use an existing commercial address', 'business_address', 55),
  rec('business_phone', 'VoIP partner', 'Listed business phone improves bankability.', 'Any business phone line', 'business_phone', 45),
  rec('website_domain_email', 'Website/domain partner', 'Web presence + domain email build legitimacy.', 'Self-built site + domain email', 'website_domain', 50),
  rec('business_credit_profile', 'Business credit tool', 'Helps establish and monitor business credit.', 'Free DUNS request from D&B', 'duns_profile', 65),
  rec('business_bank_account', 'Business banking partner', 'Dedicated account is required for funding.', 'Open at any business bank', 'business_bank_account', 60),
  rec('bookkeeping_accounting', 'Bookkeeping partner', 'Clean books strengthen funding readiness.', 'DIY spreadsheet/accounting', 'bookkeeping', 45),
  rec('vendor_credit_accounts', 'Vendor credit partner', 'Reporting net-30 vendors build business credit.', 'Open net-30 vendors directly', 'vendor_accounts', 60),
  rec('online_mailing', 'DocuPost', 'Mail certified letters online without a Post Office trip.', 'USPS Certified Mail at your local Post Office', 'mailing', 55),
  rec('funding_readiness_services', 'Funding readiness partner', 'Guided help matching you to funding paths.', 'Use the internal funding readiness checklist', 'funding_readiness', 70),
];

export function affiliateRecommendationsFor(mapsTo: string): AffiliateRecommendation[] {
  return AFFILIATE_RECOMMENDATIONS.filter((r) => r.maps_to === mapsTo);
}
