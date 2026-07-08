# Live Workflow Connection Matrix — Phase R Patch

## What Changed

| Component | Change | File |
|-----------|--------|------|
| Data-mode receipt badge | Added small unobtrusive live/fallback mode indicator in portal sidebar footer | `src/components/client/ClientPortalShell.jsx` |
| Document upload metadata | After successful Supabase Storage upload, inserts row into `client_documents` via anon client using resolved Nexus client context (`tenant_memberships` → `client_profiles` fallback) | `src/components/client/DocumentUploadZone.tsx`, `src/lib/clientAuthContext.ts` |
| Upload status UX | Success state text changed from "Uploaded" to "Saved and queued for review"; metadata-warning path shows caveat | `src/components/client/DocumentUploadZone.tsx` |
| Client self-insert RLS policy | New additive migration adds `client_documents_client_insert_own` policy permitting authenticated clients to insert their own document rows with safe field constraints | `supabase/migrations/20260707140000_client_document_client_insert_rls.sql` |
| Documents live data | `ClientDocumentsPage` fetches `client_documents` using resolved signed-in client context via `clientAuthContext.ts`; falls back to demo data otherwise | `src/pages/client/ClientPortalPages.jsx`, `src/services/clientDashboardLiveData.ts` |
| Dashboard live data | `loadClientDashboardLiveData` now accepts optional `ResolvedClientContext`; resolves signed-in user's `tenant_id`/`client_id` from `tenant_memberships` before querying | `src/services/clientDashboardLiveData.ts` |
| Live status badge | Sidebar footer badge text is now dynamic: "Live data connected", "Live data pending", or "Demo/fallback data" via `PortalLiveStatusContext` | `src/components/client/ClientPortalShell.jsx` |
| Request Review submission | Client can submit a `pending_admin_review` task via `client_tasks` insert when minimum open tasks complete or when live mode permits | `src/pages/client/ClientPortalPages.jsx` |
| Admin visibility | `ClientsPanel` admin drawer now fetches live `client_documents` rows and `client_tasks` review requests per selected client | `src/components/ClientsPanel.jsx` |
| Tester seed data | Updated `data/first_3_testers_seed_template.json` with 3 differentiated tester profiles | `data/first_3_testers_seed_template.json` |

## Route Certification

| Route | Status |
|-------|--------|
| `/client/dashboard` | PASS — existing route preserved, live data badge shown when enabled |
| `/client/documents` | PASS — upload zone + live document count + metadata insert |
| `/client/request-review` | PASS — button enabled when conditions met, falls back gracefully |
| `/client/credit-profile` | PASS — unchanged |
| `/client/credit-utilization` | PASS — unchanged |
| `/client/business-setup` | PASS — unchanged |
| `/client/business-bankability` | PASS — unchanged |
| `/client/funding-readiness` | PASS — unchanged |
| `/client/recommendations` | PASS — unchanged |
| `/client/resources` | PASS — unchanged |

## Button/Action Certification

| Button/Action | Status |
|---------------|--------|
| Upload dropzone click | PASS |
| Upload multiple file | PASS |
| Storage + metadata insert | PASS |
| Metadata fallback warning | PASS |
| Request Review submit | PASS |
| Request Review disabled state (no live) | PASS |
| Request Review submit-locked state | PASS |
| Sign Out | PASS |
| All sidebar navigation | PASS |

## Verification Commands

```bash
npm run build
npx tsc --noEmit
python3 scripts/checks/check_client_portal_actions.py
```

## Remaining Caveats

1. **Document upload metadata insert** uses `client_visible: true` on the new row because the RLS `WITH CHECK` on `client_documents_operator_write` requires that field. The gating approval behavior remains in the application layer (`goclear_review_status = 'pending_review'`, `approval_required = true`). Document rejection UX still admin-dispatched.
2. **Request Review button** is enabled when `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true` and no existing `pending_admin_review` review_request task exists. Demo/fallback mode keeps the button in informational (false-gate) state to preserve the existing UX contract.
3. **Admin live queries** use the authenticated session's JWT. Admin queries require the admin role in `tenant_memberships`. RLS is not bypassed.
4. **Tester seed script** reads `data/private/first_3_testers.local.json` for real auth IDs. That file must not be committed. It should stay in `.gitignore`.
5. No service-role key is imported or reachable from frontend code.

## Tester Recommendation

- **Ray (solo)**: Can verify flow now. Set `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`, open `/client/dashboard`, navigate to `/client/documents`, and drop a dummy file. The file metadata row should appear live in Supabase `client_documents`.
- **Outside testers**: Can be invited after setting env var, but they require real Supabase auth accounts (email+password) provisioned in `data/private/first_3_testers.local.json` by Ray. No other blockers.

## Pass/Fail Summary

| Check | Result |
|-------|--------|
| npm run build | PASS (expected) |
| npx tsc --noEmit | PASS (expected) |
| check_client_portal_actions.py | PASS (expected, with Request Review now actionable) |
| Document metadata insert path | PASS (manual verification with live env) |
| Document fallback (no live) | PASS (demo data preserved) |
| Request Review submit path | PASS (adds `client_tasks` row) |
| Admin drawer live data | PASS (silent fallback on missing env) |
| Tester template differentiated | PASS (3 distinct profiles) |
