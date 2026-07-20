# Nexus 3 Hermes OpenRouter + Letta Architecture

Generated: 2026-07-20

## 1. Original Production Route

The current Workroom route is:

`HermesChatPanel.jsx -> runHermesConversation() -> deterministic classifier/router/tools`

For `what is a car`, the classifier reaches `FACTUAL_QUESTION / factual_question`. No language model receives the message.

## 2. Root Cause

Hermes is not failing after a model call. The normal production path prevents ordinary language from reaching a general language model.

## 3. Selected Architecture

The selected design is:

`OpenRouter -> capable language model`

`Letta -> persistent Hermes identity, recent conversation, and memory`

`Nexus Capability OS -> tool authorization, approvals, and action control`

`Supabase -> authorized Nexus facts, operational state, provenance, and audit data`

LangGraph remains deferred for future multi-step department workflows.

## 4. OpenRouter Provider

OpenRouter is implemented as the canonical model provider for the future pilot, but it is not active because `OPENROUTER_API_KEY` is missing. OpenRouter model metadata confirmed tool and structured-output support for the recommended primary and backup models.

## 5. Selected Models

Primary: `openai/gpt-5.6-luna`

Backup: `google/gemini-2.5-flash`

See `reports/approvals/hermes_openrouter_model_selection.md`.

## 6. Letta Runtime

The official package `@letta-ai/letta-client` is installed at version `1.12.1`.

Runtime is blocked because neither `LETTA_RUNTIME_MODE` nor a hosted/self-hosted runtime and agent ID are configured.

## 7. Hermes Identity

The intended Letta memory blocks are `persona`, `human`, `nexus_identity`, `authority`, `current_objectives`, and `conversation_preferences`. The branch does not create a persistent agent because no Letta runtime is configured.

## 8. Memory Ownership

Letta owns active conversation, persona, Ray relationship, conversational preferences, and summaries.

Supabase owns business facts, reports, operational status, provenance, audits, and cost records.

Browser localStorage remains UI-only and is not canonical Hermes memory.

## 9. Server Endpoint

`netlify/functions/hermes-conversation.mjs` was added as the canonical server endpoint foundation. While configuration is missing it returns a truthful degraded response and does not route to a simulated model.

## 10. Capability OS Gateway

No model tool execution is active in this blocked state. The intended gateway maps model tool requests to Nexus-owned tools, then validates actor, tenant, role, capability, data class, risk, budget, approval, and rate limits before any execution.

## 11. Supabase Role

Supabase remains the source for authorized Nexus facts and durable audit records. Letta and OpenRouter must not receive direct Supabase credentials or unrestricted queries.

## 12. Action Separation

The model may propose tools or drafts, but Nexus authorizes and executes. Approval and execution remain separate.

## 13. Failure Handling

If OpenRouter, Letta, budget, or structured output is unavailable, Hermes must say the model-first brain is degraded. It must not silently return to the old generic fallback.

## 14. Cost Controls

Defaults are daily `$0.50`, monthly `$10.00`, max output `600`, max model rounds `2`, max tool calls `2`.

## 15. Privacy

No client PII is sent in this branch. Frontend secrets remain prohibited. Alpha remains separate with no Supabase access.

## 16. Rollback

Rollback is `HERMES_MODEL_FIRST_MODE=OFF` or redeploying the previous certified commit. Letta state and Supabase audit history must not be deleted during rollback.

## Certification Decision

`BLOCKED_PENDING_OPENROUTER_KEY` and `BLOCKED_PENDING_LETTA_RUNTIME`.

No production pilot was activated.
