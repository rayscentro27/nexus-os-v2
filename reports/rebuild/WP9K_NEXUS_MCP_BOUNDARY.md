# WP9K Nexus MCP Boundary

`ORACLE_TO_NEXUS_MCP_AUTH=PASS_REAL` and `LEAST_PRIVILEGE_PASS=PASS`.

The existing Mac `services/nexus_mcp/server.py` remains the authority. A
loopback-only Streamable HTTP adapter adds bearer authentication and is reached
from Oracle only through the existing reverse SSH tunnel. Missing and
incorrect bearer tokens returned HTTP 401. Authenticated discovery returned
the six canonical read tools plus bounded `nexus_delegate_specialist`.

Oracle has no filesystem, Supabase-admin, Keychain, scheduler, payment,
trading, publication, or shell authority. Delegation is allowlisted and maps
to an existing canonical read; every read and delegation writes a hashed
receipt under `data/runtime/nexus_mcp_receipts`.

Real Oracle Hermes 0.20.6 calls selected `nexus_get_reviews` and
`nexus_get_system_health` across the tunnel. A direct authenticated boundary
test selected SYSTEM delegation and created
`nexus-delegation-a8ffa4c415f644e39ea0f676c47e20f0`.

The direct delegation proves the boundary, not model-driven delegation.
