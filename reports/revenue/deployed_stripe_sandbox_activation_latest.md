# Deployed Stripe Sandbox Activation

## Result

PASS for the synthetic deployed sandbox flow.

- Supabase project: `iqjwgpnujbeoyaeuwehj`
- Migration `20260715180000_revenue_activation_test_mode.sql`: applied
- Follow-up service-role trigger correction migration: applied
- `create-stripe-checkout`: active deployed version
- `stripe-webhook`: active deployed version
- Stripe mode: test only
- Server-only Stripe variables: configured remotely without exposing values
- Three exact test products/prices: active and linked to the seeded offers
- Signed webhook endpoint: active for the required six events
- Service offers: exactly three active records with trusted prices

## Persona D result

Persona D was provisioned/reused safely, reset in a scoped operation, and
completed a real hosted $97 Stripe sandbox Checkout. The signed webhook created
one verified paid order and one `onboarding_required` fulfillment. The deployed
client portal saved synthetic intake data and a protected Funding Applications
document. Admin generated draft packet version 1, routed it to one Ray Review
item, approved that exact version, and delivered it to the authenticated client
portal.

Duplicate webhook replay produced no duplicate payment event or fulfillment.
Failed, expired, cancelled, unsigned, invalid-signature, and price-tampering
checks were safe. Tier 1 produced no consultation entitlement by default. A
referral-coded unpaid order retained attribution input without creating a
commission or payout.

## Verification

- Browser regression: 76 passed, 0 failed, 0 skipped.
- Revenue activation browser file: 9 passed, 0 failed, 0 skipped.
- Vitest: 1,322 passed.
- TypeScript: PASS.
- Production build: PASS.
- Outcome analytics: PASS.
- Authenticated RLS: 45/45 passed.
- Secret, frontend/bundle, private-key, card-data, and signed-URL scans: PASS.
- Automatic mail: none.
- DocuPost: no submission.
- Live payment: disabled; no real card or real client used.

## Release state

`GO FOR CONTROLLED HUMAN PAYMENT TEST` applies only to the bounded test-mode
activation. Public launch and Step 100 remain manually blocked pending Ray's
explicit approval.

This report contains no password, secret, card data, signed URL, raw provider
payload, or real client information.
