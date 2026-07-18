# Live Webhook Operator Certification

## Result

BLOCKED.

## Required Authoritative Endpoint

- mode: live
- host: `iqjwgpnujbeoyaeuwehj.supabase.co`
- path: `/functions/v1/stripe-webhook`
- required event: `checkout.session.completed`

## Inspected Live Endpoint Classes

- `goclearonline.cc` Netlify function endpoint: live, enabled, not the certified Supabase function.
- `nexuslive.netlify.app` Netlify function endpoint: live, enabled, not the certified Supabase function.
- `ygqglfbhxiumqdisauar.supabase.co` endpoint: live, enabled, different Supabase project.
- legacy `qrqq...` Supabase/function endpoints: live, enabled, different project or legacy route.

## Required Action

Create or align one live Stripe webhook endpoint to the certified Supabase function, then configure its signing secret as `STRIPE_LIVE_WEBHOOK_SECRET`.
