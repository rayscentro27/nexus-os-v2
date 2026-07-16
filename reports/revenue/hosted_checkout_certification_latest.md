# Hosted Checkout Certification

## Status

PASS — deployed Stripe test-mode hosted checkout completed for the synthetic
Persona D $97 readiness review.

## Deployment

- Supabase project: `iqjwgpnujbeoyaeuwehj`
- Application origin: `https://nexusv20.netlify.app`
- Checkout function: `create-stripe-checkout`, active deployed version
- Webhook function: `stripe-webhook`, active deployed version
- Stripe mode: test only
- Webhook endpoint: deployed Supabase function URL, enabled for the six required
  checkout/payment/refund/dispute events
- Server-only Stripe variables: configured remotely; values are not recorded

## Successful hosted checkout

- Persona D authenticated through the deployed client login.
- `readiness-review-97` was selected through the public offer page.
- Terms version `readiness-services-v1` was captured.
- The hosted Checkout Session used the trusted server amount of 9,700 USD cents.
- Stripe sandbox payment completed with an approved test payment method only.
- The browser returned to `/checkout/success`; the page read persisted order state
  rather than trusting the return query string.
- Signed `checkout.session.completed` processing persisted one verified payment
  event, one paid order, and one fulfillment.
- The order reached `paid` / `verified_paid`; the fulfillment began at
  `onboarding_required`.

## Security and idempotency

- An authenticated amount-tampering request still persisted 9,700 USD cents and
  USD; client-supplied amount/tier values were not trusted.
- Replaying the exact verified Stripe event left payment-event, fulfillment,
  onboarding, packet, consultation, and referral counts unchanged.
- Unsigned webhook: HTTP 400, no payment-event mutation.
- Invalid signature: HTTP 400, no payment-event mutation.
- No card number, CVV, secret, signed URL, or raw provider payload was persisted
  in the application.

## Failure paths

- Stripe failure-card attempt remained unpaid and created no fulfillment.
- Expired Checkout Session reached `expired` with no fulfillment.
- Cancelled return displayed the safe cancellation state and did not mark the
  order paid; the abandoned session was subsequently expired in test mode.
- No open synthetic Checkout Sessions remained after cleanup.

## Browser certification

- Revenue activation browser file: 9 passed, 0 failed, 0 skipped.
- Full deployed browser regression: 76 passed, 0 failed, 0 skipped.
- The successful hosted payment was additionally exercised as a real deployed
  browser flow rather than a mocked payment state.

## Decision impact

The hosted sandbox checkout gate is complete. This report contains no password,
secret, card data, signed URL, raw webhook payload, or real client information.
