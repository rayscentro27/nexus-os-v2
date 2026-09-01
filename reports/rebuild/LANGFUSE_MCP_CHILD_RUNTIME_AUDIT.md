# Langfuse MCP child runtime audit

Configured command: `/Users/raymonddavis/nexus-hermes-runtime/.venv/bin/python -m services.nexus_mcp.server` with repository `PYTHONPATH`. The interpreter exists and contains MCP SDK 1.28.1. Independent import passed and the server process starts under the configured runtime.

The initial failure was caused by the child environment not receiving correlation variables, not by a missing interpreter. The dedicated profile now explicitly passes `NEXUS_MCP_TURN_ID`, `NEXUS_MCP_UPDATE_ID`, and `NOVA_LANGFUSE_TRACE_ID` as interpolated non-secret environment entries.

`MCP_CHILD_RUNTIME_VALID=PASS`; `MCP_CHILD_PATH_REPAIR_SCOPED=NO` (path was valid).
