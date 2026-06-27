/**
 * Nexus OS v2 — GoClear subscription + readiness offer registry (proposed, approval-required).
 *
 * Builds on goclearSubscriptionTiers.ts. Offers are PROPOSED only — no billing, no charge, no
 * activation. Pure / deterministic. No I/O.
 */
import { GOCLEAR_TIERS, type GoClearTierId } from './goclearSubscriptionTiers';

export type OfferLaunchStatus = 'proposed' | 'ray_approved' | 'launched';
export type BillingCycle = 'one_time' | 'monthly';

export interface GoClearOffer {
  offer_id: string;
  offer_name: string;
  price: number;
  price_range: [number, number];
  billing_cycle: BillingCycle;
  included_services: string[];
  client_stage: string;
  trigger_condition: string;
  upgrade_path: string | null;
  downgrade_path: string | null;
  retention_reason: string;
  convenience_value: string[];
  ray_approval_status: 'pending_review';
  launch_status: OfferLaunchStatus;
  approval_required: true;
}

const TIER = (id: GoClearTierId) => GOCLEAR_TIERS.find((t) => t.tier_id === id)!;

export const READINESS_REVIEW_OFFER: GoClearOffer = {
  offer_id: 'readiness_review',
  offer_name: 'GoClear/Apex Credit + Business Funding Readiness Review',
  price: 97,
  price_range: [97, 97],
  billing_cycle: 'one_time',
  included_services: ['credit readiness score', 'business bankability score', 'top blockers', 'next actions', 'Ray-approved action plan'],
  client_stage: 'profile_created',
  trigger_condition: 'New signup / profile created.',
  upgrade_path: 'credit_action_plan (monthly subscription)',
  downgrade_path: null,
  retention_reason: 'Funds the relationship and routes into the subscription.',
  convenience_value: ['one clear plan', 'dashboard', 'prepared recommendations'],
  ray_approval_status: 'pending_review',
  launch_status: 'proposed',
  approval_required: true,
};

function tierOffer(id: GoClearTierId, clientStage: string, trigger: string, upgrade: string | null, downgrade: string | null): GoClearOffer {
  const t = TIER(id);
  return {
    offer_id: id,
    offer_name: t.name,
    price: t.recommended_monthly,
    price_range: t.recommended_range,
    billing_cycle: 'monthly',
    included_services: t.includes,
    client_stage: clientStage,
    trigger_condition: trigger,
    upgrade_path: upgrade,
    downgrade_path: downgrade,
    retention_reason: t.retention_reason,
    convenience_value: t.convenience_value,
    ray_approval_status: 'pending_review',
    launch_status: 'proposed',
    approval_required: true,
  };
}

export const SUBSCRIPTION_OFFERS: GoClearOffer[] = [
  tierOffer('credit_action_plan', 'credit_analysis_ready', 'Client needs credit guidance + score/report tracking.', 'credit_plus_business_setup', null),
  tierOffer('credit_plus_business_setup', 'business_setup_needed', 'Client needs credit repair plus business foundation.', 'funding_readiness', 'credit_action_plan'),
  tierOffer('funding_readiness', 'funding_readiness_pending', 'Client is preparing for funding.', 'post_funding_growth', 'credit_plus_business_setup'),
  tierOffer('post_funding_growth', 'funding_ready', 'Funded client maintaining/growing business credit.', null, 'funding_readiness'),
];

export const ALL_GOCLEAR_OFFERS: GoClearOffer[] = [READINESS_REVIEW_OFFER, ...SUBSCRIPTION_OFFERS];

export function getGoClearOffer(id: string): GoClearOffer | undefined {
  return ALL_GOCLEAR_OFFERS.find((o) => o.offer_id === id);
}
