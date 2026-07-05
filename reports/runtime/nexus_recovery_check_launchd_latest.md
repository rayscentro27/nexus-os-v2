# Nexus Recovery Check — launchd

**Generated**: 2026-07-05
**Phase**: E

## Job Created

| Field | Value |
|-------|-------|
| Label | com.nexus.recovery-check |
| Plist | ~/Library/LaunchAgents/com.nexus.recovery-check.plist |
| Schedule | Every 10800s (3 hours) |
| Command | python3 scripts/operations/nexus_recovery_check.py |
| WorkingDirectory | ~/nexus-os-v2 |
| Logs | logs/launchd/recovery-check.{out,err}.log |
| Loaded | YES |
| Started | YES |
| Completed | YES (exit 0) |

## Verification

- launchctl list shows com.nexus.recovery-check
- Recovery check output: 0 stale, 0 failed, 0 work_orders
- Error log empty

## Status

RECOVERY_CHECK_LOADED_AND_VERIFIED
