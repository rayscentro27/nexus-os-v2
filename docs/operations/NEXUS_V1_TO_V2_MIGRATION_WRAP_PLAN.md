# Nexus v1 → v2 Migration / Wrap Plan (no changes made — plan only)

Derived from `NEXUS_MACMINI_PROCESS_SCHEDULE_AUDIT.md`. Goal: integrate v1's already-running
automation into v2 **without duplicating it, breaking it, or exposing action-capable workers to the
UI**. Nothing here is implemented in this audit.

## 1. Leave UNTOUCHED (keep running as-is)
- All trading workers: `nexus_trading_engine.py`, `auto_executor.py`, `tournament_service.py`,
  `signal-router`, `signal-review`, `strategy-lab` (**trade-capable — do not touch**).
- `mac-mini-worker.js` (684) — the worker bridge.
- Hermes gateway (698) + `hermes-gateway-adapter.js` + cloudflared tunnels.
- v1 cron workers (autonomy/monitoring/coordination/readiness/memory/optimization) and
  `operations_center/scheduler.py` — keep; do not start a competing v2 scheduler.

## 2. WRAP into v2 (read v1, write v2) — first targets
1. **YouTube/research capture** — the v2 wrapper (`scripts/intake/run_existing_youtube_monitor.py`)
   already references the same `research-engine/collector.py`. Next: let it run one approved capture
   into **v2** tables (`research_sources`/`transcript_reviews`/`nexus_events`) instead of the v1
   `research` table. **This is the #1 wrap target.**
2. **Research → opportunity mirroring** — mirror v1 research-worker / monetization-research outputs
   into v2 `monetization_opportunities` / `improvement_candidates` (read-only mirror, no v1 change).
3. **Process status read-out** — a read-only "v1 fleet status" reader (parses `launchctl list` +
   cron + key PIDs) surfaced in a v2 Ops tab. Status only; never controls.

## 3. RETIRE later (after v2 parity + Ray approval)
- v1 social publishing pipeline (v2 has the gated FB one-post path).
- Duplicate email senders (pick one of v1 email-pipeline vs v2 Resend).
- v1 `dashboard.py` / control-center once the v2 React dashboard covers it.

## 4. v1 schedules that DUPLICATE v2 (do not double-run)
- `youtube-channel-poller` (v1) vs the v2 monitor wrapper → **do not load the v2 launchd schedule**
  until the v1 poller is retired or scoped, or they will both poll. Converge to one.
- `operations_center/scheduler.py` + cron `source_scheduling.scheduler_worker` vs any future v2
  scheduler → one scheduler on one host only.
- v1 monetization-research vs v2 canonical scoring → converge on the v2 canonical model.

## 5. v1 outputs to MIRROR into v2 Supabase
- Research sources/reviews → `research_sources`, `transcript_reviews`.
- Monetization scores → `monetization_opportunities`.
- System/ops health + proof → `nexus_events`, `system_health`.
- (Mirror = additive copy into v2; never write back to v1 `research`.)

## 6. v2 UI tabs that should show v1 process status (read-only)
- **Ops & Improvements**: v1 fleet status (launchd/cron/PIDs, last-exit, failing jobs like
  `continuous-ops-daily` exit 1, `cf.hermes.gateway` exit 11).
- **Trading Lab**: v1 trading worker status **read-only** (running/demo) — never controls.
- **Source Intake & Review**: research/youtube capture results.

## 7. Commands to add to a future v2 command registry (all read-only first)
- `v1.fleet.status` (launchctl/cron/PID snapshot), `v1.research.last` (latest research-engine run),
  `v1.trading.posture` (demo/live flag read-out), `youtube.monitor.dryrun`,
  `youtube.monitor.capture` (approved-only, gated). Action commands stay approval-gated.

## 8. Must NEVER be exposed to UI without explicit approval gating
- `auto_executor.py` / `nexus_trading_engine.py` (real trade capability).
- Any social publish / email send / deploy / scheduler load/unload.
- launchd load/unload and process start/stop controls.

## Exact next recommended action
**Run ONE approved YouTube capture into v2 tables** (the #1 wrap target) using the gated wrapper —
this proves the v1→v2 research bridge end-to-end without duplicating the v1 poller and without
enabling any schedule. Needs: one Ray-approved public URL. Keep the v1 `youtube-channel-poller`
running but do **not** load the v2 schedule yet (avoid double-polling).
