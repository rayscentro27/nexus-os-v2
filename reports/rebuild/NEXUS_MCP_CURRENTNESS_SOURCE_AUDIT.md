# Nexus MCP Currentness Source Audit

| Tool | Source/resolver | Filtering result |
|---|---|---|
| Reviews | governed approvals ledger via `get_pending_approvals` | Active pending Ray approvals only |
| Work items | governed work-order queue via `get_work_queue` | Approved/queued current queue view |
| Blockers | governed approvals plus latest governed work orders | Historical daily brief excluded |
| Opportunities | research decision artifact plus shared currentness policy | Stale and synthetic records excluded |
| Business state | shared operational summary | Components preserve independent status/source/freshness |
| System health | live shared system-health resolver | Runtime/process/worker semantics preserved |

The prior report aliases are no longer treated as authoritative current
blocker or opportunity state. Historical artifacts remain readable internally,
but cannot become current merely by being persisted.

PERSISTED_DOES_NOT_IMPLY_CURRENT=PASS
