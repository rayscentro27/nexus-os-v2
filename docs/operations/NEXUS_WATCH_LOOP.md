# Nexus Watch Loop

Status: scheduler-ready, disabled by default.

## Manual Command

Run one bounded activation pass:

```bash
npm run nexus:watch
```

The command runs `python3 scripts/run_nexus_continuous_operations.py --mode manual`.

## Recommended Schedule

During offer testing, run manually every business morning and once mid-afternoon. Do not run more frequently than hourly until stronger cross-host deduplication is added.

## Scheduler Policy

No scheduler is installed or started by this repo change.

If Ray later approves scheduling, use one scheduler only on one host. Prefer a reversible launchd, cron, or systemd entry that calls `npm run nexus:watch` from the repo root and loads secrets from `.env` or the host secret store.

## Overlap Protection

The watch script takes a nonblocking file lock at:

```text
reports/runtime/nexus_watch.lock
```

If another watch run is already active, the second run exits with `blocked_overlap` and does not start a second activation pass.

## Logs And Reports

Runtime reports are written to:

```text
reports/runtime/nexus_watch_report_latest.md
reports/runtime/nexus_watch_report_latest.json
```

Runtime reports are intentionally ignored by git. Reproducible packages live under:

```text
reports/manual_publish/
```

## Hermes Report Reader

Hermes receives only a safe summary of the latest Watch Report and can also summarize safe `nexus_events` and `system_health` rows. Do not put private customer files, secrets, SSNs, bank docs, credit reports, passwords, reset tokens, or service keys into the report.
