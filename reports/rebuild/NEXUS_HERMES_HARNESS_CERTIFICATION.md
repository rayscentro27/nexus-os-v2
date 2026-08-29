# Hermes Harness Certification — 2026-08-29

The pinned runtime harness is composed of the s6-supervised gateway, provider
client, profile/session stores, native skills/tool registry, Kanban dispatcher,
and bounded terminal/tool adapters. The Nexus integration boundary is:

`TruthKernel authority → Nexus executor allowlist → Hermes advisory review`.

The Nexus wrapper cannot approve gates, enable payments or live trading, mutate
client production without authority, or invoke arbitrary shell. The local
Ollama route remains certified for private reasoning without tools. The scoped
OpenRouter worker profile is certified for the required Kanban lifecycle tools;
provider selection is task-scoped and does not replace the local reasoning
route. A real Daily/System Operations run invoked the fixed Python executor,
validated its artifacts, recorded TruthKernel evidence, and received an
advisory Hermes review with final state `SUCCEEDED_VERIFIED`.
