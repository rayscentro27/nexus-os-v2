# Nexus Department Work Queue Standard V1

Status: reference contract derived from the Research portfolio certification  
Reference implementation: Research V2 queue  
Certification report: `reports/research/NEXUS_RESEARCH_PORTFOLIO_QUEUE_CERTIFICATION_2026-09-20.md`

## Purpose

Every department may keep a department-scoped physical queue initially, but
work must use the same semantics for identity, priority, capability routing,
leases, retries, lineage, settlement, and monitoring. This avoids both a
single uncontrolled company queue and unrelated department-specific behavior.

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

## Project status aggregation

`objective_id` is the current Research project grouping key. A project status
must aggregate all child work, evidence, evaluator state, and handoffs; it must
not be inferred from the last child row alone. Recommended precedence is:

`BLOCKED` → `WAITING`/`NEEDS_MORE_RESEARCH` → `ACTIVE` → `READY_FOR_ALPHA` →
`READY_FOR_HANDOFF` → `COMPLETE`, subject to unresolved children and required
receipts.

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

