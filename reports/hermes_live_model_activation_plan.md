# Hermes Live Model Activation Plan

**Generated:** 2026-07-01  
**Current Status:** Infrastructure ready, secrets not yet set

## Current Gateway Verification

- ✅ `supabase/functions/hermes-chat/index.ts` exists (227 lines)
- ✅ Providers: openrouter, gemini, ollama
- ✅ Required env names: HERMES_CHAT_PROVIDER, HERMES_MODEL, OPENROUTER_API_KEY/GEMINI_API_KEY/OLLAMA_URL
- ✅ Frontend does NOT call hermes-chat directly — goes through `hermesProviders.ts`
- ✅ No frontend API keys exposed
- ✅ Model status honestly reported as `not_configured`
- ✅ Cost guards added: input limits, output caps, provider/model allowlist, action rejection

## Required Environment Variables (Names Only)

| Variable | Location | Status |
|----------|----------|--------|
| `HERMES_CHAT_PROVIDER` | Supabase Edge Function secrets | Needs setting |
| `HERMES_MODEL` | Supabase Edge Function secrets | **MISSING** |
| `HERMES_FALLBACK_MODEL` | Supabase Edge Function secrets | **MISSING** |
| `OPENROUTER_API_KEY` | Supabase Edge Function secrets | Present |
| `GEMINI_API_KEY` | Supabase Edge Function secrets | Unknown |
| `OLLAMA_URL` | Supabase Edge Function secrets | Unknown |
| `VITE_HERMES_CHAT_ENABLED` | Frontend env | Present |

## Selected Model Path

- **Primary:** OpenRouter (`openrouter/auto` or `openai/gpt-4o-mini`)
- **Fallback:** Ollama (`qwen2.5:0.5b` on Mac Mini)

## Safety/Cost Controls (Already Implemented)

1. **Routing policy** — decides if message needs model (most don't)
2. **Context packing** — builds small relevant packets within token budgets
3. **Usage ledger** — logs every model call attempt
4. **Edge Function guards** — input limits, output caps, provider/model allowlist
5. **Firewall** — scans message + context before any external call
6. **Background job limits** — no_model default, cheap_model max
7. **Action rejection** — blocks send/publish/deploy/trade/charge/dispute
8. **Source labels** — every response tagged with data source

## Activation Command

```bash
supabase secrets set HERMES_MODEL=openrouter/auto HERMES_FALLBACK_MODEL=ollama/qwen2.5:0.5b HERMES_CHAT_PROVIDER=openrouter
```

## Deploy Command

```bash
supabase functions deploy hermes-chat
```

## Files Created/Modified

- `src/lib/hermesModelRoutingPolicy.ts` — routing decision engine
- `src/lib/hermesContextPacker.ts` — context budget/packing
- `src/lib/hermesModelUsageLedger.ts` — usage logging
- `src/lib/hermesProviders.ts` — updated with routed model chat
- `src/components/HermesChatPanel.jsx` — updated with model status answers
- `supabase/functions/hermes-chat/index.ts` — updated with cost guards
- `reports/hermes_model_cost_policy.json` — background job safety policy
- `reports/hermes_live_model_activation_next_steps.md` — activation guide
