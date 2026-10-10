# Nexus Staged Activation Canary — 2026-10-09

## Result

**FINAL_STATUS=NEXUS_STAGED_ACTIVATION_CANARY_PASS**

**OBSERVED FACT:** The staged scheduler and dispatcher checks passed, the post-fix internal durable canary completed with one receipt, and the separate controlled failure canary recovered on its single retry. The scheduler and dispatcher were then unloaded and disabled according to the recovery runbook. Whole-company certification remains off.

## Recovery gate and runtime sequence

- **OBSERVED FACT:** `scripts/systems/verify_safe_recovery.py` passed before activation and passed again after the launch configuration and worker import fixes. The final safe boot check returned `SAFE_BOOT_STATE=YES`, `LOCAL_RECOVERY_DRIFT=0`; registry hashes, historical replay protection, legacy queue protection, and the read-only Supabase health check passed.
- **OBSERVED FACT:** Scheduler launchd definition is one-shot every 300 seconds, `RunAtLoad=false`, `KeepAlive=false`; dispatcher is one-shot every 120 seconds with the same settings. Both use the canonical Python interpreter directly. The scheduler and dispatcher definitions remain disabled outside the staged window.
- **OBSERVED FACT:** Scheduler-only observation passed across two automatic interval firings. It exited successfully, created no scheduled jobs, and did not claim work.
- **OBSERVED FACT:** Dispatcher idle observation passed with an empty eligible queue; it recovered no leases, claimed no work, and launched no workers.
- **OBSERVED FACT:** After canaries, both services were booted out and disabled. Final state: scheduler OFF, dispatcher OFF, old kernel OFF, active operator OFF, PM2 workflow executors OFF, certification OFF.

## Defects found and repaired during staging

- **OBSERVED FACT:** The first scheduler launch exited with `SUPABASE_DURABLE_QUEUE_NOT_CONFIGURED`. The launch wrapper had been removed to avoid exporting every runtime secret, but `default_store()` did not explicitly request the non-secret Supabase URL alongside its allowlisted service credential. The store now explicitly loads only `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`; the scheduler then exited 0.
- **OBSERVED FACT:** The dispatcher claimed the first internal canary, but the worker entry point imported the repository's `platform.py` instead of the Python standard library module. This caused the worker footprint path to fail before completion. The worker now removes its package directory from `sys.path` before importing stdlib `platform`. A direct entrypoint import check and focused worker/receipt tests passed.
- **OBSERVED FACT:** The first canary job remains preserved as terminal `BLOCKED` diagnostic evidence; it was not deleted or replayed. A fresh post-fix canary was used for the final success check.

## Harmless internal canary

- **OBSERVED FACT:** One post-fix `SYSTEMS_INTERNAL_CANARY` job was created with a new durable job ID and correlation ID. It had no payload reference and explicitly denied provider, browser, external-action, trading, and resource-creation authority.
- **OBSERVED FACT:** It was claimed once, ran the deterministic local calculation, completed, persisted one result hash, one receipt, and one footprint, then exited. Its footprint lists zero providers, zero email actions, zero social actions, and zero browser actions.
- **OBSERVED FACT:** The final canary test cohort had `CANARY_JOBS_CREATED=1`, `CANARY_JOBS_CLAIMED=1`, `CANARY_JOBS_COMPLETED=1`, and `CANARY_DUPLICATE_CLAIMS=0`.
- **OBSERVED FACT:** For transparent history, the earlier pre-fix diagnostic canary is an additional terminal `BLOCKED` row retained in Supabase. Across the whole activation campaign there are three canary-class rows: that blocked diagnostic, the completed internal success canary, and the completed failure-recovery canary. No extra job was deleted.

## Controlled failure and recovery

- **OBSERVED FACT:** One separate `SYSTEMS_FAILURE_CANARY` job was claimed once. Its first attempt raised only the deterministic `CONTROLLED_CANARY_FAILURE_ONCE`, wrote a failure footprint, and entered `FAILED_RETRYABLE` with a 60-second bounded delay.
- **OBSERVED FACT:** The first-attempt metadata was preserved in this report before retry. Exactly one retry was claimed; the second attempt completed with a receipt and result hash. The job has two attempts, one retry, no active lease, and final state `COMPLETED`.
- **OBSERVED FACT:** No duplicate concurrent claim occurred. The post-recovery lease/backoff and atomic duplicate-claim tests passed using isolated local SQLite state.

## Queue and external-action checks

| Check | Result |
|---|---:|
| Historical `task_requests` | 636 before and after |
| Legacy `credit_analysis_jobs` | 25 before and after |
| Enabled durable schedules | 0 |
| Due ready/retryable jobs after canaries | 0 |
| Active durable jobs / stale leases | 0 / 0 |
| Worker processes left running | 0 |
| Duplicate canary receipt groups | 0 |
| Paid/external provider calls | 0 |
| Email / Telegram / social / payment / trading actions | 0 |
| Cloud resource creations / browser automation starts | 0 / 0 |

**OBSERVED FACT:** The worker footprints record only the expected Supabase control-plane and governor operations needed to create/claim/complete the durable jobs. They list no external provider or communication actions.

## Resource and test evidence

- **OBSERVED FACT:** Host sample: 8 GiB RAM, 78% free memory, swap pressure not elevated, load averages 1.89/1.97/1.92. No Nexus scheduler, dispatcher, or worker process remained between ticks or after shutdown.
- **OBSERVED FACT:** No Nexus-launched browser automation, ffmpeg, Ollama, or container CLI process was found. Existing interactive Chrome and Chrome Remote Desktop were left untouched.
- **OBSERVED FACT:** Focused tests passed: internal canary contract and worker receipt path (2 tests); lease expiry/backoff and atomic duplicate-claim prevention (2 tests); worker entrypoint import-origin check passed. No provider, browser, model, media, or full-suite workload was run.

## Final state and decision

- `SCHEDULER_ONLY_OBSERVATION=PASS`
- `DISPATCHER_IDLE_OBSERVATION=PASS`
- `WORKER_LIMIT_ENFORCEMENT=PASS` (maximum observed active canary workers: 1; browser/heavy limits: 0)
- `FAILURE_RECOVERY_CANARY=PASS`
- `LEASE_RECOVERY_UNDER_ACTIVE_RUNTIME=PASS`
- `DUPLICATE_CLAIM_PREVENTION_UNDER_ACTIVE_RUNTIME=PASS`
- `HOST_RESOURCE_CANARY=PASS`
- `HISTORICAL_TASK_COUNTS_UNCHANGED=YES`
- `LEGACY_CREDIT_QUEUE_COUNTS_UNCHANGED=YES`
- `STAGED_ACTIVATION_CANARY=PASS`

**RECOMMENDATION:** The recovery runbook’s frozen baseline requires scheduler and dispatcher OFF outside explicit activation. That state has been restored. This pass does not start whole-company certification or enable any department/provider workload.

`SECRET_VALUES_IN_REPORTS=0`
