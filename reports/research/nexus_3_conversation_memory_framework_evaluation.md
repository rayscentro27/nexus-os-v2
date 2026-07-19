# Nexus OS 3.0 — Conversation Memory Framework Evaluation

Generated: 2026-07-18

No external repository or package was installed.

| Candidate | Useful pattern | Nexus overlap | License/security note | Disposition |
|---|---|---|---|---|
| LangGraph | Explicit state graphs and checkpointing | Capability OS, governed execution, and Wave 4A session contracts cover current need | External dependency and persistence model would require separate security review | STUDY_PATTERN_ONLY |
| Mem0 | Memory extraction and retrieval | Wave 3 brain memory and Wave 4A advisory/selection memory cover current bounded need | Would require strict PII/tenant/memory promotion controls before use | BOUNDED_EVALUATION_LATER |
| Letta | Long-lived agent memory and tool state | Nexus intentionally avoids autonomous long-lived agents in Wave 4A | High governance burden for production use | STUDY_PATTERN_ONLY |
| Zep | Conversation history and memory summaries | Nexus-native bounded summaries are sufficient for current Hermes certification | Durable transcript storage would need RLS/retention/privacy design | BOUNDED_EVALUATION_LATER |

## Decision

`NEXUS_NATIVE_SUFFICIENT` for Wave 4A.

External frameworks may be studied later, but should not be installed until the native certification data shows a concrete gap that cannot be handled by the current Capability OS, Knowledge Layer, and Hermes conversation engine.
