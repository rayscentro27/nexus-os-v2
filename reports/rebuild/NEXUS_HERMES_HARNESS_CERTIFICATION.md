# Hermes Harness Certification — 2026-08-29

The pinned runtime harness is composed of the s6-supervised gateway, provider
client, profile/session stores, native skills/tool registry, Kanban dispatcher,
and bounded terminal/tool adapters. The Nexus integration boundary is:

`TruthKernel authority → Nexus executor allowlist → Hermes advisory review`.

The Nexus wrapper cannot approve gates, enable payments or live trading, mutate
client production without authority, or invoke arbitrary shell. The local
Ollama route is certified for API reasoning without tools. Kanban worker
execution remains blocked because its required lifecycle tools are rejected by
the available local model and the existing alternate credential is not usable.
