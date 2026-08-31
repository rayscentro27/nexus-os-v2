# Nexus MCP canonical capability audit

Campaign: HG-WP6.6-NEXUS-MCP-SERVER-FOUNDATION-AND-READ-ONLY-CAPABILITIES-20260831-01

The old `nexus_read_shadow` adapter selected capability and runtime registries. It did not answer a live operational question. The new MCP boundary maps only to approved shared Nexus reads:

| MCP tool | Shared capability | Authority/truth owner | Mode |
|---|---|---|---|
| `nexus_get_reviews` | `get_pending_approvals` | Nexus governed approval ledger | read-only |
| `nexus_get_work_items` | `get_work_queue` | Nexus governed work-order layer | read-only |
| `nexus_get_blockers` | `BLOCKERS` | Nexus canonical operational-read layer | read-only |
| `nexus_get_opportunities` | `get_opportunities` | Nexus governed opportunity reader | read-only |
| `nexus_get_business_state` | `get_operational_summary` | Nexus shared operational summary | read-only |
| `nexus_get_system_health` | `get_system_health` | Nexus runtime health reader | read-only |

Unavailable or stale upstream data remains marked unavailable/stale; the MCP server never invents an item.

