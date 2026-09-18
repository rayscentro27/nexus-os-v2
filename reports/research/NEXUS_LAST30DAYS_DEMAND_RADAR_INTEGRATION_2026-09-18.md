# Nexus Last30Days Demand Radar Integration

Date: 2026-09-18 (Phoenix)

## Status

```text
LAST30DAYS_INTEGRATION_STATUS=PARTIAL
```

The pinned adapter and governed storage boundary are implemented and tested.
The real Reddit probe completed safely but returned no usable posts; web
grounding returned zero results; YouTube/Hacker News/GitHub multi-source runs
exceeded the bounded runtime. A real multi-source demand cluster and Alpha
promotion were therefore not claimed.

## Upstream audit and pin

```text
LAST30DAYS_VERSION=3.24.0
LAST30DAYS_UPSTREAM_COMMIT=25a5cea5bfa5723991894385041ebb3b87049753
LICENSE=MIT
PYTHON_REQUIREMENT=>=3.12
NODE_REQUIREMENT=not required by the Python engine; vendored Bird/X support is optional
STRUCTURED_JSON_SUPPORTED=YES (agent profile schema 1.3)
DISCOVERY_MODE_SUPPORTED=YES
WATCHLIST_MODE_SUPPORTED=YES
DOCTOR_HEALTH_SUPPORTED=YES
UPDATE_POLICY=EXPLICIT_REVIEW_ONLY
INSTALL_PATH=.runtime/third_party/last30days-skill/25a5cea5bfa5723991894385041ebb3b87049753
```

The source was reviewed from the exact pinned checkout. It supports Reddit,
YouTube, Hacker News, GitHub, web grounding, and additional optional source
families. Its saved briefs/SQLite store are operational cache only. Nexus does
not use them as canonical state.

The upstream project documents keyless Reddit RSS/shreddit/arctic-shift paths,
optional browser-cookie extraction, and explicit publication features. Nexus
uses `--no-browser-cookies`; publication and external mutations are disabled.

## Adapter

```text
ADAPTER_PATH=scripts/nexus_agent_platform/research/last30days_adapter.py
ADAPTER_IMPLEMENTED=YES
STRUCTURED_OUTPUT_USED=YES
RESEARCH_WORK_CLASS=DEMAND_DISCOVERY
SCHEDULER_CHANGED=NO
DISCOVERY_CONCURRENCY=1 (uses the existing discovery slot)
```

The adapter:

1. builds a bounded fixed query plan, avoiding an unbounded upstream planner;
2. invokes the pinned CLI in a new process group;
3. enforces a hard timeout and terminates the process group on expiry;
4. requests versioned JSON, not Markdown;
5. normalizes source status, signal, engagement, freshness, and cluster data;
6. deduplicates by canonical URL/content hash;
7. persists new evidence to `data/governed/research_v2_sources.jsonl`;
8. writes only operational run metadata to `data/runtime/last30days_demand_radar_latest.json`;
9. promotes only multi-source clusters above threshold through the existing
   `research_needs` and `alpha_model_review.py` paths.

No second need schema, scheduler, Alpha evaluator, or handoff store was added.

## Real bounded probes

### Business funding for new LLC

```text
TOPIC_TEST=REAL_BOUNDED
WINDOW=LAST_30_DAYS
REQUESTED_SOURCES=reddit,youtube,hackernews,github
RESULT=TIMEOUT under the configured 20-second bound; no partial JSON was accepted
```

Narrow real probes were then run independently:

```text
REDDIT_STATUS=UNREACHABLE / zero usable posts
WEB_STATUS=UNREACHABLE / zero results from grounding
YOUTUBE_STATUS=TIMEOUT under bounded process-group limit
HACKER_NEWS_GITHUB_STATUS=TIMEOUT under bounded process-group limit
REDDIT_REQUIRED_FOR_DEMAND_RADAR=NO
```

The adapter correctly preserves failure states and does not convert them to
`NO_RESULTS` or evidence. It also prevents an upstream stall from taking down
the Research daemon.

### Adapter contract proof

The pinned upstream mock fixture was used only for adapter contract testing:

