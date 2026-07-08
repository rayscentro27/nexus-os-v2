# Live Documents Display Hotfix — Phase R2

## Root Cause

`/client/documents` showed fallback/demo sections instead of live `client_documents` rows because `src/services/clientDashboardLiveData.ts` used a hardcoded `TEST_CLIENT_ID = 'client_test_julius_erving'` for all live queries.

When a real tester (e.g., `gc_a2b1e51d6ca844459d18c1873d8baf34`) signed in:
1. `DocumentUploadZone.tsx` correctly wrote metadata rows with the resolved Nexus `client_id`
2. But `ClientDocumentsPage` loaded documents for `client_test_julius_erving` (hardcoded demo client)
3. Result: zero live rows found → fallback demo sections displayed

Additional issue: `RequestReviewPage` also used raw auth UID instead of resolved Nexus `client_id`.

## Files Changed

| File | Change |
|------|--------|
| `src/services/clientDashboardLiveData.ts` | **BREAKING CHANGE**: `loadClientDashboardLiveData()` now accepts optional `forcedContext: ResolvedClientContext`. When not provided, resolves signed-in user's context via `resolveClientContextForCurrentUser()`. Falls back to `client_test_julius_erving` only when no context can be resolved. |
| `src/pages/client/ClientPortalPages.jsx` | `ClientDocumentsPage` now passes `undefined` to `loadClientDashboardLiveData()` which triggers context resolution. Added `liveDocsError` state, live status label, and `resolvedClientId` tracking. |
| `src/components/client/ClientPortalShell.jsx` | Added `PortalLiveStatusContext`. Shell badge now shows dynamic live status: "Live data connected", "Live data pending", or "Demo/fallback data". |
| `src/data/clientDataMode.js` | Updated `internalLabel` to clearer text. `shouldShowInternalDataBadge` now shows badge in both live and fallback modes (previously hidden in live mode). |

## Was Hardcoded Client ID Removed?

**Partially.** `TEST_CLIENT_ID` remains in `clientDashboardLiveData.ts` as a last-resort fallback when no signed-in client context can be resolved. The primary path now resolves the actual signed-in user's `tenant_id` + `client_id` from `tenant_memberships` (fallback to `client_profiles`).

## Live Row Display Status

**FIXED.**

For the canonical live client from manual test (`tenant_id = goclear`, `client_id = gc_a2b1e51d6ca844459d18c1873d8baf34`):

- `dummy_proof_of_address_test.pdf` with `category = proof_of_address`, `status = pending_review`, `goclear_review_status = pending_review`
- Should now appear under **"Under GoClear review"** section
- Should NOT appear under "Missing / Required documents" as a duplicate

## Fallback Still Works?

**Yes.**

Fallback demo data appears when:
- `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT` is not `true`
- No authenticated session exists
- `resolveClientContextForCurrentUser()` returns null
- Live query returns zero rows and no resolved client ID

In those cases, `showLiveSections` is false and the page uses `clientPortalData.js` demo sections.

## Manual Verification Steps

```bash
# 1. Build passes
npm run build

# 2. Portal button smoke check passes
python3 scripts/checks/check_client_portal_actions.py

# 3. Manual test:
#    - Sign in as tester with live client context (gc_a2b1...)
#    - Open /client/documents
#    - Expected: "Live data connected" badge in sidebar footer
#    - Expected: dummy_proof_of_address_test.pdf appears under "Under GoClear review"
#    - Expected: No duplicate "Current address proof" in Missing section
#    - Expected: Required documents shows categories derived from live rows

# 4. Fallback test:
#    - Sign out or disable VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT
#    - Open /client/documents
#    - Expected: "Demo/fallback data" badge
#    - Expected: Demo sections render (Required documents, Uploaded, Missing, Under GoClear review)
```

## Remaining Caveats

1. `loadClientDashboardLiveData()` still uses `client_test_julius_erving` as a fallback when no client context resolves. This is intentional for standalone demo/testing scenarios.
2. The `resolvedClientId` from live data is not yet propagated to `HermesGuidancePanel` or other pages that might need it.
3. Admin drawer in `ClientsPanel.jsx` still uses its own client selection context, separate from the portal's resolved client context.
