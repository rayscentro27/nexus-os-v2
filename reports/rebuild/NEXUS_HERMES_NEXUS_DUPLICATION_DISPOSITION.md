# Hermes / Nexus Duplication Disposition — 2026-08-29

| Area | Disposition |
|---|---|
| conversations, sessions, profiles, memory | USE Hermes native; WRAP with Nexus context/receipts |
| skills, gateway API, provider routing | WRAP_WITH_NEXUS |
| Kanban/workers and handoff | WRAP_WITH_NEXUS; retain Nexus work orders as authority |
| harness/tool execution | KEEP Nexus executor broker; Hermes selects only allowlisted capability IDs |
| model fallback/retry | WRAP_WITH_NEXUS and fail closed |
| routines/cron, messaging, browser, MCP, voice | KEEP Nexus version or BLOCKED_EXTERNAL_DEPENDENCY; no blind activation |
| trajectory/evidence | WRAP_WITH_NEXUS |

No legacy implementation was deleted. Active Operator remains paused.
