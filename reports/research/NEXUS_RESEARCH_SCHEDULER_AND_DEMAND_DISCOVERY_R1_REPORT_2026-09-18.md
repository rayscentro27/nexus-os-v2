# Nexus Research Scheduler and Demand Discovery R1

Date: 2026-09-18 (Phoenix)

## Status

`RESEARCH_SCHEDULER_REPAIR_STATUS=PARTIAL`

The durable priority queue, lease recovery, explicit source lifecycle, bounded
worker caps, Alpha follow-up re-entry, operational queue projection, and
deduplicated customer-need schema are implemented and unit-proven. A live
overnight drain and a fresh external demand-discovery run are intentionally not
claimed from this local certification run.

## Root cause and architecture

The old primary selector was:

`WAKE -> score all lanes -> select one lane/source -> process one item -> sleep`

It treated assigned V2 work, recurring sources, and discovery as competing
lanes. Fairness and refresh scoring could therefore select unchanged generic
sources while unfinished YouTube or Alpha-requested work remained pending.

The new primary selector is:

`WAKE/SUPERVISE -> durable assigned queue -> due monitored work -> demand discovery -> general discovery`

Governed V2 investigations with `RESEARCH_MORE` and unfinished bounded mission
items are projected into the operational queue; governed records remain the
source of truth. Existing lane scoring remains as the lower-priority monitored
fallback and is no longer allowed to outrank a claimed assigned item.

## Work classes and priority

Implemented classes:

- `ASSIGNED`
- `MONITORED`
- `DEMAND_DISCOVERY`
- `GENERAL_DISCOVERY`

The queue stores durable work IDs, source/objective/mission links, selection
reason, attempt count, lease owner, lease expiry, attempt ID, lifecycle, and
evidence references. Priority order is assigned work, department/Alpha and
unfinished investigation work, monitored work, demand discovery, then general
discovery. Expired leases return to `QUEUED` without creating a duplicate claim.

The first governed projection produced 12 assigned queue items: four unfinished
approved-watchlist mission items plus eight unfinished V2 investigations. The
four mission items correspond to the approved Credit Plug, Michael Ionita,
Alec Delpuech, and Stedman Waiters watchlist; no new channel was invented.

## Concurrency

The daemon now dispatches bounded batches instead of one detached child per
wake. Defaults are configurable through environment variables:

```
NEXUS_RESEARCH_MAX_TOTAL_CONCURRENCY=3
NEXUS_RESEARCH_MAX_YOUTUBE_CONCURRENCY=1
NEXUS_RESEARCH_MAX_WEB_CONCURRENCY=1
NEXUS_RESEARCH_MAX_DISCOVERY_CONCURRENCY=1
```

The implementation classifies work into YouTube, web, or discovery slots and
returns a claim when its slot is full. It does not create an unbounded fan-out.
The deterministic worker-cap and bucket proof passed; a live multi-process
network run is not claimed here.

## Source lifecycle and YouTube

`ONE_TIME` work becomes `COMPLETE` and leaves the active queue. Monitored work
uses cadence and duplicate backoff; repeated unchanged results can be parked
after the configured threshold. Terminal refresh records are skipped by the
lane selector. The worker passes explicit lifecycle state into refresh
bookkeeping instead of treating every source as a recurring source.

YouTube remains a first-class monitored channel path. Channel monitoring and
video jobs remain distinct, and the existing worker continues to select only
approved channels and existing bounded mission targets. Completed one-time
video jobs are not requeued by the durable queue. Stedman Waiters remains
`BLOCKED_EXTERNAL_FINAL` in governed mission state; no anti-bot restriction is
bypassed.

## Demand discovery

`demand_discovery.py` projects repeated governed demand questions into a
deduplicated `research_needs.jsonl` record. A need requires aggregated evidence
from at least two records/references and contains audience, problem, desired
outcome, demand signals, customer congregation, existing solutions, commercial
intent, evidence gaps, and Alpha-review-required state. It does not select a
product, claim monetization, or launch an action.

