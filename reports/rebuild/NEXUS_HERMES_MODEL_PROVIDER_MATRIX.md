# Hermes / Nexus Model Provider Matrix — 2026-08-29

No provider secret values are recorded.

| Provider | Credential state | Model | Test result | Fallback |
|---|---|---|---|---|
| Oracle Ollama | present/private | `gemma3:4b` | PASS for authenticated API reasoning; does not support tools | PRIMARY |
| Groq | existing Mac credential; Oracle test rejected HTTP 403 | candidate tool-capable model | BLOCKED_EXTERNAL_DEPENDENCY | NOT ELIGIBLE |
| OpenRouter | no usable campaign route; auxiliary path reported payment/credit failure | none selected | BLOCKED_COST_POLICY | NO |
| Hermes/Nous portal | no authentication present | none | BLOCKED_EXTERNAL_DEPENDENCY | NO |

`MODEL_PROVIDER_INVENTORY_COMPLETE=YES` and
`MODEL_ROUTING_IMPLEMENTED=YES` for the single verified local route.
`MODEL_ROUTING_MULTI_PROVIDER=BLOCKED_EXTERNAL_DEPENDENCY`; no multi-provider
success is claimed. Deterministic Python remains the preferred executor for
local operational work.
