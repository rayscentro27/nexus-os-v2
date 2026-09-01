# Nova attention health final preflight

Campaign: HG-WP6.6-LANGFUSE-FINAL-LIVE-ATTENTION-HEALTH-PROVENANCE-REPAIR-20260901-01

## Provenance result

The live attention receipt was Telegram update `590357282`, message `1058`,
with parent trace `d75a9b18dbf6d7496507a4a30c5999a9` and correlated MCP trace
`71209c3dcc35fbade7ba25bd918af5a2`.

Fresh MCP supplied:

- blockers: 0 current, 9 historical filtered;
- opportunities: 0 current, 8,508 historical and 2 synthetic filtered;
- reviews: 0 current;
- work items: 1 current queued governed work order;
- health: current/partial, `DEGRADED`, `active_services=0`,
  `degraded_services=1`, with one unavailable telemetry source.

The health claims were therefore fresh-MCP-supported. The Voice work-order
claim remains supported by the current governed queue.

## Repair

The current opportunity adapter previously exposed the historical research
accumulator as `historical_running_total=8510` inside the current-state result.
That field was removed from the current production envelope. The source ledger,
classification counts, and internal historical access were not deleted or
changed. A post-repair Hermes-native preflight returned zero current
opportunities without volunteering the historical accumulator.

No Nova profile, prompt, routing, health resolver, MCP authority, delivery, or
conversation behavior was changed.

## Verification

Scoped MCP, ordering, delivery, and evidence tests: 15 focused tests passed;
31 relevant regression tests passed. Compilation and `git diff --check` passed.
The unrelated legacy suite still contains expectations for superseded operator
graph/SOUL behavior and patched handlers; those failures are outside this
campaign and were not altered.
