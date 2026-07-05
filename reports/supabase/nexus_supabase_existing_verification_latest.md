# Nexus Supabase — Existing Systems Verification

**Generated**: 2026-07-05
**Phase**: C

## Summary

| Field | Value |
|-------|-------|
| Env Keys Present | 4/4 (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY) |
| Client Code | `src/lib/supabaseClient.ts` — COMPLETE |
| Edge Functions | `supabase/functions/hermes-chat/`, `hermes-search/`, `_shared/firewall.ts` — COMPLETE |
| Migrations | 11+ SQL files, mature schema — COMPLETE |
| Frontend Service Layer | `src/services/db.ts` — COMPLETE |
| Scripts | 6 scripts in `scripts/supabase/` — COMPLETE |
| Existing Reports | 6+ reports in `reports/supabase/` — COMPLETE |
| Live Database Call | NOT PERFORMED (approval required) |
| Browser Verification | NOT PERFORMED (env confirmed, live read expected) |

## Env Key Status

| Key | Present | Frontend Safe |
|-----|---------|---------------|
| `VITE_SUPABASE_URL` | YES | YES (browser-safe) |
| `VITE_SUPABASE_ANON_KEY` | YES | YES (browser-safe) |
| `SUPABASE_URL` | YES | Server-only |
| `SUPABASE_SERVICE_ROLE_KEY` | YES | Server-only (NOT in frontend) |

## Client Configuration

- `isSupabaseConfigured`: boolean (not function) — checks VITE_ keys
- Frontend uses VITE_ keys only
- Service role key NOT in frontend code
- Auth/session detection via `isSupabaseConfigured`

## What Already Exists (DO NOT REBUILD)

1. Frontend Supabase client with anon key only
2. Edge functions (hermes-chat, hermes-search, firewall)
3. 11+ migrations defining 24-table schema
4. Database service layer with RLS, session checks
5. Seed data for social accounts
6. Supabase readiness audit script
7. Dry-run insert runner
8. Static data seeding script
9. Live status verification script
10. Browser verification report

## Blockers

1. Ray migration approval (DRAFT_client_portal_core_tables.sql needs renaming + push)
2. Linked Supabase project confirmation
3. Tenant membership seed
4. RLS policy tests
5. Private storage policy
6. Insert execution approval

## What Ray Should Do

1. Open the app in browser
2. Open DevTools → Network tab
3. Navigate to any page that uses Supabase (e.g., client portal)
4. Check if VITE_SUPABASE_URL requests succeed (200) or fail (401/403)
5. If requests succeed: VERIFIED_BROWSER_READS
6. If requests fail with 401: anon key needs regeneration
7. If requests fail with network error: Supabase project may be paused

## Final Status

**ENV_PRESENT_BROWSER_EXPECTED** — All env keys present, client configured, browser verification needed by Ray.
