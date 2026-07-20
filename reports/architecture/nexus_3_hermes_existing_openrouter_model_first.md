# Nexus 3 Hermes Existing OpenRouter Model-First Routing Repair

Generated: 2026-07-20

## 1. Old Production Path

Current production Workroom path before this repair:

`HermesChatPanel.jsx -> runHermesConversation() -> deterministic classifier/router/tools`

For `what is a car`, the classifier selected `FACTUAL_QUESTION / factual_question`, and no language model received the message.

## 2. Root Cause

The defect is routing order. Hermes was not failing after model inference; ordinary language was intercepted before the existing `hermes-chat` OpenRouter path could run.

## 3. Current Provider Configuration

Direct diagnostic call to the deployed Supabase Edge Function reported:

- provider: `openrouter`
- primary model: `openai/gpt-4o-mini`
- fallback model: `google/gemini-2.0-flash-001`
- provider configured: true
- model configured: true
- fallback configured: true
- API key configured: true

No secret values were printed.

## 4. Direct OpenRouter Smoke

Before UI routing changes, the deployed `hermes-chat` Edge Function was called with:

`What is a gondola?`

Result:

- provider: `openrouter`
- model invoked: true
- model: `openai/gpt-4o-mini`
- tool required: false
- response returned: true
- function latency: `1624ms`
- response source: `hermes-chat`

The response correctly answered the ordinary general-language question.

## 5. Routing Replacement

Added `src/lib/hermesModelFirst/hermesModelFirstController.ts`.

In `RAY_ONLY_PILOT` or `ACTIVE` mode, normal admin/Ray Workroom messages now call `hermesChat()` directly. This bypasses the older `routeModel()` no-model gate and sends ordinary language to the existing Supabase Edge Function.

`OFF` mode still uses the legacy route.

## 6. Identity / Context

The existing stable context in `supabase/functions/hermes-chat/index.ts` is reused. It now has a narrow `MODEL-FIRST CONVERSATION` addition instructing Hermes to answer ordinary general-language and conversational questions without requiring Nexus evidence, use visible conversation for references, and repair misunderstandings naturally.

## 7. Conversation History

`HermesChatPanel.jsx` now sends the latest visible Workroom messages as bounded `recentHistory` to the model-first controller. The existing Edge Function history sanitizer limits turns and removes sensitive content before external model calls.

## 8. Capability OS Gateway

This commit repairs language routing first. Full model-proposed tool execution is not activated yet. Legacy deterministic tools remain available in `OFF` mode and as future policy support, but they do not intercept normal pilot conversation before the model.

## 9. Supabase Boundary

The browser calls Supabase `hermes-chat`; OpenRouter keys stay server-side in Supabase function secrets. The browser does not receive provider keys, tenant overrides, tool approval, or execution permission.

## 10. Action Separation

The Edge Function pre-model blocker remains for external/high-risk execution verbs such as send, publish, deploy, charge, trade, SQL deletion, and live activation. Draft/planning language is no longer blocked before the model.

## 11. Provider Failure

If the model gateway is unavailable in pilot mode, Hermes returns a specific degraded model-first response:

`My conversational model is temporarily unavailable...`

It does not silently return the old generic authorized-context fallback for tool-free questions.

## 12. Cost

The existing `hermes-chat` path records provider metadata and token estimates. Current live smoke reported estimated output tokens from the Edge Function; full cost ledger integration remains a follow-up.

## 13. Security

The existing private-data firewall remains in the Edge Function and frontend provider wrapper. The changed files do not contain provider keys or credentials. Alpha is unchanged and still isolated from Supabase/client PII.

## 14. Letta Decision

Letta is deferred. This phase intentionally reuses the existing OpenRouter path before installing or activating Letta.

Current decision: `MORE_EVIDENCE_REQUIRED`.

Letta should be reconsidered only if measured problems remain after OpenRouter model-first routing is live, especially cross-session memory, long-term identity memory, durable summaries, and reference retention beyond bounded history.

## Certification State

Local code path and direct provider smoke passed. Live Ray-only UI deployment was not performed in this commit.
