# Nexus Project / Portfolio Aggregation Certification

Date: 2026-09-20
Reference commit: `9d49f3e6` plus the additive aggregation changes in this
working cycle.

## Executive result

Research now has an additive project/objective read model above the proven
work-item queue. The canonical aggregation key is the existing `objective_id`;
no second project store or scheduler was introduced. The reducer was tested
against ten status shapes and the live queue, and the canonical Nova read
capability returns the same projection.

`RESEARCH_QUEUE_REFERENCE_IMPLEMENTATION_STATUS=PASS_REAL_BOUNDED`

The individual queue engine remains the stronger certification boundary. The
new project layer is `PASS_REAL_BOUNDED`: it is a live read model with
deterministic tests, while some historical objectives still contain unresolved
or externally blocked work and therefore correctly do not aggregate to
`COMPLETE`.

## Semantics

```text
CANONICAL_PORTFOLIO_ENTITY=OBJECTIVE
CANONICAL_AGGREGATION_ID=objective_id
PROJECT=executive view of one objective and its child work
OBJECTIVE=durable desired outcome and grouping key
MISSION=optional source/campaign context
INVESTIGATION=research question/evidence activity
WORK_ITEM=one schedulable leased child
```

`parent_request_id`, Research package IDs, Alpha receipts, and department
targets remain lineage fields; they do not replace `objective_id` as the
aggregation key.

## Status contract and rules

`PROJECT_STATUS_CONTRACT=NOT_STARTED | ACTIVE | WAITING |
NEEDS_MORE_RESEARCH | WAITING_FOR_DEPARTMENT | BLOCKED | COMPLETE`.

`PROJECT_AGGREGATION_RULES=`

1. Any active required child keeps the project active.
2. An unresolved Alpha/evaluator return takes the project to
   `NEEDS_MORE_RESEARCH`.
3. A required child waiting on another department produces
   `WAITING_FOR_DEPARTMENT`.
4. Required queued/waiting/retryable work prevents completion.
5. A required blocked or exhausted path produces `BLOCKED` when no viable
   required path remains.
6. `COMPLETE` requires every required child to be terminal and at least one
   required child to have completed.
7. Optional monitoring/background work cannot block a completed objective.
8. Completed Alpha follow-ups are resolved evidence, not outstanding returns.
9. Parked portfolio-window, stale, and legacy history remains auditable but is
   excluded from current obligations; it is counted as ignored history.
10. Superseded work is terminal and non-reclaimable.

`REQUIRED_WORK_MODEL=` explicit `required_work`; compatibility inference uses
`OPTIONAL`, `MONITORING`, and `BACKGROUND` roles and Research's MONITORED/
GENERAL_DISCOVERY classes as optional.

`OPTIONAL_WORK_MODEL=` optional children contribute factual remaining-work
counters but cannot block required completion.

`SUPERSEDED_WORK_HANDLING=` terminal, preserved, excluded from active required
work and never reclaimable.

## Test evidence

`PROJECT_STATUS_CASES=10 contract cases plus 10 live/current multi-item
objectives inspected from the portfolio evidence.`

`CORRECT_STATUS_COUNT=10`

`INCORRECT_STATUS_COUNT=0`

The contract cases covered queued, waiting, running, complete, blocked,
Alpha-return, department-wait, optional-blocked, active replacement, and
superseded-child shapes. The live projection currently reported 53 objective
groups after archived-only portfolio rows were excluded. At the final read it
reported:

```text
NEEDS_MORE_RESEARCH=13
COMPLETE=27
BLOCKED=9
NOT_STARTED=4
```

Examples of live non-complete projects were the existing funding-readiness
company objective, the Marketing-linked progressive level-B objective, and
several Alpha-return objectives. Their active children and outstanding
follow-up IDs were exposed rather than hidden.

`PREMATURE_COMPLETIONS=0` in the tested cases:

- complete child plus running child;
- complete child plus pending Alpha follow-up;
- complete child plus Marketing-return work;
- complete original plus active replacement.

`INCORRECT_PROJECT_BLOCKS=0` in the tested cases. An optional blocked monitor
did not block a completed required objective; a required external blocker did.

`ALPHA_RETURN_PROJECT_STATE=NEEDS_MORE_RESEARCH while unresolved; advances
after the follow-up becomes terminal.`

`MARKETING_RETURN_PROJECT_STATE=WAITING_FOR_DEPARTMENT when a required
Marketing child is waiting; the existing live Marketing evidence request is
preserved in its original objective lineage.`

`POST_FOLLOWUP_PROJECT_STATE=ACTIVE/COMPLETE according to remaining required
children; completed Alpha returns no longer pin the project.`

