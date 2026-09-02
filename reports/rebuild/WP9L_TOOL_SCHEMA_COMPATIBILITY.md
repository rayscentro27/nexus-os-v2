# WP9L Tool Schema Compatibility

The authenticated MCP schema was inspected directly. The specialist tool is
an object with required `specialist` enum and `objective` string fields. The
allowlist is represented in the schema and revalidated server-side. Missing
or unknown specialists are rejected; objectives are bounded to 500 characters.

Local schema/unit tests passed. A real Oracle model-driven current-state read,
sequential two-tool read, and specialist call completed after the API surface
repair.

`TOOL_SCHEMA_COMPATIBILITY=PASS_REAL`.
