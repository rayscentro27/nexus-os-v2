# Hermes Shadow Web Provider Audit

The previous Hermes web tool selected Brave and received HTTP 402. The shadow
now bypasses that paid path and calls the existing Nexus/Hermes free adapters in
this order:

1. Oracle/private SearXNG (`NEXUS_SEARXNG_WEB_SEARCH_BASE_URL` or `ALPHA_SEARXNG_URL`)
2. DuckDuckGo HTML
3. Bing HTML

Observed connectivity for `current credit repair affiliate programs`:

| Provider | Implemented | Live result | Cost | Finding |
|---|---|---:|---|---|
| SearXNG | Yes | No | Private/free | Connection refused |
| DuckDuckGo HTML | Yes | No | Free | No parsed results |
| Bing HTML | Yes | Yes | Free | Six result records returned |
| Brave | Yes | No | Paid | HTTP 402; excluded from shadow |

The provider chain is implemented in `scripts/nova/nova_hermes_shadow.py` using
the existing `scripts/hermes/hermes_web_search.py` adapters. No credentials were
rotated and no new provider or spend was introduced.

