# Production Endpoint Inventory

## Supabase

- project ref: `iqjwgpnujbeoyaeuwehj`
- checkout function: `create-stripe-checkout`
- webhook function: `stripe-webhook`
- certified webhook path: `/functions/v1/stripe-webhook`
- deployed checkout function observed: active, version 6, last updated before Wave 1B commit
- deployed webhook function observed: active, version 3, last updated before Wave 1B commit

## Netlify

- repo configuration: `netlify.toml`
- build command: `npm run build`
- publish directory: `dist`
- Netlify CLI status/list commands did not return within the bounded check window.
- production site identity remains unverified by CLI in this sprint.

## Stripe

- test webhook exists for `iqjwgpnujbeoyaeuwehj.supabase.co/functions/v1/stripe-webhook`.
- live webhooks exist for `goclearonline.cc`, `nexuslive.netlify.app`, `ygqglfbhxiumqdisauar.supabase.co`, and legacy `qrqq...` hosts.
- no inspected live webhook targets `iqjwgpnujbeoyaeuwehj.supabase.co/functions/v1/stripe-webhook`.
