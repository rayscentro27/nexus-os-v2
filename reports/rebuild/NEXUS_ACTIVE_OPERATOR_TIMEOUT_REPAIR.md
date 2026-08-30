# Active Operator bounded-cycle timeout repair

Date: 2026-08-30
Campaign: `HG-WP6.5-CURRENT-LOOP-REAL-WORLD-CERTIFICATION-20260830-01`

## Finding

`MAX_RUNTIME_SECONDS=600` was declared by
`scripts/operations/nexus_active_operator_runner.py`, but the launchd path had
no cycle-level deadline. The runner could remain inside synchronous discovery,
credential metadata, state, or governed persistence work without durable
terminal evidence. The historical blocking callsite is not reconstructed and
is not inferred here.

The existing Netlify metadata subprocess has an 8-second timeout, and the
Supabase browser subprocess has a 180-second timeout. The runner's ordinary
filesystem and SQLite calls had no outer cycle deadline.

## Repair

The live cycle is now protected by a process-level `SIGALRM` deadline using the
configured `MAX_RUNTIME_SECONDS`. Sparse durable progress markers record the
last known stage. A deadline produces terminal state `TIMED_OUT`, a durable
failure receipt and degraded heartbeat, preserves a running work item as
explicitly retryable `FAILED`, and relies on context exit to release the
singleton advisory lock. A timeout cannot be reported as successful.

The command exits nonzero for a timeout so launchd does not receive a normal
success status. `KeepAlive` remains disabled; no restart storm is introduced.

## Verification

Focused Active Operator tests pass, including normal completion, timeout
receipt/heartbeat, lock release, running-item retryability, duplicate
suppression, kill-switch behavior, authority routing, and canonical 900-second
plist shape.

This report contains development-test evidence only. It does not claim a fresh
real-world scheduled cycle after the repair; that requires the normal launchd
schedule and will be recorded separately from these tests.
