# Admin Review Actual Schema Check

**Generated:** 2026-07-07

## Admin Client Review Panel

The admin `ClientsPanel` component reads from:

| Data Source | Table/Source | Status |
|-------------|-------------|--------|
| Client list | `clientsData.js` (static) + live Supabase fallback | ✓ |
| Client detail | Static mock data | ✓ |
| Storage files | Supabase Storage `client-documents` bucket | ✓ |
| Admin notes | Local state (not persisted) | ✓ |

## Live Data Loading

The `loadSection('clients', clientsList)` function:
- Queries `client_profiles` table for live data
- Falls back to static `clientsList` if no live data
- Displays source banner (Live Supabase vs Static)

## Tables Read by Admin

| Table | Purpose | RLS |
|-------|---------|-----|
| client_profiles | List all clients | Admin read ✓ |
| client_tasks | Show client tasks | Admin read ✓ |
| readiness_scores | Show readiness scores | Admin read ✓ |
| client_documents | Show document metadata | Admin read ✓ |

## Storage Access

- Admin can list all files in `client-documents` bucket ✓
- Admin can read/delete any client file ✓
- Files are client-scoped by user_id folder ✓

## Conclusion

Admin review uses correct table names. No fixes needed.
