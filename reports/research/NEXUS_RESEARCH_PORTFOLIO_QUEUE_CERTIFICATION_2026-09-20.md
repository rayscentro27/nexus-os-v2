# Nexus Research Portfolio Queue Certification

## Executive result

The current Research queue was stress-tested before changing its contract. The
test exposed strict class-priority starvation and a missing `SUPERSEDED`
terminal state. Both were repaired and the same selector/queue tests were
rerun successfully. Real portfolio executions proved objective-aware AI plans,
capability routing, public-source execution, Alpha returns, bounded overlap,
and lease exclusivity.

The result is `PASS_REAL_BOUNDED`, not a claim that all portfolio management is
complete. Explicit project-level aggregation and stronger source validation
remain internal work.

## Baseline

Before the portfolio was loaded:

```text
TOTAL_NONTERMINAL=14
QUEUED=14
RUNNING=0
WAITING=0
RETRYABLE=0
BLOCKED=0
ASSIGNED=14
MONITORED=0
DEMAND_DISCOVERY=0
GENERAL_DISCOVERY=0
ACTIVE_LEASES=0
VALID_WORK_AVAILABLE=YES
VALID_WORK_CLAIMABLE=YES
ALPHA_FOLLOWUPS=10
DEPARTMENT_REQUESTS=0 active (Marketing request existed in completed lineage)
MARKETING_RESEARCH_REQUESTS=1 historical/current lineage
YOUTUBE_ITEMS=0 active
ACTIVE_DUPLICATES=0
STALE_ITEMS=0 by current threshold
BASELINE_QUEUE_HEALTH=PARTIAL_REAL
```

The baseline already showed a concentrated `ASSIGNED` stream, which made it a
valid starvation test rather than an empty-queue test.

## Portfolio set

`PORTFOLIO_OBJECTIVE_COUNT=31` including the existing Marketing objective;
30 new bounded certification objectives were distinct.  
`PORTFOLIO_WORK_ITEM_COUNT=31` primary portfolio items, excluding derived
fallback and Alpha child rows.

`WORK_CLASS_DISTRIBUTION=ASSIGNED 13, MONITORED 5, DEMAND_DISCOVERY 5,
GENERAL_DISCOVERY 5, plus the existing Marketing lineage and two overlap
items.`

`CAPABILITY_DISTRIBUTION=WEB_ACQUISITION for public-source items,
LAST30DAYS_DEMAND for demand work, YOUTUBE for one approved watchlist item.`

`PRIORITY_DISTRIBUTION=10, 30, 35, 40, 45, 50, and 70 bounded priorities.`

All portfolio items used real public URLs or the approved YouTube watchlist;
no tool repository or fabricated customer claim was used.

## Priority and fairness

`CURRENT_PRIORITY_ORDER=ASSIGNED, DEPARTMENT_REQUEST, ALPHA_FOLLOWUP,
HIGH_VALUE_INVESTIGATION, MONITORED_YOUTUBE, MONITORED_CRITICAL,
DEMAND_DISCOVERY, GENERAL_DISCOVERY` as the semantic contract. Physical queue
classes currently map semantic department/Alpha requests into `ASSIGNED`.

Initial selector test: 12/12 claims selected `ASSIGNED`, and the same released
item was repeatedly selected. This was `PRIORITY_SELECTION_STATUS=FAILED_REAL`
for portfolio fairness.

Repair: persist a five-claim class quantum and a fairness cursor. The class
still wins by priority during its quantum, but eligible lower classes rotate
after the quantum.

Retest: 30 selector claims produced `ASSIGNED=25`, `MONITORED=2`,
`DEMAND_DISCOVERY=2`, `GENERAL_DISCOVERY=1`.

`PRIORITY_SELECTION_STATUS=PASS_REAL_BOUNDED`  
`LOW_PRIORITY_EVENTUAL_PROGRESS=YES`  
`STARVED_OBJECTIVES=NONE_OBSERVED_IN_RETEST`  
`STARVED_WORK_CLASSES=NONE_AFTER_QUANTUM_REPAIR`  
`MAX_QUEUE_AGE_BY_CLASS=not material during bounded run; age remains exposed
by the queue monitor`  
`TIME_TO_FIRST_CLAIM_BY_CLASS=ASSIGNED first; lower classes reached after
bounded quantum`  
`COMPLETION_RATE_BY_CLASS=ASSIGNED, MONITORED, DEMAND_DISCOVERY, and
GENERAL_DISCOVERY all received real claims; completion was source-dependent`
  
`FAIRNESS_STATUS=PASS_REAL_BOUNDED`

## Routing and concurrency

`TOTAL_ROUTING_DECISIONS=13` valid portfolio execution traces  
`CORRECT_ROUTING_COUNT=13`  
`INCORRECT_ROUTING_COUNT=0`  
`UNCERTIFIED_ROUTING_COUNT=0`  
`ROUTING_ACCURACY=100%`

