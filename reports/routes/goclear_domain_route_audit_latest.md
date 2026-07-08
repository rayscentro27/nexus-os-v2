# GoClear Domain Route Audit

**Date:** 2026-07-07
**Starting commit:** ae8487d

## Root Cause

`src/app/App.tsx:64` — the catch-all fallback renders `AuthGate` → `NexusAdminUI` for ANY unmatched route. Since `/` is not in `GOCLEAR_ROUTES` (line 23), visiting `goclearonline.cc/` hits the default case and shows admin login.

## Current Route Map

| Path | Behavior | File |
|------|----------|------|
| `/` | **Admin login** (WRONG) | `App.tsx:64` catch-all |
| `/goclear` | GoClear landing page | `App.tsx:47` |
| `/goclear/login` | GoClear client login | `App.tsx:50` |
| `/goclear/signup` | GoClear signup | `App.tsx:48` |
| `/goclear/pricing` | GoClear pricing | `App.tsx:49` |
| `/client` | Client portal (auth required) | `App.tsx:58-60` |
| `/client/*` | Client portal (auth required) | `App.tsx:58-60` |
| `/update-password` | Password recovery | `App.tsx:55-56` |
| `/?ui-smoke=1` | Admin UI smoke test (DEV only) | `App.tsx:61-63` |
| `/*` (anything else) | **Admin login** (catch-all) | `App.tsx:64` |

## Why `/` Shows Admin Login

1. Line 40: `path = window.location.pathname.replace(/\/+$/, '') || '/'` → path is `/`
2. Line 41: `GOCLEAR_ROUTES = ['/goclear', '/goclear/signup', '/goclear/login', '/goclear/pricing']` → `/` is NOT in this list
3. Line 43: `if (isGoClear)` → false, skips GoClear pages
4. Lines 55-63: none match `/`
5. Line 64: falls through to `<AuthGate>{...NexusAdminUI...}</AuthGate>` → shows admin sign-in

## Existing Public Landing Page

- `src/pages/goclear/GoClearPublicPages.tsx` — full React landing page (`GoClearLandingPage`)
- `public/goclear-apex-readiness.html` — static HTML fallback (159 lines)
- Currently only accessible at `/goclear`, not at `/`

## Netlify SPA Fallback

```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

SPA fallback is correctly configured. Static files like `goclear-apex-readiness.html` are served directly before the fallback.

## Client Portal Redirect Issue

`App.tsx:17` — `ClientPortalGate` redirects unauthenticated users to `/goclear/login`, which is correct (GoClear client login). This is fine.

## Admin Currently Lives At

- `/` (catch-all) — admin login
- No explicit `/admin` routes exist

## Files to Patch

| File | Change |
|------|--------|
| `src/app/App.tsx` | Make `/` render GoClear landing page; add `/admin` routes; keep `/goclear` working |

## Target Route Map

| Path | Behavior |
|------|----------|
| `/` | GoClear landing page (public) |
| `/goclear` | GoClear landing page (alias) |
| `/goclear/login` | GoClear client login |
| `/goclear/signup` | GoClear signup |
| `/goclear/pricing` | GoClear pricing |
| `/client` | Client portal (auth gate) |
| `/client/dashboard` | Client portal dashboard |
| `/admin` | Admin login |
| `/admin/login` | Admin login |
| `/admin/command-center` | Admin command center |
| `/update-password` | Password recovery |
