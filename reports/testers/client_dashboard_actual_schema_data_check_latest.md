# Client Dashboard Actual Schema Data Check

**Generated:** 2026-07-07

## Data Flow Verified

1. **Auth Gate:** `useSession()` checks Supabase auth → redirects to `/client/login` if unauthenticated ✓
2. **Profile Lookup:** Queries `tenant_memberships` for user_id → gets tenant_id + client_id ✓
3. **Profile Data:** Queries `client_profiles` by tenant_id + client_id ✓
4. **Tasks:** Queries `client_tasks` by tenant_id + client_id, client_visible=true ✓
5. **Scores:** Queries `readiness_scores` by tenant_id + client_id, client_visible=true ✓
6. **Guidance:** Uses `clientGuidance.ts` generator based on document/readiness status ✓

## Tables Used by Frontend

| Table | Query Location | Purpose |
|-------|---------------|---------|
| tenant_memberships | useClientPortalData.ts:52 | Find user's tenant/client |
| client_profiles | useClientPortalData.ts:59 | Load profile data |
| client_tasks | useClientPortalData.ts:60 | Load task list |
| readiness_scores | useClientPortalData.ts:61 | Load readiness scores |
| client_documents | DocumentUploadZone.tsx | Upload files |

## Route Behavior

| Route | Behavior | Status |
|-------|----------|--------|
| / | GoClear landing page | ✓ |
| /client/login | Client login | ✓ |
| /client/preview | Demo data with banner | ✓ |
| /client/dashboard | Auth-gated, shows profile | ✓ |
| /admin | Admin login | ✓ |
| /admin/command-center | Admin only | ✓ |

## Missing Profile Handling

When authenticated user has no profile:
- Status: "partial"
- Message: "Your portal profile is being prepared. Contact support if this persists."
- Falls back to demo data with clear labeling

## Conclusion

Frontend uses correct table names. No fixes needed.
