# Hermes Model Cost Policy

**Generated:** 2026-07-01  
**Version:** 1.0

## Core Principle

Hermes model usage must be **routed, capped, logged, and context-limited**. The model is ONE tool in Hermes orchestration — not the only brain.

## Routing Policy

| Route | Description | Max Input | Max Output | Max Turns |
|-------|-------------|-----------|------------|-----------|
| `no_model` | Local/router answer only (default for most answers) | 0 | 0 | 0 |
| `cheap_model` | Cheap/fallback model for rewrites and formatting | 1,500 | 500 | 2 |
| `primary_model` | OpenRouter/main model for strategic reasoning | 6,000 | 1,200 | 4 |
| `blocked_or_gated` | Never direct model execution | 0 | 0 | 0 |

## Background Job Rules

- Default route: `no_model`
- Allowed route: `cheap_model` (requires Ray approval for `primary_model`)
- Hard max turns: 1
- Hard max input: 1,000 tokens
- Hard max output: 300 tokens
- No recursive model-triggered jobs
- No model calls inside tight loops
- No automatic web+model chains
- Log every model call
- Stop after repeated failure

## Context Budgets

- Default max input estimate: 3,000 tokens
- Cheap model max input: 1,500 tokens
- Primary model max input: 6,000 tokens
- Background job max input: 1,000 tokens
- Default max output: 700 tokens
- Primary model max output: 1,200 tokens

## Edge Function Cost Guards

- Max input chars: 24,000 (~6,000 tokens)
- Max output tokens: 1,200
- Provider allowlist: openrouter, gemini, ollama
- Model allowlist enforced
- Firewall scans all messages before external call
- Rejects execution requests (send, email, publish, deploy, charge, trade, dispute)
- Returns structured metadata with every response

## Usage Logging

- Enabled: yes
- Storage: localStorage (`nexus-hermes-model-usage-v1`)
- Max entries: 200
- Logged: route, provider, model, tokens, context sources, duration, error
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
10. No model calls for dangerous execution
11. Firewall scans message and context before any external model call
