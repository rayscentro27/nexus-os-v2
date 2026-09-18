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
