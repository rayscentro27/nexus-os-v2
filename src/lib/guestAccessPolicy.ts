export const FREE_GUEST_ACCESS = {
  accessTier: 'FREE_GUEST',
  paymentBypassScope: 'ONBOARDING_AND_READINESS',
  fundingGate: 'PAYMENT_OR_SERVICE_AGREEMENT_REQUIRED',
  allowed: ['PROFILE', 'EDUCATION', 'DOCUMENTS', 'BANKABILITY', 'READINESS', 'RECOMMENDATIONS', 'PREPARATION'] as const,
  gated: ['PAID_FUNDING_EXECUTION', 'APPLICATION_PROCESSING', 'PAID_CONCIERGE'] as const,
} as const;

export function isFreeGuest(accessTier: unknown): boolean {
  return accessTier === FREE_GUEST_ACCESS.accessTier;
}

export function canStartPaidFunding(accessTier: unknown, entitlementVerified = false): boolean {
  return !isFreeGuest(accessTier) || entitlementVerified;
}

export function fundingGateMessage(accessTier: unknown): string {
  return isFreeGuest(accessTier)
    ? 'Funding process access requires verified payment or a service agreement. Readiness remains free.'
    : 'Continue through the governed funding access flow.';
}
