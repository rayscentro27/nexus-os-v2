/**
 * Nexus OS v2 — Four revenue streams (GoClear / Apex).
 *
 * Internal model — streams are PROPOSED, not launched. Nothing here charges, sends, or contacts.
 * Pure / deterministic. No I/O.
 */
import type { GoClearTierId } from './goclearSubscriptionTiers';

export type RevenueStreamId =
  | 'readiness_review'
  | 'monthly_subscription'
  | 'affiliate_partner_engine'
  | 'funding_commission_pipeline';

export interface RevenueStream {
  stream_id: RevenueStreamId;
  name: string;
  description: string;
  client_trigger: string;
  deliverables: string[];
  pricing_note: string;
  approval_gate: string;
  upsell_path: string;
  hermes_recommendation: string;
  status: 'proposed';
}

export interface AffiliateStreamItem {
  category: string;
  recommended_partner: string;
  diy_option: string;
  revenue_opportunity_score: number; // 0-100
}

export const AFFILIATE_STREAM_ITEMS: AffiliateStreamItem[] = [
  { category: 'credit_monitoring', recommended_partner: 'SmartCredit', diy_option: 'AnnualCreditReport.com (free)', revenue_opportunity_score: 80 },
  { category: 'business_formation', recommended_partner: 'Formation partner', diy_option: 'State SoS + IRS.gov (free EIN)', revenue_opportunity_score: 70 },
  { category: 'registered_agent', recommended_partner: 'Registered agent partner', diy_option: 'Self as agent', revenue_opportunity_score: 40 },
  { category: 'business_address', recommended_partner: 'Virtual address partner', diy_option: 'Existing commercial address', revenue_opportunity_score: 55 },
  { category: 'business_phone', recommended_partner: 'VoIP partner', diy_option: 'Any business line', revenue_opportunity_score: 45 },
  { category: 'website_domain_email', recommended_partner: 'Website/domain partner', diy_option: 'Self-built site + domain email', revenue_opportunity_score: 50 },
  { category: 'business_credit_profile', recommended_partner: 'Business credit tool', diy_option: 'Free DUNS from D&B', revenue_opportunity_score: 65 },
  { category: 'online_business_bank_account', recommended_partner: 'Bluevine (primary)', diy_option: 'Client’s own bank/credit union', revenue_opportunity_score: 70 },
  { category: 'bookkeeping_accounting', recommended_partner: 'Bookkeeping partner', diy_option: 'DIY spreadsheet', revenue_opportunity_score: 45 },
  { category: 'vendor_credit_accounts', recommended_partner: 'Vendor credit partner', diy_option: 'Open net-30 vendors directly', revenue_opportunity_score: 60 },
  { category: 'online_mailing', recommended_partner: 'DocuPost', diy_option: 'USPS Certified Mail', revenue_opportunity_score: 55 },
];

export const REVENUE_STREAMS: RevenueStream[] = [
  {
    stream_id: 'readiness_review',
    name: 'GoClear/Apex Credit + Business Funding Readiness Review',
    description: 'Front-end paid review that assesses credit + business funding readiness and produces a Ray-approved action plan.',
    client_trigger: 'New signup / profile created.',
    deliverables: ['credit readiness score', 'business bankability score', 'top blockers', 'next actions', 'Ray-approved action plan'],
    pricing_note: 'Likely starting point: $97 readiness review (validate against market).',
    approval_gate: 'Client-facing plan exposed only after Ray approval.',
    upsell_path: 'Into the monthly subscription (Credit + Business Setup tier).',
    hermes_recommendation: 'Offer the readiness review at signup; it funds the relationship and routes into the subscription.',
    status: 'proposed',
  },
  {
    stream_id: 'monthly_subscription',
    name: 'Monthly GoClear Subscription',
    description: 'Recurring tiers from credit action plan through post-funding growth.',
    client_trigger: 'After the readiness review or when ongoing tracking is needed.',
    deliverables: ['monitoring', 'monthly action plans', 'business setup tracking', 'funding readiness tracking'],
    pricing_note: 'Tiers: ~$49 / ~$97 / ~$197 / ~$149 post-funding (validate).',
    approval_gate: 'No client charged automatically; billing is a separate approved step.',
    upsell_path: 'Action Plan → Credit + Business Setup → Funding Readiness → Post-Funding Growth.',
    hermes_recommendation: 'Retention engine: clients stay for ongoing tracking after credit wins, then move to business credit + funding.',
    status: 'proposed',
  },
  {
    stream_id: 'affiliate_partner_engine',
    name: 'Affiliate + Partner Recommendation Engine',
    description: 'Per-task partner recommendations, each with a DIY/free option and disclosure.',
    client_trigger: 'A workflow task needs a tool/service (e.g., missing business bank account).',
    deliverables: ['recommended partner path', 'DIY/free option', 'affiliate disclosure', 'revenue opportunity score'],
    pricing_note: 'Commission/referral revenue; no client charged by Nexus.',
    approval_gate: 'Affiliate URLs activate only via approved partner_offers.',
    upsell_path: 'Recommendations align to the client’s current stage/missing tasks.',
    hermes_recommendation: 'Surface partner options only when relevant to a missing task; always show the DIY option.',
    status: 'proposed',
  },
  {
    stream_id: 'funding_commission_pipeline',
    name: 'Funding Commission / Funding Readiness Pipeline',
    description: 'Tracks clients to funding-ready, routes Ray-approved funding paths, and tracks commission opportunity. Funding applications are never automated.',
    client_trigger: 'Client reaches funding-ready status.',
    deliverables: ['funding readiness confirmation', 'Ray-approved funding path', 'commission opportunity tracking', 'post-funding tier offer'],
    pricing_note: 'Funding commission opportunity (tracked, not auto-applied).',
    approval_gate: 'Ray approves the funding path; no auto-apply, no auto-contact lenders.',
    upsell_path: 'Into Post-Funding Growth subscription tier.',
    hermes_recommendation: 'Only route funding-ready clients; never send not-ready clients to lenders.',
    status: 'proposed',
  },
];

export function getRevenueStream(id: RevenueStreamId): RevenueStream | undefined {
  return REVENUE_STREAMS.find((s) => s.stream_id === id);
}

/** Subscription stream maps to the GoClear tiers. */
export const SUBSCRIPTION_TIER_ORDER: GoClearTierId[] = [
  'credit_action_plan',
  'credit_plus_business_setup',
  'funding_readiness',
  'post_funding_growth',
];