`TOTAL_CONCURRENCY_LIMIT=3`  
`YOUTUBE_LIMIT=1`  
`WEB_LIMIT=1`  
`DISCOVERY_LIMIT=1`

The valid overlap retest used unique execution IDs in two independent runs:

- `research_exec_parallel_a9b4e78a294cee2d` — web acquisition, objective 05
- `research_exec_parallel_e5e426491e0baefc` — demand discovery, objective 30

Both were claimed and completed concurrently with approximately 17.8 seconds
of overlap. An earlier invalid overlap attempt reused one execution ID; it was
excluded from the result and did not create a double claim.

`PEAK_CONCURRENT_EXECUTIONS=2`  
`AVERAGE_ACTIVE_EXECUTIONS_WHILE_ELIGIBLE_WORK_EXISTS=not measured continuously
by this bounded run`  
`IDLE_CAPACITY_WITH_CLAIMABLE_WORK=NOT_PROVEN`  
`CONCURRENCY_UTILIZATION_STATUS=PASS_REAL_BOUNDED`

## Lease safety

On a real portfolio item, the first claim succeeded, a second simultaneous
claim returned no claim, completion cleared the lease, and a post-completion
reclaim returned no claim.

`DUPLICATE_CLAIMS=0`  
`LEASE_COLLISIONS=0`  
`EXPIRED_LEASE_RECOVERIES=1 bounded queue test`  
`COMPLETED_WORK_RECLAIMED=0`  
`LEASE_SAFETY_STATUS=PASS_REAL_BOUNDED`

## Lineage and deduplication

The tested lineage cases covered five ordinary portfolio objectives, three
Alpha follow-ups, two department-origin requests, and the existing Marketing
Research-return request.

`LINEAGE_CASES_TESTED=11`  
`BROKEN_LINEAGE_COUNT=0` for new objective-backed execution events  
`LINEAGE_STATUS=PASS_REAL_BOUNDED`

Execution events now carry `objective_id`, `work_id`, and parent request IDs
from the first CLAIMED event onward. Older unscoped events were not rewritten.

`FOLLOWUP_REQUESTS_GENERATED=5` portfolio Alpha follow-up returns  
`FOLLOWUP_WORK_CREATED=5`  
`FOLLOWUPS_DEDUPED=0 newly competing duplicates in the bounded portfolio;
the prior dedup repair remained at zero active duplicates`  
`ACTIVE_DUPLICATES_AFTER=0`  
`FOLLOWUP_DEDUP_STATUS=PASS_REAL_BOUNDED`

## Retry and settlement

Six first executions initially failed because the portfolio generator had
swapped source titles and URLs. The worker correctly classified the malformed
source and created strategy-changing children. The test input was repaired,
the exact fallback children were marked `SUPERSEDED`, and the originals were
rerun successfully or identified as unchanged duplicates.

`RETRY_CASES=6 malformed-source cases plus successful retry and duplicate
settlement cases`  
`STRATEGY_CHANGES=6 recorded`  
`IDENTICAL_FAILURE_LOOPS=0 after input repair`  
`BLOCKED_EXTERNAL=0 in this portfolio set`  
`RECOVERED_BY_FALLBACK=0; source repair made the fallback unnecessary`
  
`RETRY_MANAGEMENT_STATUS=PASS_REAL_BOUNDED`

The queue implementation previously rejected the documented `SUPERSEDED`
state. It now accepts it as terminal and non-reclaimable.

`COMPLETED_WORK_LEFT_ACTIVE=0` for the bounded portfolio window  
`TERMINAL_STATE_ERRORS=0`  
`SETTLEMENT_STATUS=PASS_REAL_BOUNDED`

All portfolio-derived primary and follow-up work was parked after the bounded
window with preserved execution history. Existing non-portfolio Research and
Marketing work was not cleared.

## Project status

Current Research uses `objective_id` as the project grouping key. `work_id`
identifies an executable item; `parent_request_id` identifies a request/return
parent; Research packages and Alpha receipts are governed evidence children.
There is not yet a separate durable `project_id` or complete aggregate status
reducer.

`PROJECT_GROUPING_MODEL=objective_id grouping with parent/evidence links`  
`PROJECT_STATUS_CASES=10 multi-item objectives inspected`  
`INCORRECT_PROJECT_STATUS_COUNT=NOT_MEASURED; aggregate reducer is not yet a
certified capability`  
`PROJECT_STATUS_AGGREGATION=PARTIAL_REAL`

This is a remaining internal defect, not a reason to rename the current model.

## Portfolio scheduler

`TEST_DURATION=approximately 3 minutes of bounded selection/execution tests`
  
`SCHEDULER_CYCLES=30 fairness selections plus 11 valid worker execution IDs`
  
`CLAIMS=16 valid execution claims; additional selector claims were released
for fairness measurement`  
`COMPLETIONS=10 valid execution completions`  
`FOLLOWUPS=5`  
`RETRIES=6 malformed-input retries`  
`HANDOFFS=0 new external/department handoffs; existing Marketing lineage
remained present`

