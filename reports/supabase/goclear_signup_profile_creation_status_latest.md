# GoClear Signup Profile Creation Status

**Date**: 2026-07-06

---

## Current Signup Flow

1. User fills: full name, email, password, business name (optional), agrees to ToS
2. Frontend calls `supabase.auth.signUp({ email, password, options: { data: { full_name, business_name } } })`
3. Supabase creates auth user with metadata
4. Frontend shows "Check Your Email" confirmation page
5. **NO database row is created** beyond the auth user

## What's Missing

### No Profile Creation Trigger
- There is NO `auth.users` INSERT trigger that creates a `client_profiles` row
- There is NO `tenant_memberships` row created for the new user
- The user's `full_name` and `business_name` are stored in `auth.users.raw_user_meta_data` only

### No Profile Bootstrap Path
- The frontend does NOT call any Supabase function to create a profile after signup
- The `client_profiles` table has no `user_id` column to link to auth users
- The `tenant_memberships` table (DRAFT) would link `user_id` to `tenant_id` and `client_id`

## Database Tables (from migrations)

### `client_profiles` (base table — `20260629090000`)
- `id` uuid PK (NOT linked to auth.users)
- `workspace_id` uuid → references `workspaces(id)`
- `client_label` text
- `current_stage` text default 'signup_started'
- NO `user_id` column

### `client_profiles` (portal extension — `20260629095450`, DRAFT)
- Adds `tenant_id`, `client_id`, `external_id`
- Adds `title`, `summary`, `status`, `score`, `priority`
- Adds `client_visible`, `approval_required`
- Still NO `user_id` column

### `tenant_memberships` (DRAFT)
- `tenant_id` text + `user_id` uuid → composite PK
- `role` text (super_admin | admin | operator | client)
- `client_id` text
- THIS is the link between auth users and client data

## Gap Analysis

| Requirement | Status |
|-------------|--------|
| Auth user created on signup | PASS |
| Metadata (full_name, business_name) saved | PASS |
| Profile row created | FAIL — no trigger/function |
| Membership row created | FAIL — no trigger/function |
| User can read own profile after login | FAIL — no link exists |
| RLS allows user to read own data | FAIL — policies reference `tenant_memberships` which doesn't exist |

## Recommended Fix

Create a database function + trigger:
1. On `auth.users` INSERT → create `tenant_memberships` row with `role='client'`
2. On `auth.users` INSERT → create `client_profiles` row with user metadata
3. Link via `user_id` in `tenant_memberships` and `client_id` in `client_profiles`

OR (simpler, frontend-side):
1. After successful signup, call a Supabase Edge Function to create profile
2. OR use `supabase.rpc()` to call a server-side function

## Status: BLOCKED

Signup creates auth user but no profile/membership. User has no data in the database.
