# Nexus — Capture Queue Worker (report)

- generated_at: 2026-06-25 · build PASS · watch PASS · worker dry-run PASS

## Built
`scripts/intake/run_capture_queue_worker.py` — bounded/manual/safe queue worker (see
`docs/operations/NEXUS_CAPTURE_QUEUE_WORKER.md`). Default DRY-RUN; `--no-external-ai` default; hard
cap `--limit 3`. Source Intake "Capture Queue" UI now shows queued/running/captured/done/failed +
result summary.

## Processes
- Safe queued `youtube_capture_request` (`approval_required=false`, `source_capture_policy=
  safe_admin_submitted_capture_v1`).
- Approved review-required items ONLY when a linked `approvals` row is `approved` (never
  auto-approved).

## Dry-run result (this build)
`{candidates: 1, eligible: 0, processed: 0}` — the single existing request is correctly **skipped**:
"approval_required and linked approval not approved". **No safe queued request exists**, so per the
build rule **no real capture was run**. The worker + skip logic are verified by the dry-run.

## Real run
Not executed (no eligible safe queued item). When Ray submits a safe YouTube URL from Source Intake
(creates `approval_required=false` + policy), `--no-dry-run` will process exactly one and write v2
rows + proofs, updating the task_request to `done`.

## Safety (verified)
no capture run · no scheduler · v1 untouched · no social publish · no email · no trade · no deploy ·
no external AI · no summarize.py · no v1 research-table write · `research_sources` still 2 ·
`social_publish_receipts` unchanged (1) · `social_accounts.publish_enabled` false · no secrets ·
`.env` not committed · no schema/RLS change.

## Next
Approvals-UI "approve & queue" button for review-required source items, then the worker can process
approved ones; optionally surface worker run history in the Capture Queue.
