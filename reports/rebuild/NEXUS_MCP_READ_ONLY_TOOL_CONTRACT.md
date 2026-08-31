# Nexus MCP read-only tool contract

Each result is structured data with `status`, `as_of`, `source`, `source_type`, `data`, `items`, `metadata`, `error`, and `request_id`. Metadata identifies canonical/read-only boundaries, freshness, and item count. User-facing prose is not generated here.

Each receipt contains tool name, request ID, timestamps, canonical capability, result status, item count, error, read-only flag, Nexus authority owner, and a receipt hash. Six tools are registered:

`nexus_get_reviews`, `nexus_get_work_items`, `nexus_get_blockers`, `nexus_get_opportunities`, `nexus_get_business_state`, `nexus_get_system_health`.

