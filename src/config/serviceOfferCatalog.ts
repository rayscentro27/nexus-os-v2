/**
 * Controlled GoClear service offers.
 *
 * This is safe public display/configuration data. The authoritative amount used
 * to create checkout sessions is read from service_offers on the server.
 */
export type ServiceOfferSlug =
  | 'readiness-review-97'
  | 'readiness-action-plan-297'
  | 'funding-readiness-concierge-497';

export type FulfillmentType = 'readiness_review' | 'action_plan' | 'concierge';

export interface ServiceOffer {
  id: string;
  slug: ServiceOfferSlug;
  name: string;
  tier: 1 | 2 | 3;
  price_cents: number;
  currency: 'usd';
  description: string;
  deliverables: string[];
  client_provides: string[];
  exclusions: string[];
  consultation_entitlement: 'none' | 'one_review_session' | 'priority_consultation';
  active: boolean;
  test_price_id_env: string;
  public_route: string;
  terms_version: string;
  refund_policy_reference: string;
  privacy_notice_reference: string;
  readiness_scope: string[];
  fulfillment_type: FulfillmentType;
}

export const SERVICE_OFFER_DISCLAIMERS = [
  'Payment purchases a professional readiness-review service, not funding.',
  'Results depend on client information, documentation, review, and follow-through.',
  'Nexus does not guarantee funding approval, credit-score increases, deletion, financing, limits, or timelines.',
  'Nexus does not provide legal advice. Third-party lender and program decisions remain outside Nexus control.',
] as const;

const COMMON_EXCLUSIONS = [
  'No funding approval guarantee',
  'No credit-deletion or score-increase guarantee',
  'No legal advice',
  'No lender submission or funding application creation',
];

export const SERVICE_OFFER_CATALOG: readonly ServiceOffer[] = [
  {
    id: 'offer_readiness_review_97',
    slug: 'readiness-review-97',
    name: 'Credit & Funding Readiness Review',
    tier: 1,
    price_cents: 9700,
    currency: 'usd',
    description: 'An entry paid assessment that turns your current information into a readiness snapshot and prioritized next-action plan.',
    deliverables: ['Readiness snapshot', 'Credit and business readiness findings', 'Prioritized next-action plan', 'Document-gap review', 'Recommended review path'],
    client_provides: ['Current profile information', 'Relevant reports and supporting documents', 'Consent and authorization acknowledgements'],
    exclusions: COMMON_EXCLUSIONS,
    consultation_entitlement: 'none',
    active: true,
    test_price_id_env: 'STRIPE_TEST_PRICE_READINESS_REVIEW_97',
    public_route: '/readiness-review',
    terms_version: 'readiness-services-v1',
    refund_policy_reference: 'refund-policy-v1',
    privacy_notice_reference: 'privacy-notice-v1',
    readiness_scope: ['credit', 'business_foundation', 'business_bankability', 'funding_readiness'],
    fulfillment_type: 'readiness_review',
  },
  {
    id: 'offer_readiness_action_plan_297',
    slug: 'readiness-action-plan-297',
    name: 'Readiness Action Plan',
    tier: 2,
    price_cents: 29700,
    currency: 'usd',
    description: 'A deeper readiness review with a detailed corrective action plan and one approval-gated consultation or review session.',
    deliverables: ['Everything in the $97 review', 'Detailed corrective action plan', 'Prioritized credit and business tasks', 'Document checklist', 'Strategy review', 'One consultation or review session'],
    client_provides: ['Completed intake', 'Relevant reports and supporting documents', 'Questions and confirmations needed for review'],
    exclusions: COMMON_EXCLUSIONS,
    consultation_entitlement: 'one_review_session',
    active: true,
    test_price_id_env: 'STRIPE_TEST_PRICE_ACTION_PLAN_297',
    public_route: '/readiness-action-plan',
    terms_version: 'readiness-services-v1',
    refund_policy_reference: 'refund-policy-v1',
    privacy_notice_reference: 'privacy-notice-v1',
    readiness_scope: ['credit', 'business_foundation', 'business_bankability', 'funding_readiness'],
    fulfillment_type: 'action_plan',
  },
  {
    id: 'offer_funding_readiness_concierge_497',
    slug: 'funding-readiness-concierge-497',
    name: 'Funding Readiness Concierge',
    tier: 3,
    price_cents: 49700,
    currency: 'usd',
    description: 'Deeper document and bankability review with guided implementation support and priority approval-gated review.',
    deliverables: ['Everything in the $297 plan', 'Deeper document and bankability review', 'Guided implementation support', 'Readiness follow-up', 'Priority review', 'Additional consultation or support window'],
    client_provides: ['Completed intake', 'Current business and financial documentation', 'Questions and confirmations needed for review'],
    exclusions: COMMON_EXCLUSIONS,
    consultation_entitlement: 'priority_consultation',
    active: true,
    test_price_id_env: 'STRIPE_TEST_PRICE_CONCIERGE_497',
    public_route: '/funding-readiness-concierge',
    terms_version: 'readiness-services-v1',
    refund_policy_reference: 'refund-policy-v1',
    privacy_notice_reference: 'privacy-notice-v1',
    readiness_scope: ['credit', 'business_foundation', 'business_bankability', 'funding_readiness'],
    fulfillment_type: 'concierge',
  },
];

export function getServiceOffer(slug: string): ServiceOffer | undefined {
  return SERVICE_OFFER_CATALOG.find((offer) => offer.slug === slug);
}

export function formatOfferPrice(offer: Pick<ServiceOffer, 'price_cents' | 'currency'>): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: offer.currency }).format(offer.price_cents / 100);
}
