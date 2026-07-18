# Checkout Function Production Certification

Generated: 2026-07-18T02:24:54Z

## Changes

`create-stripe-checkout` now:

- resolves server-side Stripe runtime;
- supports `test` and `live`;
- validates expected secret prefix;
- resolves separate test/live `$97` prices;
- requires HTTPS public URL for live;
- creates internal pending order before Stripe session;
- stores Checkout Session correlation;
- rejects session-prefix mismatch;
- returns mode without returning secrets.

## Tests

- `npx vitest run tests/revenue_activation.test.ts`: PASS, 12/12.
- `npm run typecheck`: PASS.
- `npm run build`: PASS.

## Status

Implemented-Uncertified for live runtime because live credentials are not configured.
