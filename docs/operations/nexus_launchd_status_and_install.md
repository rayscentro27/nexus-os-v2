# Nexus launchd — Status and Install Guide

**Generated**: 2026-07-05

## Current Status

| Job | Label | Plist | Loaded | Schedule |
|-----|-------|-------|--------|----------|
| Daily monitor | com.nexus.daily-operating | ~/Library/LaunchAgents/com.nexus.daily-operating.plist | NO | Daily 08:00 |
| Evening closeout | com.nexus.evening-closeout | ~/Library/LaunchAgents/com.nexus.evening-closeout.plist | NO | Daily 18:00 |
| Continuous loop | com.nexus.continuous-ops-daily | ~/Library/LaunchAgents/com.nexus.continuous-ops-daily.plist | NO | Every 30min |

## Install Commands

### Load Existing Jobs

```bash
launchctl load ~/Library/LaunchAgents/com.nexus.daily-operating.plist
launchctl load ~/Library/LaunchAgents/com.nexus.evening-closeout.plist
launchctl load ~/Library/LaunchAgents/com.nexus.continuous-ops-daily.plist
```

### Create Active Operator Job (Hourly)

```bash
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
    <key>RunAtLoad</key><false/>
    <key>KeepAlive</key><false/>
    <key>StandardOutPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/active_operator_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/active_operator_launchd_error.log</string>
</dict>
</plist>
PLIST
launchctl load ~/Library/LaunchAgents/com.nexus.active-operator.plist
```

### Create Recovery Check Job (Every 3 Hours)

```bash
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
    <key>RunAtLoad</key><false/>
    <key>KeepAlive</key><false/>
    <key>StandardOutPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/recovery_check_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/raymonddavis/nexus-os-v2/reports/runtime/recovery_check_launchd_error.log</string>
</dict>
</plist>
PLIST
launchctl load ~/Library/LaunchAgents/com.nexus.recovery-check.plist
```

## Verify Loaded Jobs

```bash
launchctl list | grep com.nexus
```

## Unload Jobs (if needed)

```bash
launchctl unload ~/Library/LaunchAgents/com.nexus.active-operator.plist
launchctl unload ~/Library/LaunchAgents/com.nexus.recovery-check.plist
launchctl unload ~/Library/LaunchAgents/com.nexus.daily-operating.plist
launchctl unload ~/Library/LaunchAgents/com.nexus.evening-closeout.plist
```
