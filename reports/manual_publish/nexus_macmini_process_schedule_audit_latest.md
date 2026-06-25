# Nexus Mac Mini Process/Schedule Audit — Report

- generated_at: 2026-06-25 · read-only (nothing started/stopped/killed)
- full detail: `docs/operations/NEXUS_MACMINI_PROCESS_SCHEDULE_AUDIT.md`
- plan: `docs/operations/NEXUS_V1_TO_V2_MIGRATION_WRAP_PLAN.md`

## Bottom line
v1 already runs a large live automation fleet: **~15 long-running processes, 33 nexus/hermes launchd
plists, 7 cron jobs.** Includes **scheduled YouTube/research polling** and **trade-capable workers**.
v2 runs only a dev server + manual `nexus:watch`. **Do not duplicate v1 — wrap/observe it.**

## Active automation (summary)
- **Processes (v1):** signal-router, orchestrator, research-worker, trading-engine, dashboard,
  research-signal-bridge, mac-mini-worker (bridge), **auto_executor (trade-capable)**, ops scheduler,
  Hermes gateway, tournament-service, ollama, cloudflared tunnels. **(v2):** vite dev server only.
- **launchd:** trading (trading-engine, auto-executor, tournament, signal-router/review, strategy-lab);
  research (research-worker, research-signal-bridge, monetization-research, **youtube-channel-poller**);
  ops (orchestrator, scheduler, coordination/monitoring/ops-control workers, **continuous-ops-daily =
  FAILING exit 1**, control-center, dashboard, mac-mini-worker, ollama, email-pipeline); hermes
  (`ai.hermes.gateway`, **`cf.hermes.gateway` = FAILING exit 11**).
- **cron (v1, every 1m–6h):** autonomy, monitoring, coordination, readiness, memory, optimization,
  **source_scheduling.scheduler_worker**.
- **tmux/screen:** none.

## Direct answers
- **YouTube/research scheduler already exists?** **YES** — `com.nexus.youtube-channel-poller` →
  `~/nexus-ai/research-engine/run_research.sh` (yt-dlp collector), plus cron source scheduler. Writes
  v1 `research` table.
- **Trading workers running?** **YES** — engine + auto_executor + tournament. Flags show demo/dry-run
  present but **live_trading code paths exist**; auto_executor is action-capable. Not v2-controlled.
- **mac-mini-worker running?** **YES** — PID 684 (`mac-mini-worker/src/mac-mini-worker.js`).

## Safety / risk
- **Action-capable (must stay approval-gated, never UI-exposed raw):** `auto_executor.py`,
  `nexus_trading_engine.py`, social publish, email send, scheduler load/unload, mac-mini-worker exec.
- **Failing jobs (FYI, not fixed here):** `continuous-ops-daily` (exit 1), `cf.hermes.gateway` (exit 11).

## What to wrap into v2 first
1. **YouTube/research capture → v2 tables** (wrapper already references the same collector). #1 target.
2. Mirror v1 research/monetization outputs into v2 Supabase (read-only).
3. Read-only v1 fleet-status reader for the v2 Ops tab.

## What to leave untouched
All trading workers, mac-mini-worker bridge, Hermes gateway + tunnels, v1 cron + ops scheduler.

## Verification
- `npm run build` PASS · `npm run nexus:watch` PASS.
- No scheduler started/stopped, no process killed, no real YouTube capture, no publish/send/trade/
  deploy, no secrets printed, `.env` not committed, v1 jobs untouched.
- approval `13eafcab` = **pending**; Facebook `publish_enabled` = **false**.

## Exact next action
Provide ONE approved public YouTube URL → run the gated wrapper into **v2** tables (proves the v1→v2
research bridge). Keep the v1 poller running; do **not** load the v2 schedule yet (avoid double-poll).
