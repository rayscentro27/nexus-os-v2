# Nexus Department Work Queue Standard V1

Status: reference contract derived from the Research portfolio certification  
Reference implementation: Research V2 queue  
Certification report: `reports/research/NEXUS_RESEARCH_PORTFOLIO_QUEUE_CERTIFICATION_2026-09-20.md`

## Purpose

Every department may keep a department-scoped physical queue initially, but
work must use the same semantics for identity, priority, capability routing,
leases, retries, lineage, settlement, and monitoring. This avoids both a
single uncontrolled company queue and unrelated department-specific behavior.

## Purpose layer above the queue

For Research, queue state is execution state, not purpose. The standing
hierarchy is:

```text
COMPANY GOAL
→ RESEARCH CHARTER
→ CURRENT KNOWLEDGE / GAPS
→ GENERATED OBJECTIVE
→ WORK ITEM
→ EVIDENCE / ALPHA
→ HANDOFF / GOAL PROGRESS
→ NEXT OBJECTIVE
```

`QUEUE EMPTY != NO WORK`. When no eligible useful work exists, the supervisor
reads active company goals and the durable Research charter, identifies the
highest-value unresolved knowledge gap, generates a bounded objective, checks
its dedup key against active/recent objective work, and enqueues it through the
same queue contract. Goal-generated work must not outrank explicit Alpha or
urgent department returns unless its explicit work-item priority says so.

## Common work-item contract

Required for every queued item:

```json
{
  "work_id": "stable department-scoped identifier",
  "objective_id": "parent objective or project identifier",
  "parent_work_id": "optional direct parent work item",
  "department": "owning department",
  "work_type": "department-defined work type",
  "work_class": "department-defined class mapped to a universal class",
  "required_capabilities": ["certified capability IDs"],
  "priority": 0,
  "status": "QUEUED",
  "assigned_worker": null,
  "lease_owner": null,
  "lease_expiry": null,
  "attempt_count": 0,
  "max_attempts": 3,
  "retry_strategy": "bounded strategy identifier",
  "next_retry_at": null,
  "input_refs": [],
  "result_refs": [],
  "evidence_refs": [],
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "terminal_reason": null,
  "requested_by": "agent, department, or executive",
  "destination_department": null
}
```

`parent_work_id`, `destination_department`, and result/evidence references are
optional only when the work has no parent, handoff, result, or evidence yet.
`objective_id`, `work_id`, status, timestamps, and ownership are required for
objective-backed work. A department may retain compatibility aliases such as
Research `source_url`, `parent_request_id`, and `alpha_followup_required`, but
the canonical meaning must remain explicit.

## Standard lifecycle

```text
NEW → QUEUED → CLAIMED → RUNNING → EVALUATING
                              ├→ COMPLETE
                              ├→ FOLLOWUP_REQUIRED / QUEUED child
                              ├→ WAITING
                              ├→ RETRYABLE / WAITING with changed strategy
                              ├→ BLOCKED_EXTERNAL
                              ├→ SUPERSEDED
                              └→ FAILED_TERMINAL
```

Research compatibility mapping:

- `QUEUED`, `WAITING`, `IN_PROGRESS` remain the current active scheduling
  states; `IN_PROGRESS` represents CLAIMED/RUNNING.
- `COMPLETE`, `BLOCKED_EXTERNAL`, `FAILED_FINAL`, `PARKED`, and `SUPERSEDED`
  are terminal/non-reclaimable states.
- `MONITORING` is a nonterminal watch state and must not silently represent
  completed one-time work.

Every terminal transition clears the lease. A terminal item cannot be claimed
again.

## Priority and fairness

Universal priority tiers:

1. approval return or blocker repair
2. department request
3. Alpha or evaluator follow-up
4. assigned objective
5. monitored critical work
6. discovery
7. background monitoring

Research currently maps `ASSIGNED` to the highest active class, then
`MONITORED`, `DEMAND_DISCOVERY`, and `GENERAL_DISCOVERY`. Semantic types such
as department request and Alpha follow-up currently map to `ASSIGNED` with
their reason and parent fields preserved.

Priority is not an unlimited starvation rule. The Research reference
implementation grants a bounded five-claim quantum to a continuously
replenished class, then rotates through eligible lower classes using persisted
fairness state. Priority and age still order items inside a selected class.

## Capability routing

1. Work declares required capability IDs.
2. Dispatcher loads the certification registry.
3. Only `PASS_REAL` or explicitly bounded `PASS_REAL_BOUNDED` executors are
   eligible.
4. Limitations, bucket capacity, and external restrictions are enforced.
5. The best eligible executor is selected and a routing receipt records why.
6. The queue creates the lease; the worker claims and executes.
7. The result and evidence references return to the same work/objective
   lineage.

Worker registration, import success, or tool installation is never sufficient
for eligibility.

## Retry model

- A retryable failure preserves the objective and records the failure class.
- A same-strategy retry is allowed only when conditions may have changed and
  the bounded attempt budget remains.
- A strategy-changing retry must change source, capability, acquisition route,
  or another material condition.
- Malformed input is repaired, rerouted, superseded, or blocked; it is never
  retried forever unchanged.
- Provider/auth/anti-bot restrictions become `BLOCKED_EXTERNAL` when safe
  alternatives are exhausted.
- Exhausted meaningful strategies become `FAILED_TERMINAL` or an explicitly
  parked/superseded record with evidence preserved.

## Cross-department handoff

A handoff creates child work in the destination department, not an unrelated
row. It preserves:

