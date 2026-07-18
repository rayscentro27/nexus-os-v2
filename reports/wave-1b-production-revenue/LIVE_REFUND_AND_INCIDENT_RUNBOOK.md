# Live Refund and Incident Runbook

Generated: 2026-07-18T02:24:54Z

## Refund Conditions

- duplicate charge;
- service cannot be delivered;
- accidental payment;
- approved cancellation;
- material technical failure;
- legal/compliance requirement.

## Incident Response

1. Stop new checkout creation if payment integrity is uncertain.
2. Preserve `client_orders`, `payment_events`, and Stripe event evidence.
3. Do not delete records.
4. Pause fulfillment if customer association or amount is uncertain.
5. Notify Customer 001 through approved support route.
6. Refund only through approved Stripe live dashboard/operator flow.

## Owner

Ray or explicitly approved revenue operator must authorize any live refund.
