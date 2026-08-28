# Nexus V2 Operational Truth Kernel — WP1-B

## WP1-B hardening

The kernel is evidence-derived. A caller's `output_verified` boolean is only
one input: authority, dependencies, required artifact existence and hashes,
verified real evidence, freshness, and declared side effects must also pass.
SQLite foreign keys are enabled on every connection. Requested runs remain
`PENDING_EXECUTION` until `mark_run_started()` is called; a run row alone is
not proof that execution is running.

Freshness is recomputed at read time from the process freshness contract, so a
historically verified run can become `STALE` without rewriting history.
Continuous processes require observed heartbeat evidence; a loaded scheduler
is not a heartbeat. Expired human gates cannot be approved, and approval is
bound to the exact action recorded on that gate.

## Decision

Use a local SQLite database at `data/runtime/nexus_operational_truth.db`.
SQLite is durable, inspectable, transactional, low-resource, and available in
the Python standard library. It keeps truth derivation available when
Supabase, Hermes, Oracle, or external models are unavailable. The database is
runtime state and is gitignored; committed schema/API code and sanitized
reports remain the reviewable source.

## State separation

Definitions describe intent and contracts only. Runs record execution facts.
Evidence records provenance, realness, artifact hashes, scope, and verification
status. The derived process state is calculated from the latest run and its
evidence. No definition flag, scheduler declaration, exit code, or receipt
alone can produce `SUCCEEDED_VERIFIED`.

The kernel distinguishes:

`NOT_CONFIGURED`, `CONFIGURED`, `READY`, `RUNNING`,
`SUCCEEDED_UNVERIFIED`, `SUCCEEDED_VERIFIED`, `FAILED`, `DEGRADED`, `STALE`,
`PAUSED`, `BLOCKED_AUTHORITY`, `BLOCKED_DEPENDENCY`, and `UNKNOWN`.

Current implementation derives the applicable subset deterministically and
leaves unsupported conditions explicit rather than guessing.

## Records

### Process definition

`process_id`, `canonical_entrypoint`, `purpose`, `execution_mode`, dependency,
authority, input, output, side-effect, verification, receipt, freshness,
health, and recovery contracts are stored as JSON. `execution_mode` is one of
`RUN_ONCE`, `ON_DEMAND`, `SCHEDULED`, or `CONTINUOUS`.

### Process run

The run record stores `run_id`, process/trigger identity, git SHA, request/start/
completion times, execution host, entrypoint, authority/dependency results,
exit status/code, output artifacts and SHA-256 hashes, side-effect expectation
and observation, verification/freshness results, recovery usage, final state,
and continuous-process fields: process start, heartbeat, interval, successful
cycle, cycle count, shutdown reason, expected-running, and scheduler
supervision.

### Evidence

Evidence stores an ID, run ID, type, source, creation time, artifact/hash,
scope, `REAL`/`SAFE_SYNTHETIC`/`DRY_RUN`/`SIMULATION`, and verification status.
Only verified `REAL` evidence can participate in a real verified run.

### Human gate

Each gate stores an ID, exact action, reason, risk, requested authority,
timestamps, status, and approver. Approval compares the exact action string
and gate ID; approval for one gate cannot authorize another.

## Python interface

`TruthKernel` exposes the small deterministic API:

- `register_process`
- `start_run`
- `mark_run_started`
- `record_dependency_result`
- `record_authority_result`
- `record_output`
- `record_evidence`
- `complete_run`
- `derive_process_state`
- `get_process_status`
- `get_run`
- `verify_freshness`
- `create_human_gate` / `approve_human_gate`

`get_process_status` is a read-only structured model exposing definition and
current derived state, execution mode, latest requested/started/completed
runs, real and verified run identifiers, dynamic freshness/age, authority and
dependency results, output/side-effect verification, heartbeat status,
warnings, and evidence.

The Daily Monitor adapter is bounded, internal/read-only, and records the
monitor’s execution/output truth separately from the monitor’s own findings.
Thus a successful monitor run may be `SUCCEEDED_VERIFIED` while its report
truthfully says that some telemetry is stale or unavailable.

## Golden-process proof

`scripts/nexus_agent_platform/golden_daily_monitor.py` registers
`scripts/operations/nexus_daily_monitor.py`, records authority and dependency
checks, executes one bounded subprocess, hashes the JSON/Markdown outputs,
records real evidence, verifies a five-minute artifact freshness contract, and
derives the final state.

The first proof produced a real bounded run with fresh output and derived
state `SUCCEEDED_VERIFIED`. It did **not** infer that all monitored systems are
healthy.

## Non-goals

This package does not replace the legacy process registry, migrate all
candidates, activate Active Operator, alter production schedulers, integrate
Hermes, or create external authority. Those remain future work after this
kernel is reviewed and further proven.
