# GoClear RLS Policy Verification

**Date**: 2026-07-06

---

## RLS Architecture

### Admin Tables (APPLIED — `0002` + `20260624190000`)
- `admin_users`: self-select only (`id = auth.uid()`)
- Dashboard tables: `nexus_is_active_admin()` → checks `admin_users` table
- Function: `public.nexus_is_active_admin()` — SECURITY DEFINER, returns boolean
- All 13 core tables + ~30 extended tables have admin read policies

### Client Portal Tables (DRAFT — `20260629095450`)
- `tenant_memberships`: self-select + admin manage
- `client_profiles`: tenant-based access via `tenant_memberships`
- `client_tasks`, `client_documents`, `readiness_scores`, etc.: same pattern
- **NOT APPLIED** — migration is DRAFT

### Client Workflow Tables (APPLIED — `20260629090000`)
- `client_profiles` (base), `client_workflow_stage_history`, `credit_score_history`, etc.
- Admin-only policies (read/insert/update via `admin_users`)
- NO client-facing policies

## RLS Policy Analysis

### `tenant_memberships` (DRAFT)
```sql
-- Self-select: users can read their own membership
CREATE POLICY "memberships_self_or_admin_select"
  ON tenant_memberships FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.nexus_is_active_admin());

-- Admin manage: only admins can insert/update
CREATE POLICY "memberships_admin_manage"
  ON tenant_memberships FOR ALL TO authenticated
  USING (public.nexus_is_active_admin())
  WITH CHECK (public.nexus_is_active_admin());
```
**Issue**: Only admins can CREATE memberships. A self-service signup cannot create its own membership row.

### `client_profiles` (DRAFT)
```sql
-- Read: admin OR member of same tenant with appropriate role
CREATE POLICY "client_profiles_tenant_select"
  ON client_profiles FOR SELECT TO authenticated
  USING (
    public.nexus_is_active_admin()
    OR EXISTS (
      SELECT 1 FROM tenant_memberships tm
      WHERE tm.tenant_id = client_profiles.tenant_id
        AND tm.user_id = auth.uid()
        AND (tm.role IN ('super_admin','admin','operator')
             OR (tm.role='client' AND tm.client_id = client_profiles.client_id
                 AND client_profiles.client_visible))
    )
  );
```
**Issue**: Client users can only see their own profile IF `client_visible = true` AND they have a membership row AND `tm.client_id` matches `client_profiles.client_id`.

### Base `client_profiles` (APPLIED)
```sql
-- Admin-only policies via admin_users
CREATE POLICY "admin read client_profiles" ...
CREATE POLICY "admin insert client_profiles" ...
CREATE POLICY "admin update client_profiles" ...
```
**Issue**: Only admins can read/write. No client-facing access.

## Gap Analysis

| Requirement | Status |
|-------------|--------|
| RLS enabled on all tables | PASS |
| Admin access gated | PASS |
| Client can read own profile | FAIL — no membership row, no user_id link |
| Client can read own tasks | FAIL — same reason |
| Anon cannot read private data | PASS (default deny) |
| Signup creates membership | FAIL — admin-only policy blocks self-service |

## Critical Issues

1. **No self-service membership creation** — `tenant_memberships` INSERT requires admin role
2. **No user_id in client_profiles** — can't link auth user to profile
3. **DRAFT migration not applied** — client portal policies don't exist in production
4. **Base client_profiles is admin-only** — clients can't read their own data

## Recommended Fixes

1. Add self-service signup policy to `tenant_memberships`:
   ```sql
   CREATE POLICY "client_self_signup" ON tenant_memberships
     FOR INSERT TO authenticated
     WITH CHECK (user_id = auth.uid() AND role = 'client');
   ```
2. Create a trigger/function to auto-create membership + profile on signup
3. Apply the DRAFT client portal migration
4. Add `user_id` column to `client_profiles` or use `tenant_memberships` as the link

## Status: BLOCKED

RLS policies exist but block self-service signup. Client cannot access own data.
