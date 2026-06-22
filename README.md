# Nexus OS v2

A clean rebuild of Nexus around three goals — **Communication · Monetization · Automation** —
with **Supabase as the single source of truth**. No file/report/manifest-as-state, no
duplicate schedulers, no hidden automation. Every meaningful action writes to `nexus_events`.

## Stack
- **Frontend:** Vite + React + TypeScript (7-tab Nexus OS dashboard)
- **State/ledger:** Supabase (Postgres) — `nexus_events` + 12 supporting tables
- **Jobs:** one job runner (`agent_jobs`) + one scheduler (added later)
- **Comms:** guarded Telegram / War Room (`telegram_messages` + send guard, Day 2)

## Quick start
```bash
npm install
cp .env.example .env          # fill in Supabase URL + anon key (frontend)
npm run dev                    # dashboard (shows setup state until Supabase is configured)
npm run build                  # type-check + production build
```

Apply the schema in Supabase (SQL editor or CLI):
```
supabase/migrations/0001_nexus_os_v2_core.sql
supabase/seed/0001_social_accounts.sql
```

Seed the Day 1 proof (server-side, needs the service-role key in `.env`):
```bash
python3 scripts/seed_day1_event.py
```

## Principles
- **Supabase is state.** The UI and reports are read-only projections.
- **One scheduler, one runner.** No duplicate launchctl/cron/systemd jobs.
- **Secrets never in Git.** Only `.env` (gitignored) + deployment secret stores. Account IDs
  may be committed; tokens may not.
- **Honest status.** Capabilities report `ok / partial / failed / rebuild_needed` from real
  `system_health` rows — never fake data.

## Docs
- `docs/architecture/NEXUS_OS_V2_ARCHITECTURE.md`
- `docs/operations/ENVIRONMENT.md`
- `docs/operations/SUPABASE_SETUP.md`
- `docs/operations/DEPLOYMENT.md`
- `docs/operations/SOCIAL_MIGRATION.md`
- `docs/operations/SCHEDULER_POLICY.md`

## Status
**Day 1:** repo + Supabase ledger schema + dashboard shell + Day 1 proof seed. No publishing,
no trading, no secrets committed.
