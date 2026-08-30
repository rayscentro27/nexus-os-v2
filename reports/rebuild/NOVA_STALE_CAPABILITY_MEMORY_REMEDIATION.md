# Nova Stale Capability Memory Remediation

Campaign: `HG-WP6.5-NOVA-STALE-SESSION-MEMORY-QUARANTINE-RUNTIME-TELEMETRY-AND-FRESH-SESSION-RETEST-20260830-01`

The prior active Ray session was archived before migration. Its complete historical JSON remains under `scripts/data/runtime/nova_memory_archive/` and is marked `HISTORICAL_SESSION` with `current_capability_truth_eligible=false`.

The active memory now uses schema 3 and `capability_state=QUERY_ON_DEMAND`. Seven stale capability assertions were removed in the first migration and one additional “haven’t been able…” variant was removed in the second migration. No historical file was deleted.

Quarantined categories include stale claims about web access, Nexus access, Gmail, Calendar, external systems, and simulated/19-process state. The active memory retains non-matching conversational turns; current capability state is not migrated from conversation.

`STALE_ASSISTANT_ASSERTIONS_REMAINING=0` in the active session.
