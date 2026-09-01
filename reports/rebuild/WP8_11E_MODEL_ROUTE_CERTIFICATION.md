# WP8.11E Model Route Certification

`ORACLE_OLLAMA_DIAGNOSTIC=PASS` — Oracle was healthy at the host/API level, but `/api/ps` had no loaded model; `gemma3:4b` is installed and a short bounded generation remained a timeout. Host memory/load were healthy and no runner process was present. No long blind probe was repeated.

`ORACLE_OLLAMA_RECOVERY_ATTEMPTED=YES`; `ORACLE_MODEL_LOAD_STATE=INSTALLED_NOT_LOADED`; `ORACLE_TINY_INFERENCE=TIMEOUT`; `ORACLE_FIRST_TOKEN_MS=NOT_OBSERVED`; `ORACLE_TOTAL_MS=BOUNDED_TIMEOUT`.

The active Hermes runtime is `/Users/raymonddavis/.hermes/hermes-agent`, commit `cea87d9139044870752aafdcdf9ca253049ae175`, model `gpt-5.5`, provider `OpenAI Codex` using an existing authenticated OAuth route. WP8.11B's inspected reference checkout was `/Users/raymonddavis/nexus-hermes-runtime`, `0.20.0`, commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`; they are distinct. The Creative router now uses completed `creative_ai` evidence to prefer the working route over reachability-only Oracle health.

Real bounded Director, Copywriter, Critic, and Revision calls completed: 4/12 calls, with latencies 16.4s, 12.6s, 23.3s, and 14.9s. Results are concise summaries only; no chain-of-thought is persisted. `CREATIVE_MODEL_FALLBACK_POLICY=PASS`, timeout/failure state is bounded, and state is retained on failure.
