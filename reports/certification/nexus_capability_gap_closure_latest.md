# Nexus capability-gap closure — 2026-09-13

## Evidence

- Synthetic certification identities were provisioned/repaired by the existing `provision_synthetic_certification_accounts.py` path. No secrets are recorded here. Persona A and Persona B are distinct synthetic tenants; the synthetic Admin identity is separate.
- Direct authenticated Supabase runtime probe: client gateway returned `POLICY_ALLOW`, intent `NEXT_STEP`, and a non-empty answer for Persona A. No stack trace or secret was exposed.
- OANDA Practice second bounded loop: `GBP_USD:H1`, 120 complete candles, chronological 84/36 split, in-sample `NO_VALID_SETUP`, OOS `NO_VALID_SETUP`, local paper result `NO_PAPER_ACTION`, broker order API `false`, live/funded trading `false`. Receipt: `reports/runtime/trading_real_data_oos_paper_latest.json`.
- Browser Support proof remains non-terminal for this run: the Playwright login flow hangs before the route assertion; the stale generated result showed controlled Clyde unavailability. This is isolated to browser proof/session execution and must not be promoted to `PASS_REAL` from the direct gateway probe.

## Scheduler boundary

`scheduler-health-recovery-approval` remains open. The recovery checker identified a stale scheduler health artifact while the active operator heartbeat is current. Scheduler mutation is explicitly approval-required; no mutation was attempted. Unrelated work continued.

## TikTok

No TikTok account, developer app, client key, authorization, or app-audit evidence was found in the canonical connector/credential registries. Current capability: draft/internal preparation only; private upload/direct-post is unverified; public posting remains approval- and platform-review-gated. TikTok's current documentation requires a registered app, Content Posting API, user authorization for `video.publish`, and approval of that scope. Unaudited clients are restricted to private viewing. Sources: [Direct Post setup](https://developers.tiktok.com/docs/en/content-posting-api-get-started), [Direct Post API](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post), [TikTok app review](https://developers.tiktok.com/docs/en/app-review-guidelines).

## Webull

No Webull account, sandbox application, app key, app secret, or sandbox receipt was found in canonical Nexus configuration. Capability remains external-setup-gated. Webull documents the sandbox base URL as `https://api.sandbox.webull.com`; its sandbox workflow requires a Webull account, sandbox OpenAPI application, and generated App Key/App Secret. Sources: [Webull Data API](https://developer.webull.com/apis/docs/market-data-api/data-api/), [Webull market-data overview](https://developer.webull.com/apis/docs/market-data-api/overview/), [Webull sandbox application](https://developer.webull.com/apis/docs/authentication/IndividualApplicationAPI/).

## Communication, calendar, SEO, affiliate, merchandise

- Governed customer email: not sent in this run; prior provider acceptance/receipt evidence is preserved. No new approval was present.
- Calendar: Google Workspace read capability is verified; no event mutation was performed. Event create/update/cancel remains governed test-mutation work, not an external meeting proof.
- SEO: current-source research was recorded for Arizona FAST (Sept–Oct 2026 window), CFPB Section 1071, Federal Reserve 2026 supervision updates, and current small-business AI/commercial topics. Search-volume claims remain unvalidated; no paid campaign or publication occurred. Arizona FAST source: [Arizona Commerce Authority](https://www.azcommerce.com/fast-program/).
- Affiliate: Shopify affiliate existence and current referral conditions were verified from official pages; approval was not claimed and no application was submitted. Sources: [Shopify Affiliates](https://www.shopify.com/affiliates), [Shopify earnings terms](https://help.shopify.com/en/affiliates/earnings).
- Merchandise: existing `public/creative-r24a/video/tshirt-product-reveal-r24a.mp4` and `public/creative-r20d1/MERCH_CAMPAIGN_PACKAGE.json` were recovered. The package remains draft-only with no store destination, spend, or publication.

## Current classification

`GLOBAL_LOOP_AUTONOMY=PARTIAL` — Systems, Research/Alpha, and Admin have prior two-loop real evidence. The fresh client, provider, and second-loop gaps above remain partial or externally gated. No live/funded trade, public social post, real customer email, external meeting, grant/funding application, or commercial launch was performed.

### Exact Ray/external actions

1. Scheduler: approve the existing governed scheduler-health recovery work order if mutation is desired.
2. TikTok: create/configure the developer app, Content Posting API, redirect/privacy/terms URLs, request `video.upload`/`video.publish` as appropriate, authorize the controlled account, and complete TikTok review/audit. Until then, keep public posting disabled.
3. Webull: create/verify a sandbox account and OpenAPI sandbox application, generate sandbox credentials, and supply them through the canonical secret store. Do not provide live credentials.

