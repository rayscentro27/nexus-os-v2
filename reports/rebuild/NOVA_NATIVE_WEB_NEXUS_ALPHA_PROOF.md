# Native Web, Nexus, and Alpha Shadow Proof

## Adapters

`web` uses Hermes's existing `web_search` / `web_extract` tool registry and
provider chain. The shadow does not install or replace a search provider.

`nexus_read_shadow` calls the existing governed shared capability for
`NEXUS_CAPABILITY_MAP` or `NEXUS_LIVE_TRUTH` only.

`alpha_challenge_shadow` calls the existing Alpha research capability for a
bounded objective. Durable Alpha work remains on its existing lifecycle.

## Required bounded proof runs

Development results through the Hermes shadow:

- **Web search:** EXECUTED; Hermes `web_search` called the configured Brave
  backend, which returned HTTP 402 after bounded retries. No external evidence
  was falsely claimed.
- **Page retrieval:** EXECUTED; `web_extract` returned the provider's explicit
  search-only limitation. Full page content was not returned.
- **Nexus capability-map read:** EXECUTED and successful; current capability
  registry data and provenance returned to Nova.
- **Bounded Alpha challenge:** EXECUTED and completed; `bing_html` returned six
  evidence records, Alpha receipt `alpha-receipt-54b3582cc454454f`, and research
  job `alpha-research-10532edbd1b84f1f`. The artifact reported zero supported
  claims, so Nova did not treat it as strong evidence.
- **Multi-resource synthesis:** PARTIAL; Nexus read succeeded, but public web
  provider failure prevented a complete external-evidence comparison.

No mocked result is considered proof.
