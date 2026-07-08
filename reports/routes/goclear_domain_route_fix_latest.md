# GoClear Domain Route Fix — Report

**Date:** 2026-07-07
**Starting commit:** ae8487d

## Problem
`goclearonline.cc/` showed admin login because the catch-all in `App.tsx:64` rendered `AuthGate` → `NexusAdminUI` for any unmatched route, including `/`.

## Root Cause
`/` was not in `GOCLEAR_ROUTES` array (line 23), so the `isGoClear` check failed, and the code fell through to the admin catch-all.

## Fix Applied

### `src/app/App.tsx`
- `/` now renders `GoClearLandingPage` (public homepage)
- Added `/admin` route prefix with `AuthGate` → `NexusAdminUI`
- Catch-all now redirects to `/` instead of showing admin login
- `GoClearScrollUnlock` now applies to `/` in addition to `/goclear` routes

### `src/pages/goclear/GoClearPublicPages.tsx`
- Logo link changed from `/goclear` to `/`
- Header nav links changed from `/goclear#section` to `/#section`
- Footer nav links changed from `/goclear#section` to `/#section`

## Final Route Map

| Path | Behavior | Auth Required |
|------|----------|---------------|
| `/` | GoClear landing page (public) | No |
| `/goclear` | GoClear landing page (alias) | No |
| `/goclear/login` | GoClear client login | No |
| `/goclear/signup` | GoClear signup | No |
| `/goclear/pricing` | GoClear pricing | No |
| `/client` | Client portal | Yes (Supabase) |
| `/client/dashboard` | Client dashboard | Yes (Supabase) |
| `/admin` | Admin login | Yes (Supabase) |
| `/admin/login` | Admin login | Yes (Supabase) |
| `/admin/command-center` | Admin command center | Yes (Supabase) |
| `/update-password` | Password recovery | No |
| `/*` (unknown) | Redirects to `/` | No |

## Netlify SPA Fallback
Already correctly configured:
```toml
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```
Static files (`goclear-apex-readiness.html`, `got-funding/`) served directly before fallback.

## Files Changed
- `src/app/App.tsx` — routing logic
- `src/pages/goclear/GoClearPublicPages.tsx` — nav links

## Test URLs
- `goclearonline.cc/` → GoClear landing page ✓
- `goclearonline.cc/goclear` → GoClear landing page ✓
- `goclearonline.cc/goclear/login` → GoClear client login ✓
- `goclearonline.cc/goclear/signup` → GoClear signup ✓
- `goclearonline.cc/goclear/pricing` → GoClear pricing ✓
- `goclearonline.cc/client` → Client auth gate → redirect to `/goclear/login` ✓
- `goclearonline.cc/client/dashboard` → Client auth gate → redirect to `/goclear/login` ✓
- `goclearonline.cc/admin` → Admin login (AuthGate) ✓
- `goclearonline.cc/admin/command-center` → Admin login (AuthGate) ✓
- SPA refresh on `/client/dashboard` → works (SPA fallback) ✓
- SPA refresh on `/admin` → works (SPA fallback) ✓

## Demo/Mock Data Status
- Client portal: all demo/mock (no live claims)
- Admin: reads from `data/` runtime files (no live external actions)
- Landing page: static content (no live data)

## Remaining Blockers
- Client portal still uses mock `clientPortalData` — needs Supabase queries
- No real credit bureau connection
- No live funding approval
- No real payment processing
- Hermes guidance is static, not engine-driven
