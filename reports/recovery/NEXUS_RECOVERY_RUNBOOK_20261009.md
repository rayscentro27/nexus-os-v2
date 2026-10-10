# Nexus Recovery Runbook — 2026-10-09

## A. After a Mac crash or reboot

1. Log in normally. Do not open legacy launchers or run PM2 resurrection.
2. Keep Nexus safe mode active. Do not start workers or certification.
3. Run the read-only check below from Terminal.

## B–H. Verify safe mode and baseline

Run:

```sh
cd /Users/raymonddavis/nexus-os-v2-canonical
./.venv-agent-platform/bin/python3 scripts/systems/verify_safe_recovery.py
```

`safe_boot_state=YES` verifies the canonical checkout/runtime, pinned registries,
disabled scheduler/dispatcher/operator state, no loaded Nexus LaunchAgents,
no Nexus executor processes, the historical-request eligibility gate, retained
legacy credit queue with no autonomous consumer, and a bounded read-only
Supabase `SELECT 1`. It prints sanitized metadata only and does not change state.
If Supabase is temporarily unreachable, run with `--skip-supabase` only to
diagnose local recovery; this does not certify Supabase connectivity.

## I. Escalation rules

- If the check exits nonzero, keep Nexus OFF. Preserve its JSON stdout and
  investigate the named failing check before any activation.
- Do not manually load a Nexus plist, run a scheduler/dispatcher script, claim
  a job, or run recovery against production queues.
- Root-cron inspection may require an administrator shell. The latest audit
  verified no root crontab; if that evidence changes, refresh it before
  activation.
- Netlify production metadata and Meta revocation remain production/security
  follow-ups; they do not authorize local autonomous execution.

## J. Conditions before staged activation

Require a passing recovery report, unchanged provider/secret/environment
registry hashes, clean local drift, historical replay protection, no legacy
autostart executor, and a separate approved staged-activation plan. This
runbook does not enable the scheduler, dispatcher, workers, browser automation,
or certification.

## Current frozen state

- Scheduler and dispatcher: OFF; definitions have `RunAtLoad=false` and
  `KeepAlive=false`; all 28 saved Nexus plist definitions are explicitly
  disabled and have rollback metadata under `reports/recovery/evidence/`.
- Old continuous kernel, active operator, PM2 workflow executors, legacy
  Telegram pollers, browser automation, and heavy workers: OFF.
- Historical task requests: 636 classified; dispatcher eligibility requires
  explicit approved `CURRENT_V2_MIGRATED` metadata.
- Legacy credit queue: 25 historical rows preserved; upload trigger uses the
  durable queue; the legacy queue consumer is non-autonomous.
- Meta's old exposed credential: locally quarantined; provider-side revocation
  remains a human action.
- Netlify remains a production-only blocker; no production deployment is part
  of recovery.