When all terminal monitored sources are exhausted and no higher-priority work is
queued, the scheduler seeds one bounded `DEMAND_DISCOVERY` pass. The worker
executes the governed-question projection and settles the work item. This is a
safe demand-signal projection; a fresh public multi-source demand crawl still
requires a separate approved acquisition cycle.

## Alpha and downstream handoff

Alpha evaluations classified as `MORE_RESEARCH_USEFUL` or
`MATERIAL_CONTRADICTION` now create durable `ASSIGNED` follow-up work with
priority 2, parent evaluation ID, objective ID, and evidence references. The
source URL is preserved when present. This creates the return path:

`Alpha deficiency -> assigned Research follow-up -> evidence -> Alpha re-review`

Existing Alpha routing and governed handoff semantics are preserved. Qualified
department handoff execution is not expanded in this scheduler patch.

## Runtime observability

`research_operational_state.py` now exposes queue-backed current state:

- active assigned, monitored, and discovery work
- queue depth by class
- Alpha follow-ups
- blocked items
- recent completed work
- next scheduled work
- productivity counters for assigned completion, monitoring, new content,
  demand discovery, investigations, Alpha handoffs, qualified findings,
  department handoffs, duplicate unchanged work, parked, and blocked work

This prevents a stale historical report from being presented as current work.

## Tests and proof

Passed:

- assigned items drain before monitored/discovery items
- expired lease recovery
- one-time completion is not requeued
- demand discovery requires aggregated evidence and deduplicates needs
- worker bucket and concurrency defaults
- scheduler/operational-state regressions
- Python compilation
- `git diff --check`
- governed projection proof: 12 assigned items projected; three claims settled
  sequentially while the next assigned item remained selected
- bounded demand projection proof: one structured need created from two source
  records

Command:

```text
env PYTHONPATH=scripts python3 -m pytest -q \
  scripts/nexus_agent_platform/tests/test_research_work_queue.py \
  scripts/nexus_agent_platform/tests/test_continuous_operating_kernel.py \
  scripts/nexus_agent_platform/tests/test_research_operational_state.py
```

Result: `17 passed`.

The broader Alpha pipeline test file still contains two pre-existing
expectations for the earlier Alpha decision vocabulary (`QUALIFIED` and
`REJECTED`); current implementation intentionally returns
`SUFFICIENT_FOR_PRELIMINARY_PLAN` and `MORE_RESEARCH_USEFUL`. Those expectations
were not changed as part of this scheduler repair.

## Remaining blockers

1. A production-equivalent live drain needs to run long enough to observe three
   assigned workers completing without manual restart.
2. A fresh public demand-discovery acquisition cycle is not yet implemented;
   current demand discovery is a bounded governed-question projection.
3. Department handoff execution remains owned by the existing downstream
   handoff path and was not widened in this run.
4. A live concurrency run should be performed during an approved maintenance
   window because it can invoke real network acquisition and provider calls.

## Production certification window

The existing launchd owner was verified as:

```text
com.nexus.continuous-loop
  -> scripts/ops/run_with_nexus_runtime_env.sh
  -> .venv-agent-platform/bin/python3 scripts/run_continuous_operating_kernel.py --daemon --interval-seconds 1200
```

No competing Research daemon was started. The service was safely kickstarted to
load the repaired runtime. Initial queue state was 12 queued assigned items,
zero active leases, and zero monitored/discovery queue items.

Observed real production dispatches included:

- assigned V2 investigation `investigation:investigation_8905027434994d81db93`,
  completed with `FULLY_PROCESSED`;
- assigned Alpha follow-up
  `alpha-followup:alpha_eval_a4a3517b35a34fd383a72c86b238e129`, completed with
  `FULLY_PROCESSED` and a new Research package;
- assigned mission items for approved YouTube channels, with external
  acquisition failures preserved as retryable rather than stopping other work;
