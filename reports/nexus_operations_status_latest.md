# Nexus Operations Status

Checked: 2026-07-01T15:34:38.683589+00:00

## What is real

- Repo `main` at `c290074b9d66`.
- 18 Nexus-related processes had direct `ps` proof.
- 31 Nexus launchd plists were inspected.
- CLI availability was checked without reading credentials.

## What is running

- pid-538
- pid-580
- pid-582
- pid-586
- pid-587
- pid-588
- pid-590
- pid-598
- pid-607
- pid-613
- pid-618
- pid-622
- pid-1135
- pid-1176
- pid-1192
- pid-6514
- pid-43939
- pid-46345

## Installed but not proven running

- ai.nexus.control-center
- ai.nexus.email-pipeline
- com.nexus.auto-executor
- com.nexus.autonomy-worker
- com.nexus.cloudflare-tunnel
- com.nexus.continuous-ops-daily
- com.nexus.coordination-worker
- com.nexus.daily-operating
- com.nexus.demo-trading-loop
- com.nexus.evening-closeout
- com.nexus.hermes-status
- com.nexus.mac-mini-worker
- com.nexus.monetization-research
- com.nexus.monitoring-worker
- com.nexus.ollama
- com.nexus.ops-control-worker
- com.nexus.orchestrator
- com.nexus.research-signal-bridge
- com.nexus.research-worker
- com.nexus.signal-review
- com.nexus.signal-router
- com.nexus.strategy-lab
- com.nexus.tournament
- com.nexus.trading-engine
- com.nexus.youtube-channel-poller
- com.raymonddavis.nexus.control-center
- com.raymonddavis.nexus.dashboard
- com.raymonddavis.nexus.hermes-mobile
- com.raymonddavis.nexus
- com.raymonddavis.nexus.scheduler
- com.raymonddavis.nexus.telegram

## Static or report-only

- Package scripts, report timestamps, cached YouTube metadata, and Supabase-ready files are evidence snapshots, not process proof.

## Broken or unproven

- YouTube research: **not_proven_live**. YouTube tooling and cached metadata exist, but live operation requires concurrent process/log/write proof.
- Token/rate limits: unknown; no values were guessed.

## What Hermes can report

- Git/repo state, safe process inventory, launchd inventory, CLI availability, env-name presence, report freshness, and YouTube proof status.

## What needs Ray approval

- Starting/stopping/restarting jobs, deployment, Supabase writes/seeds, external research, sends, publishing, charges, disputes, and trading.

Safe refresh command: `python3 scripts/ops/collect_nexus_operations_status.py`
