# Payment Environment Inventory

Generated: 2026-07-18T02:24:54Z

## Flow

Offer UI -> `createRevenueCheckout` -> `create-stripe-checkout` -> Stripe Checkout -> `stripe-webhook` -> `client_orders` -> `service_fulfillments` -> customer/admin views.

## Source Paths

- Checkout: `supabase/functions/create-stripe-checkout/index.ts`
- Webhook: `supabase/functions/stripe-webhook/index.ts`
- Display catalog: `src/config/serviceOfferCatalog.ts`
- Client wrapper: `src/lib/revenueActivationClient.ts`
- Revenue helpers/tests: `src/lib/stripeTestMode.ts`, `tests/revenue_activation.test.ts`

## Current Status

- Test path: preserved and unit-certified.
- Live path: implemented in source but not deployed/configured.
- Live credentials: absent locally; must be entered through hosting/Supabase secrets, not source.
- Live endpoint: Stripe account contains live endpoints, but the currently certified Supabase endpoint does not yet have a matching live endpoint.
