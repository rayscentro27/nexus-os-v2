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

## Changed implementation

- `scripts/nexus_agent_platform/research_work_queue.py`
- `scripts/nexus_agent_platform/research_lane_scheduler.py`
- `scripts/run_continuous_operating_kernel.py`
- `scripts/research/run_dispatched_research_job.py`
- `scripts/nexus_agent_platform/research_alpha_pipeline.py`
- `scripts/nexus_agent_platform/research_operational_state.py`
- `scripts/nexus_agent_platform/demand_discovery.py`
- `scripts/nexus_agent_platform/tests/test_research_work_queue.py`
