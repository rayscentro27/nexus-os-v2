# Hermes Chat Live Model Trace

**Generated:** 2026-07-01

## Call Path

| Step | Component | File | Action |
|------|-----------|------|--------|
| 1 | HermesChatPanel.jsx | `send()` :27 | User types message |
| 2 | hermesWorkroomData.js | `buildHermesResponse()` | Get synchronous local response |
| 3 | HermesChatPanel.jsx | model status check :46 | Check if model status question (answered locally) |
| 4 | hermesOrchestrator.ts | `orchestrateHermes()` :5 | Route intent |
| 5 | hermesProviders.ts | `hermesModelChat()` :126 | Main routed model chat entry |
| 6 | hermesModelRoutingPolicy.ts | `routeModel()` :140 | Decide route |
| 7 | hermesContextPacker.ts | `packContext()` :97 | Build context packet |
| 8 | hermesProviders.ts | `hermesChat()` :107 | Call Edge Function |
| 9 | hermes-chat/index.ts | `Deno.serve` :155 | Edge Function handler |
| 10 | hermes-chat/index.ts | OpenRouter call :208 | Fetch openrouter.ai |
| 11 | OpenRouter API | External | Returns completion |
| 12 | hermes-chat/index.ts | Response :230 | Format response with metadata |
| 13 | hermesProviders.ts | `hermesChat()` :112 | Parse response |
| 14 | hermesProviders.ts | `hermesModelChat()` :251 | Log usage, return result |
| 15 | hermesModelUsageLedger.ts | `logModelAttempt()` :60 | Log to localStorage |
| 16 | HermesChatPanel.jsx | display :117 | Show response to user |

## Files Involved

- `src/components/HermesChatPanel.jsx` — UI, send flow, model status answers
- `src/lib/hermesProviders.ts` — Provider abstraction, routed model chat
- `src/lib/hermesModelRoutingPolicy.ts` — Route decision engine
- `src/lib/hermesContextPacker.ts` — Context budget/packing
- `src/lib/hermesModelUsageLedger.ts` — Usage logging
- `src/lib/hermesOrchestrator.ts` — Intent orchestration
- `supabase/functions/hermes-chat/index.ts` — Edge Function (server-side)
- `supabase/functions/_shared/firewall.ts` — Firewall

## Root Cause of Previous Failure

The model string `openrouter/auto` is NOT a valid OpenRouter model ID. OpenRouter expects IDs like `openai/gpt-4o-mini`. The fallback `ollama/qwen2.5:0.5b` is an Ollama model, not usable through OpenRouter.

Additionally, the Edge Function had duplicate `const` declarations (`MAX_HISTORY_TURNS`, `MAX_HISTORY_CHARS`) causing a boot error.

## Fixes Applied

1. Changed `HERMES_MODEL` from `openrouter/auto` to `openai/gpt-4o-mini`
2. Changed `HERMES_FALLBACK_MODEL` from `ollama/qwen2.5:0.5b` to `google/gemini-2.0-flash-001`
3. Removed duplicate const declarations in Edge Function
4. Added `__diagnostic__` endpoint for safe env status check
5. Added ollama model filtering for OpenRouter provider
6. Added safe error reporting with errorCode in metadata
7. Fixed frontend to show actual model metadata instead of env var names
8. Fixed badge to show "Live Supabase + Model Ready"
