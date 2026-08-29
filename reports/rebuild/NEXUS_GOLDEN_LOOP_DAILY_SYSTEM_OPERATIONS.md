# Daily/System Operations Golden Loop — 2026-08-29

The Nexus-owned loop is implemented in
`scripts/nexus_agent_platform/wp3_golden_loop.py`.

It performs authority and dependency checks, invokes only the fixed Daily
Monitor Python entrypoint, hashes and validates its two reports, records a
real TruthKernel run/evidence receipt, then requests an advisory Hermes
review. Hermes cannot write TruthKernel or authorize side effects.

`PYTHON_EXECUTOR_ALLOWLIST_CREATED=YES`.
`PYTHON_EXECUTOR_REAL_EXECUTION=PASS` for the local report generation.
The end-to-end loop now has a real `SUCCEEDED_VERIFIED` receipt at
`reports/rebuild/nexus_golden_loop_receipts/receipt_0769d26ce6334e27b71ee4c2838ef6eb.json`.
The fixed Python executor generated and validated its local reports, and the
scoped `nexusopenrouter` Hermes profile returned an advisory review. TruthKernel
authority remained read-only to Hermes and no external side effect occurred.
Earlier failed-closed receipts remain preserved under the same directory.
