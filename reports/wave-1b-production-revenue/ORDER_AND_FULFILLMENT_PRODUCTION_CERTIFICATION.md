# Order and Fulfillment Production Certification

Generated: 2026-07-18T02:24:54Z

## Current Model

- `client_orders` remains the payment source of truth.
- `service_fulfillments` remains the readiness-review activation record.
- No duplicate entitlement system was created.
- No migration was applied.

## Environment Safety

Environment is inferred from stored Stripe Checkout Session prefix and webhook event `livemode`. This avoids schema churn while preventing live/test event mutation of the wrong order type.

## Remaining Certification

Live order and fulfillment must be certified after live deployment and one controlled payment.
