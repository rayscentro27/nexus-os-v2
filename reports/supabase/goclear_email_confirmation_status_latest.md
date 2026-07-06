# GoClear Email Confirmation Status

**Date**: 2026-07-06

---

## Assumed Configuration

Supabase default: **Email confirmation required** for new signups.

## Current Behavior

### Signup Page (`/goclear/signup`)
- Calls `supabase.auth.signUp({ email, password, options: { data: {...} } })`
- On success: shows "Check Your Email" page with message:
  > "We sent a confirmation link to **{email}**. Click the link to activate your account, then come back to sign in."
- Links to `/goclear/login`

### Login Page (`/goclear/login`)
- Calls `supabase.auth.signInWithPassword({ email, password })`
- On error: shows raw Supabase error message
- **Does NOT specifically handle "unconfirmed email" error**

## Supabase Error Messages

| Scenario | Supabase Error | Current Handling |
|----------|---------------|-----------------|
| Wrong password | "Invalid login credentials" | Shows raw error |
| Unconfirmed email | "Email not confirmed" | Shows raw error |
| User not found | "Invalid login credentials" | Shows raw error (same as wrong password) |
| Email already registered | "User already registered" | Shows raw error |

## Issues

1. **Raw error messages shown to user** — "Email not confirmed" is technical jargon
2. **No resend confirmation option** — user must know to check spam
3. **No "unconfirmed email" specific UI** — same error styling as wrong password

## Recommended Improvements

### Login Page
1. Detect "Email not confirmed" error
2. Show friendly message: "Please check your email and click the confirmation link before signing in."
3. Add "Resend confirmation email" button

### Signup Page
1. Already shows "Check Your Email" — correct
2. Could add "Didn't receive it? Check spam or resend" link

## Status: FUNCTIONAL (with UX gaps)

Email confirmation works via Supabase defaults. Error handling could be improved.
