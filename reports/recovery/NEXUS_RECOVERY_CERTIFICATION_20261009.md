# Nexus Recovery Certification — 2026-10-09

**Purpose:** Verify a safe known state after crash, reboot, login, shell restart,
or process loss without activating Nexus.

## Evidence and scope

- The canonical checkout is `/Users/raymonddavis/nexus-os-v2-canonical`, branch
  `main`; local and `origin/main` commit identity was checked at snapshot time.
- The canonical Python environment is `.venv-agent-platform`; imports require
  the repository `scripts/` path, which the recovery verifier adds explicitly.
- Current repository LaunchAgent definitions for scheduler/dispatcher are
  disabled and use the canonical interpreter. The stale `configs/launchd`
  copies were corrected to the canonical interpreter. All 28 Nexus plist
  definitions across `launchd/`, `configs/launchd/`, `ops/launchd/`, and
  `scripts/ops/` now explicitly set `Disabled=true`, `RunAtLoad=false`, and
  `KeepAlive=false`. Their prior launch flags are preserved as sanitized
  rollback metadata. No service was loaded or restarted.
- The recovery command is read-only and uses bounded subprocess timeouts. Its
  optional live health operation is a `SELECT 1`; output is parsed in memory
  and provider/CLI output is never printed.
- Historical task requests remain ineligible unless explicitly migrated with
  reviewed migration metadata. The legacy credit queue remains preserved, and
  has no autonomous consumer.

## Non-destructive recovery simulation

The existing durable-job unit tests create an isolated temporary SQLite queue,
expire a worker lease, verify bounded retry/backoff, reject an early duplicate
claim, reclaim only when due, and ensure only one receipt is written. No live
queue is opened. Safe-recovery tests verify that historical requests without
the migration marker remain ineligible and that scheduler/dispatcher plists
must be canonical and disabled. No provider, browser, model, container, or
business worker is started.

## Certification fields

The machine-readable baseline is `NEXUS_RECOVERY_BASELINE_20261009.json`.
The command below should return `safe_boot_state=YES` and exit 0 for a matching
local state:

```sh
cd /Users/raymonddavis/nexus-os-v2-canonical
./.venv-agent-platform/bin/python3 scripts/systems/verify_safe_recovery.py
```

The baseline status is `PRE_ACTIVATION_RECOVERY_BASELINE`, not certified for
production. This pass does not activate services or resume certification.

## Observed result

- `SAFE_BOOT_STATE=YES`; local recovery drift is zero.
- Read-only Supabase health query returned `READ_ONLY_SELECT_PASS`.
- Nexus executor processes and loaded Nexus LaunchAgents: zero.
- Host: 8 GiB RAM; memory free estimate 78%; load averages approximately
  1.8/1.9/2.1 during the check.
- Focused tests: 28 passed. Coverage includes lease expiry/backoff, atomic
  duplicate-claim prevention, idempotent single receipt, stale lock-file
  metadata, historical task fail-closed eligibility, and recovery verifier
  boundaries. Tests used isolated temporary state.
- Interactive Chrome Remote Desktop remains untouched. No browser automation,
  heavy worker, model, container, provider call, message, or deployment was
  started by this pass.
- The root crontab was previously verified empty. A fresh `sudo -n` read in
  this session was unavailable because the shell has no administrator
  credential; the verifier labels this as reliance on the previous evidence.

**Decision:** `NEXUS_RECOVERY_READY=YES` and
`FINAL_PRE_ACTIVATION_GATE=PASS`. Scheduler, dispatcher, old kernel, active
operator, and certification remain OFF.

## Staged activation canary — 2026-10-09

**OBSERVED FACT:** The scheduler passed two automatic 300-second interval
observations. The dispatcher passed idle observation while no eligible or
active jobs existed. One post-fix internal SYSTEMS canary completed with one
claim, result hash, receipt, and footprint. A separate failure canary recorded
one deterministic first-attempt failure, waited through bounded backoff, then
completed on its sole retry.

