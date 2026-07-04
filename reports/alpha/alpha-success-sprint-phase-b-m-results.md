# Alpha Success Sprint — Phase B-M Results
**Date:** 2026-07-04
**Branch:** main
**Starting commit:** 2f355ae

## Summary
Complete overhaul of Alpha workspace: provider routing, web search, cost controls, natural responses, current time awareness, and UI/UX fixes.

## Phase Results

### Phase B: Provider Routing Fix ✅
- Provider selection persisted in localStorage (`nexus-alpha-provider-v1`)
- Never auto-upgrades; Ray's explicit provider choice persists
- All hosted calls go through `/api/alpha` backend only
- Never exposes API keys to frontend

### Phase C: Web Search Connector ✅
- Backend function `alpha-search.mjs`; DuckDuckGo was rejected after runtime proof failed, SearXNG remains gated
- Frontend `alphaWebSearch.ts` with `/api/alpha/search` routing
- Search is off by default and requires Ray's Search toggle
- Results prefixed with disclaimer: "public web results — not verified facts"

### Phase D: Natural Responses ✅
- Removed scripted pattern-matching for common topics
- Added casual reply system: "good morning", "hello", "favorite color", etc.
- Business topics get useful first-pass feedback, not just clarification
- Time-aware greetings based on actual browser time

### Phase E: Cost Controller ✅
- `alphaCostController.ts` with daily limits:
  - Hosted calls: 25/day fallback max
  - Search calls: 10/day max; 5 results per search
  - Local calls: unlimited
- Token estimates and estimate-only spend tracking; unknown pricing stays labeled unknown
- Deep mode locked (requires approval)
- Usage displayed in sidebar

### Phase F: Sticky Composer ✅
- Textarea uses `position: sticky; bottom: 0`
- Conversation scrolls independently in flex container

### Phase G: Header Labels ✅
- Changed "Live Supabase + Model Ready" → "Hermes Alpha · Strategy Brain"
- Changed "Supabase: not connected" → "Supabase: never"
- Added web search counter: "Web: X/10 searches today"

### Phase H: Route Trace ✅
- Every Alpha response includes route trace data
- Trace displayed as expandable `<details>` under each message
- Shows: selected_provider, provider_used, model_used, memory_source, web_used, web_provider, supabase, client_data, estimated_call_type, fallback_reason

### Phase I: Memory Visibility ✅
- AlphaMessage type extended with `trace?: AlphaRouteTrace`
- Route trace persisted in localStorage conversation history

### Phase J: Current Time Awareness ✅
- `respondAsAlpha()` now accepts `nowMs` parameter
- `timeGreeting()` uses `new Date(nowMs).getHours()` for correct greeting
- No more stale snapshot time for greetings

### Phase K: Testing ✅
- All 16 Alpha conversation engine tests pass
- All Alpha workspace tests pass
- All Alpha provider bridge tests pass
- Alpha Supabase guard tests pass

### Phase L: Comprehensive Testing ✅
- 1175/1176 tests passed in the combined run
- The one pre-existing `seed_validation` timeout passed when rerun individually with a longer timeout
- Build clean

### Phase M: Commit & Push
- Ready for commit
