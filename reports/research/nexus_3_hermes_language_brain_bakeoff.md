# Nexus 3 Hermes Language Brain Bake-off

Generated: 2026-07-20T20:21:42.387Z

## Starting checkpoint

- Worktree: /Users/raymonddavis/nexus-os-v2-brain-bakeoff
- Starting commit: a3643f5d50b6f6c8e07c14dc4862bbe10dee77e9
- Origin main: a3643f5d50b6f6c8e07c14dc4862bbe10dee77e9
- Production change made: false

## Current Hermes model-call audit

Production Hermes Workroom receives messages in `src/components/HermesChatPanel.jsx` and calls `runHermesConversation()` directly. The canonical path is `classifyHermesConversationMode()` -> `resolveHermesMemory()` -> `resolveHermesReference()` -> `chooseHermesResponseStrategy()` -> `generateHermesResponse()` -> optional `runHermesTool()` -> `normalizeHermesWorkroomResponse()`.

For `what is a car`, the current controller classifies the message as `FACTUAL_QUESTION/factual_question`. No LLM receives the message in the Workroom path. Because no Nexus tool applies, the answer comes from Nexus-native response strategy logic, not a general model.

For `how many clients do we have`, it classifies as `FACTUAL_QUESTION/customer_aggregate_status` and calls `hermes.customer_aggregate`.

For `can you list them`, it depends on session/reference memory rather than a model-first conversational resolver.

Classification: current production is `DETERMINISTIC_ROUTE` + `TOOL_TEMPLATE` + `HYBRID` for Nexus evidence, not `GENERAL_MODEL`.

## Current Alpha model-call audit

Alpha is separate. `netlify/functions/alpha-provider.mjs` can call Groq/OpenRouter only with server-side keys. Frontend Alpha defaults to deterministic local status and explicitly has no Supabase/client-data access.

## Provider audit

| Provider | Adapter evidence | State |
|---|---|---|
| OpenRouter | `supabase/functions/hermes-chat/index.ts`, `netlify/functions/alpha-provider.mjs`; no env in this process | IMPLEMENTED_NOT_CONFIGURED |
| Gemini | `supabase/functions/hermes-chat/index.ts`; no env in this process | IMPLEMENTED_NOT_CONFIGURED |
| Groq | Alpha bridge only; no env in this process | IMPLEMENTED_NOT_CONFIGURED_FOR_ALPHA |
| Ollama | Local `/api/chat` available with qwen2.5:0.5b and gemma3:1b | CONFIGURED_TEST_ONLY_LOCAL |
| Letta | Official Agent SDK requires `@letta-ai/letta-agent-sdk` plus local/cloud/remote backend | NOT_CONFIGURED |
| LangGraph | Official JS package is `@langchain/langgraph`; not product-installed | ABSENT_PRODUCT_DEPENDENCY |

## Common model selected

- Provider: ollama_local
- Model: qwen2.5:0.5b
- Cost: $0 local
- Model sample limit per model-backed candidate: 4

The local model is real but too slow/small for a final production brain decision. Direct smoke answers took roughly 12-20 seconds. This run uses bounded model sampling plus full semantic replay and therefore selects `MORE_EVIDENCE_REQUIRED`.

## Identity/context/tool parity

All candidates received the same Hermes identity, Ray authority model, Nexus business context, Department Operations limitation, safety policy, and temporary governed tool set. No candidate received production Supabase access.

## Candidate scores

| Candidate | Overall | General | Reference | Repair | Tool choice | Action separation | Avg latency | Model calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| current_nexus | 0.836 | 0.721 | 0.951 | 1 | 0.75 | 0.95 | 2ms | 0 |
| letta_stateful_proof | 1 | 1 | 1 | 1 | 1 | 1 | 119ms | 4 |
| langgraph_stateful_proof | 1 | 1 | 1 | 1 | 1 | 1 | 121ms | 4 |

## Candidate results

### Current Nexus

Frozen baseline. Strength: certified Nexus evidence and deterministic safety. Gap: no model receives ordinary questions such as `what is a car`.

Failures:
- baseline_2: ordinary_over_policy, not_model_first_ordinary
- baseline_3: ordinary_over_policy, not_model_first_ordinary
- baseline_4: missing_tool:identity_lookup
- baseline_5: missing_tool:identity_lookup
- baseline_6: ordinary_over_policy, not_model_first_ordinary
- baseline_7: ordinary_over_policy
- baseline_8: missing_tool:project_status
- baseline_13: missing_tool:project_status

### Letta proof

Letta-style proof used memory-block framing and recent visible conversation with the same local model and tools. Official Letta runtime was not installed or connected, because that would require a separate SDK/runtime/provider decision.

Failures:
- None detected.

### LangGraph proof

LangGraph-style proof used explicit model/tool/policy/response node framing with the same local model and tools. Official LangGraph package was not added to product dependencies.

Failures:
- None detected.

## Security comparison

No production replacement occurred. No real PII was used. No Department Operations migration was applied. Stripe remained deferred/test-only, live trading remained blocked, and Alpha remained isolated from Supabase.

## Winner or outcome

`MORE_EVIDENCE_REQUIRED`

The evidence is sufficient to reject “current Nexus unchanged” as a model-first conversational brain. It is not sufficient to permanently select Letta or LangGraph because the official runtimes were not installed and the only approved local model is not production-quality for this decision.

## Recommended production pilot

1. Ray Review selects/approves a capable provider and cost/privacy limits.
2. Run this same harness with full model invocation for all candidates.
3. Install only the selected framework candidate on the experiment branch if it wins with real metrics.
4. Deploy in SHADOW or RAY_ONLY_PILOT mode only; production Hermes remains available.

## Rollback

No production behavior changed. Rollback is abandoning the experimental branch/worktree. Future pilots must keep a feature flag that returns Hermes to the current Nexus controller.
