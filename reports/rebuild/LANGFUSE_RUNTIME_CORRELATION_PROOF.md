# Runtime correlation proof

`NovaTrace` assigns the turn id before MCP discovery and exports `NOVA_LANGFUSE_TRACE_ID`, `NOVA_LANGFUSE_UPDATE_ID`, `NEXUS_MCP_TURN_ID`, and `NEXUS_MCP_UPDATE_ID` before tool discovery. MCP receipts also have trace, turn, and update fields.

The local greeting trace proves non-null turn correlation through intake, context, generation, synthesis, and completion. The controlled MCP attempt did not reach a successful MCP child, so successful end-to-end parent/child MCP correlation remains unproven. The normal result path now finalizes the trace before returning; the no-tool early-return path also finalizes it.

No behavior was changed in routing, freshness, referent handling, deduplication, or conversation presentation.
