# Document Upload RLS Hotfix — Phase R1

## Observed Error

During manual test of `/client/documents` with `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`:

```
new row violates row-level security policy for table client_documents
```

**When**: Supabase Storage upload succeeds, but the `client_documents` metadata insert fails.

## Root Cause

Two issues were present:

1. **Auth UID used as Nexus `client_id`**: `DocumentUploadZone.tsx` inserted `client_id = supabase.auth.getUser().id` (the auth UID). Nexus `tenant_memberships.client_id` is a derived Nexus client ID (e.g., `gc_<uuid>` or `client_test_julius_erving`), not the raw auth UID.

2. **RLS policy missing client self-insert**: The existing `client_documents_operator_write` policy only allows `super_admin`, `admin`, and `operator` roles to write. There was no policy permitting an authenticated client to insert their own document metadata row.

## Files Changed

| File | Change |
|------|--------|
| `src/lib/clientAuthContext.ts` | **NEW** — helper to resolve auth UID → `{ tenant_id, client_id }` via `tenant_memberships`, fallback to `client_profiles` |
| `src/components/client/DocumentUploadZone.tsx` | Updated `writeDocumentMetadata` to accept `ResolvedClientContext` instead of raw `userId`; context is resolved before insert |
| `src/pages/client/ClientPortalPages.jsx` | `RequestReviewPage` now also resolves live client context before inserting `client_tasks` review request |
| `supabase/migrations/20260707140000_client_document_client_insert_rls.sql` | **NEW** — additive migration: `client_documents_client_insert_own` policy allowing authenticated clients to insert rows matching their `tenant_memberships` with safe field constraints |

## Identity Mapping Fix Status

**YES** — Code identity mapping was fixed.

`resolveClientContextForCurrentUser()` resolves in this order:
1. `tenant_memberships` row where `user_id = auth.uid()` and `role = 'client'`
2. Fallback to `client_profiles` row where `user_id = auth.uid()`
3. If neither resolves, the upload shows: "Could not resolve your client profile. Please sign out and sign back in or contact GoClear."

Inserted rows now carry the resolved `tenant_id` and `client_id`, not the raw auth UID.

## RLS Migration Needed

**YES** — `supabase/migrations/20260707140000_client_document_client_insert_rls.sql`

Policy: `client_documents_client_insert_own`

Allows INSERT only when ALL of:
- Row's `tenant_id` and `client_id` match the authenticated user's `tenant_memberships`
- `client_visible = true`
- `approval_required = true`
- `source = 'client_portal_upload'`

Does NOT grant broad authenticated insert. Does NOT change select or update paths.

## Verification Steps

```bash
# 1. Build and type check pass
npm run build

# 2. Portal button smoke check passes
python3 scripts/checks/check_client_portal_actions.py

# 3. Apply migration to target Supabase project:
#    supabase db push
#    OR apply via Supabase Dashboard SQL editor

# 4. Manual upload test:
#    - Sign in as tester
#    - Open /client/documents
#    - Upload tmp/test-upload-proof-of-address.txt
#    - Expected UI: "Saved and queued for review"
#    - Verify row in Supabase SQL editor:
#      SELECT id, tenant_id, client_id, source, goclear_review_status, created_at
#      FROM public.client_documents
#      WHERE source = 'client_portal_upload'
#        AND client_id != auth.uid()::text
#      ORDER BY created_at DESC LIMIT 5;
#    - Verify admin drawer sees the new row

# 5. Request Review submit test:
#    - Navigate to /client/request-review
#    - Click Request Review
#    - Verify row in client_tasks with category='review_request'
#    - Verify client_id is Nexus client ID, not auth UID
```

## Remaining Caveats

1. **Migration must be applied** to resolve the RLS failure. Code fix alone is insufficient without the new policy.
2. **Manual upload verification** must be performed by Ray before marking the document upload path as fully green in the readiness score.
3. **Orphan upload handling**: If metadata insert fails after Storage upload, the file remains in Storage. No auto-deletion is performed. Ray should manually clean orphaned files if needed.
4. **Tenant membership requirement**: Users without a `tenant_memberships` row with `role = 'client'` will see the resolution error message and cannot upload metadata from the portal. This is expected behavior.
5. **No service-role key** is used in frontend code. All inserts go through the anon client with the new scoped policy.

## Readiness Score Impact

Phase R1 fixes a blocking RLS error that prevented live document upload metadata writes.
- **Previous**: 82/100 with caveat
- **Current**: 85/100 pending manual upload verification
  - +3 for fixing identity mapping + RLS policy
  - Manual verification remains outstanding

## Go/No-Go

Pending manual upload test confirming:
1. Storage upload succeeds
2. `client_documents` metadata row is created with resolved `client_id`
3. Admin drawer shows the new row

Once verified: update readiness score to **87/100**.
