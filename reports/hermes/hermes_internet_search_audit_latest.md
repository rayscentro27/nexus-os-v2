# Hermes Internet Search Audit Report

**Date:** 2026-07-06
**Status:** AUDIT COMPLETE — NEW LAYER ADDED

## Current Hermes Stack

| File | Purpose | Status |
|------|---------|--------|
| `scripts/hermes/classify_hermes_intent.py` | Intent classification | EXISTING |
| `scripts/hermes/handle_hermes_message.py` | Message routing | EXISTING |
| `scripts/hermes/search_business_context.py` | Internal context search | EXISTING |
| `scripts/hermes/generate_hermes_advisor_response.py` | Response generation | EXISTING |
| `scripts/hermes/hermes_web_search.py` | **NEW** — Provider-abstracted web search | ADDED |
| `scripts/hermes/hermes_research_advisor.py` | **NEW** — Research answer builder | ADDED |

## Telegram Bridge

| File | Purpose | Status |
|------|---------|--------|
| `scripts/telegram/nexus_telegram_bridge.py` | Mobile operator console | UPDATED — web search routing added |

## Netlify Functions

| File | Purpose | Provider |
|------|---------|----------|
| `netlify/functions/alpha-search.mjs` | Server-side search | SearXNG (needs `ALPHA_SEARXNG_URL`) |
| `netlify/functions/alpha-url-review.mjs` | URL extraction | Firecrawl (needs `FIRECRAWL_API_KEY`) |
| `netlify/functions/alpha-provider.mjs` | AI model routing | OpenRouter/Groq |

## Provider Env Vars Detected

| Env Var | Present in .env | Status |
|---------|----------------|--------|
| `BRAVE_SEARCH_API_KEY` | NO | Not configured |
| `TAVILY_API_KEY` | NO | Not configured |
| `SERPAPI_API_KEY` | NO | Not configured |
| `ALPHA_SEARXNG_URL` | NO | Not configured |
| `FIRECRAWL_API_KEY` | NO | Not configured |
| `OPENROUTER_API_KEY` | YES | Available for AI model calls |
| `VITE_HERMES_CHAT_ENABLED` | YES | Hermes chat enabled |

## Current Telegram Commands/Intents

| Intent | Web Search? | Status |
|--------|-------------|--------|
| GREETING | No | Working |
| CASUAL_AGENT_CHAT | No | Working |
| HERMES_ADVISORY | Now yes (when query needs it) | Updated |
| HERMES_WEB_SEARCH | **NEW** — Always triggers search | Added |
| HERMES_URL_REVIEW | **NEW** — URL-specific review | Added |
| ALPHA_RESEARCH_REQUEST | No (internal context) | Working |
| ALPHA_CONTEXT_FOLLOWUP | No | Working |
| NEXUS_STATUS_OR_REPORT | No | Working |
| APPROVAL_ACTION | No | Working |
| WORK_ORDER_REQUEST | No | Working |
| UNKNOWN_HELPFUL_FALLBACK | No | Working |

## Gaps and Risk Level

| Gap | Risk | Mitigation |
|-----|------|------------|
| No search provider key configured | Medium | Safe fallback explains missing keys, does not fake results |
| Web search only for Ray/private | Low | Policy enforced in code, not exposed to client-facing |
| External action without approval | High | Blocked by approval-gated model, work orders require Ray approval |
| API key exposure | Medium | Keys never logged, errors redacted, receipts store metadata only |
