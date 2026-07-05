# Nexus Existing launchd Jobs — Loaded

**Generated**: 2026-07-05
**Phase**: C

## Jobs Loaded

| Job | Label | Status | PID | Exit |
|-----|-------|--------|-----|------|
| Daily monitor | com.nexus.daily-operating | LOADED_AND_STARTED | 82181 | 0 |
| Evening closeout | com.nexus.evening-closeout | LOADED_AND_STARTED | 82183 | 0 |

## Verification

- Both jobs loaded via `launchctl load`
- Both jobs started via `launchctl start`
- Both completed with exit code 0
- Logs produced in reports/runtime/

## Status

EXISTING_JOBS_LOADED_AND_VERIFIED