`PORTFOLIO_SCHEDULER_STATUS=PASS_REAL_BOUNDED`

## Marketing request under load

`MARKETING_OBJECTIVE_ID=progressive-level-b-objective-20260919`  
`MARKETING_RESEARCH_WORK_ID=marketing-research-return:mkt_research_return_1ba3a9a0ecc7441583f6`
  
`MARKETING_REQUEST_PRIORITY=ASSIGNED semantic department request, priority 0`
  
`MARKETING_REQUEST_CLAIMED=YES`  
`MARKETING_REQUEST_RESULT=completed on same objective; Alpha/Marketing still
require more evidence`  
`OTHER_WORK_CONTINUED=YES`  
`DEPARTMENT_REQUEST_PRIORITY_STATUS=PASS_REAL_BOUNDED`

## Nova visibility

`NOVA_PORTFOLIO_READ=PASS_REAL_BOUNDED` through the canonical
`get_research_operational_state` capability and Research operational state
projection. It exposes queue depth by class, active work, Alpha follow-ups,
blocked work, recent completion, and next scheduled work.

`NOVA_QUEUE_SUMMARY=PASS_REAL_BOUNDED`  
`NOVA_PROJECT_DETAIL=PARTIAL_REAL` — objective lineage is available, but no
certified aggregate project reducer exists.  
`NOVA_WHY_STILL_QUEUED=PASS_REAL_BOUNDED` at item level through status,
priority, lease, retry, blocker, and lineage fields.

## Defects and repairs

1. `PORTFOLIO-PRIORITY-001`: strict class precedence starved lower classes.
   Repaired with persisted five-claim quantum and fairness cursor. Retest
   reached all four queue classes.
2. `PORTFOLIO-LEASE-001`: repeated release observation reselected the same
   item. This is safe from double claim but inefficient; bounded class fairness
   now limits class starvation. Per-item claim-history policy remains a future
   optimization.
3. `PORTFOLIO-INPUT-001`: test generator supplied title as URL. Corrected
   portfolio records, superseded unnecessary fallback children, and reran.
4. `QUEUE-STATUS-001`: `SUPERSEDED` was documented but rejected by the queue.
   Added it to the canonical status vocabulary and terminal settlement.
5. `PROJECT-AGG-001`: no complete project-level status reducer. Not repaired
   in this run because it requires a separate read-model change; documented as
   the next internal queue-standard adoption item.

`DEFECTS_FOUND=5`  
`DEFECTS_REPAIRED=4`  
`DEFECTS_REMAINING=1` (`PROJECT-AGG-001`)`

## Retest summary

```text
RETEST_PRIORITY=PASS_REAL_BOUNDED
RETEST_FAIRNESS=PASS_REAL_BOUNDED
RETEST_ROUTING=PASS_REAL_BOUNDED
RETEST_CONCURRENCY=PASS_REAL_BOUNDED
RETEST_LEASES=PASS_REAL_BOUNDED
RETEST_LINEAGE=PASS_REAL_BOUNDED
RETEST_DEDUP=PASS_REAL_BOUNDED
RETEST_RETRY=PASS_REAL_BOUNDED
RETEST_SETTLEMENT=PASS_REAL_BOUNDED
RETEST_PROJECT_STATUS=PARTIAL_REAL
RESEARCH_PORTFOLIO_MANAGEMENT_STATUS=PASS_REAL_BOUNDED
```

## Standardization

`STANDARD_CREATED=YES`  
`STANDARD_PATH=docs/architecture/NEXUS_DEPARTMENT_WORK_QUEUE_STANDARD_V1.md`

`STANDARD_WORK_LIFECYCLE=NEW → QUEUED → CLAIMED → RUNNING → EVALUATING →
COMPLETE/FOLLOWUP_REQUIRED/WAITING/RETRYABLE/BLOCKED_EXTERNAL/SUPERSEDED/
FAILED_TERMINAL`

`STANDARD_PRIORITY_MODEL=universal priority tiers with bounded class quantum
and persisted fairness cursor`

`STANDARD_CAPABILITY_ROUTING=required capabilities → certification registry →
eligible executor → routing receipt → lease → worker → result`

`STANDARD_RETRY_MODEL=bounded attempts, changed strategy, backoff, explicit
external block, and terminal settlement`

`STANDARD_HANDOFF_MODEL=child destination work preserving objective, origin
work, artifact/evidence, source department, destination department, and
requested outcome`

`STANDARD_MONITOR_MODEL=objectives, queue states, age, utilization, leases,
follow-ups, handoffs, blockers, and why-still-queued`

`DEPARTMENT_ADOPTION_PLAN=Research reference implementation; then Marketing,
Creative, Systems, Funding/Clyde, Customer Service, and Trading where safe.`

## Runtime

`RESEARCH_LEFT_RUNNING=YES`  
`RAY_REQUIRED_TO_RESTART=NO`  
`CODEX_REQUIRED_TO_CONTINUE=NO`

