# WP8.11D Model Route Recovery

The Oracle Ollama VM was reachable and had `gemma3:4b` installed, but
`/api/ps` showed no loaded model and a tiny JSON generation request timed out
after 120 seconds. Remote memory was healthy (about 20 GB available, no swap
pressure, near-zero load), and Ollama was running. The bounded conclusion is a
model-load/inference-path failure, not host exhaustion. Logs were not exposed
and no secrets were printed.

Implemented `creative/model_router.py` with explicit health states, model
metadata, primary-to-fallback policy, and no silent paid fallback. The
existing `model_intelligence.py` remains bounded at 12 calls and records
provider failures without losing Creative state.

`CREATIVE_MODEL_ROUTER=IMPLEMENTED`
`CREATIVE_MODEL_HEALTH_CONTRACT=PASS`
`CREATIVE_MODEL_FALLBACK_POLICY=PASS`
`CREATIVE_MODEL_TIMEOUT_BUDGET=PASS`
`CREATIVE_MODEL_FAILURE_RECOVERY=PASS`
`REAL_CREATIVE_DIRECTOR_MODEL=NOT_PROVEN`
`REAL_CREATIVE_COPY_MODEL=NOT_PROVEN`
`REAL_CREATIVE_CRITIC_MODEL=NOT_PROVEN`
`REAL_CREATIVE_REVISION_MODEL=NOT_PROVEN`

The canonical Hermes CLI also has no configured LLM provider. Ray review is
required to restore an approved functioning model route before Creative
after-hours model operation can be certified.

