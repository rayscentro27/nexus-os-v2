# GoClear Signup Migration Apply Status

**Date**: 2026-07-06
**Migration**: `20260706120000_goclear_signup_profile_membership_bootstrap.sql`

---

## Apply Method: MANUAL (Supabase SQL Editor)

This migration must be applied manually via the Supabase Dashboard SQL Editor.
No local Supabase CLI or `supabase db push` is configured in this environment.

## Application Steps

### Step 1: Open Supabase Dashboard
1. Go to https://supabase.com/dashboard
2. Select the Nexus OS v2 project
3. Navigate to SQL Editor

### Step 2: Apply Migration
1. Copy the contents of `supabase/migrations/20260706120000_goclear_signup_profile_membership_bootstrap.sql`
2. Paste into SQL Editor
3. Click "Run" or press Cmd+Enter
4. Verify: "Success. No rows returned"

### Step 3: Verify Tables
Run in SQL Editor:
```sql
-- Check tenant_memberships exists
SELECT EXISTS (
  SELECT FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'tenant_memberships'
) as tenant_memberships_exists;

-- Check trigger exists
SELECT EXISTS (
  SELECT FROM pg_trigger
  WHERE tgname = 'on_auth_user_created'
) as trigger_exists;

-- Check function exists
SELECT EXISTS (
  SELECT FROM pg_proc
  WHERE proname = 'goclear_handle_new_user'
) as function_exists;
```

Expected: all three return `true`

### Step 4: Test Signup
1. Open `/goclear/signup` in browser
2. Create a test account
3. Check "Check Your Email" page appears
4. In Supabase Dashboard → Authentication → Users: confirm user exists
5. In Supabase Dashboard → SQL Editor:
```sql
-- Check membership was created
SELECT * FROM public.tenant_memberships
WHERE user_id = (SELECT id FROM auth.users WHERE email = 'test@example.com');

-- Check profile was created
SELECT * FROM public.client_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'test@example.com');
```

Expected: both queries return 1 row

### Step 5: Test Login
1. Go to `/goclear/login`
2. Sign in with test credentials
3. Confirm redirect to `/client`
4. Confirm portal loads (may show mock data still — that's expected)

## Rollback

If needed, reverse the migration:
```sql
-- Remove trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Remove function
DROP FUNCTION IF EXISTS public.goclear_handle_new_user();

-- Remove RLS policies
DROP POLICY IF EXISTS "memberships_self_select" ON public.tenant_memberships;
DROP POLICY IF EXISTS "memberships_admin_select" ON public.tenant_memberships;
DROP POLICY IF EXISTS "memberships_admin_manage" ON public.tenant_memberships;
DROP POLICY IF EXISTS "client_profiles_self_select" ON public.client_profiles;
DROP POLICY IF EXISTS "client_profiles_admin_select" ON public.client_profiles;
DROP POLICY IF EXISTS "client_profiles_self_update" ON public.client_profiles;
DROP POLICY IF EXISTS "client_profiles_admin_manage" ON public.client_profiles;

-- NOTE: do NOT drop the tables — they may have data
```

## Status: AWAITING MANUAL APPLICATION
