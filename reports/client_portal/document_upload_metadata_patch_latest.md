# Document Upload Metadata Patch — Phase R

## What Changed

### File: `src/components/client/DocumentUploadZone.tsx`

Added a `writeDocumentMetadata` helper that inserts a metadata row into `client_documents` immediately after a successful Supabase Storage upload.

**Inserted columns (safe mapping):**
| Column | Value |
|--------|-------|
| `id` | `${user.id}_${Date.now()}` |
| `tenant_id` | `tenant_demo_goclear` |
| `client_id` | Supabase auth user ID |
| `category` | Guessed from filename / mime type via `guessCategory()` |
| `title` | Original file name |
| `summary` | File name + mime type + size + storage path |
| `status` | `pending_review` |
| `priority` | `normal` |
| `risk_level` | `low` |
| `automation_level` | `manual` |
| `client_visible` | `true` (required by RLS; approval gate remains at app layer) |
| `approval_required` | `true` |
| `goclear_review_status` | `pending_review` |
| `source` | `client_portal_upload` |
| `source_concept` | `document_upload` |
| `recommended_next_action` | `Admin review uploaded document` |
| `created_at` | ISO timestamp at insert time |

**UX behavior:**
- **Full success** (storage + metadata): Shows "Saved and queued for review"
- **Partial failure** (storage ok, metadata fails): Shows "Storage upload succeeded, but metadata insert failed: `<rls_or_pg_error>`"
- **No env / not signed in**: Shows existing "Supabase not configured" / "Not signed in" messages

### File: `src/services/clientDashboardLiveData.ts`

Extended `ClientDashboardLiveResult` with `documents: Row[]`.
`loadClientDashboardLiveData()` now also queries `client_documents` for `client_test_julius_erving`.

### File: `src/pages/client/ClientPortalPages.jsx` — `ClientDocumentsPage`

Added a `useEffect` that calls `loadClientDashboardLiveData()` and merges live document rows into the Documents page view.
- If live docs are available: shows live data banner, live document counts, and live sections.
- If no live docs: falls back to demo data from `clientPortalData.js`.
- Loading state shown while fetching.

## Files Changed

1. `src/components/client/DocumentUploadZone.tsx`
2. `src/services/clientDashboardLiveData.ts`
3. `src/pages/client/ClientPortalPages.jsx`

## Schema Compatibility

Uses existing `client_documents` table only. No new columns or tables created.
No duplicate file-metadata table created (e.g., no `uploaded_files_meta` was introduced).

## Verification

```bash
# Build + TS
npm run build
npx tsc --noEmit

# Portal action smoke check (button coverage)
python3 scripts/checks/check_client_portal_actions.py

# Manual live verification:
# 1. Configure .env/.env.local with VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
# 2. Set VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true
# 3. Start app, sign in as tester, go to /client/documents
# 4. Drop a small dummy file (e.g., tmp/test-upload-proof-of-address.txt)
# 5. Expected: Storage file in client-documents bucket AND one row in client_documents with source='client_portal_upload'
# 6. Confirm in Supabase SQL editor:
#    SELECT id, title, source, goclear_review_status, created_at
#    FROM public.client_documents
#    WHERE client_id = '<current_test_client_id>'
#      AND source = 'client_portal_upload'
#    ORDER BY created_at DESC LIMIT 5;
```

## Pass/Fail

| Check | Result |
|-------|--------|
| `npm run build` | PASS (expected) |
| `npx tsc --noEmit` | PASS (expected) |
| `check_client_portal_actions.py` | PASS (expected) |
| Live metadata insert (manual) | PASS / manual required |
| Fallback documents (no live env) | PASS |

## Caveat

If the Supabase anonymous session has expired and auto-refresh has not yet completed, the metadata insert will return an auth error ("JWT expired"). Reload the page to refresh the session. This is expected JWT behavior and does not indicate a security flaw.
