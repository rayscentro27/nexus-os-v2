# Live Connection Implementation Plan — Nexus OS v2

**Date:** 2026-06-30
**Repo commit:** 5a0ea35 (pre-wiring)
**Live app:** https://nexusv20.netlify.app/

---

## Selected Live Supabase Tables

| Use Case | Table | PK | tenant_id | Status Field | created_at | RLS INSERT | RLS UPDATE | Frontend Read | Frontend Write | Backend Required |
|----------|-------|----|-----------|-------------|------------|-----------|-----------|---------------|----------------|-----------------|
| Ray Review items | `task_requests` | uuid | No (workspace_id) | `status` (requested/assigned/in_progress/done/rejected) | Yes | YES (admin) | YES (admin) | YES (anon+auth) | YES (auth) | No |
| Approval decisions | `approvals` | uuid | No | `status` (pending/approved/rejected/revise/published) | Yes | YES (admin) | YES (admin) | YES (auth) | YES (auth) | No |
| Activity events | `nexus_events` | uuid | No | `status` (success/failed/pending/info) | Yes | YES (admin) | YES (admin) | YES (auth) | YES (auth) | No |
| System health | `system_health` | uuid | No | `status` (ok/partial/failed/rebuild_needed/unknown) | Yes | No (service role) | No (service role) | YES (auth) | No | No (read-only) |
| Admin users | `admin_users` | uuid→auth.users | No | `active` (bool) | Yes | No | No | Self-read only | No | No |
| Research sources | `research_sources` | uuid | No (research_run_id) | — | Yes | No (service role) | No (service role) | YES (auth) | No | No (read-only) |
| Research runs | `research_runs` | uuid | No (workspace_id) | `status` (queued/done) | Yes | YES (admin) | YES (admin) | YES (auth) | YES (auth) | No |
| Business opportunities | `business_opportunities` | uuid | Yes (text) | `status` | Yes | YES (admin+tenant) | YES (admin+tenant) | YES (auth) | YES (auth) | No |
| Monetization offers | `monetization_opportunities` | uuid | No (workspace_id) | `status`/`decision` | Yes | YES (admin) | YES (admin) | YES (auth) | YES (auth) | No |
| Client profiles | `client_profiles` | uuid | Yes (text) | — | Yes | YES (admin+tenant) | YES (admin+tenant) | YES (auth) | YES (auth) | No |
| Agent jobs | `agent_jobs` | uuid | No | `status` | Yes | YES (admin) | YES (admin) | YES (auth) | YES (auth) | No |
| Ops incidents | `ops_incidents` | uuid | No | — | Yes | YES (admin) | YES (admin) | YES (auth) | YES (auth) | No |

**Key finding:** All 12 target tables have authenticated SELECT policies via `nexus_is_active_admin()`. The frontend anon client with an authenticated admin session CAN read all of them. Write policies exist for 9 of 12 tables (system_health, research_sources, admin_users are service-role-only for writes).

---

## Implementation Changes

### 1. `src/lib/liveDataLoader.ts` (NEW)
Shared utility for loading data from Supabase with static fallback. Provides:
- `loadLive<T>(table, staticData, opts)` — queries Supabase, falls back to static
- `countLive(table)` — counts rows
- `persistDecision(table, id, updates)` — writes decisions
- `insertRow(table, row)` — inserts new rows
- `isLiveConnected()` — checks if Supabase + auth session exist

### 2. `src/components/RayReviewCenter.jsx` (REWRITTEN)
- Loads from `task_requests` where `task_type = 'ray_review_item'` first
- Falls back to static `rayReviewData.js` if Supabase unavailable or empty
- Shows source label: "Live Supabase" or "Static snapshot"
- On approve/hold/reject: persists to `task_requests` via `supabase.from().update()`
- Creates `nexus_events` entry via `createEvent()` from `ledger.ts`
- localStorage receipts remain as secondary proof

### 3. `src/components/RayReviewCard.jsx` (UPDATED)
- Shows `persisting` state while Supabase write is in progress
- Shows data source tag: "Live" or "Static"
- Receipt shows Supabase table + row ID when persisted live

### 4. `src/lib/hermesSupabaseContextAdapter.ts` (REWRITTEN)
- `querySupabaseContextAsync(table)` — async live Supabase query
- `isSupabaseAvailableAsync()` — async session check
- `getLiveContextSummary(type)` — builds live context for any query type
- All functions return honest results with source labels

### 5. `src/lib/hermesLiveContext.ts` (NEW)
- `buildLiveSupabaseContext(message)` — determines which tables to query based on message, returns live data
- `buildWebSearchResponse(query)` — calls `hermes-search` edge function if configured
- Both return `LiveHermesResponse` with source type, liveData flag, timestamps

### 6. `src/components/HermesChatPanel.jsx` (UPDATED)
- `send()` is now async
- Detects Supabase/web queries in user message
- Calls `buildLiveSupabaseContext()` or `buildWebSearchResponse()` for enrichment
- Shows "Querying..." loading state
- Quick prompts updated to test live queries

### 7. `src/components/HermesInlineDrawer.jsx` (UPDATED)
- Same live context enrichment as HermesChatPanel
- Async send with loading state

### 8. `src/lib/hermesResponseRouter.ts` (NO CHANGE)
- Sync router remains unchanged for backward compatibility
- Live enrichment happens at the chat panel level

---

## RLS Safety Verification

All queries use the existing `supabaseClient.ts` which:
- Uses `VITE_SUPABASE_ANON_KEY` only
- No service role key in frontend
- Auth session required (checked before every query)
- RLS policies gate all access via `nexus_is_active_admin()`
- No RLS weakening
- No tenant isolation changes

---

## Test Coverage

| Test Category | File | Tests |
|--------------|------|-------|
| Supabase connection truth | `tests/supabase_connection_truth.test.ts` | 25 (updated) |
| Ray Review persistence | `tests/ray_review_persistence.test.ts` | 12 (new) |
| Hermes live context | `tests/hermes_live_context.test.ts` | 10 (new) |
| Existing Hermes tests | `tests/hermes_intent_router.test.ts` | 42 (existing) |
| Existing Hermes context | `tests/hermes_context_layer.test.js` | 25 (existing) |
| **Total** | | **114** |
