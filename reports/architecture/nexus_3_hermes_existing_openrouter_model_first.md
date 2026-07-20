# Nexus 3 Hermes Existing OpenRouter Model-First Tool Bridge

Generated: 2026-07-20

## 1. Old Production Path

Previous production Workroom path:

`HermesChatPanel.jsx -> runHermesConversation() -> deterministic classifier/router/tools`

For ordinary language such as `what is a car`, the legacy classifier selected `FACTUAL_QUESTION / factual_question`, so no language model received the message.

## 2. Root Cause

The defect was routing order. Hermes was not failing after model inference; ordinary language was intercepted before the existing OpenRouter `hermes-chat` Edge Function could run.

## 3. Current Provider Configuration

The existing provider stack is reused:

- provider: `openrouter`
- primary model: `openai/gpt-4o-mini`
- fallback model: `google/gemini-2.0-flash-001`
- key location: Supabase Edge Function secret only

No provider, model, or secret configuration was changed in this phase.

## 4. Direct OpenRouter Smoke

Previous direct smoke against the deployed `hermes-chat` Edge Function:

- prompt: `What is a gondola?`
- provider: `openrouter`
- model invoked: true
- tool required: false
- response returned: true
- observed function latency: approximately `1624ms`
- fallback used: false

This proved the existing OpenRouter runtime can answer ordinary language once reached.

## 5. Routing Replacement

`src/lib/hermesModelFirst/hermesModelFirstController.ts` remains the canonical pilot controller.

In `RAY_ONLY_PILOT` or `ACTIVE` mode, normal Ray/admin Workroom messages call `hermesChat()` with `mode: model_first_conversation`. This bypasses the older `routeModel()` no-model gate and sends ordinary language to the existing Supabase Edge Function.

`OFF` mode still uses the legacy deterministic route.

## 6. Turn Decision Contract

The Edge Function now defines a bounded model decision contract:

- `DIRECT_RESPONSE`
- `TOOL_REQUEST`
- `CLARIFICATION`

The OpenRouter decision call requests strict structured JSON. A single correction retry is allowed for malformed decision output. Hidden chain-of-thought is neither requested nor stored.

## 7. Model Request Modes

Tool-free flow:

`OpenRouter decision -> DIRECT_RESPONSE -> browser`

Tool-backed flow:

`OpenRouter decision -> TOOL_REQUEST -> Nexus validation -> tool execution -> OpenRouter grounded final answer -> browser`

The bridge does not require two model calls for ordinary conversation.

## 8. Tool Registry

The server-owned registry in `supabase/functions/hermes-chat/index.ts` exposes only safe tool metadata to the model:

- `get_current_time`
- `get_hermes_identity`
- `get_nexus_version`
- `get_project_status`
- `get_system_health`
- `list_reports`
- `summarize_report`
- `get_client_aggregate`
- `get_approval_summary`
- `get_department_status`
- `get_revenue_status`
- `get_repo_intelligence_status`
- `get_answer_provenance`
- `draft_task`
- `draft_ray_review`
- `draft_schedule`

The model never receives Supabase credentials, service-role credentials, tenant overrides, or approval authority.

## 9. Capability OS Gateway

Before execution, tool requests pass server-side validation for:

- known tool name
- authenticated actor token presence
- Ray/admin role eligibility
- input schema
- action class
- self-approval denial

Denied requests return a policy result to the model for a safe final answer. Unknown tools and malformed arguments are denied.

## 10. Supabase Boundary

Supabase remains authoritative for Nexus facts. The first bridge uses safe aggregate and report-backed adapters. `get_client_aggregate` performs aggregate-only count checks and never returns names, SSNs, credit data, addresses, bank details, or raw documents.

The Department Operations migration remains separate and unapplied in this phase; department status is labeled `SYNTHETIC_READ_MODEL` where appropriate.

## 11. Conversation History

`HermesChatPanel.jsx` sends recent visible Workroom messages. The Edge Function sanitizes and bounds history before sending it externally. Latest visible conversation remains the priority source for references.

## 12. Action Separation

Draft tools return draft-only results:

- no approval
- no execution
- no deployment
- no external send

Self-approval and execution attempts are denied by policy. The pre-model high-risk action blocker remains for direct execution verbs such as deploy, charge, trade, delete, and live activation.

## 13. Provider Failure

Provider failures return a specific degraded model-first response:

`My conversational model is temporarily unavailable. I can still provide certain verified local Nexus status responses, but general conversation is degraded.`

The old generic authorized-context fallback is not used for ordinary tool-free questions in the pilot path.

## 14. Cost

The Edge metadata records model, fallback use, model rounds, token usage where supplied, token estimates where usage is absent, max output tokens, and latency.

No model was changed to optimize theoretical cost during this phase.

## 15. Security

Security posture:

- OpenRouter key: server-side Supabase secret only
- Supabase service role: not used in the browser
- browser: no provider keys, no service-role key, no raw sensitive client data
- Alpha: unchanged; no Supabase/client PII access
- client PII: excluded from tool outputs and model context

## 16. Letta Decision

Letta remains deferred. The selected next measurement is whether existing OpenRouter plus bounded visible history and Supabase facts is sufficient after the governed bridge is deployed.

Current outcome: `LETTA_DEFERRED`.

## 17. Local Certification

Completed locally in the clean worktree:

- focused Hermes model-first tests: PASS, 8/8
- TypeScript: PASS
- production build: PASS
- full non-e2e suite: PASS, 98 files / 1502 tests
- secret scan of changed paths: PASS for new credentials; existing redacted report mentions remain unrelated

## 18. Live Certification

Live Ray-only certification was not run from this environment because the clean worktree does not contain local Supabase/OpenRouter credentials and the updated Edge Function has not been deployed from this branch.

Required next gate:

1. deploy the updated `hermes-chat` Edge Function,
2. deploy Netlify with `VITE_HERMES_MODEL_FIRST_MODE=RAY_ONLY_PILOT`,
3. run Ray-only live UI acceptance,
4. verify page/console errors are zero,
5. verify rollback with `VITE_HERMES_MODEL_FIRST_MODE=OFF`.

## Certification State

`LOCAL_TOOL_BRIDGE_PASS_NOT_LIVE_DEPLOYED`
