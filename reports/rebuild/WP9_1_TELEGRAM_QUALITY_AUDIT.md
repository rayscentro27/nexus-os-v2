# WP9.1 Telegram Quality Audit

## Findings

The actual scheduled completion message was generated in
`scripts/wp9_company_scheduler.py` by a hard-coded four-line f-string. It
used only cycle ID, work-order count, and daily cash, then replaced all
resource detail with the generic sentence that unknown balances remain
unknown. It did not invoke Nova synthesis, and it dropped department result,
artifact, failure/recovery, needs-Ray, and recommendation context that was
already present in the completion record.

The 19:20 and 19:56/19:57 messages were setup transport tests and retry/test
traffic, not autonomous work. They were created by explicit manual
`--transport-test` invocations and are absent from the normal scheduled path.
No scheduler code automatically emits them. They are documented as setup-only
and excluded from Night 1 autonomy evidence.

## Repair

The completion formatter now builds a bounded executive summary from the
durable completion record. It names completed departments and outputs,
separates no-change work, lists failure/recovery context, reports cash,
compute, free/credited use, quota and estimated-equivalent cost, and ends with
needs-Ray and recommendation lines. It is capped at 3,800 characters for
mobile delivery. Transport-test messages remain explicitly manual and are not
part of normal operation.
