# Client Portal Auth Audit

**Date:** 2026-07-07

## Current `/client/dashboard` Behavior

When visiting `/client/dashboard` unauthenticated:
- `ClientPortalGate` (App.tsx:13) calls `useSession()` → `supabase.auth.getSession()`
- If no session: redirects to `/goclear/login` (GoClear client login page)
- This is **NOT** the admin login — it's the GoClear-branded client login
- The GoClear login page says "Client Login" and "Access your GoClear portal"

**Verdict:** `/client/dashboard` currently shows the GoClear client login, not admin login. This is acceptable but needs improvement — the redirect goes to a different URL path (`/goclear/login`) instead of a dedicated `/client/login`.

## Auth System

- **Single Supabase auth session** — no role/profile system
- `AuthGate` component (auth.tsx:106) — used for admin routes, shows `SignInForm` (admin-branded)
- `useSession()` hook (auth.tsx:7) — used by `ClientPortalGate` for client routes
- No `ClientAuthGate` or `AdminAuthGate` components exist
- No role column in Supabase profiles table
- No `admin_users` table

## Current Route Auth Map

| Route | Auth | Login Target |
|-------|------|--------------|
| `/client` | `ClientPortalGate` → `useSession()` | `/goclear/login` |
| `/client/dashboard` | `ClientPortalGate` → `useSession()` | `/goclear/login` |
| `/admin` | `AuthGate` → `SignInForm` | Shows admin login |
| `/admin/*` | `AuthGate` → `SignInForm` | Shows admin login |

## Risk Assessment

- **Low risk:** Admin and client auth are already visually separate (different pages, different branding)
- **No role system:** Any authenticated user can access both `/client` and `/admin` routes
- **No client login at `/client/login`:** Currently redirects to `/goclear/login`
- **No preview route:** No way to view client portal without auth

## Files to Update

| File | Change |
|------|--------|
| `src/app/App.tsx` | Add `/client/login` and `/client/preview` routes, fix `ClientPortalGate` redirect |
| `src/pages/client/ClientLoginPage.tsx` | NEW — client-facing login page |
| `src/pages/client/ClientPortalRoot.jsx` | No change needed (already works) |

## What Already Works

- GoClear login page is client-branded ("Client Login", "GoClear portal")
- Supabase auth is functional (sign-in, sign-out, session persistence)
- Client portal renders behind auth gate
- Admin auth is separate from client redirect target
