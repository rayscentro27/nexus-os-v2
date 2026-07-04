# Alpha Web Search Connector

Search is backend-only through `/api/alpha/search`. DuckDuckGo keyless JSON was evaluated, but Node-runtime verification returned an empty body and the connector was disabled instead of faking availability. The endpoint now returns `connector_missing` unless an approved `ALPHA_SEARXNG_URL` is configured. SearXNG requests are single-call, capped at five, and cached briefly in the warm Netlify function.

The frontend calls only the same-origin Nexus endpoint. Search remains off by default and never silently activates from a current-events prompt. No HTML scraping, browser automation, page extraction, crawler, or repeated search loop exists.
