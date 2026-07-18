# Live Configuration Action Plan

Values must be entered in the appropriate provider dashboard or CLI. No values are recorded here.

| Variable | Platform | Boundary | Current Status | Expected Classification | Deploy Required |
| --- | --- | --- | --- | --- | --- |
| `STRIPE_MODE` | Supabase Edge Function secrets | server | PRESENT | must remain `test` until Nexus 3.0 live launch | yes if changed |
| `STRIPE_LIVE_SECRET_KEY` | Supabase Edge Function secrets | server | NOT CONFIGURED | deferred until Nexus 3.0 production launch | yes |
| `STRIPE_LIVE_WEBHOOK_SECRET` | Supabase Edge Function secrets | server | NOT CONFIGURED | deferred until live webhook is created for Nexus 3.0 | yes |
| `STRIPE_LIVE_PRICE_READINESS_REVIEW_97` | Supabase Edge Function secrets | server | NOT CONFIGURED | deferred until approved live `$97` price is created | yes |
| `NEXUS_PUBLIC_APP_URL` | Supabase Edge Function secrets | server | PRESENT BUT VALUE UNVERIFIED | production HTTPS customer URL; confirm value before live launch | yes if changed |
| `PUBLIC_SITE_URL` | Supabase Edge Function secrets | server fallback | UNVERIFIED | production HTTPS customer URL | yes if changed |
| `VITE_STRIPE_LIVE_PUBLISHABLE_KEY` | Netlify production env if used by UI | client | UNVERIFIED | `pk_live_...` only | yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase function runtime | server | PRESENT | server-only writer | no unless changed |

## Owner Deferral Response

1. Not configured - intentionally deferred until Nexus 3.0 is complete.
2. Not configured - intentionally deferred until Nexus 3.0 is complete.
3. Not configured - intentionally deferred until Nexus 3.0 production launch.
4. Not configured - intentionally deferred until the live webhook is created for Nexus 3.0.
5. Not configured - intentionally deferred until the approved live $97 price is created.
6. Not configured - `STRIPE_MODE` must remain test. Do not enable live mode.
7. Not confirmed - `NEXUS_PUBLIC_APP_URL` is present but its value cannot be read from Supabase secrets output; confirm the current production HTTPS Nexus URL before live launch.
8. Not configured - only configure later if the Nexus 3.0 frontend requires it.

Live payment certification is intentionally deferred.
