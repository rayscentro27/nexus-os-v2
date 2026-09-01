# Nexus MCP live-runtime forensic preflight

`MCP_CURRENTNESS_FILTER_NOT_ON_LIVE_PATH=NO`: live receipts prove the resolver
ran and filtered historical data.

`LIVE_RUNTIME_STALE=NO` for the MCP server code: receipts use the current
schema/canonical sources, although the profile invokes an external Hermes venv.

Primary proven causes: `NO_FRESH_MCP_READ`,
`SESSION_CONTEXT_DOMINATES_FRESH_RESULT`, and referent freshness failure.

The required readiness result is `NO`: the live evidence does not prove fresh
review/blocker/opportunity reads on the required follow-up turns.
