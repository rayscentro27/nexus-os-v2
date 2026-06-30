# Safe Schedule Install Plan

Generated: 2026-06-30T02:21:32.404828+00:00

- ok: true
- status: launchd_plan_ready_not_installed
- plist_path: ops/launchd/com.nexus.continuous-loop.plist
- plist_valid: true
- installed: false
- safe_internal_only: true
- external_actions_enabled: false
- permanent_daemon_started: false
- approval_required: true
- external_action_performed: false

## Install commands

- mkdir -p ~/Library/LaunchAgents
- cp ~/nexus-os-v2/ops/launchd/com.nexus.continuous-loop.plist ~/Library/LaunchAgents/
- launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.nexus.continuous-loop.plist
- launchctl kickstart gui/$UID/com.nexus.continuous-loop

## Rollback commands

- launchctl bootout gui/$UID ~/Library/LaunchAgents/com.nexus.continuous-loop.plist
- rm ~/Library/LaunchAgents/com.nexus.continuous-loop.plist
