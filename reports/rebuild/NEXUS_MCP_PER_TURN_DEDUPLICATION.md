# Nexus MCP per-turn deduplication

The prior duplicate pattern came from repeated model/tool continuation requests
being executed independently by the MCP boundary. The server now keys a small
in-memory result cache by `(turn_id, capability)`, reuses only successful,
current-turn results, and writes a receipt for each duplicate request marked
`deduplicated=true`. A new turn always gets a new read. Failed reads are not
cached, so legitimate retry remains possible.

Receipts include turn/update correlation when supplied by the runtime.
