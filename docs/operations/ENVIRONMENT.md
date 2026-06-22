# Environment

Real values go ONLY in `.env` (gitignored). `.env.example` ships empty placeholders.

## Who gets what
| Var | Where it's used | Exposed to browser? |
|---|---|---|
| `VITE_SUPABASE_URL` | frontend | **yes** (safe) |
| `VITE_SUPABASE_ANON_KEY` | frontend | **yes** (safe, RLS-protected) |
| `SUPABASE_SERVICE_ROLE_KEY` | server / job runner / scripts | **never** |
| `META_PAGE_ID`, `META_INSTAGRAM_ACCOUNT_ID` | server | account IDs are public-safe |
| `META_PAGE_ACCESS_TOKEN` | server only | **never** |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | server only | **never** |
| `OANDA_API_KEY`, `OANDA_ACCOUNT_ID` | server only | **never** |
| `HERMES_GATEWAY_URL`, `HERMES_API_KEY` | server / function | **never** key |

## Rules
- The frontend bundle may reference **only** `VITE_*` vars. Anything else must stay server-side.
- The service-role key bypasses RLS — it must never reach the browser or the repo.
- **Account IDs can be committed; tokens cannot.** Tokens live in `.env` and deployment secret
  stores (Netlify env, etc.).
- Never embed secrets in launchd/cron/systemd unit files — load them from `.env` at runtime.
- Secret-scan every commit; never `git add .` / `git add -A`.
