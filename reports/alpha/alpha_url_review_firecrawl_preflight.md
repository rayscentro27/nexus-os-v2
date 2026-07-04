# Alpha URL Review Firecrawl Preflight

## Current Alpha Search Status
- **SearXNG backend**: Configured via `ALPHA_SEARXNG_URL` env var, currently not set in `.env`
- **DuckDuckGo keyless**: Failed Node-runtime verification and is disabled honestly
- **Web search UI**: Available as "Search Mode" toggle, uses SearXNG when configured

## DuckDuckGo Disabled Reason
- Node-runtime verification failed during Alpha Success Sprint
- DuckDuckGo HTML scraping is client-side unfriendly and fragile in serverless environments
- Keyless mode was attempted but rejected due to runtime constraints

## SearXNG Status
- Backend support exists in `netlify/functions/alpha-search.mjs`
- Requires `ALPHA_SEARXNG_URL` environment variable
- Currently not configured (no value in `.env`)
- Will be documented as future general search provider

## Firecrawl Env Status
- **Required env var**: `FIRECRAWL_API_KEY` (server-side only)
- **NOT configured in `.env`** or `.env.example`
- **Must NOT be exposed** as `VITE_FIRECRAWL_API_KEY`
- Must be set as Netlify server environment variable only

## URL Review Mode Status
- **Does NOT exist yet** - this is a new feature
- No existing URL detection in chat
- No existing URL review connector

## Security Rules Verified
1. No FIRECRAWL_API_KEY in frontend code planned
2. No VITE_FIRECRAWL_API_KEY will be created
3. No Supabase connection for URL review
4. No client data usage
5. No crawl by default
6. No external actions (send/publish/trade)

## Next Steps
- Create `netlify/functions/alpha-url-review.mjs` backend function
- Update `alphaRouteTrace.ts` with `url_review` provider type
- Add URL detection and review mode to UI
- Add cost tracking for URL reviews