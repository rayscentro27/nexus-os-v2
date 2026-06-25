# Nexus Mac Mini — Process / Scheduler / Worker / Automation Audit

- generated_at: 2026-06-25 (read-only audit; nothing started/stopped/killed)
- purpose: truth map of v1/v2 Nexus automation before enabling any new v2 schedules or duplicating v1.

## Headline
**Ray is right — the v1 Mac Mini already runs a large, live automation fleet.** ~15 long-running v1
processes, **33 nexus/hermes launchd plists** (many loaded), and **7 cron jobs** are active. This
includes **scheduled YouTube/research polling** and **trading workers with live-capable flags**.
v2 (`nexus-os-v2`) currently runs **only a Vite dev server + manual `nexus:watch`** — no v2
scheduler/worker. **Do not duplicate v1; wrap/observe it.**

## 1. Repos / folders
| Path | Git | Origin | Class |
|---|---|---|---|
| `~/nexus-os-v2` | repo (main) | rayscentro27/nexus-os-v2 | **v2** (this project) |
| `~/nexus-ai` | repo (main) | rayscentro27/**nexuslive** | **v1 primary** (shares the nexuslive remote) |
| `~/nexus-ai-worker` | not a git repo | — | v1 worker mirror (loose copy) |
| `~/nexuslive` | repo (main) | rayscentro27/nexuslive | v1 web (goclearonline.cc) |
| `~/mac-mini-worker` | not a git repo | — | **Mac Mini worker bridge** (running) |
| `~/.hermes`, `~/.hermes-backup-*` | — | — | Hermes gateway home/backup |
| `~/.vibe-trading`, `~/nexus-ai/trading-engine` | — | — | trading automation |
| `~/nexus-claw3d`, `~/nexus-mobile`, `~/nexus-oracle-api`, `~/nexus-ai-council-sandbox` | mixed | — | adjuncts/archives |

## 2. Running processes (long-running; none touched)
| PID | Command | Owner | Role | Action-capable? | Writes DB? | Recommendation |
|---|---|---|---|---|---|---|
| 661 | `nexus-ai/signal-router/tradingview_router.py` | v1 | trading signal router | reads signals | likely | leave alone; document |
| 663 | `nexus-ai/services/nexus-orchestrator/index.js` | v1 | orchestrator | yes (coordinates) | likely | document; investigate |
| 665 | `ollama serve` | shared | local LLM | no | no | keep (v2 may use) |
| 668 | `nexus-ai/services/nexus-research-worker/index.js` | v1 | research worker | research writes | likely | **wrap into v2 later** |
| 671 | `nexus-ai/trading-engine/nexus_trading_engine.py` | v1 | trading engine | **trade-capable** | yes | **do not touch; review** |
| 673 | `nexus-ai/dashboard.py` | v1 | v1 dashboard | read/report | reads | leave alone |
| 680 | `nexus-ai/research_intelligence/research_signal_bridge.py` | v1 | research→signal bridge | yes | likely | document; wrap later |
| 684 | `mac-mini-worker/src/mac-mini-worker.js` | worker | **Mac Mini worker bridge** | yes (executes tasks) | likely | leave alone; document |
| 689 | `nexus-ai/trading-engine/auto_executor.py` | v1 | **auto executor** | **trade-capable** | yes | **do not touch; review posture** |
| 694 | `nexus-ai/operations_center/scheduler.py` | v1 | ops scheduler | orchestrator | yes | leave alone; document |
| 698 | `.hermes/hermes-agent/venv … hermes_cli gateway run` | hermes | Hermes gateway | sends/acts | yes | leave alone (live Hermes) |
| 699, 61337 | `cloudflared tunnel …` | shared | tunnels (Hermes gateway) | network | no | leave alone |
| 700 | `nexus-ai/trading-engine/tournament_service.py` | v1 | strategy tournament | backtest | yes | leave alone; review |
| 4358 | `server/hermes-gateway-adapter.js` | hermes | gateway adapter | yes | maybe | leave alone |
| 7002, 44496 | `nexus-os-v2 … vite` | **v2** | dev server(s) | no | no | dev only (two instances — can stop one) |

(Hermes Agent.app desktop + Antigravity/editor helpers excluded — not Nexus automation.)

## 3. launchd jobs (33 nexus/hermes plists; key ones)
Loaded `com.nexus.*` / `com.raymonddavis.nexus.*` include: `trading-engine`, `auto-executor`,
`tournament`, `signal-router`, `signal-review`, `strategy-lab` (**trading**); `research-worker`,
`research-signal-bridge`, `monetization-research`, **`youtube-channel-poller`** (**research/YouTube**);
`orchestrator`, `scheduler`, `coordination-worker`, `monitoring-worker`, `ops-control-worker`,
`continuous-ops-daily` (**last exit = 1, FAILING**), `control-center`, `dashboard`, `mac-mini-worker`,
`ollama`, `cloudflare-tunnel`, `email-pipeline`; `ai.hermes.gateway`, `cf.hermes.gateway`
(**last exit = 11, FAILING**), `nexusd`.

**YouTube scheduler confirmed:** `com.nexus.youtube-channel-poller` runs
`/bin/bash ~/nexus-ai/research-engine/run_research.sh` (the yt-dlp collector). So v1 already polls
YouTube channels on a schedule and writes to the v1 `research` table.

Action-risk: trading jobs = **trade-capable**; research/youtube = DB-writing; gateway = sends/acts.

## 4. cron jobs (7 — all v1 `~/nexus-ai`)
| Cadence | Worker |
|---|---|
| every 1 min | `autonomy.autonomy_worker` |
| every 5 min | `monitoring.monitoring_worker` |
| every 5 min | `source_scheduling.scheduler_worker` (**source/research scheduler**) |
| every 15 min | `coordination.coordination_worker` |
| every 1 h | `readiness.readiness_worker` |
| every 2 h | `memory_engine.memory_worker` |
| every 6 h | `optimization_engine.optimization_worker` |

tmux: none. screen: none.

## 5. v1 research / YouTube automation
- **`~/nexus-ai/research-engine/`** — `run_research.sh` (launchd `youtube-channel-poller`), `collector.py`
  (yt-dlp transcript capture, channel allowlist `channels/trading_channels.json`, `MAX_VIDEOS=3`),
  `summarize.py` (**external AI**), `strategy_extractor/ranker.py` (trading focus), `supabase_store.py`
  (writes v1 `research` table, dedup by title). Output: `./transcripts` files + v1 Supabase.
- **`~/nexus-ai/services/nexus-research-worker/`** (Node, PID 668) + `research_intelligence/`
  (`research_signal_bridge.py`, PID 680) — turn research into signals/opportunities.
- **`source_scheduling.scheduler_worker`** (cron, 5 min) — schedules source ingestion.
- Produces opportunity scores + **trading signals** (trading-oriented). Dedup by title. Calls external
  AI in summarize.
- **Safely wrappable into v2?** Yes — the collector (yt-dlp, bounded, allowlisted) is the same one the
  v2 wrapper already references. Missing for v2: write to **v2** tables (not v1 `research`), GoClear/
  credit-funding categories (v2 canonical model), and Ray-approved v2 source allowlist.

## 6. v1 trading automation (NOT executed; names/flags only)
- Processes: `nexus_trading_engine.py` (671), `auto_executor.py` (689), `tournament_service.py` (700),
  `signal-router` (661), plus `signal-review`, `strategy-lab` launchd jobs.
- Flag-name scan of `trading-engine/*.py`: `DRY_RUN` ×12, `demo/DEMO` ×26, `practice/PRACTICE` ×4,
  **`live_trading/LIVE_TRADING` ×9**. → demo/dry-run posture is present, **but live-trading code paths
  exist**. `auto_executor` is **action-capable**.
- **Real broker order capability:** plausibly present (live_trading flags + auto_executor). Cannot
  confirm current demo-vs-live without deeper inspection, which this audit does not do.
- **v2 controls it?** No. **Recommendation:** do not touch; flag `auto_executor` for a focused
  posture review before relying on it. v2 trading remains demo/paper-only and read-only.

## 7. v1 ↔ v2 overlap
| Capability | v1 | v2 | Running today | Scheduled | Writes Supabase | Reports | In v2 UI | Risk | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| Research / YouTube monitor | research-engine + research-worker + youtube-poller | wrapper (dry-run) | **v1 yes** | **v1 yes** | v1 → v1 `research` | yes | partial | med | **wrap v1 into v2** (write v2 tables) |
| Transcript review | research_intelligence | `transcript_reviews` + wrapper | v1 yes | v1 yes | both | yes | yes | low | migrate to v2 |
| Monetization scoring | monetization-research | canonical v1 model | v1 yes | v1 yes | v1 | yes | yes | low | migrate to v2 |
| Creative generation | content_employee | Creative Studio | v1 maybe | — | v1 | yes | yes | low | migrate to v2 |
| Social publishing | v1 pipeline | gated FB one-post | gated | no | v2 | yes | yes | **high** | keep v2 gated; retire v1 publish later |
| Resend / email | email-pipeline | nexus:watch newsletter | v1 + v2 | v1 yes | v2 | yes | partial | med | dedupe; pick one sender |
| Oanda / demo trading | trading-engine + auto_executor | demo display only | **v1 yes** | v1 yes | v1 | yes | read-only | **high** | leave untouched; review posture |
| Strategy backtest / tournament | tournament_service, strategy-lab | Trading Lab (display) | v1 yes | v1 yes | v1 | yes | read-only | med | document; migrate later |
| Hermes chat / advisor | hermes gateway (698) | Edge Function `hermes-chat` | both | n/a | v2 | yes | yes | med | keep both; converge later |
| Telegram / ops alerts | ops-control / monitoring | none | v1 yes | v1 yes | v1 | yes | no | med | document; wrap later |
| Scheduler / continuous ops | operations_center/scheduler + cron | bounded `nexus:overnight` (manual) | v1 yes | v1 yes | v1 | yes | no | med | **do not duplicate**; converge |
| Mac Mini worker bridge | mac-mini-worker.js (684) | none | **yes** | n/a | likely | maybe | no | med | leave alone; expose status read-only later |
| Reports / proof events | various | nexus_events | both | — | both | yes | yes | low | standardize on v2 nexus_events |
| Dashboard / control center | dashboard.py (673), control-center | v2 React app | both | n/a | reads | — | yes | low | migrate to v2 |

## 8. Health flags
- `com.nexus.continuous-ops-daily` last exit **1** (failing). `cf.hermes.gateway` last exit **11**
  (failing). Worth Ray's attention but **out of scope to fix** in this read-only audit.

See `NEXUS_V1_TO_V2_MIGRATION_WRAP_PLAN.md` for the wrap/migration plan.
