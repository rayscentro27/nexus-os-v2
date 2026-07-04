# Alpha Search vs URL Review Strategy

## Decision
- **SearXNG**: Future general search provider. Exists as backend code but not yet configured.
- **Firecrawl**: Primary URL extraction/review provider. Replaces DuckDuckGo keyless for the URL review use case.

## duckduckgo keyless status
- Honesty-disabled after Node-runtime verification failed.
- Not suitable for serverless extraction.
- Not re-enabled.

## Why Firecrawl for URL Review?
- Single URL extraction is the exact use case Ray described.
- Better quality page content than SERP scraping.
- Designed for LLM context, not search ranking.

## Workflow
1. Ray pastes a URL.
2. Ray asks Alpha to review it.
3. Frontend detects URL and review intent.
4. Frontend calls `/api/alpha/url-review` (server-only).
5. Server calls Firecrawl, returns title, domain, markdown excerpt.
6. If model provider available, Alpha summarizes + scores against Nexus/GoClear opportunity.
7. If no model provider, deterministic fallback shows extracted text with structured recommendation template.
8. Route trace shows extraction provider, URL, result status, model provider, cost label, web_used.

## Disabled-state behavior
- If `FIRECRAWL_API_KEY` is missing: returns clear disabled status.
- No fake content.
- No fallback to other extractors.

## Ray’s use case
- Paste URL + "review this" → structured recommendation in ≤2 calls.
- No crawl, no recursive links, no autonomous re-checks.
