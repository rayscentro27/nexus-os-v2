# WP9L Direct Tool Surface

`GENERIC_WRAPPER_INTERFERENCE=YES`.

The Oracle API surface now exposes `skills` and the authenticated
`nexus_mcp_remote` server, while the generic `delegation` wrapper is removed
from that lane. The existing Mac MCP remains the only authority. Its direct
surface is six current-state reads plus the bounded allowlisted specialist
tool; no arbitrary shell or department write tool is exposed.

`NOVA_DIRECT_TOOL_SURFACE=PASS`.
`TOOL_TRIGGER_QUALITY=PASS` after descriptions were made explicit about when
to use each read, returned provenance, and read-only constraints.
