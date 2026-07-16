# Deployed Stripe Sandbox Activation

## Scope

- Starting commit: `bee5eb519d1489fb3713d1b9b6b3c648c8cc1bb9`
- Supabase project: `iqjwgpnujbeoyaeuwehj`
- Stripe account interaction: test mode only
- Public v2 origin verified: `https://nexusv20.netlify.app`
- Real card or live payment: not used

## Deployment results

- Applied only `20260715180000_revenue_activation_test_mode.sql`.
- Remote migration history now matches the local Phase 6 migration.
- All seven Phase 6 tables respond through the protected REST schema.
- Checkout Function deployed and active, version 2, JWT verification enabled.
- `stripe-webhook` deployed and active, version 1, JWT verification disabled so the Stripe signature is the authentication boundary.
- Server-side variables are configured by name only: `STRIPE_MODE`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, three `STRIPE_TEST_PRICE_*` variables, and `NEXUS_PUBLIC_APP_URL`.
- No frontend Stripe secret or service-role value was configured.

## Webhook

Endpoint: `https://iqjwgpnujbeoyaeuwehj.supabase.co/functions/v1/stripe-webhook`

Enabled test events: checkout completion, checkout expiration, payment success, payment failure, refund, and dispute creation.

Unsigned and invalid-signature requests returned HTTP 400. No database mutation occurs before signature verification.

## Remaining condition

The existing Persona D provisioning utility stopped before any Auth or client write because the ignored local variable `E2E_PERSONA_D_PASSWORD` is missing. No password was invented, displayed, committed, or sent. Hosted Checkout and purchase-to-delivery certification therefore remain pending.
