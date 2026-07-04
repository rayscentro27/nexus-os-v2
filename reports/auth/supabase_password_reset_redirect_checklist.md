# Supabase Password Reset Redirect Checklist

**Generated**: 2026-07-04

---

## Required Supabase Dashboard Configuration

### Auth → URL Configuration

**Site URL:**
```
https://goclearonline.cc
```

**Redirect URLs (add all):**
```
https://goclearonline.cc/update-password
https://goclearonline.cc/update-password/
https://nexusv20.netlify.app/update-password
https://nexusv20.netlify.app/update-password/
http://localhost:5173/update-password
http://localhost:5173/update-password/
```

> Add each URL as a separate entry in the Redirect URLs list in Supabase Dashboard → Authentication → URL Configuration.

---

## How to Test the Reset Flow

### Step 1: While logged in (change password from Settings)
1. Sign in to Nexus OS
2. Navigate to Settings → Account Security
3. Enter new password + confirm
4. Click "Change password"
5. Verify success message appears
6. Verify session remains active (no sign-out)

### Step 2: While logged out (reset via email)
1. Sign out of Nexus OS
2. On the sign-in page, click "Forgot password?"
3. Enter your admin email
4. Click "Send secure reset link"
5. Check email inbox (and spam folder)
6. Click the reset link in the email
7. Verify the `/update-password` page loads
8. Enter new password + confirm
9. Click "Set new password"
10. Verify redirect to sign-in page with success message

### Step 3: Test expired/invalid link
1. Open `/update-password` directly (without a recovery link)
2. Verify "Reset link expired" message appears
3. Verify "Back to sign in" button works

---

## How to Test While Auto-Logged-In

If Ray is currently auto-logged in and wants to test the reset flow:

1. Open a private/incognito window
2. Go to `https://goclearonline.cc`
3. Click "Forgot password?" on the sign-in form
4. Enter your email and send the reset link
5. Click the link in the email
6. Complete the password change

Alternatively, sign out first, then test the reset flow.

---

## What to Do If Link Says "Session Missing"

If the reset link opens but shows "Reset link expired":

1. **Check redirect URLs** in Supabase Dashboard → ensure `/update-password` is listed
2. **Check the link** — ensure it hasn't expired (Supabase links expire after 1 hour by default)
3. **Check for URL encoding** — the redirect URL must match exactly
4. **Request a new link** — go back to sign-in and click "Forgot password?" again
5. **Do not** manually edit the password in the Supabase database
6. **Do not** use the service role key to update passwords

---

## What NOT to Do

- Do not use the Supabase service role key in the frontend
- Do not manually edit passwords in the auth.users table
- Do not disable RLS to bypass auth
- Do not share recovery tokens or passwords
- Do not store passwords in localStorage or sessionStorage
- Do not log passwords or recovery tokens to console

---

## Files Changed

| File | Purpose |
|------|---------|
| `src/lib/authHelpers.ts` | Redirect URL config + auth helper functions |
| `src/components/AccountSecurityPanel.tsx` | Settings/Security UI component |
| `src/pages/UpdatePasswordPage.tsx` | `/update-password` route page |
| `src/components/auth.tsx` | Updated to use shared helpers |
| `src/app/App.tsx` | Added `/update-password` route |
| `src/admin/NexusAdminUI.jsx` | Added Security section to Settings |

---

## Environment Variables Required

| Variable | Where | Purpose |
|----------|-------|---------|
| `VITE_SUPABASE_URL` | `.env` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | `.env` | Supabase anonymous key |

No new environment variables needed. No service role key in frontend.
