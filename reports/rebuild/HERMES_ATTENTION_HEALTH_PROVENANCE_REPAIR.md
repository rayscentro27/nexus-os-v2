# Hermes attention health and history provenance

Campaign: HG-WP6.6-NOVA-DEDICATED-PROFILE-LIVE-CERTIFICATION-AND-NEXUS-RESOURCE-AUDIT-20260831-01

## Trace evidence

The 07:08 local attention turn is Telegram update `590357282`, outgoing message
`1058`, and Langfuse parent trace `d75a9b18dbf6d7496507a4a30c5999a9`. Its
correlated MCP trace is `71209c3dcc35fbade7ba25bd918af5a2`.

The fresh system-health result was current and partial. It contained
`overall_status=DEGRADED`, `active_services=0`, `degraded_services=1`, and the
warning `Partial telemetry: 1 source(s) returned errors`. Therefore the health
claims in the response were supported by fresh Nexus MCP state; no health
source repair was justified.

The same trace showed fresh canonical reads for blockers, opportunities,
reviews, work items, and health. The opportunity result had zero eligible
current items but exposed `historical_running_total=8510` in the current read
envelope. The response repeated that historical count even though the user
asked for current attention. This was the trace-proven presentation defect.

## Scoped repair

The current opportunity adapter no longer includes the historical accumulator
in its production current-state data envelope. The underlying research ledger
and internal historical access are unchanged. Current filtering metadata and
the truthful empty result remain available.

The repair does not alter Nova conversation behavior, Nexus health semantics,
MCP authority, delivery, or the dedicated Hermes profile.

## Verification

- `system_health`: fresh current/partial result; health claims supported.
- `nexus_get_opportunities`: zero eligible current items; historical and
  synthetic records remain filtered.
- stale daily-brief blockers: not returned by MCP.
- voice work order `wo_b5a3b90892804ec79164159997caf264`: current queued
  governed work item and remains eligible for attention responses.
