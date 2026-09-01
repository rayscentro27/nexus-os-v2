# Nexus MCP Blocker Currentness Repair

`reports/hermes_modernization/daily_brief.json` is now evidence/context only
for blocker reads. Its nine historical entries are excluded from the live MCP
blocker view.

The live resolver derives blockers from:

- pending Ray approvals in `data/governed/approvals.jsonl`;
- latest governed work orders in `data/governed/work_orders.jsonl` whose state
  is explicitly `blocked`.

The known queued engineering work order remains a current work item, not an
automatically asserted blocker.

Observed result: `0` current blockers, `9` historical report entries filtered.

STALE_DAILY_BRIEF_BLOCKERS_EXPOSED_AS_CURRENT=0
