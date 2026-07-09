# Client Portal Mapping Snapshot

## Current Commit
2995d1d

## Git Log (latest)

- 2995d1d fix live status label runtime crash
- 5431861 fix live client documents display
- 8a52e01 fix client document upload metadata rls
- b2b052f complete client portal live workflow patch
- 6542d11 certify live client portal tester workflows
- 71b9dd4 fix client portal tester ux actions and dashboard fit
- 8bdf62f verify and repair first tester client login
- 6c6a3ec prepare first three real tester account activation
- 96abbef prepare first three tester activation with actual schema
- 9c719e5 reconcile client portal live supabase schema

## Working Tree Summary

- Dirty tree: Yes — many dirty runtime/cache/generated files.
- In-scope dirty files: `src/app/App.tsx` (modified for R4 admin guard), security report files, check scripts.
- Out-of-scope dirty files (do NOT clean): `data/cache/`, `data/runtime/`, `data/alpha/`, `reports/alpha/`, `reports/telegram/`, `reports/work_orders/`, `reports/runtime/`, `scripts/ops/`, `tmp/`, `data/recommendations/`, `reports/advisor_idea_briefs/`, `reports/command_plans/`, `reports/hermes/web_search/`, `reports/launch/`, `reports/scheduler/`, `reports/telegram/`, `reports/work_orders/drafts/`.

## Supabase Project Ref
iqjwgpnujbeoyaeuwehj

## Netlify Status
CLI present. Deploy connected per mission context. No env changes made.

## Admin Route Guard State
`/admin` and `/admin/*` now gated by `AdminGuard` (added in R4 work). Uses `admin_users` and `tenant_memberships` role checks.

## Client Live Mode State
`VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT` env flag. Default: false (demo/fallback). When true, live Supabase reads enabled for authenticated client with valid `tenant_memberships`.

## Known Issues from Recent Patches
- R2B fixed `ReferenceError: liveStatusLabel is not defined` in `ClientPortalShell.jsx`.
- R2 fixed hardcoded `client_test_julius_erving` in `clientDashboardLiveData.ts`; now resolves signed-in user's `tenant_id`/`client_id`.
- R1 fixed auth UID used as Nexus `client_id`; added `clientAuthContext.ts` helper.
- R1 added RLS migration `20260707140000_client_document_client_insert_rls.sql` for client self-insert into `client_documents`.

## Out-of-Scope Dirty Files (DO NOT TOUCH)
- `data/cache/**`
- `data/runtime/**`
- `data/alpha/**`
- `data/exports/**`
- `data/operations/**`
- `reports/alpha/**`
- `reports/telegram/**`
- `reports/work_orders/**`
- `reports/runtime/**`
- `reports/hermes/**`
- `reports/manual_publish/**`
- `reports/nexus_research/**`
- `reports/advisor_idea_briefs/**`
- `reports/command_plans/**`
- `reports/launch/**`
- `reports/scheduler/**`
- `scripts/ops/**`
- `tmp/**`
- `data/recommendations/**`
- `collect_router_repair_results.sh`
