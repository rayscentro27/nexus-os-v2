# Signup Membership Profile Schema Audit

**Date**: 2026-07-06
**Branch**: main

---

## Migration Classification: `20260629095450_client_portal_core_tables.sql`

**Verdict**: NEEDS_PATCH_BEFORE_APPLY

### Why
1. Header says "DRAFT ONLY: review, timestamp, and approve before applying"
2. `tenant_memberships` INSERT policy is admin-only — blocks self-service signup
3. No trigger/function to auto-create rows on `auth.users` INSERT
4. `client_profiles` has no `user_id` column to link to auth users
5. `client_profiles` SELECT policy requires `client_visible = true` AND matching `client_id` — new users won't have this

### What's Safe
- All statements are additive (CREATE TABLE IF NOT EXISTS, ALTER TABLE ADD COLUMN IF NOT EXISTS)
- No DROP/TRUNCATE/destructive statements
- RLS is enabled on all new tables
- Uses `nexus_is_active_admin()` consistently

### What Needs Patching
1. Add self-service INSERT policy for `tenant_memberships` (or use trigger)
2. Create `goclear_handle_new_user()` trigger function
3. Add `user_id` column to `client_profiles` (or rely on `tenant_memberships` as the link)
4. Fix `client_profiles` SELECT policy for new users (initial `client_visible` should be true for own profile)

## Existing Schema

### `admin_users` (APPLIED — `0002`)
- `id` uuid PK → `auth.users(id)`
- `email`, `role`, `active`
- RLS: self-select only

### `client_profiles` (APPLIED — `20260629090000`)
- `id` uuid PK (NOT linked to auth.users)
- `workspace_id`, `client_label`, `current_stage`
- NO `user_id`, NO `tenant_id`, NO `client_id`
- RLS: admin-only

### `nexus_is_active_admin()` (APPLIED — `20260624190000`)
- SECURITY DEFINER function
- Checks `admin_users` table for active admin
- Used by all RLS policies

## Required New Objects

1. `public.goclear_default_tenant_id()` — returns 'goclear' constant
2. `public.goclear_handle_new_user()` — trigger function on auth.users INSERT
3. Trigger: `on_auth_user_created` → fires `goclear_handle_new_user()`
4. RLS policies for authenticated client self-read on `tenant_memberships` and `client_profiles`

## Status: NEEDS_PATCH_BEFORE_APPLY

Migration is structurally sound but requires trigger function + RLS policy patches before safe application.
