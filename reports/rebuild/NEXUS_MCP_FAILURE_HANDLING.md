# MCP failure handling

The server catches canonical-read exceptions and returns an explicit `NOT_AVAILABLE` result with an empty item list and error metadata. It never fabricates current Nexus state. A successful read can still carry `partial`, `unknown`, or stale freshness from the canonical source.

Focused tests cover canonical-read exceptions, empty results, read-only receipts, and the complete six-tool surface. The stdio protocol probe also covered server startup, initialize, discovery, and all six calls.