**OBSERVED FACT:** The first pre-fix canary was retained as a terminal BLOCKED
diagnostic row after exposing a worker import-shadowing defect. The defect was
fixed and focused tests passed before the successful canary retest. The first
failure attempt metadata is retained in
`reports/certification/NEXUS_STAGED_ACTIVATION_CANARY_20261009.json`.

**OBSERVED FACT:** Historical task requests remained 636; legacy credit queue
rows remained 25. No provider, messaging, payment, trading, browser, heavy
worker, or cloud resource action occurred. There were zero due jobs, active
jobs, stale leases, orphan workers, or duplicate receipt groups after the
canaries.

**OBSERVED FACT:** Scheduler and dispatcher were unloaded and disabled after
the canary, consistent with the recovery runbook's frozen OFF baseline. Old
kernel, active operator, PM2 workflow executors, legacy pollers, and
certification remain OFF.

**DECISION:** `STAGED_ACTIVATION_CANARY=PASS`. This does not authorize
whole-company certification or department/provider activation.


## Marketing + Creative workflow canary — 2026-10-09

**OBSERVED FACT:** One test campaign completed the durable Research → Marketing → Creative V1 → revision → Creative V2 → Marketing acceptance flow. Nine workflow jobs and nine durable handoffs have receipts. The review sequence is `REVISE`, `ACCEPT`; one revision was created. The campaign is at `ITERATION_READY`, with Ray publishing approval pending.

**OBSERVED FACT:** Publishing remained blocked by approval with zero publication attempts. A deterministic local asset route was used. Synthetic performance is explicitly `DATA_CLASS=TEST`; no production metrics were asserted. Provider calls, spend, ads, email, social, payment, trading, cloud creation, and browser publishing were zero.

**OBSERVED FACT:** One separate malformed-artifact failure job was claimed once and terminally blocked at its one-attempt limit. The performance job’s expired lease was recovered once and it completed on attempt two. No duplicate claims, active canary jobs, or due canary jobs remained. Historical counts stayed at 636 task requests and 25 legacy credit jobs.

**REPAIR / TEST:** The canary controller’s retry wait was changed from repeated queue polling to one bounded scheduled wait. Focused workflow tests passed: 15. Scheduler, dispatcher, and department workers are OFF after this canary.

**DECISION:** `MARKETING_CREATIVE_WORKFLOW_READY=YES` for this provider-free internal workflow. Whole-company certification remains OFF. Full result: `reports/certification/NEXUS_MARKETING_CREATIVE_WORKFLOW_20261009.md`.

**POST-WORKFLOW RECOVERY CHECK:** After refreshing the expected local worktree fingerprint to include the reviewed workflow/controller and report changes, the read-only recovery verifier returned `SAFE_BOOT_STATE=YES`, `LOCAL_RECOVERY_DRIFT=0`, intact provider/secret registry hashes, read-only Supabase health pass, no loaded Nexus services, and no forbidden runtime processes. Scheduler, dispatcher, old kernel, active operator, and certification remain OFF. This verification started no services and created no business work.

## Whole-company certification follow-up — 2026-10-10

The whole-company campaign completed using bounded durable jobs. Post-run recovery verification returned `SAFE_BOOT_STATE=YES`, `LOCAL_RECOVERY_DRIFT=0`, no stale leases or orphan workers, and read-only Supabase health passed. Historical task requests (636) and the preserved legacy credit queue (25) remained unchanged. The new scheduler and dispatcher, old kernel, and active operator remain OFF. See `reports/certification/NEXUS_WHOLE_COMPANY_CERTIFICATION_20261009.md` and its JSON/checkpoint for campaign evidence.

Final whole-company post-run recovery verifier: `SAFE_BOOT_STATE=YES`, `LOCAL_RECOVERY_DRIFT=0`, read-only Supabase health passed, provider/secret registry hashes matched, no forbidden processes or loaded Nexus launch agents, scheduler/dispatcher/old kernel/operator OFF; verified 2026-10-10T01:38:22Z.
