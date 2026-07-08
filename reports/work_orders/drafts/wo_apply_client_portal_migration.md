# Work Order: Apply Client Portal Migration

**Status:** Draft
**Priority:** High
**Created:** 2026-07-07

## Goal
Apply the `20260629095450_client_portal_core_tables.sql` migration to enable all client portal database tables.

## Why It Matters
The migration creates 20+ tables with RLS policies that the client portal depends on. Without it, no real client data can be stored.

## Scope
- Review the draft migration for safety
- Apply via `supabase db push` or Supabase Dashboard SQL editor
- Verify tables exist and RLS is active
- Verify the SECURITY DEFINER trigger for profile bootstrap

## Acceptance Criteria
- All tables exist in Supabase
- RLS is enabled on all tables
- Client can read their own profile/tasks/scores
- Admin can read all client records
- Profile bootstrap trigger fires on auth user creation

## Files Involved
- `supabase/migrations/20260629095450_client_portal_core_tables.sql`

## Risk Level
Medium — destructive review required before applying

## Test Plan
1. Apply migration to staging/preview branch
2. Create test auth user
3. Verify trigger creates membership + profile
4. Verify client can read own data
5. Verify admin can read all data
