/**
 * Controlled GoClear service offers.
 *
 * This is safe public display/configuration data. The authoritative amount used
 * to create checkout sessions is read from service_offers on the server.
 */
export type ServiceOfferSlug =
  | 'readiness-review-97'
  | 'readiness-action-plan-297'
  | 'funding-readiness-concierge-497'
  | 'invited-readiness-test'
  | 'real-payment-pilot-1';

export type FulfillmentType = 'readiness_review' | 'action_plan' | 'concierge' | 'invited_test' | 'pilot_test';

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

export type InvitationTestingLevel = 'synthetic_internal' | 'invited_test_mode' | 'controlled_live_pilot';

export interface PilotOffer {
  id: string;
  slug: string;
  name: string;
  price_cents: number;
  is_test_pilot_offer: boolean;
  publicly_visible: boolean;
  requires_invitation: boolean;
  requires_allowlist: boolean;
  max_orders_per_client: number;
  max_orders_per_invitation: number;
  active: boolean;
  live_activation_status: 'disabled' | 'enabled' | 'paused';
  payment_mode_required: 'test' | 'controlled_live_pilot';
  refund_supported: boolean;
  terms_version: string;
  pilot_disclosure_version: string;
  maximum_total_pilot_orders: number;
  pilot_start_at: string | null;
  pilot_end_at: string | null;
}

export const HIDDEN_PILOT_OFFERS: readonly PilotOffer[] = [
  {
    id: 'offer_invited_readiness_test',
    slug: 'invited-readiness-test',
    name: 'Invited Readiness Test',
    price_cents: 100,
    is_test_pilot_offer: false,
    publicly_visible: false,
    requires_invitation: true,
    requires_allowlist: false,
    max_orders_per_client: 1,
    max_orders_per_invitation: 1,
    active: false,
    live_activation_status: 'disabled',
    payment_mode_required: 'test',
    refund_supported: false,
    terms_version: 'readiness-services-v1',
    pilot_disclosure_version: 'pilot-disclosure-v1',
    maximum_total_pilot_orders: 50,
    pilot_start_at: null,
    pilot_end_at: null,
  },
  {
    id: 'offer_real_payment_pilot_1',
    slug: 'real-payment-pilot-1',
    name: 'Real Payment Pilot ($1)',
    price_cents: 100,
    is_test_pilot_offer: true,
    publicly_visible: false,
    requires_invitation: true,
    requires_allowlist: true,
    max_orders_per_client: 1,
    max_orders_per_invitation: 1,
    active: false,
    live_activation_status: 'disabled',
    payment_mode_required: 'controlled_live_pilot',
    refund_supported: true,
    terms_version: 'readiness-services-v1',
    pilot_disclosure_version: 'pilot-disclosure-v1',
    maximum_total_pilot_orders: 10,
    pilot_start_at: null,
    pilot_end_at: null,
  },
] as const;

export const PILOT_DISCLOSURE_TEXT = 'This is a limited paid product-testing program. It is not the full $97 Credit & Funding Readiness Review. The $1 charge is used to test the real payment, onboarding, portal, review, delivery, and refund experience. Testing participation and feedback are part of this pilot. No funding, credit, deletion, approval, timeline, or outcome is guaranteed.' as const;

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
  {
    id: 'offer_invited_readiness_test',
    slug: 'invited-readiness-test',
    name: 'Invited Readiness Test',
    tier: 1,
    price_cents: 100,
    currency: 'usd',
    description: 'A test-mode purchase for invited testers to verify the payment and onboarding flow. No real charge is processed.',
    deliverables: ['Test-mode checkout verification', 'Onboarding flow test', 'Portal experience validation'],
    client_provides: ['Test payment card', 'Completion of assigned checklist', 'Feedback submission'],
    exclusions: ['No real payment', 'No funding review', 'No credit analysis', 'Test environment only'],
    consultation_entitlement: 'none',
    active: false,
    test_price_id_env: 'STRIPE_TEST_PRICE_INVITED_TEST',
    public_route: '/tester/tasks',
    terms_version: 'readiness-services-v1',
    refund_policy_reference: 'refund-policy-v1',
    privacy_notice_reference: 'privacy-notice-v1',
    readiness_scope: ['payment_test', 'onboarding_test'],
    fulfillment_type: 'invited_test',
  },
];

export function getServiceOffer(slug: string): ServiceOffer | undefined {
  return SERVICE_OFFER_CATALOG.find((offer) => offer.slug === slug);
}

export function formatOfferPrice(offer: Pick<ServiceOffer, 'price_cents' | 'currency'>): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: offer.currency }).format(offer.price_cents / 100);
}
