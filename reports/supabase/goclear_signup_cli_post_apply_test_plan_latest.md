# GoClear Signup CLI Post-Apply Test Plan

**Date**: 2026-07-06
**Status**: Migration applied via `supabase db push`

---

## Test 1: Verify Trigger Exists
**SQL Editor**:
```sql
SELECT proname, prosecuritydefiner
FROM pg_proc WHERE proname = 'goclear_handle_new_user';
```
**Expected**: 1 row, `prosecuritydefiner = true`

## Test 2: Verify Trigger Exists
**SQL Editor**:
```sql
SELECT tgname, tgenabled
FROM pg_trigger WHERE tgname = 'on_auth_user_created';
```
**Expected**: 1 row, `tgenabled = 'O'` (enabled)

## Test 3: Verify RLS Policies
**SQL Editor**:
```sql
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('client_profiles', 'tenant_memberships')
ORDER BY tablename, policyname;
```
**Expected**: 8 rows (4 per table)

## Test 4: Create Test User via Signup
1. Visit `http://localhost:5173/goclear/signup`
2. Fill: Name = "CLI Test User", Email = `cli-test-{{timestamp}}@example.com`, Password = `Test123!@#`
3. Click "Create My Account"
4. Confirm "Check Your Email" page

## Test 5: Verify Auth User
**SQL Editor**:
```sql
SELECT id, email, raw_user_meta_data->>'full_name' AS full_name,
       raw_user_meta_data->>'business_name' AS business_name
FROM auth.users
WHERE email = 'cli-test-{{timestamp}}@example.com';
```
**Expected**: 1 row with metadata

## Test 6: Verify tenant_memberships
**SQL Editor**:
```sql
SELECT tm.tenant_id, tm.role, tm.client_id, au.email
FROM public.tenant_memberships tm
JOIN auth.users au ON au.id = tm.user_id
WHERE au.email = 'cli-test-{{timestamp}}@example.com';
```
**Expected**: 1 row, `tenant_id='goclear'`, `role='client'`

## Test 7: Verify client_profiles
**SQL Editor**:
```sql
SELECT cp.client_label, cp.title, cp.status, cp.client_visible, cp.source
FROM public.client_profiles cp
WHERE cp.id = (SELECT id FROM auth.users WHERE email = 'cli-test-{{timestamp}}@example.com');
```
**Expected**: 1 row, `client_visible=true`, `source='goclear_signup'`

## Test 8: Login and Portal
1. Visit `/goclear/login`
2. Login with test credentials
3. Confirm redirect to `/client`
4. Confirm portal loads

## Test 9: Logout
1. Click logout icon in portal header
2. Confirm redirect to `/goclear/login`

## Test 10: RLS Check
**SQL Editor** (as test user in Supabase Dashboard → Authentication → Users → Impersonate):
```sql
SELECT * FROM public.client_profiles;
-- Should return only the test user's profile
```

## Pass Criteria

Tests 1-3 verify database objects exist.
Tests 4-9 verify the end-to-end signup flow.
Test 10 verifies RLS isolation.

## Status: TEST PLAN READY
