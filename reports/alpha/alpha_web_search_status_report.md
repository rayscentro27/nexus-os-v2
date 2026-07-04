# Alpha Web Search Status

- DuckDuckGo keyless: evaluated and disabled after Node-runtime response verification failed.
- SearXNG: supported backend architecture; `ALPHA_SEARXNG_URL` not configured, so status is `connector_missing`.
- Firecrawl: evaluation only; no keyless crawling enabled.
- Brave: not configured; no browser key.
- Default UI state: Off.
- Failure behavior: explicit error plus trace `web_status: failed`; no current-fact claim.
