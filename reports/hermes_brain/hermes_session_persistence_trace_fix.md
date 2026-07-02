# Hermes Session Persistence, Trace & Provenance Fix

## Summary

Fixed the core multi-turn conversation lifecycle: sessions now persist across turns, continuation phrases route correctly, lastSuccessfulTrace captures route provenance, and client provenance no longer claims "not verified" when a read succeeds with 0 rows.

## Root Causes Fixed

### 1. Session Not Persisted Across Turns
- `startReviewSession` wrote to `sessionStore` (module-level Map) but the router never called `isSessionActive()`
- Continuation phrases ("start there", "walk through the list", "next", "can we review them") fell through to `fallback_clarification`

**Fix:**
- Added `isSessionActive()` check in `hermesPriorityRouter.ts` **before** intent frame and keyword chains
- Added `active_session_continue` route handler in `hermesBrainPipeline.ts` for report inventory and business opportunity continuation
- Added broad continuation pattern detection in `hermesIntentClassifier.ts`

### 2. No lastSuccessfulTrace
- `hermesRoutingTrace.ts` stored traces in a Map but pipeline read via `getLastRoutingTrace()` which may not use the same key
- No concept of "last successful non-fallback trace" existed

**Fix:**
- Added `lastSuccessfulTraceByScope` Map in `hermesAdvisorSession.ts`
- Added `setLastSuccessfulTrace()` and `getLastSuccessfulTrace()` functions
- Pipeline writes `lastSuccessfulTrace` on every successful non-fallback, non-trace, non-safety answer
- Fallback answers do NOT overwrite `lastSuccessfulTrace`
- Trace handler uses `lastSuccessfulTrace` when no routing trace exists

### 3. Client Provenance Contradiction
- When `client_profiles` returned 0 rows, `renderRecordContract` showed "client_profiles: not verified" in the blocker
- The read succeeded (status: success, rowCount: 0) but the wording implied failure

**Fix:**
- Changed fallback blocker text from "not verified" to "access denied" / "read failed"
- Added 0-row success detection: "none — the Supabase client_profiles read succeeded but returned 0 client rows"
- Added clearer next action for 0-row client reads

### 4. Report Inventory Session Not Created
- When Hermes listed reports, no review session was created, so continuation phrases had nothing to continue

**Fix:**
- Added `startReviewSession`, `updateSessionSource`, `updateSessionList`, `setSessionFocus` calls in the `process_settings_reports_status` route for report inventory
- Added `report_inventory_review` to `ReviewMode` type

### 5. Trace Handler Missing Session Context
- Trace answers never included information about active sessions

**Fix:**
- Trace handler now includes session state (mode, item count, focus) from `lastSuccessfulTrace`

## Files Modified

| File | Changes |
|------|---------|
| `src/lib/hermesAdvisorSession.ts` | Added `lastSuccessfulTraceByScope`, `setLastSuccessfulTrace`, `getLastSuccessfulTrace`, `isSessionActive`, `getSessionListForContinuation`, `getSessionFocusForContinuation`, `SuccessfulTraceEntry` interface, `report_inventory_review` ReviewMode |
| `src/lib/hermesIntentClassifier.ts` | Added `active_session` followupType detection with continuation patterns |
| `src/lib/hermesPriorityRouter.ts` | Added early `isSessionActive()` check before intent frame/keyword chains, `scopeKey` parameter |
| `src/lib/hermesBrainPipeline.ts` | Added `active_session_continue` route, `scopeKey` parameter to `executeRoute`, `lastSuccessfulTrace` writing on success, report inventory session creation, session-aware trace handler |
| `src/lib/hermesOperationalContracts.ts` | Fixed client provenance: 0-row success wording, blocker text, next action |

## New Tests (8 multi-turn persistence tests)

| Test | What it verifies |
|------|-----------------|
| session persists across turns | `getActiveSession()` returns session after creation |
| "start there" routes to active_session_continue | Continuation phrase triggers correct route |
| "walk through the list" routes to active_session_continue | Walkthrough phrase triggers correct route |
| "next" advances focus through list | Focus advances to next item in list |
| lastSuccessfulTrace persists after review | Trace is written after business opportunity review |
| report inventory creates review session | Report listing creates `report_inventory_review` session |
| trace question returns routing information | Trace questions return valid routing data |
| fallback does not overwrite lastSuccessfulTrace | Fallback answers preserve previous successful trace |

## Verification

- Build: `npm run build` passes (tsc --noEmit && vite build)
- Tests: 701/701 pass across 26 test files
- No regressions in existing route behavior, safety gates, or production polish
