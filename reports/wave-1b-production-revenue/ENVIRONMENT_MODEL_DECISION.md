# Environment Model Decision

Generated: 2026-07-18T02:24:54Z

## Decision

Use server-side `STRIPE_MODE` with values:

- `test`
- `live`

Checkout and webhook independently validate their runtime mode and expected key/session/event boundaries.

## Server Variables

- `STRIPE_MODE`
- `STRIPE_TEST_SECRET_KEY` or legacy `STRIPE_SECRET_KEY` for test
- `STRIPE_LIVE_SECRET_KEY` or environment-specific `STRIPE_SECRET_KEY` for live
- `STRIPE_TEST_WEBHOOK_SECRET` or legacy `STRIPE_WEBHOOK_SECRET` for test
- `STRIPE_LIVE_WEBHOOK_SECRET` or environment-specific `STRIPE_WEBHOOK_SECRET` for live
- `STRIPE_TEST_PRICE_READINESS_REVIEW_97`
- `STRIPE_LIVE_PRICE_READINESS_REVIEW_97`
- `NEXUS_PUBLIC_APP_URL` or `PUBLIC_SITE_URL`

## Fail-Closed Behavior

- live mode requires `sk_live_`
- test mode requires `sk_test_`
- webhook secret must be present and `whsec_`
- live mode requires HTTPS public app URL
- live/test Checkout Session prefix must match mode
- event `livemode` must match mode
- webhook rejects order/session environment mismatch
