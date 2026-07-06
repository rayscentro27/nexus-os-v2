# Hermes Internet Search Setup

## Purpose

Hermes can now search the internet for current information when Ray asks research questions in Telegram. This document explains how to configure a search provider.

## Provider Options (Priority Order)

### 1. Brave Search (Recommended)

Best balance of quality, speed, and cost. Free tier available.

**Get a key:** https://brave.com/search/api/

**Add to .env:**
```
BRAVE_SEARCH_API_KEY=your_key_here
```

**Free tier:** 2,000 queries/month

### 2. Tavily

Good for research-focused queries. Built for AI agents.

**Get a key:** https://tavily.com

**Add to .env:**
```
TAVILY_API_KEY=your_key_here
```

**Free tier:** 1,000 queries/month

### 3. SerpAPI

Google search results. More expensive but comprehensive.

**Get a key:** https://serpapi.com

**Add to .env:**
```
SERPAPI_API_KEY=your_key_here
```

**Free tier:** 100 searches/month

### 4. SearXNG (Self-hosted)

Already used by Alpha. Requires a running SearXNG instance.

**Add to .env:**
```
ALPHA_SEARXNG_URL=https://your-searxng-instance.com
```

## How to Test

After adding a key, test in Telegram:

```
hermes search the web for business credit monitoring tools
hermes what are the best low-cost CRM platforms
hermes find current SBIR grant opportunities
```

Or test locally:

```bash
python3 scripts/hermes/hermes_web_search.py --query "best credit monitoring tools" --json
python3 scripts/hermes/hermes_research_advisor.py --query "low-cost affiliate programs" --json
```

## Telegram Examples

### Research Triggers
- `hermes search the web for ...`
- `hermes research ...`
- `hermes look up ...`
- `hermes find current ...`
- `hermes what are the best ...`
- `hermes check latest ...`
- `hermes are there grants for ...`
- `hermes find affiliate programs for ...`
- `search the web for ...`
- `what are the best tools for ...`

### URL Review
- `hermes review https://example.com for Nexus`
- Any message containing a URL to Hermes

### Non-Search (No Web)
- `hermes good morning`
- `hermes what is today's priority?`
- `hermes what should we do next?`
- `hermes recommend ...`
- `/report`
- `/status`

## Safety Rules

1. **Ray/private only** — Web search is NOT exposed to client-facing agents
2. **No secrets logged** — API keys never appear in receipts or logs
3. **Safe fallback** — If no provider is configured, Hermes says so clearly
4. **No fake results** — Hermes never pretends to have searched the web
5. **Approval-gated execution** — Search is read-only; actions require Ray approval
6. **Receipts saved** — Every search is logged with metadata (query, provider, result count, timestamp)

## Client-Facing Restriction

Search results are NEVER used directly in client-facing responses. If a result is useful for clients:
1. Ray reviews it
2. It's converted to approved knowledge base content
3. Stored in Supabase
4. Client agents reference the approved source

## Recommended Setup

For most users, add **Brave Search** as the single provider:

```
BRAVE_SEARCH_API_KEY=your_key_here
```

This enables Hermes to search the web for current information while keeping costs low (free tier: 2,000 queries/month).
