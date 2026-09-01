# Nova attention aggregation forensics

The attention request used Hermes multi-tool reasoning, not a Nexus-side
attention summary. The live 07:08 MCP trace queried blockers, opportunities,
reviews, work items, and system health. Each result was fresh for the turn.

- Reviews: `get_pending_approvals`, zero current.
- Blockers: governed current-state resolver, zero current; historical report
  entries filtered.
- Opportunities: research-decision adapter, zero eligible current before and
  after the repair; its historical accumulator was the defect.
- Work items: governed queue, one queued Voice repair work order.
- Health: live composite resolver, partial/current degraded telemetry result.

The 8,510 claim entered through the pre-repair opportunity MCP payload and was
then selected by Hermes as apparently relevant context. It was not injected by
the profile, global memory, or shadow path.

The repaired current envelope now exposes current opportunity state and filter
metadata without exposing the historical accumulator as answer material.