```text
STRUCTURED_EXPORT_SCHEMA=1.3
NORMALIZED_SIGNALS=1
NORMALIZED_CLUSTERS=1
CANONICAL_SOURCE_PERSISTENCE=PASS_TEST
BROWSER_COOKIES_ENABLED=NO
PUBLICATION_ENABLED=NO
EXTERNAL_MUTATIONS=NO
```

This is not counted as live demand evidence.

## Existing Research integration

```text
CANONICAL_EVIDENCE_STORE=data/governed/research_v2_sources.jsonl
UPSTREAM_CACHE_STORE=.runtime/last30days-cache
LAST30DAYS_STATUS=DEGRADED for the latest real Reddit probe
```

The existing Research roles remain distinct:

```text
Last30Days = recent human-signal acquisition / Demand Radar
Brave/Web Research = direct evidence acquisition
Nexus YouTube Monitor = approved recurring channel monitoring
Research V2 = governed evidence, investigations, and provenance
Alpha = model-backed challenge and qualification
Departments = governed action owners
```

Last30Days YouTube topic discovery is not allowed to create duplicate source
artifacts or replace the approved channel monitor. Existing source URLs are
linked rather than reinserted.

## Need and Alpha promotion boundary

A cluster must have at least two independent source types and two signals before
promotion. Existing needs are matched and enriched by evidence before a new
need is created. New qualifying clusters call the existing
`alpha_model_review.review_demand_package` path, which is the proven
OpenRouter/Gemini Alpha boundary. Upstream synthesis, if present, is never
treated as Alpha approval.

No live cluster met the promotion threshold in this certification window, so:

```text
EXISTING_NEED_MATCH=NOT_PROVEN_LIVE
EXISTING_NEED_ENRICHED=NO_LIVE_CLUSTER
ALPHA_HANDOFF=NOT_RUN_FOR_LAST30DAYS_EVIDENCE
DEPARTMENT_HANDOFF=NOT_RUN_FOR_LAST30DAYS_EVIDENCE
```

This preserves the already-proven need `need_f527d1db8c4d1e5de721` and its
Gemini-backed Alpha/handoff records without duplicating them.

## Operational visibility

`research_operational_state.py` now exposes a bounded `demand_radar` projection:

- status and last run;
- last query and time window;
- per-source health;
- source coverage;
- signal/cluster counts;
- new evidence and existing-source links;
- next action.

Nova can therefore distinguish Demand Radar availability from Research truth and
from Alpha qualification.

## Security and limits

```text
BROWSER_COOKIES_ENABLED=NO
PUBLICATION_ENABLED=NO
EXTERNAL_MUTATIONS=NO
MAX_RUNTIME_SECONDS=bounded per request, default 90, hard cap 180
MAX_RESULTS=bounded per request, hard cap 50
DISCOVERY_CONCURRENCY=1
```

No credentials were committed. The isolated upstream checkout is runtime-only
and not vendored into the repository. Optional upstream source credentials are
not automatically enabled.

## Tests

```text
21 passed
PY_COMPILE=PASS
REAL_REDDIT_PROBE=PASS_BOUNDED_DEGRADED
REAL_WEB_PROBE=PASS_BOUNDED_EMPTY
REAL_YOUTUBE_PROBE=TIMEOUT_ISOLATED
REAL_HN_GITHUB_PROBE=TIMEOUT_ISOLATED
MOCK_ADAPTER_CONTRACT=PASS (not production evidence)
```

## Remaining blockers

1. The pinned upstream multi-source run needs an approved longer maintenance
   window or source-specific performance tuning before live cross-source cluster
   certification.
2. Reddit currently returns no usable live evidence in this environment.
3. No live Last30Days cluster reached the existing Alpha path in this window.

These are isolated acquisition/coverage limitations. They do not alter the
proven Research scheduler, queue priority, leases, concurrency, YouTube
monitor, Alpha model path, department handoff system, Hermes runtime, or
Resource Governor.

## Live source certification and performance tuning

The initial combined run was not sufficient evidence because one stalled source
discarded the upstream CLI's final JSON document. The adapter now supports
source-specific bounded invocations and merges valid completed results. This is
implemented in `last30days_adapter.py`; it does not change scheduler priority,
Research work classes, Alpha, or the upstream skill.

