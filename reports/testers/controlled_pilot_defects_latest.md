# Controlled Pilot Defects and Closeout

## Verified defects repaired

| Issue | Severity | Scope | Repair | Retest |
|---|---|---|---|---|
| CP-001 reset could fall back to broad/global row selection | High operational safety | Synthetic reset script | Fail-closed exact Auth → membership → tenant/client scope; no fallback; composite join handling; protected Ray Review links preserved | A/B/C dry-run + verify passed; real resets passed |
| CP-002 replay mode/scoping was not reliably persona-specific and follow-up flag handling was defective | High operational safety | Synthetic replay/fixture scripts | Explicit persona and replay modes; selected-persona seed; bounded idempotent pilot state; no active duplicate jobs | A/B/C full replay repeated successfully with stable counts |
| CP-003 first Tester Readiness browser assertion could race AdminGuard/Supabase session hydration | Medium reliability | Existing certification stabilization | Targeted hydration wait in the affected certification test | Tester Readiness 10/10 passed |

## Pilot feedback triage

- `PILOT-OBS-A`: medium, synthetic Persona A, backlog, reproducible observation; no Ray Review required.
- `PILOT-OBS-B`: low, synthetic Persona B, backlog, reproducible observation; no Ray Review required.
- `PILOT-OBS-C`: medium, synthetic Persona C, backlog, reproducible observation; no Ray Review required.

The persisted synthetic history contains additional observations from earlier bounded reruns; all are medium/low backlog records and no duplicates were promoted.

## Ray Review linkage

The existing blocker/high tester-feedback path was exercised and audited: exactly one linked `task_requests` Ray Review draft exists for the linked feedback record. Re-routing is idempotent, the feedback row retains the link, and the draft remains approval-gated with `auto_approve=false` and `auto_execute=false`. No fix was approved or executed automatically.

## Open defects

No blocker defects remain open. No high-severity security or data-isolation defect remains open. Medium/low observations remain backlog items for later prioritization.
