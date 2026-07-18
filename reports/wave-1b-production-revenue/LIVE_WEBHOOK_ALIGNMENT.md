# Live Webhook Alignment

Generated: 2026-07-18T02:24:54Z

## Current Test Endpoint

- test endpoint: `we_1Ttd***piPL`
- mode: test
- URL: certified Supabase Edge Function host `iqjwgpnujbeoyaeuwehj`
- events include checkout completion, expiration, payment success/failure, refund, dispute.

## Live Stripe Endpoints Inspected

Live endpoints exist for `goclearonline.cc`, `nexuslive.netlify.app`, `ygqglfbhxiumqdisauar`, and legacy `qrqq...` hosts.

## Gap

No inspected live endpoint matches the currently certified Supabase project host `iqjwgpnujbeoyaeuwehj`.

## Required Human/Operator Action

Create or select the approved live webhook endpoint for the deployed Wave 1B function and configure `STRIPE_LIVE_WEBHOOK_SECRET` for that endpoint.
