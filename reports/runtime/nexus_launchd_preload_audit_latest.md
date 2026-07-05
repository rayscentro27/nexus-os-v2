# Nexus launchd — Pre-Load Audit

**Generated**: 2026-07-05
**Phase**: B

## Plist Inspection Results

### com.nexus.daily-operating.plist
| Field | Value |
|-------|-------|
| Label | com.nexus.daily-operating |
| Script | /usr/local/bin/python3 scripts/activation/run_daily_operating_cycle.py --json --scheduled |
| Repo Path | /Users/raymonddavis/nexus-os-v2 |
| Schedule | Daily 08:00 (StartCalendarInterval) |
| Logs | reports/runtime/daily_operating_launchd.log |
| Loaded | NO (pid=-) |
| Points to nexus-os-v2 | YES |
| Contains Secrets | NO |
| Safe to Load | YES |
| Classification | NEXUS_V2_READY |

### com.nexus.evening-closeout.plist
| Field | Value |
|-------|-------|
| Label | com.nexus.evening-closeout |
| Script | /usr/local/bin/python3 scripts/activation/run_evening_closeout_cycle.py --json --scheduled |
| Repo Path | /Users/raymonddavis/nexus-os-v2 |
| Schedule | Daily 18:00 (StartCalendarInterval) |
| Logs | reports/runtime/evening_closeout_launchd.log |
| Loaded | NO (pid=-) |
| Points to nexus-os-v2 | YES |
| Contains Secrets | NO |
| Safe to Load | YES |
| Classification | NEXUS_V2_READY |

### com.nexus.continuous-ops-daily.plist
| Field | Value |
|-------|-------|
| Label | com.nexus.continuous-ops-daily |
| Script | /usr/local/bin/python3 /Users/raymonddavis/nexus-ai-worker/scripts/run_nexus_continuous_operations.py --mode daily --no-send |
| Repo Path | /Users/raymonddavis/nexus-ai-worker (WRONG) |
| Schedule | Daily 07:00 (StartCalendarInterval) |
| Logs | /Users/raymonddavis/nexus-ai/logs/proof_automation/ |
| Loaded | NO (pid=-) |
| Points to nexus-os-v2 | NO — points to old nexus-ai-worker |
| Contains Secrets | NO |
| Safe to Load | NO — stale path |
| Classification | STALE_ORIGINAL_NEXUS_PATH |

### com.raymonddavis.nexus.telegram.plist
| Field | Value |
|-------|-------|
| Label | com.raymonddavis.nexus.telegram |
| Contains Secrets | YES — bot tokens, OpenRouter key, Hermes gateway key |
| Safe to Load | NO — contains exposed secrets |
| Classification | UNSAFE_SECRETS_EXPOSED |

## Original Nexus Jobs Still Loaded (NOT from nexus-os-v2)

| Job | PID | Exit | Notes |
|-----|-----|------|-------|
| com.nexus.trading-engine | 540 | 0 | Active |
| com.nexus.signal-router | 532 | 0 | Active |
| com.nexus.research-worker | 538 | 0 | Active |
| com.nexus.research-signal-bridge | 550 | 0 | Active |
| com.nexus.mac-mini-worker | 554 | 0 | Active |
| com.nexus.signal-review | 536 | 0 | Active |
| com.nexus.ollama | 535 | 0 | Active |
| com.nexus.auto-executor | 559 | 0 | Active |
| com.nexus.orchestrator | 534 | 0 | Active |
| com.nexus.tournament | 573 | 0 | Active |
| ai.nexus.control-center | 571 | 0 | Active |
| com.raymonddavis.nexus.scheduler | 564 | 0 | Active |
| com.raymonddavis.nexus.dashboard | 542 | 0 | Active |

## Safe to Load

1. com.nexus.daily-operating — YES
2. com.nexus.evening-closeout — YES

## Not Safe to Load

1. com.nexus.continuous-ops-daily — STALE path (nexus-ai-worker)
2. com.raymonddavis.nexus.telegram — SECRETS EXPOSED