The first source-specific probes exposed a Mac runtime compatibility issue. HN
and GitHub were failing with Python's
`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. The Mac
runtime already has `certifi`; the adapter now passes that CA bundle to the
pinned subprocess using process-scoped `SSL_CERT_FILE` and
`REQUESTS_CA_BUNDLE`. TLS verification remains enabled and no credentials or
cookies are added.

### Timing baseline

```text
PYTHON_STARTUP_SECONDS=0.05
MODULE_IMPORT_STARTUP_SECONDS=0.09
ADAPTER_SETUP_SECONDS=0.19
PLAN_SETUP_SECONDS=<sub-second local file write>
```

Observed real source wall times after the CA-bundle repair:

```text
HACKERNEWS=4.39s, 3 results, OK
GITHUB=8.91s, 1 result, OK
REDDIT=17.80s, 2 results, OK
YOUTUBE=21.24s, 1 metadata result, OK; 0 transcripts, degraded quality
GROUNDING=2.65s, 0 results, NO_RESULTS
```

The previous 20-second monolithic bound was therefore too short for some
healthy sources, especially Reddit and YouTube. Source-aware bounds are now:

```text
FAST_SOURCE_TIMEOUT=60s (Hacker News, GitHub)
MEDIUM_SOURCE_TIMEOUT=45s (Reddit, grounding/web)
SLOW_SOURCE_TIMEOUT=90s (YouTube)
DISCOVERY_CONCURRENCY=1
```

The adapter hard cap remains 180 seconds. Child process groups are terminated
and escalated to SIGKILL after the bounded grace period.

### Source certification

```text
HN_CERTIFICATION=PASS_REAL
HN_SOURCE_STATUS=OK
HN_RESULTS=3
HN_BACKEND=Algolia Hacker News API

GITHUB_CERTIFICATION=PASS_REAL
GITHUB_SOURCE_STATUS=OK
GITHUB_RESULTS=1
GITHUB_BACKEND=GitHub search API / existing gh-auth availability

REDDIT_CERTIFICATION=PASS_REAL
REDDIT_SOURCE_STATUS=OK
REDDIT_RESULTS=2
REDDIT_BACKEND=keyless RSS plus arctic-shift supplement

YOUTUBE_CERTIFICATION=PASS_REAL_METADATA_DEGRADED_TRANSCRIPT
YOUTUBE_METADATA_RESULTS=1
YOUTUBE_TRANSCRIPT_STATUS=0 captured; yt-dlp/caption coverage degraded
YOUTUBE_FAILURE_BOUNDARY=transcript enrichment, not metadata search

