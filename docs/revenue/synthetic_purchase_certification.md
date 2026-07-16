# Synthetic Purchase-to-Delivery Certification

Persona D is `nexus-persona-d-revenue@goclear.test` with an isolated synthetic client scope. Credentials are supplied only through ignored local environment variables and are never printed or committed.

Utilities:

- `seed_service_offers.py`: seeds the three active catalog rows; supports `--dry-run`, `--seed`, and `--verify`.
- `provision_synthetic_revenue_persona.py`: creates or verifies the synthetic Auth/client scope and a draft order; it never writes paid state.
- `reset_synthetic_revenue_flow.py`: deletes only Persona D payment/order/fulfillment/packet/consultation/referral rows; it preserves Auth and client records.
- `verify_synthetic_revenue_flow.py`: checks order, verified events, single fulfillment, packet delivery, and duplicate IDs.
- `run_revenue_webhook_fixture.py`: creates a signed Stripe-shaped test event and sends it through `stripe-webhook`; it never writes `paid` directly.

The complete configured certification is: seed → provision → create hosted test Checkout → complete Stripe test payment → signed webhook → paid order → one fulfillment → onboarding/intake/documents → analysis → draft packet → admin review → Ray Review → exact-version approval → portal delivery → consultation/referral checks → completed fulfillment. Repeat the webhook and verify unchanged counts. Also run failed, expired, refunded/cancelled, and dispute scenarios.

In this checkout repository environment, Stripe test price IDs and webhook secret are absent, so the checked-in certification stops before external test Checkout and is reported as conditional. No real card or live payment was attempted.
