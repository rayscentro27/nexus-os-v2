# Hermes / Nexus Model Provider Matrix — 2026-08-29

No provider secret values are recorded.

| Provider | Credential state | Model | Test result | Fallback |
|---|---|---|---|---|
| Oracle Ollama | present/private | `gemma3:4b` | PASS for authenticated API reasoning; does not support tools | PRIMARY |
| Groq | existing route; Oracle test rejected HTTP 403 | candidate tool-capable model | BLOCKED_EXTERNAL_DEPENDENCY | NOT ELIGIBLE |
| OpenRouter | existing canonical runtime credential | `minimax/minimax-m2.7:free` for tool workers; `google/gemma-4-31b-it:free` schema probe | PASS for scoped tool worker; one free route rate-limited | SCOPED TOOL WORKER |
| Hermes/Nous portal | no authentication present | none | BLOCKED_EXTERNAL_DEPENDENCY | NO |

`MODEL_PROVIDER_INVENTORY_COMPLETE=YES` and
`MODEL_ROUTING_IMPLEMENTED=YES`. Oracle Ollama remains the private reasoning
route; OpenRouter `minimax/minimax-m2.7:free` is the certified scoped tool
worker route. Deterministic Python remains the preferred executor for local
operational work.