## Priority, progress, and projection

`PROJECT_PRIORITY_MODEL=` read-only minimum numeric priority across active
required children. It does not alter the proven work-item fairness scheduler.
Department requests and Alpha returns retain their own child priority and
reason.

`PROJECT_PROGRESS_MODEL=` required completed, required remaining, optional
remaining, active count, blocked count, outstanding follow-ups, and child IDs.
No arbitrary percentage is exposed.

`PORTFOLIO_PROJECTION=` `build_project_portfolio()` groups canonical queue
rows by objective, derives status/counters/priority/oldest active child, and
returns status counts, top five projects, and oldest active project. It is
included in `research_operational_state` and the shared
`get_research_operational_state` capability.

`NOVA_PORTFOLIO_STATUS=PASS_REAL_BOUNDED` — a direct canonical capability call
returned the live projection, source `data/runtime/research_work_queue.json`,
53 project groups, status counts, and highest-priority project details. This
was a state read, not a hardcoded conversational response.

## Regression certification

`FAIRNESS_REGRESSION_STATUS=PASS_REAL_BOUNDED` — existing 30-claim retest
still reached ASSIGNED, MONITORED, DEMAND_DISCOVERY, and GENERAL_DISCOVERY;
low-priority eventual progress remained YES; routing remained 100%; duplicate
claims and lease collisions remained zero.

`CONCURRENCY_REGRESSION_STATUS=PASS_REAL_BOUNDED` — prior valid overlap
evidence remains two distinct executions with approximately 17.8 seconds of
overlap under total limit 3, with no duplicate claim. The read-model change is
additive and the queue/Alpha regression suite passed after it was added.

`WORK_ITEM_MANAGEMENT=PASS_REAL_BOUNDED`

`PRIORITY_MANAGEMENT=PASS_REAL_BOUNDED`

`FAIRNESS=PASS_REAL_BOUNDED`

`CAPABILITY_ROUTING=PASS_REAL_BOUNDED`

`LEASE_MANAGEMENT=PASS_REAL_BOUNDED`

`CONCURRENCY=PASS_REAL_BOUNDED`

`FOLLOWUP_MANAGEMENT=PASS_REAL_BOUNDED`

`RETRY_MANAGEMENT=PASS_REAL_BOUNDED`

`TERMINAL_SETTLEMENT=PASS_REAL_BOUNDED`

`PROJECT_AGGREGATION=PASS_REAL_BOUNDED`

`PORTFOLIO_VISIBILITY=PASS_REAL_BOUNDED`

`NOVA_PORTFOLIO_CONTROL=PASS_REAL_BOUNDED read-only`

## Standard and adoption

`QUEUE_STANDARD_UPDATED=YES`
Path: `docs/architecture/NEXUS_DEPARTMENT_WORK_QUEUE_STANDARD_V1.md`

The standard now defines both Layer 1 work-item behavior and Layer 2 project/
portfolio aggregation, required/optional semantics, blocker propagation,
progress, and executive visibility.

`ADOPTION_TEMPLATE_CREATED=YES`
Path: `docs/architecture/NEXUS_DEPARTMENT_QUEUE_ADOPTION_TEMPLATE_V1.md`

`MARKETING_STANDARD_GAPS=`

- Marketing has a real bounded AI/work-order path, but it is not yet mapped to
  the common `objective_id` project projection.
- Marketing capability routing is bounded but lacks a separately certified
  standard registry/read model equivalent to Research.
- Marketing's Research-return and revision receipts need common parent/child
  fields and aggregate status exposure.
- Marketing queue fairness, lease recovery, and portfolio aggregation have not
  been independently certified.
- Migration should reuse Marketing AI and map receipts; it should not replace
  the Marketing runtime.

`CREATIVE_STANDARD_GAPS=`

- Creative has existing bounded brief/asset and approval workflows, but a
  standard queue receive/claim/lease lifecycle has not been certified.
- Creative handoff lineage from Marketing and Research needs a standard child
  work contract and destination receipt.
- Creative project aggregation, retry/fairness, and Nova portfolio visibility
  remain unproven.
- Publication and approval boundaries must remain separate from internal
  Creative work.

## Runtime

`RESEARCH_LEFT_RUNNING=YES`
`RAY_REQUIRED_TO_RESTART=NO`
`CODEX_REQUIRED_TO_CONTINUE=NO`

The canonical launchd owner remained `com.nexus.continuous-loop`, with one
running process observed during the certification read. No second daemon was
created.

`NEXT_MACHINE_ACTION=` use this reference implementation and adoption template
to map Marketing's existing queue/receipts, then certify the Creative handoff
boundary; do not rewrite the Research scheduler.
