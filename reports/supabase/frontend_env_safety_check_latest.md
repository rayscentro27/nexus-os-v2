# Frontend Environment Safety Check

**Date**: 2026-07-06

---

## Frontend Environment Variables

### ALLOWED (confirmed in source)

| Variable | Used In | Purpose |
|----------|---------|---------|
| `VITE_SUPABASE_URL` | `src/lib/supabaseClient.ts` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | `src/lib/supabaseClient.ts` | Supabase anonymous/public key |

### NOT EXPOSED (confirmed NOT in any frontend source)

| Variable | Status |
|----------|--------|
| `SUPABASE_SERVICE_ROLE_KEY` | NOT in any `src/` file |
| `STRIPE_SECRET_KEY` | NOT in any `src/` file |
| `TELEGRAM_BOT_TOKEN` | NOT in any `src/` file |
| `RESEND_API_KEY` | NOT in any `src/` file |
| `OANDA_API_KEY` | NOT in any `src/` file |
| `META_PAGE_ACCESS_TOKEN` | NOT in any `src/` file |
| `YOUTUBE_API_KEY` | NOT in any `src/` file |
| `OPENROUTER_API_KEY` | NOT in any `src/` file |

## Verification Method

1. Searched all `src/**` files for `SUPABASE_SERVICE_ROLE`, `STRIPE_SECRET`, `TELEGRAM_BOT`, `RESEND_API`, `OANDA_API`, `META_PAGE`, `YOUTUBE_API`, `OPENROUTER_API`
2. Searched all `src/**` files for generic `API_KEY`, `SECRET`, `password` patterns
3. Confirmed `supabaseClient.ts` only imports `VITE_*` prefixed env vars
4. Confirmed `.env` file is in `.gitignore` (not committed)

## Auth Security Notes

- `supabaseClient.ts` creates client with `persistSession: true` (localStorage)
- `autoRefreshToken: true` keeps session alive
- `detectSessionInUrl: true` handles OAuth callbacks
- Service role key is used ONLY in server-side scripts (`scripts/supabase/`)
- `authHelpers.ts` uses `supabase.auth` methods only (no service role)

## Status: PASS

No private API keys or secrets are exposed to the frontend.
