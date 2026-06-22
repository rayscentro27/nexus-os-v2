# Nexus OS v2 — Architecture

Three goals, one ledger. Supabase is the source of truth; the dashboard is a projection.

```
        ┌───────────────────────── Nexus OS dashboard (Vite/React) ─────────────────────────┐
        │ Overview · Communication · Monetization · Automation · Social · Trading · Approvals│
        └──────────────────────────────────▲────────────────────────────────────────────────┘
                                            │ anon key (read)
                              ┌─────────────┴─────────────┐
                              │   Supabase (Postgres)     │   ← single source of truth
                              │   nexus_events + 12 tables│
                              └─────────────▲─────────────┘
                                            │ service role (read/write)
        ┌───────────────────────────────────┴───────────────────────────────────┐
        │  job runner (agent_jobs)   ·   one scheduler   ·   comms (guarded)      │
        └─────────────────────────────────────────────────────────────────────────┘
```

## Tables (see `supabase/migrations/0001_nexus_os_v2_core.sql`)
- `nexus_events` — the ledger / proof log (every action).
- `agent_jobs` — one job runner's work units.
- `approvals` — approve / reject / revise / publish workflow.
- `social_accounts` — connected accounts (IDs + token **env key name**, never the token).
- `social_posts` — one social queue.
- `social_publish_receipts` — token-free publish receipts.
- `creative_assets` — posts, videos, landing copy, newsletter, hooks, scripts.
- `business_opportunities` — monetization pipeline.
- `trading_signals` — research/signals first.
- `demo_trades` — Oanda demo/practice only (Day 6).
- `telegram_messages` — one guarded War Room output record.
- `system_health` — dashboard health cards.
- `settings` — app flags/config.

## Layers
- **A. Event ledger** — append-only `nexus_events`; the state.
- **B. Job runner** — `agent_jobs`; each job reads ledger → works → writes events; `run_lock` idempotency.
- **C. Communication** — Hermes (live or snapshot) + TheChoseone commands + War Room; ALL sends go through the guard and a `telegram_messages` row.
- **D. Monetization** — offers ($97 → $197 → $297), creative, landing, social, leads.
- **E. Automation** — research → creative → publish → trading demo (jobs only).
- **F. Approvals** — `draft → needs_review → approved → published`; no faked approvals, no one-click real publish.
- **G. Scheduler** — exactly one; documented; `run_lock` + ledger `dedup` prevent double-runs.
- **H. Dashboard** — 7 tabs, all projections of the ledger.

## Security
- Frontend: anon key only (`VITE_*`). Service role is server/script-side, never in the browser.
- RLS enabled on all tables; explicit read policies added once the auth model is set.
- Tokens live in env/secret stores; account IDs may be committed.
