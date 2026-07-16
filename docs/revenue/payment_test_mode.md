# Payment Test Mode

Stripe is the approved provider for this flow. Phase 6 permits only Stripe test mode.

Server-only variables:

- `STRIPE_MODE=test`
- `STRIPE_SECRET_KEY` (server-only test-mode secret from the ignored environment)
- `STRIPE_WEBHOOK_SECRET` (server-only signing secret from the ignored environment)
- `STRIPE_TEST_PRICE_READINESS_REVIEW_97`
- `STRIPE_TEST_PRICE_ACTION_PLAN_297`
- `STRIPE_TEST_PRICE_CONCIERGE_497`
- `NEXUS_PUBLIC_APP_URL` (server-controlled return URL origin)
- `SUPABASE_SERVICE_ROLE_KEY` only inside server/Edge Function or ignored operator scripts

Browser variables are limited to public Supabase variables and, if a future hosted checkout needs it, a publishable `VITE_STRIPE_PUBLISHABLE_KEY`. No secret or webhook value belongs in Vite variables.

`create-stripe-checkout` authenticates the client, validates terms, loads the active offer, uses the persisted amount and test price ID, creates a draft order, and creates a hosted Stripe test Checkout Session. The client cannot submit a trusted amount; payment details remain with the hosted provider.

`stripe-webhook` reads the raw request body, verifies the Stripe signature and five-minute tolerance, rejects unsigned/invalid requests, sanitizes the stored event, and deduplicates `provider_event_id`. Verified success events are the only path to `paid` and fulfillment creation. A repeated event returns a duplicate response and does not create another order, fulfillment, packet, or consultation.

The current repository environment has no Stripe test price IDs or webhook secret configured. This is intentional in the checked-in code and prevents an accidental charge. Configure ignored server variables before a controlled human payment test; never change `STRIPE_MODE` to live during this phase.
