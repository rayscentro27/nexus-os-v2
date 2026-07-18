# Stripe Configuration Matrix

Generated: 2026-07-18T02:24:54Z

Values were not printed.

| Variable | Boundary | Local Presence | Status |
| --- | --- | --- | --- |
| `STRIPE_MODE` | server | absent | required before deploy |
| `STRIPE_TEST_SECRET_KEY` | server | absent | optional if deployed test uses legacy key |
| `STRIPE_SECRET_KEY` | server | absent | legacy environment-specific fallback |
| `STRIPE_TEST_WEBHOOK_SECRET` | server | absent | optional if deployed test uses legacy key |
| `STRIPE_WEBHOOK_SECRET` | server | absent | legacy environment-specific fallback |
| `STRIPE_TEST_PRICE_READINESS_REVIEW_97` | server | absent | optional fallback to `service_offers.test_price_id` in test |
| `STRIPE_LIVE_SECRET_KEY` | server | absent | human action required |
| `STRIPE_LIVE_WEBHOOK_SECRET` | server | absent | human action required |
| `STRIPE_LIVE_PRICE_READINESS_REVIEW_97` | server | absent | human action required |
| `VITE_STRIPE_LIVE_PUBLISHABLE_KEY` | client | absent | not used by server checkout route |
| `NEXUS_PUBLIC_APP_URL` / `PUBLIC_SITE_URL` | server | absent | required for live success/cancel URLs |

No live secret or webhook secret is present in Git.
