# WP3 Hermes Capability Integration — 2026-08-29

Campaign: `HG-WP3-HERMES-CAPABILITY-PYTHON-LOOPS-20260829-01` (approved by
TruthKernel). The pinned Hermes 0.20.6 runtime remains private and Nexus is
the authority. Capability work is recorded as active, wrapped, or blocked;
no consequential capability is enabled merely because Hermes ships it.

| Capability family | Native evidence | Disposition | Current result |
|---|---|---|---|
| conversations, sessions, memory, profiles | tagged API/CLI and persistence tests | USE_HERMES_NATIVE / WRAP_WITH_NEXUS | PASS |
| skills / AgentSkills | bundled sync and skills API | WRAP_WITH_NEXUS | PASS |
| gateway API, provider routing, fallback | gateway/API and config surfaces | WRAP_WITH_NEXUS | Ollama PASS; fallback blocked |
| Bot Mode / gateway workers | native gateway and worker entrypoints | WRAP_WITH_NEXUS | PASS with scoped OpenRouter tool-worker profile |
| Kanban / worker board | native SQLite board, dispatcher, claims, task lifecycle | WRAP_WITH_NEXUS | bounded worker lifecycle, review handoff, and restart persistence PASS |
| harness, terminal, execute_code | native CLI/tool backends | WRAP_WITH_NEXUS | restricted; no arbitrary shell |
| MCP, browser, research, image, voice | native surfaces present | WRAP_WITH_NEXUS or BLOCKED_EXTERNAL_DEPENDENCY | disabled or credential-gated |
| cron/routines, hooks, trajectory | native surfaces present | KEEP_NEXUS_VERSION / WRAP_WITH_NEXUS | disabled or receipt-governed |
| messaging gateways | native gateway adapters | BLOCKED_EXTERNAL_DEPENDENCY | no new external communication |
| dashboard, SSH-backed execution | native commands | KEEP_NEXUS_VERSION | dashboard/SSH execution not enabled |

All listed campaign-scope capabilities have a disposition. Active Operator,
payments, live trading, production client mutation, public communication, and
TruthKernel authority transfer remain prohibited.
