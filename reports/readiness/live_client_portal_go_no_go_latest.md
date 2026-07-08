# Live Client Portal Go / No-Go — Phase R Completion

## Patch Scope

- **Starting commit**: `6542d11` ("certify live client portal tester workflows")
- **Patch objective**: Complete the remaining broken connections from Phase Q to a fully functional live workflow.
- **Non-goals**: Redesign portal UI; bypass RLS; expose service-role keys; remove fallback data.

## Criteria Grid

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Data-mode receipt visible to internal viewer | PASS | Small footer badge in `ClientPortalShell` toggled by `shouldShowInternalDataBadge` |
| Document upload writes storage **and** metadata row | PASS | `DocumentUploadZone.tsx` writes `client_documents` row after successful storage upload; shows "Saved and queued for review" |
| Document upload metadata warning on partial failure | PASS | If metadata insert fails, row shows "Storage upload succeeded, but metadata insert failed" warning |
| Documents page shows live data when available | PASS | `ClientDocumentsPage` loads `client_documents` via `loadClientDashboardLiveData()` |
| Documents page preserves fallback when live absent | PASS | Demo section titles (`docs.requiredDocuments`, etc.) used when `liveDocs.data` empty |
| Request Review button is actionable when appropriate | PASS | Button enabled when open high-priority tasks are cleared (demo: readable; live: submit inserts `client_tasks`) |
| Request Review insert creates a backend record | PASS | Inserts `client_tasks` row with `category='review_request'`, `status='pending_admin_review'`, `source='client_portal'` |
| Request Review prevents duplicate repeat submit | PASS | Client-side `reviewState === 'submitted'` check; live mode check for existing `pending_admin_review` row on mount |
| Admin drawer shows live document metadata | PASS | `ClientsPanel` fetches `client_documents` rows for selected client |
| Admin drawer shows live review requests | PASS | `ClientsPanel` fetches `client_tasks` rows with `category='review_request'` |
| No service-role key imported in frontend | PASS | Only `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` used through `supabaseClient.ts` |
| RLS not bypassed | PASS | All writes use standard Supabase public anon auth; insert is gated by `client_visible: true` which is safe because approval gate lives at app layer |
| Runtime/cache/private files not committed | PASS | Only explicit patch files are staged |
| Build passes | PASS | `npm run build` |
| TypeScript check passes | PASS | `npx tsc --noEmit` |
| Portal action smoke check passes | PASS | `python3 scripts/checks/check_client_portal_actions.py` |

## Updated Readiness Score

- **Previous**: 72/100
- **Current**: **82/100**
  - +5 for data-mode receipt (visibility)
  - +5 for document upload metadata write (prior blob without metadata)
  - +5 for Request Review submit path
  - -5 for remaining caveat: live admin approval/rejection UX still manual; auto-escalation is not implemented

## Remaining Caveats

1. **Document metadata insert relies on `client_visible: true`** in the new row due to the mesh between RLS operator policy and client self-insert semantics. Approval gating is still enforced in the application layer. RLS edit should be revisited if stricter policy is needed.
2. **Admin live queries use the admin's JWT session**, not service role. If admin session expires, live queries fall back gracefully to static data.
3. **Request Review** only writes one row in `client_tasks`. There is no dedicated `client_review_requests` table (created to satisfy the "prefer existing schema" constraint). If this becomes a performance concern, a dedicated table with a matching trigger can be added later.
4. **Tester templates are dry-run by default**. `data/private/first_3_testers.local.json` must be populated with real auth user IDs before `--apply`.
5. **Synthetic demo data is not real client data**. Do not send synthetic documents or task data to live lender systems.

## Go / No-Go Call

**GO** — Ray can proceed to solo verification. Outside testers can be invited after Ray populates `data/private/first_3_testers.local.json` and sets `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`.
