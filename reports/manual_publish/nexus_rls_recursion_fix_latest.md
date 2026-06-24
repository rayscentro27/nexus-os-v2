# Nexus RLS Recursion Fix Report

Date: 2026-06-24

## Root cause

The live UI connected to Supabase and authenticated as `goclearonline@gmail.com`, but the Approvals query failed with:

`infinite recursion detected in policy for relation "admin_users"`

The recursive policy was:

`admin read admin_users`

It was defined on `public.admin_users` and queried `public.admin_users` inside its own `USING` clause:

`exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true)`

When PostgreSQL evaluated that policy, it had to read `admin_users` again, causing RLS to re-enter the same policy.

## Migration created

`supabase/migrations/20260624190000_fix_admin_users_rls_recursion.sql`

## Policy/function changes

The migration creates:

- `public.nexus_is_active_admin()`
- `admin_users_select_self`

It replaces recursive admin checks on dashboard policies with:

`public.nexus_is_active_admin()`

The helper is `SECURITY DEFINER`, uses a fixed `search_path`, and checks only whether the current `auth.uid()` has an active row in `public.admin_users`.

The `admin_users` table itself is not made public. Authenticated users may read only their own `admin_users` row via:

`id = auth.uid()`

## Why this is safe

- RLS remains enabled.
- Dashboard tables remain admin-gated.
- `admin_users` is not publicly readable.
- Anonymous users get no new access.
- The frontend still uses only the Supabase anon key and authenticated user session.
- No service-role key is exposed to browser code.
- Approvals remain protected by active-admin membership.

## Expected UI result after applying migration

After the migration is applied to Supabase and Ray refreshes/signs in:

- Approvals diagnostics should show `Admin mapping found: yes`.
- Approvals query should report `connected_with_records` if rows exist.
- Pending approval `13eafcab-6940-4612-8239-54786e8c9e60` should appear.

## Revenue/safety gates unchanged

- `publish_enabled` remains false.
- Facebook still requires separate explicit approval and the one-post gated publish flow.
- No social post was published by this fix.
- No email was sent by this fix.
- No trade was placed by this fix.
- No scheduler was started by this fix.

## Apply step

This report documents the committed migration. The migration still must be applied to the Supabase project before the live UI behavior changes.
