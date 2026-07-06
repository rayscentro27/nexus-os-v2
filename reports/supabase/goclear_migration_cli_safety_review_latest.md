# GoClear Migration CLI Safety Review

**Date**: 2026-07-06
**Migration**: `20260706120000_goclear_signup_profile_membership_bootstrap.sql`

---

## Classification: SAFE_TO_APPLY

## Safety Checks

| Check | Status |
|-------|--------|
| Contains `goclear_handle_new_user()` | YES — SECURITY DEFINER trigger function |
| Contains trigger on `auth.users` | YES — `on_auth_user_created` |
| Creates `tenant_memberships` rows | YES — via trigger, idempotent |
| Creates `client_profiles` rows | YES — via trigger, idempotent |
| Contains RLS policies | YES — self-select, admin-select, admin-manage |
| Uses `search_path = public` | YES — prevents search_path injection |
| No service role key | CONFIRMED — no secrets in SQL |
| No RLS disable | CONFIRMED — no `DISABLE ROW LEVEL SECURITY` |
| No destructive DROP | CONFIRMED — only `DROP TRIGGER IF EXISTS` and `DROP POLICY IF EXISTS` (safe guards) |
| All statements are additive | YES — `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, `CREATE OR REPLACE` |
| Idempotent | YES — `ON CONFLICT DO NOTHING` on all inserts |
| Wrapped in transaction | YES — `BEGIN` / `COMMIT` |

## What It Creates

1. `tenant_memberships` table (IF NOT EXISTS)
2. 18 portal columns on `client_profiles` (ADD COLUMN IF NOT EXISTS)
3. 2 indexes (IF NOT EXISTS)
4. `goclear_handle_new_user()` function (CREATE OR REPLACE)
5. `on_auth_user_created` trigger (DROP IF EXISTS + CREATE)
6. 4 RLS policies on `tenant_memberships`
7. 4 RLS policies on `client_profiles`
8. 2 GRANT statements

## Risk Assessment

- **Data loss**: NONE — all additive
- **Schema change**: LOW — only adds columns/tables
- **Performance**: LOW — trigger fires once per signup
- **Security**: IMPROVED — adds RLS policies

## Status: SAFE_TO_APPLY — APPLIED VIA `supabase db push`
