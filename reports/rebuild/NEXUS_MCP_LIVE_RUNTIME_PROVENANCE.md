# Nexus MCP live runtime provenance

Campaign: HG-WP6.6-NEXUS-MCP-LIVE-RUNTIME-PROVENANCE-AND-FRESHNESS-FAILURE-FORENSICS-20260831-01

The worker log identifies the live sequence as updates `590357265` through
`590357272`, session `nova-telegram-primary-1288928049`, using
`scripts/nova/nova_telegram_worker.py` and the repository
`scripts/nova/nova_hermes_shadow.py`. The repository HEAD and origin/main were
`036536b`.

The profile points MCP discovery at
`/Users/raymonddavis/nexus-hermes-runtime/.venv/bin/python`, while its
`PYTHONPATH` points at this repository. Live MCP receipts written at
00:28 UTC have the current receipt schema and canonical sources, proving the
repository MCP server/currentness resolver executed. Their turn correlation is
null because the turn environment was set after MCP discovery; this is a
proven receipt-correlation defect, not proof of stale state.

The live worker is not running now; launchd reports
`com.nexus.telegram-hermes-nova` disabled. No reload was performed.