```text
origin objective
→ origin work
→ origin artifact/evidence
→ source department
→ destination department
→ requested outcome
```

The child must carry the originating Research package, Alpha receipt, and
relevant evidence references when those exist. A handoff is not complete until
the destination queue receives, claims, reads the inputs, and persists a
result or a truthful blocker.

## Portfolio monitor

Every department monitor should expose the same conceptual fields:

- active objectives and project status
- queued, running, waiting, retryable, blocked, and terminal counts
- oldest work by class
- worker and capability utilization
- active leases and expiry
- follow-ups and evaluator returns
- handoffs in and out
- stale items and exact `why_still_queued`
- current next action

Nova should read this operational projection rather than reconstructing state
from chat text or process existence.

## Project / portfolio aggregation (Layer 2)

Research's canonical portfolio entity is the durable **objective**. The
canonical aggregation key is `objective_id`; there is no second Research
`project_id` store. A project is the executive view of one objective and all
of its child work, follow-ups, evaluator returns, retries, blockers, and
department dependencies.

The terms map as follows:

| Term | Standard meaning |
|---|---|
| project | Executive/portfolio view of one objective |
| objective | Durable aggregation key and desired outcome |
| mission | Optional source or campaign context; not a scheduling parent |
| investigation | A research question or evidence activity |
| work item | One schedulable child with a lease and terminal lifecycle |

The read model is additive above the queue. It groups children by
`objective_id` and derives, rather than stores last-write-wins, the following
fields: `status`, child state counts, required work completed/remaining,
optional work remaining, active/blocked work, outstanding follow-ups,
department dependencies, project priority, oldest active time, and child IDs.

### Project status contract

The supported aggregate statuses are:

`NOT_STARTED`, `ACTIVE`, `WAITING`, `NEEDS_MORE_RESEARCH`,
`WAITING_FOR_DEPARTMENT`, `BLOCKED`, and `COMPLETE`.

The reducer uses these rules in order:

1. An active required child (`IN_PROGRESS`) makes the project `ACTIVE`.
2. An unresolved Alpha/evaluator follow-up makes it `NEEDS_MORE_RESEARCH`.
3. A required child waiting on a destination department makes it
   `WAITING_FOR_DEPARTMENT`.
4. Required queued, waiting, or retryable work makes it `WAITING` or `ACTIVE`.
5. A required blocked/exhausted path makes it `BLOCKED` unless a completed
   required path and a still-viable alternate path establish a different
   status.
6. The project is `COMPLETE` only when every required child is terminal and at
   least one required child completed. Optional monitoring or background work
   cannot prevent completion.

Completed Alpha follow-ups no longer count as outstanding. Parked historical
portfolio/test rows are retained for audit but excluded from live obligations;
they are reported as `ignored_historical_work_count`. Superseded children are
terminal and never reclaimable.

### Required, optional, and replacement work

`required_work=true|false` is the explicit contract. Until a department adds
that field, `OPTIONAL`, `MONITORING`, and `BACKGROUND` roles, plus Research's
`MONITORED` and `GENERAL_DISCOVERY` classes, are treated as optional. A
replacement remains required unless explicitly marked optional. Historical
parked/legacy rows are excluded from current aggregation without deleting
their evidence.

### Project priority and progress

Execution priority remains a work-item concern and the fairness scheduler is
authoritative. Portfolio priority is a read-only derived value: the lowest
numeric priority among active required children, with department/evaluator
return work represented by its child priority. It must not change claim order.

Progress is factual, not an arbitrary percentage: required completed,
required remaining, optional remaining, active count, blocked count, and
follow-ups outstanding. Nova and Admin must explain the remaining child IDs
and next state instead of displaying a misleading completion percentage.

### Portfolio projection and executive visibility

Every department implementing this layer should expose a projection with:

- project count and status counts;
- five highest-priority projects and oldest active project;
- child states, required/optional counters, follow-ups, blockers, leases, and
  department dependencies;
- exact `why_still_queued` or `next action` when work is not complete.

Research exposes this projection through
`get_research_operational_state.project_portfolio`, sourced from the canonical
Research work queue. Nova reads that same live projection; it must not infer
portfolio state from chat text, process existence, or a single child row.

An explicit `project_id` may be added later when a department needs one
objective to participate in multiple coordinated programs. It is not required
for current Research compatibility.

## Adoption plan

| Department | Existing state | Gap | Reuse / migration risk |
|---|---|---|---|
| Research | JSON-backed queue, leases, capability routing | Add project aggregation and stronger source validation | Reference implementation; low risk if additive |
| Marketing | AI orchestration and bounded work-order path | Map work/return/revision receipts to common fields | Reuse Research lineage; avoid replacing Marketing AI |
| Creative | Handoff boundary exists; full queue certification pending | Prove receive/claim/result lifecycle | Start with child handoffs; no publication |
| Systems | Existing engineering/work-order paths | Normalize lease/retry/terminal vocabulary | Reuse governed work orders; protect repair authority |
| Funding/Clyde | Capability/evidence paths | Map funding requests and receipts | Preserve funding-specific evidence constraints |
| Customer Service | Department/service work paths | Add objective and destination lineage | Start read-only/support work |
| Trading | Specialized bounded/paper paths | Apply only where safe and non-live | Keep trading risk controls separate; no live mutation |

Adoption order: Research, Marketing, Creative, Systems, Funding/Clyde,
Customer Service, then Trading where the governance envelope permits it.
