# Product and Price Certification

Generated: 2026-07-18T02:24:54Z

## Product Key

Current client submits existing offer slug `readiness-review-97`.

## Server Mapping

- Test: environment variable `STRIPE_TEST_PRICE_READINESS_REVIEW_97` or existing `service_offers.test_price_id`.
- Live: required environment variable `STRIPE_LIVE_PRICE_READINESS_REVIEW_97`.

## Guards

- client cannot submit amount;
- client cannot submit price id;
- client cannot select test/live mode;
- unknown/invalid terms rejected;
- live missing price rejected;
- Checkout Session prefix must match mode.

## Remaining Gate

Approved live Stripe price amount/currency must be verified in Stripe Dashboard or CLI after Ray provides live configuration.
