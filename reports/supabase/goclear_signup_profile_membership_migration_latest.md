# GoClear Signup Profile Membership Migration

**Date**: 2026-07-06
**Migration**: `20260706120000_goclear_signup_profile_membership_bootstrap.sql`

---

## What This Migration Does

1. **Creates `tenant_memberships` table** (if not exists) — links auth users to tenants
2. **Extends `client_profiles`** with portal columns (tenant_id, client_id, status, etc.)
3. **Creates trigger function** `goclear_handle_new_user()` — SECURITY DEFINER
4. **Creates trigger** `on_auth_user_created` — fires on `auth.users` INSERT
5. **Sets up RLS** — self-select + admin policies for both tables

## Trigger Behavior

When a new user signs up:
1. Extracts `full_name` and `business_name` from `raw_user_meta_data`
2. Generates `client_id` = `'gc_' || replace(user_id, '-', '')`
3. Inserts `client_profiles` row (idempotent, ON CONFLICT DO NOTHING)
4. Inserts `tenant_memberships` row (idempotent, ON CONFLICT DO NOTHING)

## RLS Policies

### `tenant_memberships`
- `memberships_self_select`: authenticated users can read their own row
- `memberships_admin_select`: admins can read all rows
- `memberships_admin_manage`: admins can insert/update/delete

### `client_profiles`
- `client_profiles_self_select`: authenticated users can read their own profile (via membership link)
- `client_profiles_admin_select`: admins can read all profiles
- `client_profiles_self_update`: authenticated users can update their own profile
- `client_profiles_admin_manage`: admins can full CRUD

## Safety

- No DROP/TRUNCATE/destructive statements
- All INSERT uses ON CONFLICT DO NOTHING (idempotent)
- SECURITY DEFINER function runs with owner privileges (not caller)
- No service role key exposed to frontend
- RLS stays enabled on all tables
- Admin policies are additive, not replacing existing ones

## Status: READY TO APPLY
