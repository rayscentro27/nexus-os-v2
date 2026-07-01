# Hermes Model Cost Policy

**Version:** 2.0  
**Generated:** 2026-07-01

## Core Principle

Hermes model usage must be **routed, capped, logged, context-limited, and cost-estimated**. The model is ONE tool in Hermes orchestration — not the only brain.

## Known Model Pricing (Estimated)

| Provider | Model | Input $/1M tokens | Output $/1M tokens | Source |
|----------|-------|-------------------|---------------------|--------|
| openrouter | openai/gpt-4o-mini | $0.15 | $0.60 | estimated |
| openrouter | openai/gpt-4o | $2.50 | $10.00 | estimated |
| openrouter | anthropic/claude-3.5-sonnet | $3.00 | $15.00 | estimated |
| openrouter | google/gemini-2.0-flash-001 | $0.10 | $0.40 | estimated |
| gemini | gemini-1.5-flash | $0.075 | $0.30 | estimated |
| ollama | qwen2.5:0.5b | $0 | $0 | local |
| ollama | gemma3:1b | $0 | $0 | local |

**Source of truth:** Provider billing. All estimates are approximate.

## Unknown Pricing Behavior

If pricing is unknown, Hermes reports token count but not dollar amount. Display: "pricing not configured".

## Routing Policy

| Route | When to use | Typical cost |
|-------|-------------|-------------|
| `no_model` | Status, casual, Supabase counts, scheduling, memory, source labels | $0.00 |
| `cheap_model` | Short rewrites, brief explanations, formatting | <$0.001 |
| `primary_model` | Strategy, deep analysis, complex synthesis, business recommendations | ~$0.001 |
| `blocked_or_gated` | Execution requests (send, publish, deploy, charge, trade) | $0.00 |

## Cost Reduction Strategies

1. Use **no_model** for status questions (how many rows, is it running, what is the source)
2. Use **cheap_model** for short rewrites (rewrite this, simplify, briefly explain)
3. Reserve **primary_model** for strategy and deep reasoning only
4. Keep context packets small — Hermes packs only relevant excerpts
5. Avoid sending full reports to the model
6. Cap output length (1200 for primary, 500 for cheap)
7. Background jobs default to **no_model**
8. Avoid recursive model loops — each question gets one model call max
9. Ask Hermes to summarize one report instead of the full audit

## Background Job Cost Limits

- Default route: `no_model` ($0)
- Allowed route: `cheap_model` (<$0.001)
- Requires Ray approval for: `primary_model`
- Hard max turns: 1
- Hard max input: 1,000 tokens
- Hard max output: 300 tokens

## Usage Logging

- Enabled: yes
- Storage: localStorage (`nexus-hermes-model-usage-v1`)
- Max entries: 200
- Logged: route, provider, model, tokens, cost estimate, cost confidence, was_necessary, cheaper_alternative, context sources, duration, error
- Never logged: secrets, raw prompts, PII, full .env, private keys

## Safety Rules

1. No frontend API keys — all provider keys in Supabase Edge Function secrets only
2. No service role in frontend
3. No RLS weakening
4. No destructive SQL
5. No external sends/trades/charges/disputes/publishing
6. No arbitrary shell from frontend
7. No uncontrolled loops
8. No heavy benchmarks
9. No fake model/web/Supabase claims
10. **No fake exact billing claims** — cost is always estimated
11. No model calls for dangerous execution
12. Firewall scans message and context before any external model call
