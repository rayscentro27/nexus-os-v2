# GoClear Business Active Operator — Phase N

## Scope

Phase N extends the existing hourly Active Operator. It does not add an
operator, scheduler, queue, approval system, Mission Control, Revenue Hub,
Opportunity Engine, or Growth Engine.

## Business attention

The runner reads canonical Phase K opportunities, Phase L revenue snapshots,
Phase M growth experiments, and existing approvals/work orders. It emits
`nexus.business-attention.v1` findings with the deterministic
`nexus.business-priority.v1` policy. P0 system/safety findings remain ahead of
P1–P4 business items.

Opportunity review, growth review, research needs, measurement gaps, and stale
states retain their source IDs, evidence references, truth class, freshness,
approval requirement, and recommended next action. Revenue UNKNOWN/
NOT_CONNECTED is a P3 measurement connection gap, never a fabricated zero or
business failure.

## Governance and safety

Ray review uses the existing `opportunity.review` or bounded
`business_attention.review` action. Existing approval/work-order idempotency is
reused, including approval reuse for opportunity-linked growth work. No
approval is automatically resolved. The operator cannot publish, email, SMS,
post socially, spend, charge, refund, submit funding/grant applications, trade,
mutate production databases, or run arbitrary shell.

One bounded internal-safe action runs in the same dispatch: generating the
business priority brief. It writes a compact report, receipt, heartbeat fields,
and process telemetry with `external_action_performed=false`.

## Unattended behavior

Business attention executes inside the existing hourly
`com.nexus.active-operator-v2` schedule. No second cadence is installed.
Unchanged findings use stable dedupe keys and material fingerprints, so a
replayed hourly state produces duplicate suppression rather than new approvals
or work orders. Changed fixtures produce new fingerprints; resolved conditions
are no longer active findings.

## Live certification

The live dispatch consumed the Phase K pending Ray-review opportunity, the Phase
M evidence-backed growth experiment and its disconnected measurement state,
and the Phase L Revenue Truth snapshot. It generated a safe internal business
brief, created only bounded research work for genuine `NEEDS_RESEARCH` items,
reused/suppressed existing opportunity review approvals, and preserved
`UNKNOWN/NOT_CONNECTED` revenue semantics. The replay produced duplicate
suppression with no new business work orders.

Mission Control reads the existing Active Operator heartbeat and exposes the
Business Operator section with findings, priority counts, source statuses,
safe actions, work orders, duplicate suppression, top priority, and core-health
isolation. Hermes should read this canonical output for “what should I focus on
today?” and “what did Nexus do while I was away?” rather than recomputing
business priority.
