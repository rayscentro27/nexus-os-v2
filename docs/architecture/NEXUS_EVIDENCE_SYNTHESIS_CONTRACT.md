# Nexus Evidence and Synthesis Contract

The Phase A boundary is:

`Telegram → authenticated Nexus ingress → deterministic evidence broker → existing Hermes/LangGraph graph → claim validation → Telegram`

The broker is not a prose generator and is not an authority source. It projects only the selected capability result for the current request. Each projected item is one of `FACT`, `ESTIMATE`, `ASSUMPTION`, or `UNKNOWN`, and includes source, freshness, confidence, and authority metadata.

TruthKernel/Nexus remains authoritative for approvals, canonical state, credentials, capability eligibility, execution, and receipts. Hermes may interpret and explain the projected evidence; it cannot turn `UNKNOWN` into `FACT`, approve a gate, or claim an action without a verified result.

The current implementation reuses the existing `AgentState` and Hermes graph. Operational reads attach `evidence_payload` and `claim_validation` metadata before response composition. If claim validation detects a material unsupported claim, the response degrades safely and the existing deterministic route remains available. The graph and platform remain flag-gated, preserving rollback; no live Telegram route was enabled by this phase.

Business/financial synthesis must label scenarios separately from facts: costs and revenue examples are estimates or scenarios unless backed by evidence. No business authority was expanded.

