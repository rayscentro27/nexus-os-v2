# Nexus launchd — Existing Audit

**Generated**: 2026-07-05
**Phase**: D

## Summary

| Field | Value |
|-------|-------|
| Total launchd jobs (all) | 28+ |
| Nexus v2 jobs found | 3 active + 2 disabled |
| Original Nexus jobs | ~20 (still loaded) |
| Plist location | ~/Library/LaunchAgents/ |

## Nexus v2 Jobs (Current Repo)

| Job | Label | Schedule | Status | Last Run |
|-----|-------|----------|--------|----------|
| daily-operating | com.nexus.daily-operating | Daily 08:00 | EXISTS_NOT_LOADED (pid=-, exit=0) | Jul 4 08:03 |
| evening-closeout | com.nexus.evening-closeout | Daily 18:00 | EXISTS_NOT_LOADED (pid=-, exit=0) | Jul 4 18:00 |
| continuous-ops-daily | com.nexus.continuous-ops-daily | Every 30min | EXISTS_NOT_LOADED (pid=-, exit=0) | Unknown |

## Plist Details

### com.nexus.daily-operating.plist
- Label: com.nexus.daily-operating
- Program: /usr/local/bin/python3 scripts/activation/run_daily_operating_cycle.py --json --scheduled
- Schedule: StartCalendarInterval Hour=8 Minute=0
- RunAtLoad: false
- KeepAlive: false
- Logs: reports/runtime/daily_operating_launchd.log

### com.nexus.evening-closeout.plist
- Label: com.nexus.evening-closeout
- Program: /usr/local/bin/python3 scripts/activation/run_evening_closeout_cycle.py --json --scheduled
- Schedule: StartCalendarInterval Hour=18 Minute=0
- RunAtLoad: false
- KeepAlive: false
- Logs: reports/runtime/evening_closeout_launchd.log

### com.nexus.continuous-ops-daily.plist
- Label: com.nexus.continuous-ops-daily
- Schedule: Every 30 minutes (inferred from name)
- RunAtLoad: false
- KeepAlive: false

## Original Nexus Jobs Still Loaded (NOT from nexus-os-v2)

| Job | Exit Code | Notes |
|-----|-----------|-------|
| com.nexus.trading-engine | 0 | Active, pid=540 |
| com.nexus.signal-router | 0 | Active, pid=532 |
| com.nexus.research-worker | 0 | Active, pid=538 |
| com.nexus.research-signal-bridge | 0 | Active, pid=550 |
| com.nexus.mac-mini-worker | 0 | Active, pid=554 |
| com.nexus.signal-review | 0 | Active, pid=536 |
| com.nexus.ollama | 0 | Active, pid=535 |
| com.nexus.auto-executor | 0 | Active, pid=559 |
| com.nexus.orchestrator | 0 | Active, pid=534 |
| com.nexus.tournament | 0 | Active, pid=573 |
| ai.nexus.control-center | 0 | Active, pid=571 |
| com.raymonddavis.nexus.scheduler | 0 | Active, pid=564 |
| com.raymonddavis.nexus.dashboard | 0 | Active, pid=542 |

## Disabled/Stub Jobs

| Job | Status | Notes |
|-----|--------|-------|
| com.nexus.demo-trading-loop | Not loaded | |
| com.nexus.strategy-lab | Not loaded | |
| com.nexus.monitoring-worker | Not loaded | |
| com.nexus.ops-control-worker | Not loaded | |
| com.nexus.autonomy-worker | Not loaded | |
| com.nexus.youtube-channel-poller | Not loaded | |
| com.nexus.coordination-worker | Not loaded | |

## Desired Jobs for Nexus OS v2

| Desired Job | Status | Classification |
|-------------|--------|----------------|
| Active operator (hourly) | Not found | MISSING |
| Daily monitor (morning) | EXISTS_NOT_LOADED | com.nexus.daily-operating |
| Recovery check (every few hours) | Not found | MISSING |
| Telegram bridge (bounded) | Not found (com.raymonddavis.nexus.telegram.plist exists but not in v2) | EXISTS_NOT_LOADED |

## Existing Plist Files for Desired Jobs

- `com.raymonddavis.nexus.telegram.plist` — EXISTS but not inspected (may be from original Nexus)
- `com.raymonddavis.nexus.scheduler.plist` — EXISTS, loaded as com.raymonddavis.nexus.scheduler

## Recommendations

1. **Daily monitor**: Already exists as `com.nexus.daily-operating` — just needs `launchctl load`
2. **Evening closeout**: Already exists as `com.nexus.evening-closeout` — just needs `launchctl load`
3. **Active operator**: No existing plist — create new one pointing to `scripts/operations/nexus_active_operator_runner.py --once`
4. **Recovery check**: No existing plist — create new one pointing to `scripts/operations/nexus_recovery_check.py`
5. **Telegram bridge**: `com.raymonddavis.nexus.telegram.plist` exists — inspect before creating new

## Install Commands (DO NOT RUN WITHOUT RAY APPROVAL)

```bash
# Load existing daily/evening jobs
launchctl load ~/Library/LaunchAgents/com.nexus.daily-operating.plist
launchctl load ~/Library/LaunchAgents/com.nexus.evening-closeout.plist

# Create new active operator job
cat > ~/Library/LaunchAgents/com.nexus.active-operator.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nexus.active-operator</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/raymonddavis/nexus-os-v2/scripts/operations/nexus_active_operator_runner.py</string>
        <string>--once</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/active_operator_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/active_operator_launchd_error.log</string>
</dict>
</plist>
PLIST

# Create new recovery check job
cat > ~/Library/LaunchAgents/com.nexus.recovery-check.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nexus.recovery-check</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/raymonddavis/nexus-os-v2/scripts/operations/nexus_recovery_check.py</string>
    </array>
    <key>StartInterval</key>
    <integer>10800</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/recovery_check_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/recovery_check_launchd_error.log</string>
</dict>
</plist>
PLIST

# Load new jobs
launchctl load ~/Library/LaunchAgents/com.nexus.active-operator.plist
launchctl load ~/Library/LaunchAgents/com.nexus.recovery-check.plist
```

## Final Status

**LAUNCHD_EXISTS_NEEDS_LOAD** — 3 Nexus v2 jobs exist as plists but are not loaded. Daily monitor and evening closeout are ready to load. Active operator and recovery check need new plists created.
