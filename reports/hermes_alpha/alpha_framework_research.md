# Hermes Alpha Framework Research

Research date: 2026-07-03. Primary sources were official repositories/docs.

| Framework | Runtime/license | Strengths | Weaknesses / Alpha fit | Decision |
|---|---|---|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Python and JS/TS; MIT | Explicit state graphs, conditional edges, durable execution, memory, HITL, tracing ecosystem | Adds a framework/runtime and optional platform coupling; Alpha v1 needs only eight deterministic nodes | Copy graph-state, transition, checkpoint, interrupt, and trace concepts; do not install now |
| [CrewAI](https://github.com/crewAIInc/crewAI) | Python; MIT | Clear role/crew/flow separation and approachable task delegation | Multi-agent autonomy/tool surface is excessive for Phase 1; telemetry/sharing settings require scrutiny | Copy desk/lab role boundaries conceptually; do not install |
| [Pydantic AI](https://github.com/pydantic/pydantic-ai) | Python; MIT | Typed dependencies/outputs, provider abstraction, validation, evals, OTel support | Python dependency conflicts with current TS-native scaffold; structured output reliability still depends on model | Copy schema validation, provider result, cost, and eval patterns conceptually |
| [Agno](https://github.com/agno-agi/agno) | Python; Apache-2.0 | Agent/team/workflow layers, memory, HITL, guardrails, tracing, service runtime | Broad production platform, storage, integrations, scheduling, and control plane exceed Alpha Phase 1 | Reference later for operations/observability; reject as v1 dependency |
| [Letta](https://github.com/letta-ai/letta) | Python/TS API; Apache-2.0 | Long-lived memory blocks, model independence, message history, local mode | Server/API and self-modifying memory are too broad and create new persistence/security concerns | Copy working/episodic/promoted-memory concepts only |
| Lightweight internal TS state machine | Existing runtime; project license | Small, auditable, zero new dependencies, deterministic tests, exact safety boundaries | Fewer built-in tools/traces; must build evaluation discipline | Use for Alpha v1 |

## Recommendation

Keep the internal TypeScript scaffold. Use LangGraph-style state transitions, CrewAI-style desk labels, Pydantic-style typed outputs/provider contracts, and Letta-style tiered memory promotion. Add an immutable node trace and evaluation fixtures before considering a framework. Do not install large agent frameworks until a real need—durable resumability, parallel graphs, or production tracing—survives a measured prototype.