WEB_CERTIFICATION=DEGRADED_NO_RESULTS
WEB_BACKEND=upstream grounding backend
WEB_RESULTS=0
WEB_FAILURE_REASON=no usable result/credential-backed grounding in this runtime
```

The Reddit result is a genuine improvement over the prior direct probe: the
upstream keyless path used RSS and arctic-shift without browser cookies. The
existing direct Nexus Reddit blocker remains isolated; Last30Days does not read
browser cookies and does not bypass access controls.

The pinned preflight returned `status=ready`, available source families for
Reddit, YouTube, Hacker News, GitHub, and grounding, `gh` and `yt-dlp`
available, browser-cookie mode off, and no publication writes. Preflight did
not predict the Mac CA-bundle defect, so the HN/GitHub preflight/live mismatch
is recorded as a runtime compatibility defect repaired in the adapter.

### Partial-result proof

The real source-specific merge was exercised with HN at 60 seconds and YouTube
at an intentionally bounded 5-second test timeout. HN returned 3 real rows;
YouTube timed out during search initialization. The merged result remained
`PASS` with HN evidence, retained the YouTube timeout diagnostic, and did not
report a zero-result total. This proves source-specific execution and partial
result preservation.

### Cross-source run

After certification, an independent-source run for `business funding for new
LLC` returned 9 real signals across Hacker News, GitHub, Reddit, and YouTube in
56.8 seconds. The adapter produced a bounded cross-source cluster candidate:

```text
CROSS_SOURCE_CLUSTER_TEST=PASS_REAL_CANDIDATE
DEMAND_CLUSTER_ID=cluster_e2768598144ff5e9de9d
CLUSTER_SOURCE_TYPES=GITHUB,HACKERNEWS,REDDIT,YOUTUBE
CLUSTER_SIGNAL_COUNT=9
```

The candidate remains `DISCOVERY_ONLY`, not Alpha-promoted: several HN/GitHub
items were semantically weak for the funding question. The relevant current
signals include two Reddit business-banking/LLC items and one YouTube new-LLC
funding item. This is sufficient to prove acquisition and clustering, but not
to claim a validated business need or to create a duplicate of
`need_f527d1db8c4d1e5de721`. No Last30Days Alpha review or department handoff was
run on the mixed-quality candidate.

```text
EXISTING_NEED_MATCH=NOT_PROMOTED_MIXED_RELEVANCE
EXISTING_NEED_ID=need_f527d1db8c4d1e5de721
EXISTING_NEED_ENRICHED=NO
ALPHA_HANDOFF=NOT_RUN_EMPTY_QUALIFICATION_THRESHOLD
DEPARTMENT_HANDOFF=NOT_RUN
```

### Current certification summary

```text
HEALTHY_SOURCE_TYPES=HACKERNEWS,GITHUB,REDDIT,YOUTUBE_METADATA
DEGRADED_SOURCE_TYPES=YOUTUBE_TRANSCRIPTS,GROUNDING_WEB
UNAVAILABLE_SOURCE_TYPES=NONE_AFTER_CA_BUNDLE_REPAIR
SOURCE_SPECIFIC_EXECUTION=PASS_REAL
PARTIAL_RESULT_PRESERVATION=PASS_REAL
PROCESS_GROUP_CLEANUP=PASS_REAL
RUNAWAY_PROCESSES=NONE_OBSERVED
MAC_RESULT=PASS_WITH_PROCESS_SCOPED_CA_BUNDLE
ORACLE_RESULT=NOT_RUN
HOST_RUNTIME_BOUNDARY=MAC_RUNTIME_CA_LOOKUP_REPAIRED
```

The integration is therefore `PASS_REAL` for bounded source acquisition and
partial-result preservation, while remaining `PARTIAL` for the broader Demand
Radar business objective because the live candidate did not meet the quality
threshold for existing-need enrichment, Alpha review, or department handoff.

## Business-relevance closure attempt

Focused customer-demand variants were run against the higher-signal Reddit and
YouTube sources, with source weighting supported by the adapter at request time:

```text
CUSTOMER_DEMAND_PRIMARY_SOURCES=REDDIT,YOUTUBE
CUSTOMER_DEMAND_SECONDARY_SOURCES=HACKERNEWS,GITHUB
SOURCE_WEIGHTING_IMPLEMENTED=YES_REQUEST_LEVEL_PLAN_WEIGHTS
```

Variants included:

```text
new LLC denied business funding
business funding new LLC no revenue
new business funding documentation requirements
new LLC business bank account
startup business funding denied
business credit approval new business
How to get business funding for a new LLC
```

The runs were real and bounded, but they did not pass the coherence gate. The
ranker returned unrelated Reddit material for two narrow funding queries, one
relevant new-LLC banking thread for another, and a relevant lender-document
YouTube metadata result without a second corroborating source. One Reddit run
was rate-limited and YouTube frequently returned no result for the narrow
phrasing.

```text
FOCUSED_QUERY_EXPANSION=PASS_REAL_BOUNDED
COHERENCE_GATE=FAIL_NO_STABLE_TWO_SOURCE_AUDIENCE_PROBLEM_OUTCOME_CLUSTER
COHERENT_CLUSTER_FOUND=NO
EXISTING_NEED_MATCH=NOT_PROMOTED
EXISTING_NEED_ENRICHED=NO
ALPHA_HANDOFF=NOT_RUN
DEPARTMENT_HANDOFF=NOT_RUN
TOPICLESS_DISCOVERY_TEST=TIMEOUT_NO_CANDIDATES
```

The existing need `need_f527d1db8c4d1e5de721` remains unchanged. This is a
business-relevance limitation in upstream query/ranking quality, not a source
plumbing failure. The next safe improvement is a bounded semantic coherence
filter over audience, problem, desired outcome, and source relevance before
promotion; no threshold was lowered and no Alpha review was fabricated.
