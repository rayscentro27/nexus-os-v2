# Hermes Live Model — Browser Verification Report

**Generated:** 2026-07-01

## Model Status

| Field | Value |
|-------|-------|
| Configured | Yes |
| Provider | OpenRouter (via Supabase Edge Function) |
| Model | openai/gpt-4o-mini |
| Fallback | google/gemini-2.0-flash-001 |
| Smoke Test | PASS (1056ms) |

## Cost Controls

| Control | Status |
|---------|--------|
| Routing Policy | no_model / cheap_model / primary_model / blocked_or_gated |
| Section Status Questions | always no_model |
| Cost/Meta Questions | always no_model |
| Context Packer | 6000 token max input |
| Output Cap | 1200 tokens |
| Usage Ledger | localStorage with cost estimates |
| Edge Function Guards | enabled |

## Supabase Secrets

- HERMES_MODEL: present
- HERMES_FALLBACK_MODEL: present
- HERMES_CHAT_PROVIDER: present
- OPENROUTER_API_KEY: present

## Verification

- Smoke test result: HERMES_MODEL_OK
- Response time: 1056ms
- Model called: yes
- Estimated cost: $0.0001

## Notes

Model is live and working via OpenRouter. Cost controls active. Section status and cost questions routed to no_model to avoid token spend. All costs estimated — provider billing is source of truth.
