# Hosted Checkout Certification

## Status

Conditional and not yet executed end-to-end.

## Verified

- Public `/pricing` route responds from the deployed v2 origin.
- Unauthenticated checkout requests are rejected with HTTP 401.
- Server-side Stripe test key and exact test price IDs are configured in Supabase Edge Function secrets.
- Three active offers are seeded with trusted amounts of 9,700, 29,700, and 49,700 USD cents.
- Browser-side price input is not used as the trusted amount.
- Stripe test webhook endpoint is enabled for exactly six required events.
- Unauthenticated and invalid webhook requests return HTTP 400.

## Failure and idempotency scenarios

- Unsigned request: deployed rejection verified; no payment-row mutation path.
- Invalid signature: deployed rejection verified; no payment-row mutation path.
- Duplicate signed event: deterministic idempotency is covered locally but was not replayed against a Persona D order.
- Failed payment, expired checkout, and cancelled return: pending the authenticated Persona D flow.

## Not executed

- Persona D authenticated checkout-session creation.
- Hosted Stripe test payment.
- Success/pending state after a real signed webhook.
- Payment tampering attempt with an authenticated Persona D session.

## Blocker

`E2E_PERSONA_D_PASSWORD` is not present in the ignored local environment. The existing provisioning architecture requires that operator-supplied synthetic credential before creating or authenticating Persona D. No credential was generated or exposed.
