# Daily/System Operations Golden Loop — 2026-08-29

The Nexus-owned loop is implemented in
`scripts/nexus_agent_platform/wp3_golden_loop.py`.

It performs authority and dependency checks, invokes only the fixed Daily
Monitor Python entrypoint, hashes and validates its two reports, records a
real TruthKernel run/evidence receipt, then requests an advisory Hermes
review. Hermes cannot write TruthKernel or authorize side effects.

`PYTHON_EXECUTOR_ALLOWLIST_CREATED=YES`.
`PYTHON_EXECUTOR_REAL_EXECUTION=PASS` for the local report generation.
The end-to-end loop is currently `BLOCKED_REVIEW_PROVIDER_TIMEOUT`: three
distinct bounded Hermes review attempts failed closed after the native Kanban
provider compatibility issue saturated the same local route. No success is
invented; failed receipts are preserved under
`reports/rebuild/nexus_golden_loop_receipts/`.
