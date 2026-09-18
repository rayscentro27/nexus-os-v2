# Nexus Primary SEO Capability Implementation

Date: 2026-09-18 (Phoenix)

## Status

The partial OpenCode implementation was recovered and completed without
changing Hermes, Research scheduling, Alpha, or the Admin UI. The canonical
runtime is the published `iannuttall/seo@0.2.40` artifact, pinned to the
audited source commit `52f10012021131c2405cddfb976d583a6af3b490`.

## Recovery notes

OpenCode had created `seo_adapter.py`, a source checkout under
`.runtime/third_party/iannuttall-seo/`, and a partially prepared npm runtime.
The adapter structure and the pinned version were reusable. It was incomplete:
it pointed at the wrong runtime directory, could install implicitly, used
`subprocess.run` without process-group cleanup, called a nonexistent
`upsert_evidence` API, had a site-URL normalization bug, and used the wrong
published CLI syntax for crawl (`crawl --url` instead of `crawl <url>`).

The GitHub monorepo checkout remains a non-canonical audit artifact and is not
the production runtime. The adapter uses only the published npm artifact.

## Runtime and contract

| Item | Certified value |
|---|---|
| Tool | `iannuttall/seo` |
| Version | `0.2.40` |
| Audited commit | `52f10012021131c2405cddfb976d583a6af3b490` |
| Runtime | `.runtime/third_party/iannuttall-seo/npm-runtime-0.2.40` |
| Source | Published npm artifact |
| Node | `v22.22.3` |
| Node requirement | `>=22.19.0` (met) |
| Concurrency | 1 |
| Max pages/depth | 25 / 3 |
| Max runtime | 120 seconds |

The adapter accepts typed Nexus requests and only constructs these read-only
operations: `crawl`, `audit-page`, `crawl --sitemap-url ... --health`, and
`reports list`. It rejects mutation/auth/provider/configuration operations,
never accepts arbitrary shell text, sets `DO_NOT_TRACK=1`, requires complete
JSON on stdout, and runs each child in its own process group. Timeout cleanup
terminates the group and escalates to SIGKILL when necessary.

## Governed storage and deduplication

Normalized SEO evidence is appended to the existing governed
`research_v2_sources` collection. Each record retains the upstream observation,
derived Research classification, severity, coverage state, skipped/partial
checks, verification fields, request/work/objective/investigation IDs, stable
finding ID, and content hash. Stable identity is based on site, page, rule,
and report type. Repeated unchanged findings link to existing records instead
of appending duplicates.

The only additional file is the bounded operational read model
`data/runtime/seo_operational_state_latest.json`, used by the existing
Research operational-state projection. It is not a second evidence store.

## Real adapter certification

### `example.com`

The adapter completed a real bounded crawl with `max_pages=1` and
`max_depth=1`:

- status: SUCCESS
- pages crawled: 1
- findings: 8
- severity: 0 high, 1 medium, 7 low
- coverage: PARTIAL (the tool reported bounded/partial coverage)
- structured JSON: yes
- governed persistence: 8 inserted

### `https://goclearonline.cc`

The adapter completed a real bounded crawl with the production-safe limits:

- status: SUCCESS
- pages crawled: 1
- findings: 10
- severity: 1 high, 1 medium, 8 low
- coverage: PARTIAL
- runtime: approximately 6 seconds
- structured JSON: yes
- governed persistence: 0 new / 10 linked as unchanged existing evidence on
  the final repeat run

The crawl was read-only. It did not modify GoClear. The published runtime
observed the public site and returned structured findings, including the
previously verified canonical/technical evidence family.

## Operational visibility

`build_research_operational_state()` now exposes `seo` with installed/version,
last run, site, pages crawled, finding count, severity counts, coverage state,
and last error. This is read-only and requires no frontend change. Future
Hermes/Nexus MCP exposure can reuse this existing operational projection.

## Security and capability boundary

GSC, GA4, DataForSEO, Semrush, and Ahrefs remain disconnected. No OAuth,
browser-cookie extraction, credentials, IndexNow submission, publication, or
site mutation was performed. `DO_NOT_TRACK=1` is process-scoped. The package
does expose an MCP entry point, but it is not connected to Hermes in this
task; the Python adapter remains the canonical Nexus integration boundary.

## Tests

Focused tests cover the typed read-only allowlist, mutation rejection,
complete-JSON parsing, stable IDs, coverage preservation, governed persistence,
deduplication, and invalid-request rejection. Python compilation and real
adapter runs were also performed. The existing Admin/Hermes/Research systems
were not modified.

## Remaining work

GSC/GA4/provider integrations remain intentionally unavailable and require
separate authorization and provider decisions. A future Hermes MCP bridge may
expose this adapter, but should call the same bounded adapter and governed
store rather than create a second SEO control plane.
