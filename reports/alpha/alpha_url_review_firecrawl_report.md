# Alpha URL Review Firecrawl Report

## Alpha Search Status
- SearXNG backend connector exists in `netlify/functions/alpha-search.mjs`.
- `ALPHA_SEARXNG_URL` is NOT configured in `.env`.
- Web search UI is available as "Search Mode" toggle.
- DuckDuckGo keyless was honestly disabled after Node-runtime verification failed during Alpha Success Sprint.

## SearXNG Status
- Support exists and is wired via local dev bridge and Netlify function.
- Will remain documented as the future general search provider.
- Not required for URL review.

## Firecrawl Env Status
- Required env var: `FIRECRAWL_API_KEY` (server-side only).
- NOT configured in `.env` or `.env.example`.
- NOT exposed to frontend.
- Must be set in Netlify server environment only.

## Backend Connector
- Created `netlify/functions/alpha-url-review.mjs`.
- Added Netlify redirect rule for `/api/alpha/url-review` -> `/.netlify/functions/alpha-url-review`.
- Added local dev bridge in `vite.config.ts`.
- Default: one URL per request, no crawl, no recursive links.
- Max content: 12,000 chars before model call.
- Timeout: 15 seconds.
- Missing key returns clear disabled status with no fake extraction.
- No Supabase, no client data, no external actions.

## Frontend Changes
- Created `src/hermes/alpha/alphaUrlReview.ts` with URL extraction and review request detection.
- Updated `src/components/HermesAlphaWorkspace.tsx` with:
  - URL Review mode toggle.
  - URL input detection.
  - "Review this URL" flow.
  - Source label: "URL review · Firecrawl backend · No Supabase · No client data".
- Updated `src/hermes/alpha/alphaRouteTrace.ts` with:
  - `url_review_backend` provider source.
  - `extracted` web status.
  - `firecrawl` web provider.
- Updated `src/hermes/alpha/alphaProviderStatus.ts` with `urlReview` status block.
- Updated `src/hermes/alpha/alphaCostController.ts` with URL review cost tracking.
- Updated `netlify/functions/alpha-provider.mjs` with `urlReview` in status response.
- Updated `vite.config.ts` with `url-review` local dev bridge and `urlReview` in status response.

## Route/Source Trace
- `provider_source`: `url_review_backend`
- `web_provider`: `firecrawl`
- `web_status`: `extracted` or `failed` or `disabled`
- `web_used`: true
- `noSupabaseUsed`: false
- `clientDataUsed`: false
