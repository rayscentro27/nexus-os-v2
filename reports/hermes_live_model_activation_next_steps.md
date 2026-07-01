# Hermes Live Model Activation — Next Steps

**Generated:** 2026-07-01  
**Status:** Ready to activate (secrets not yet set)

## 1. Required Supabase Secrets

| Secret Name | Status | Notes |
|-------------|--------|-------|
| `HERMES_MODEL` | **MISSING** | Primary model identifier |
| `HERMES_FALLBACK_MODEL` | **MISSING** | Fallback model when primary unavailable |
| `OPENROUTER_API_KEY` | Present | From inventory — do not print value |
| `VITE_HERMES_CHAT_ENABLED` | Present | Frontend flag — already true |
| `HERMES_CHAT_PROVIDER` | Needs setting | Provider selection (openrouter/gemini/ollama) |

## 2. Activation Command

```bash
supabase secrets set \
  HERMES_MODEL=openrouter/auto \
  HERMES_FALLBACK_MODEL=ollama/qwen2.5:0.5b \
  HERMES_CHAT_PROVIDER=openrouter
```

> **Note:** If OpenRouter requires a specific model string (not `auto`), use:
> `HERMES_MODEL=openai/gpt-4o-mini` (cheapest OpenRouter option)

## 3. Deploy/Update Function

```bash
supabase functions deploy hermes-chat
```

## 4. Verification Questions

After activation, test these in Hermes chat:

1. "Are you using a live model right now?" → Should say yes, provider/model
2. "What is your favorite food?" → Should answer locally, no model call
3. "What model did you use?" → Should report provider/model or "no model"
4. "How are you controlling token cost?" → Should explain routing/budgets
5. "Explain the Nexus audit in plain language" → Should use model for complex reasoning
6. "Publish this post" → Should be blocked/gated, no model call

## 5. Rollback

```bash
# Disable model by unsetting HERMES_MODEL
supabase secrets unset HERMES_MODEL

# Or disable chat entirely
supabase secrets unset VITE_HERMES_CHAT_ENABLED

# Redeploy
supabase functions deploy hermes-chat
```

## 6. What's Already Built

- ✅ Model routing policy (`hermesModelRoutingPolicy.ts`)
- ✅ Context budgeting/packing (`hermesContextPacker.ts`)
- ✅ Usage ledger (`hermesModelUsageLedger.ts`)
- ✅ Routed model chat integration (`hermesProviders.ts`)
- ✅ Edge Function cost guards (input limits, output caps, provider/model allowlist)
- ✅ Background job safety policy
- ✅ Model status answers in Hermes chat
- ✅ Source labels on responses
- ✅ Firewall on server side

## 7. Cost Estimate

With `openrouter/auto` (cheapest available model):
- ~$0.001-0.005 per complex reasoning call
- Most answers: $0.00 (no model call)
- Estimated monthly: $1-5 depending on usage

With `openai/gpt-4o-mini` (explicit cheapest):
- ~$0.00015 per 1K input tokens
- ~$0.0006 per 1K output tokens
- Estimated monthly: <$1 for typical usage
