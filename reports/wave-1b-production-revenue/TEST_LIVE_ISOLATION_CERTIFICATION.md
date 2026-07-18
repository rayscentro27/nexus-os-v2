# Test/Live Isolation Certification

Generated: 2026-07-18T02:24:54Z

## Implemented Guards

- test mode requires `sk_test_`
- live mode requires `sk_live_`
- test sessions must be `cs_test_`
- live sessions must be `cs_live_`
- webhook event `livemode` must match runtime mode
- webhook order session prefix must match runtime mode
- `checkout.session.completed` must match stored Checkout Session id
- metadata mode mismatch is rejected

## Tests

Revenue tests include secret, session, event, and source-string isolation checks.

Status: PASS for static/helper certification; live runtime certification pending credentials and deployment.
