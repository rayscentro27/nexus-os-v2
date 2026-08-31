# Nova Brain Path Consistency

The same configured Telegram session uses the stable chat-derived Nova memory namespace and the same source graph/model configuration across turns. Source inspection showed the same five-stage graph and same active SOUL for all controlled prompt classes.

The path is not behaviorally identical across turns:

- utility requests can finish before model generation;
- factual company questions can execute the existing capability gate before generation;
- ordinary advisory/current questions use `model_first`;
- model capability envelopes add a bounded continuation call;
- validation failures use deterministic fallback text.

Prompt and resource hashes were stable for equivalent empty-memory assemblies. A real Telegram receipt does not currently persist prompt hash, resource-catalog hash, session prompt version, or fallback branch, so historical per-turn identity cannot be proven from receipts alone.

Primary forensic conclusion: the live brain is one model/SOUL/graph with multiple execution branches, not evidence of a second Nova model. The key unresolved issue is whether resource requests and failures are being observed and executed on the Telegram path.
