# Hermes 0.20.6 Feature Utilization

Campaign: `HG-WP6.5-HERMES-CANONICAL-REASONING-PATH-REPAIR-20260830-01`

| Feature | Available | Current use | Disposition |
|---|---|---|---|
| Sessions | YES | Hermes foundation and platform context | Reuse; revalidate facts through Nexus |
| Memory | YES | Scoped conversational context | Context only, never factual authority |
| Profiles | YES | Hermes/Alpha/Nova role separation | Preserve |
| Skills / AgentSkills | YES | WP4/WP5 governed skills | Preserve allowlists |
| Bot Mode | YES | Scoped worker capability | Preserve Nexus governance |
| Kanban/workers | YES | Certified worker lifecycle | Use only for governed work |
| Handoffs | YES | Certified bounded handoffs | Preserve |
| Tool invocation | YES | Scoped provider route | Allowlist and validate |
| Model routing | YES | Ollama private / scoped tool provider | Preserve workload separation |
| Gateway/API | YES | Oracle Hermes 0.20.6 | Canonical runtime |
| Routines | AVAILABLE | Active Operator/Nexus scheduling | Preserved; not expanded |
| MCP/web/browser | PARTIAL | Existing bounded adapters | No unbounded enablement |

`LANGGRAPH_COMPLEMENTS_HERMES=YES`. LangGraph handles explicit stateful orchestration; Hermes owns agent/session behavior; Nexus owns evidence, authority, deterministic execution, and receipts.

`HERMES_NATIVE_FEATURES_BYPASSED=NONE_BY_THIS_REPAIR`. The previous live failure was a routing short-circuit, not replacement of a Hermes-native feature. Live utilization of the repaired path requires fresh Telegram certification.
