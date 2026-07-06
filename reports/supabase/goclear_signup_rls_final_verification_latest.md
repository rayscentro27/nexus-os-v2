# GoClear Signup RLS Final Verification

**Date**: 2026-07-06
**Migration**: `20260706120000_goclear_signup_profile_membership_bootstrap.sql`

---

## Policy Summary

### `tenant_memberships`

| Policy | Operation | Role | Condition |
|--------|-----------|------|-----------|
| `memberships_self_select` | SELECT | authenticated | `user_id = auth.uid()` |
| `memberships_admin_select` | SELECT | authenticated | `nexus_is_active_admin()` |
| `memberships_admin_manage` | ALL | authenticated | `nexus_is_active_admin()` |

### `client_profiles`

| Policy | Operation | Role | Condition |
|--------|-----------|------|-----------|
| `client_profiles_self_select` | SELECT | authenticated | membership link exists |
| `client_profiles_admin_select` | SELECT | authenticated | `nexus_is_active_admin()` |
| `client_profiles_self_update` | UPDATE | authenticated | membership link exists |
| `client_profiles_admin_manage` | ALL | authenticated | `nexus_is_active_admin()` |

## Verification: Authenticated Client User

### CAN:
- Read own `tenant_memberships` row (self_select)
- Read own `client_profiles` row (self_select via membership link)
- Update own `client_profiles` safe fields (self_update)

### CANNOT:
- Read another client's `tenant_memberships` (RLS blocks)
- Read another client's `client_profiles` (RLS blocks)
- INSERT into `tenant_memberships` (no self-service INSERT policy)
- DELETE from `tenant_memberships` (admin_manage only)
- INSERT into `client_profiles` (admin_manage only)
- Grant themselves admin role (trigger hardcodes role='client')

## Verification: Anon User

### CANNOT:
- Read any `tenant_memberships` rows (RLS default deny)
- Read any `client_profiles` rows (RLS default deny)
- Insert/update/delete any rows (RLS default deny)

## Verification: Admin User

### CAN:
- Read all `tenant_memberships` rows (admin_select + admin_manage)
- Read all `client_profiles` rows (admin_select + admin_manage)
- Insert/update/delete both tables (admin_manage)
- Existing admin dashboard functionality remains intact (nexus_is_active_admin)

## Verification: Trigger Security

- Function is `SECURITY DEFINER` — runs with function owner privileges
- `SET search_path = public` — prevents search_path injection
- Only creates rows with `role = 'client'` — cannot escalate to admin
- Uses `ON CONFLICT DO NOTHING` — idempotent, no duplicates
- Trigger fires AFTER INSERT on `auth.users` — only for new users

## Status: PASS

RLS correctly gates all access. Trigger is secure and idempotent.
