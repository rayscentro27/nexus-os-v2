# GoClear Signup Profile Manual Test Plan

**Date**: 2026-07-06
**Prerequisite**: Migration `20260706120000_goclear_signup_profile_membership_bootstrap.sql` applied

---

## Test 1: Apply Migration
**Steps**:
1. Open Supabase Dashboard → SQL Editor
2. Paste migration SQL
3. Click "Run"

**Expected**: "Success. No rows returned"

**Verify**:
```sql
SELECT EXISTS (SELECT FROM pg_trigger WHERE tgname = 'on_auth_user_created');
-- Returns: true
```

---

## Test 2: Create Test User via Signup
**Steps**:
1. Open `http://localhost:5173/goclear/signup`
2. Fill: Full Name = "Test User", Email = "test-signup@example.com", Password = "Test123!@#", Business Name = "Test Co"
3. Check Terms checkbox
4. Click "Create My Account"

**Expected**: "Check Your Email" page with test-signup@example.com

---

## Test 3: Verify Auth User Created
**Steps**:
1. Supabase Dashboard → Authentication → Users
2. Search for "test-signup@example.com"

**Expected**: User exists with:
- Email confirmed: depends on Supabase config
- `raw_user_meta_data` contains `full_name: "Test User"` and `business_name: "Test Co"`

---

## Test 4: Verify tenant_memberships Row Created
**Steps**:
1. Supabase Dashboard → SQL Editor
2. Run:
```sql
SELECT tm.*, au.email
FROM public.tenant_memberships tm
JOIN auth.users au ON au.id = tm.user_id
WHERE au.email = 'test-signup@example.com';
```

**Expected**: 1 row with:
- `tenant_id` = 'goclear'
- `role` = 'client'
- `client_id` starts with 'gc_'
- `user_id` matches auth user ID

---

## Test 5: Verify client_profiles Row Created
**Steps**:
1. Supabase Dashboard → SQL Editor
2. Run:
```sql
SELECT cp.*
FROM public.client_profiles cp
WHERE cp.id = (SELECT id FROM auth.users WHERE email = 'test-signup@example.com');
```

**Expected**: 1 row with:
- `tenant_id` = 'goclear'
- `client_id` matches membership's client_id
- `client_label` = 'Test User'
- `title` = 'Test Co'
- `status` = 'active'
- `client_visible` = true
- `source` = 'goclear_signup'

---

## Test 6: Login and Verify Redirect
**Steps**:
1. Open `http://localhost:5173/goclear/login`
2. Enter: test-signup@example.com / Test123!@#
3. Click "Login"

**Expected**: Redirects to `/client`

---

## Test 7: Verify Portal Loads
**Steps**:
1. After login, verify `/client/dashboard` loads
2. Check browser console for errors

**Expected**: Portal renders (may show mock data — that's expected for now)

---

## Test 8: Verify Logout
**Steps**:
1. In client portal header, click the logout icon (LogOut)
2. Verify redirect to `/goclear/login`

**Expected**: Logged out, redirected to login page

---

## Test 9: Verify Cannot Query Other Users' Data
**Steps**:
1. Create a second test user via signup
2. Login as first user
3. In browser console, run:
```javascript
const { data } = await supabase.from('client_profiles').select('*');
console.log(data);
```

**Expected**: Only first user's profile returned (RLS filters out second user's data)

---

## Test 10: Verify No Service Role Key in Browser
**Steps**:
1. Open browser DevTools → Network tab
2. Perform any Supabase request
3. Check request headers for `Authorization` header

**Expected**: Token starts with `eyJ` (anon key JWT), NOT the service role key

---

## Test 11: Verify Idempotency
**Steps**:
1. In SQL Editor, manually insert a duplicate auth user with same email
2. Check that tenant_memberships and client_profiles don't get duplicate rows

**Expected**: ON CONFLICT DO NOTHING prevents duplicates

---

## Pass Criteria

All 11 tests pass = signup bootstrap is working correctly.

## Status: TEST PLAN READY