- concurrent workers `research_exec_248b85b083604995addb`,
  `research_exec_811efb859b9240dd9135`, and
  `research_exec_63c81efc49a44c608f77` claimed at approximately
  `2026-09-18T15:32:26Z` and ran concurrently. They represented YouTube,
  assigned follow-up web research, and monitored web work respectively. The
  observed total was 3, within the configured cap.

The queue moved from 12 initial assigned items to a changing live queue because
fresh Alpha `MORE_RESEARCH_USEFUL` decisions also created three new priority-2
follow-ups. At the latest observation, two assigned items were complete, three
were retryable failures caused by external YouTube acquisition/provider limits,
and the remaining assigned work stayed queued or was actively leased. This is
real progression, not a claim that the entire queue drained in one window.

The first three production batches selected assigned work before generic lane
work. A monitored SBA item was allowed only after the YouTube and web class
slots were occupied; it did not preempt an available assigned slot.

## YouTube monitor certification

The real approved-channel monitor path checked all four approved channels:

| Channel | Monitor | Candidate | Result |
|---|---:|---|---|
| Credit Plug | PASS | `MJDeOEJ_kio` | monitoring |
| Michael Ionita | PASS | `TlpJdvFQLeY` | monitoring; acquisition failed externally |
| Alec Delpuech | PASS | `6XngV5NQgMg` | monitoring; acquisition failed externally |
| Stedman Waiters | PASS | `CiGQ7to-5J4` | remains externally blocked |

No CAPTCHA or anti-bot bypass was attempted. The queue/mission state prevents
completed one-time jobs from re-entering. The follow-up patch also preserves
`ONE_TIME` lifecycle on mission-backed YouTube video refresh records rather than
misclassifying them as generic monitored sources.

## Fresh demand and Alpha result

A bounded public-demand attempt used two current public Reddit URLs about LLC
funding and business-credit denial. The fetcher reached Reddit, but received a
JavaScript challenge page with zero posts and zero evidence spans. The evidence
quality was therefore `UNVERIFIED`; no customer need was promoted and no
commercial claim was made.

Alpha’s real governed evaluator returned `MORE_RESEARCH_USEFUL` with confidence
`HIGH`, created a durable Alpha receipt/evaluation record, and automatically
created priority-2 Research follow-up work. The follow-up executed through the
production Research worker and produced an updated Research package. The
evaluator used in this path recorded `MODEL_CALLS=0`; this certification does
not falsely call a model-backed Alpha review proven for this new demand item.

## Current certification classification

```text
PRODUCTION_RUNTIME_TEST=PASS_REAL_BOUNDED
ASSIGNED_QUEUE_DRAINING=PASS_REAL_PROGRESS
PARALLEL_WORK_PROOF=PASS_REAL
YOUTUBE_MONITORING=PASS_REAL_MONITOR_CHECKS; acquisition partially blocked externally
FRESH_DEMAND_DISCOVERY=PARTIAL_UNVERIFIED_SOURCE_ACCESS
ALPHA_FOLLOWUP_LOOP=PASS_REAL
OVERALL=PARTIAL
```

The remaining blockers are external source access for fresh community evidence,
YouTube media acquisition failures (`HTTP 403`/caption or audio unavailable),
and a model-backed Alpha review receipt for the new demand item. The scheduler,
leases, priority ordering, bounded overlap, queue visibility, and follow-up
return path are production-proven.

## Changed implementation

- `scripts/nexus_agent_platform/research_work_queue.py`
- `scripts/nexus_agent_platform/research_lane_scheduler.py`
- `scripts/run_continuous_operating_kernel.py`
- `scripts/research/run_dispatched_research_job.py`
- `scripts/nexus_agent_platform/research_alpha_pipeline.py`
- `scripts/nexus_agent_platform/research_operational_state.py`
- `scripts/nexus_agent_platform/demand_discovery.py`
- `scripts/nexus_agent_platform/tests/test_research_work_queue.py`
