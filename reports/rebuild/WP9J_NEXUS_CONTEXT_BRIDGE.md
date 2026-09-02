# WP9J Nexus context bridge

`services/nexus_mcp/server.py` is a real, governed, read-only Mac-side MCP
boundary. It exposes current reviews, work items, blockers, opportunities,
business state, and system health with currentness/provenance metadata and
receipts.

The Oracle `nova_nexus` profile currently has no `mcp_servers` entries in its
Oracle-side configuration. The Mac repository and its stdio MCP process are
not reachable from the Oracle container through the existing API bridge.

`NOVA_CURRENT_COMPANY_CONTEXT=NOT_PROVEN_ON_ORACLE`
`NOVA_CURRENT_STATE_QUERY=NOT_RUN`

The safe next implementation is a narrow authenticated context/MCP bridge,
with Mac Nexus retaining authority and Oracle receiving only structured
read-only results. No repository dump or Telegram cutover was performed.

