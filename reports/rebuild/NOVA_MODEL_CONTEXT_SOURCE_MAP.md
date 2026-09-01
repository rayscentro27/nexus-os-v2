# Nova Model Context Source Map

| Source | Purpose | Scope | Currentness | Model-visible on casual turn |
|---|---|---|---|---|
| `config/hermes/nova-profile/SOUL.md` | durable Nova identity | profile | static | yes |
| `recent_turns` user messages | conversational continuity | session | historical/contextual | yes |
| `recent_turns` assistant messages | continuity and referents | session | not authoritative | yes, now labeled |
| Nexus MCP definitions | optional capability access | turn | capability metadata | available, not result state |
| Nexus MCP results | canonical operational truth | turn | currentness-owned by Nexus | only after selection |
| `_current_shadow_context` | resource follow-up index | resource-backed turn | volatile/turn-linked | non-native resource path only |
| global Hermes SOUL/memory | other workloads | global | excluded | no |

The boundary is: history can explain what a user means; only a fresh canonical
capability result can establish present Nexus truth. Resource-backed prior
answers remain retained but are marked as continuity/history, not current state.

`COMPLETE_OBSERVABLE_CONTEXT_MAP=YES`; chain of thought is not captured.
