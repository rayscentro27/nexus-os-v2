# Nexus Research Continuation Doctrine V1

Status: bounded real implementation on the Research reference queue.

## Purpose

Research exists to continuously reduce uncertainty around active Nexus company
goals with sourced, challengeable intelligence. A queue is the execution
surface; it is not the source of Research purpose.

## Goal hierarchy

```text
COMPANY GOAL
→ RESEARCH DEPARTMENT CHARTER
→ CURRENT KNOWLEDGE / GAPS
→ GENERATED RESEARCH OBJECTIVE
→ STANDARD QUEUE WORK ITEM
→ CERTIFIED WORKER / PUBLIC EVIDENCE
→ AI INTERPRETATION
→ ALPHA REVIEW
→ DEPARTMENT HANDOFF / GOAL PROGRESS
→ NEXT KNOWLEDGE GAP
```

The canonical company-goal portfolio remains the goal store. Research uses
`objective_id` for work aggregation and `parent_goal_id` for purpose lineage.
It does not create a second goal or queue system.

## Standing charter

The durable charter is `research-charter-nexus-continuous-intelligence-v1`,
stored at `data/governed/research_charter.json`. Its standing duties are to
find customer needs and unmet demand, identify customer language and desired
outcomes, investigate existing alternatives and missing value, support
GoClear/Clyde funding intelligence, monitor approved sources, answer
department requests, and reduce uncertainty around active company goals.

## Goal-driven objective generation

The planner reads:

- active company goals and success conditions;
- the Research charter;
- active and completed objective questions;
- current queue/project state;
- known evidence and gaps;
- Alpha returns and department dependencies.

It emits a bounded objective with:

`objective_id`, `parent_goal_id`, `question`, `why_it_matters`,
`unknown_to_resolve`, `required_evidence`, `likely_capabilities`, `priority`,
`stop_condition`, and `dedup_key`.

The model may propose a capability, but the continuation layer maps it to a
certified Research executor. Unsupported labels are never silently routed.

## Empty-queue behavior

```text
QUEUE EMPTY
→ read active goals
→ read charter
→ inspect portfolio and gaps
→ generate one bounded objective
→ deduplicate
→ enqueue through ResearchWorkQueue
→ claim through the existing scheduler
```

An empty queue must not return a terminal “nothing to do” state. A bounded
deterministic fallback is allowed only when the model is unavailable, and must
still be derived from the goal/charter rather than a generic random topic.

## Deduplication

The key is derived from normalized `goal_id + question + unknown_to_resolve`.
An active or recent matching key links to existing work instead of creating a
new objective. Historical evidence is retained.

## No-goal fallback

If no active company goal exists, Research follows the charter and the normal
priority order: department requests, Alpha follow-ups, unfinished
investigations, monitored sources, customer-demand discovery, then general
discovery. This is still bounded and uses the standard queue.

## Blocked and terminal goals

Research records the dependency, blocker, and missing evidence for a goal with
no researchable path, then continues independent goals and standing duties.
It does not retry forever. A goal stops generating new work only when it is
complete, paused, cancelled, externally blocked with no researchable
alternative, or additional investigation is documented as unlikely to reduce
uncertainty materially.

The `$1,000/month` certification goal is a planning target only. Research
evidence must never mark revenue earned or the company goal achieved.

## Result feedback

Each goal-generated work item preserves the goal and objective lineage. After
settlement, the result and Alpha state are recorded in
`data/governed/research_goal_progress.jsonl` with `YES`, `PARTIAL`, or `NO`
uncertainty reduction, the next knowledge gap, and the next action. Goal
portfolio progress is updated without claiming completion from a research
package alone.

## Nova visibility

The existing `get_research_operational_state` read exposes
`research_continuation`, including active goals, charter status, pending
goal-generated work, recent goal feedback, and the empty-queue rule. Nova can
therefore answer what goal Research supports, why an objective was generated,
what was learned, and what comes next from canonical state.
