# Pre-Deployment Live Configuration Certification

| Gate | Result | Evidence |
| --- | --- | --- |
| `STRIPE_MODE` present | PASS | present in Supabase secrets; must remain test until Nexus 3.0 |
| live secret configured | DEFERRED | `STRIPE_LIVE_SECRET_KEY` intentionally not configured |
| live webhook secret configured | DEFERRED | `STRIPE_LIVE_WEBHOOK_SECRET` intentionally not configured |
| live `$97` price configured | DEFERRED | `STRIPE_LIVE_PRICE_READINESS_REVIEW_97` intentionally not configured |
| production URL configured | PARTIAL | `NEXUS_PUBLIC_APP_URL` present, value not readable from secret listing |
| live webhook aligned | DEFERRED | live endpoint creation deferred until Nexus 3.0 |
| live price verified | DEFERRED | approved live `$97` price creation deferred until Nexus 3.0 |

No live Checkout Session should be created until deferred rows are completed during Nexus 3.0 launch.
