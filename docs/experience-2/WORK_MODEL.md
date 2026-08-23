# Nexus Work Model

## Purpose

Work is a presentation model over existing canonical stores. It is not a new queue, scheduler, database, or operator.

## Source map

| Work view | Existing truth |
| --- | --- |
| Running / scheduled | Active Operator, Continuous Loop, worker/runtime status |
| Needs You / approvals | Ray Review, approvals, work orders, governed action state |
| Completed / outputs | Reports, receipts, artifacts, mission activity |
| Failed / degraded | Mission Control, runtime reports, error receipts |
| Evidence | MarkItDown/Crawl4AI evidence, research sources, report references |
| Business result | Revenue Truth, Opportunity Engine, Growth, Business Active Operator |

## Work item shape

```text
title
agent_or_system
status
started_at / updated_at
progress (only when sourced)
reason
evidence_refs
receipt_refs
artifact_refs
next_step
approval_requirement
authority_boundary
```

Absent fields are rendered as `UNKNOWN` or omitted with an explanation; they are not inferred.

## Filters

`Needs You`, `Running`, `Scheduled`, `Completed`, `Failed`, `Approvals`, `All`.

Needs You is ranked by decision urgency and consequence. Running is grouped by meaningful work, collapsing repetitive healthy heartbeats. Failed shows the first actionable failure and source. All supports search and date filtering but does not become the front door.

## Work thread

The detail view has four layers:

1. **Brief:** what is happening, why it matters, and what is needed from Ray.
2. **Timeline:** agent/system events, handoffs, checks, and decisions.
3. **Evidence and receipts:** expandable source-backed proof.
4. **Next step:** governed action, ask an agent, open artifact, approve, or reject.

Example:

```text
Client Live Data Verification
Hermes started work
  → Supabase checked
  → Adapter checked
  → dependency identified
  → recommendation generated
  → Needs Ray
```

## Approval language

An approval card must say what, why, source, risk, proposed next step, what approval unlocks, what remains blocked, and evidence. It never uses “run now” as a substitute for the existing governed approval flow.

## Handoffs and artifacts

Handoffs appear in the same timeline as work events. Artifacts are linked outputs, not copied chat content. A work item can point to an Alpha report, Creative render, Hermes recommendation, or Mission Control receipt.

## Failure language

Use `FAILED`, `DEGRADED`, `WAITING`, `BLOCKED`, and `UNKNOWN` only when source truth supports them. Include retryability and owner. Do not turn a missing heartbeat into “healthy.”

## Mobile

On phone, a work card shows title, owner, status, reason, and next step. Evidence, timeline, and receipts open in a drawer. Approval actions remain large and explicit.
