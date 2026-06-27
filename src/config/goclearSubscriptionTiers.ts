/**
 * Nexus OS v2 — GoClear monthly subscription tiers + market pricing bands.
 *
 * Internal pricing RESEARCH model (report-only). Prices are estimates to validate, NOT live offers.
 * Pure / deterministic. No I/O, no external scraping. Nothing here charges anyone.
 */

export interface MarketPriceBand {
  category: string;
  low_monthly: number;
  typical_monthly: number;
  high_monthly: number;
  notes: string;
}

/** Curated market reference bands (USD/month) to validate — internal estimates, not scraped. */
export const MARKET_PRICE_BANDS: MarketPriceBand[] = [
  { category: 'Credit repair (DIY/service)', low_monthly: 19, typical_monthly: 79, high_monthly: 149, notes: 'Common credit-repair monthly service range.' },
  { category: 'Credit monitoring', low_monthly: 10, typical_monthly: 25, high_monthly: 40, notes: '3-bureau monitoring + score tracking.' },
  { category: 'Business credit monitoring', low_monthly: 39, typical_monthly: 79, high_monthly: 149, notes: 'Business credit profile + monitoring.' },
  { category: 'Business funding readiness/coaching', low_monthly: 97, typical_monthly: 199, high_monthly: 497, notes: 'Coaching/readiness programs.' },
  { category: 'Business credit builder subscription', low_monthly: 49, typical_monthly: 99, high_monthly: 199, notes: 'Vendor/tradeline + builder tools.' },
];

/** Services competitors commonly bundle into monthly plans (used for the comparison table). */
export const COMPETITOR_PLAN_FEATURES = [
  'credit report review',
  'dispute guidance',
  'credit monitoring',
  'score tracking',
  'portal access',
  'monthly updates',
  'letters/disputes',
  'creditor interventions',
  'business credit guidance',
  'funding preparation',
  'coaching/consultation',
  'reminders/follow-up',
  'document tracking',
] as const;

export type GoClearTierId = 'credit_action_plan' | 'credit_plus_business_setup' | 'funding_readiness' | 'post_funding_growth';

export interface GoClearTier {
  tier_id: GoClearTierId;
  name: string;
  pricing_band: 'low' | 'core' | 'premium' | 'post_funding';
  recommended_monthly: number;
  recommended_range: [number, number];
  includes: string[];
  convenience_value: string[];
  retention_reason: string;
  next_tier: GoClearTierId | null;
}

export const GOCLEAR_TIERS: GoClearTier[] = [
  {
    tier_id: 'credit_action_plan',
    name: 'Credit Monitoring & Action Plan',
    pricing_band: 'low',
    recommended_monthly: 49,
    recommended_range: [39, 69],
    includes: ['credit report review', 'score tracking (via SmartCredit)', 'dispute guidance', 'monthly action plan', 'portal access', 'reminders/follow-up'],
    convenience_value: ['client dashboard', 'reminders', 'SmartCredit score tracking', 'Ray-approved action plan'],
    retention_reason: 'Ongoing monitoring + monthly action steps keep progress visible after the first wins.',
    next_tier: 'credit_plus_business_setup',
  },
  {
    tier_id: 'credit_plus_business_setup',
    name: 'Credit + Business Setup',
    pricing_band: 'core',
    recommended_monthly: 97,
    recommended_range: [79, 129],
    includes: ['everything in Action Plan', 'business setup checklist', 'affiliate/DIY choices', 'letter packet tracking', 'document tracking', 'business credit guidance'],
    convenience_value: ['business setup checklist', 'affiliate/DIY choices', 'letter packet tracking', 'Credit Specialist prepared recommendations'],
    retention_reason: 'Clients keep building business credit and bankability after personal credit improves.',
    next_tier: 'funding_readiness',
  },
  {
    tier_id: 'funding_readiness',
    name: 'Funding Readiness',
    pricing_band: 'premium',
    recommended_monthly: 197,
    recommended_range: [149, 297],
    includes: ['everything in Credit + Business Setup', 'funding readiness tracking', 'bankability scoring', 'vendor accounts guidance', 'funding preparation', 'Ray-approved funding path'],
    convenience_value: ['funding readiness tracking', 'Hermes/Credit Specialist prepared recommendations', 'Ray-approved plans'],
    retention_reason: 'Clients want to reach and maintain funding-ready status before applying.',
    next_tier: 'post_funding_growth',
  },
  {
    tier_id: 'post_funding_growth',
    name: 'Post-Funding Growth',
    pricing_band: 'post_funding',
    recommended_monthly: 149,
    recommended_range: [99, 249],
    includes: ['monthly financial readiness tracking', 'business credit building', 'vendor accounts', 'grant/funding opportunity monitoring', 'bankability maintenance'],
    convenience_value: ['monthly financial readiness tracking', 'grant/funding opportunity monitoring'],
    retention_reason: 'After funding, clients keep growing business credit and monitoring new funding/grant opportunities.',
    next_tier: null,
  },
];

export function getGoClearTier(id: GoClearTierId): GoClearTier | undefined {
  return GOCLEAR_TIERS.find((t) => t.tier_id === id);
}

export const SUBSCRIPTION_DISCLAIMER =
  'Pricing figures are internal market-research estimates to validate, not live offers. No client is charged. Services are educational/planning and do not guarantee approval, deletion, score increase, or funding.';
