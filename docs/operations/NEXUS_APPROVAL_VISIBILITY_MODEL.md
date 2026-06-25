# Nexus — Approval Visibility Model

## Why the earlier request didn't show in Approvals
Source Intake wrote the request to the **`task_requests`** table, but the **Approvals tab
(`ApprovalCenter`) reads the `approvals` table** (`listTable('approvals')`). Different tables → the
`task_requests` row was created and visible only via the Capture Queue, never in Approvals. It was
not an RLS or status-filter problem; it was a **table mismatch**.

## Fix (this build)
- **Safe admin capture** stays in `task_requests` only (Capture Queue, `approval_required=false`) —
  it must NOT clutter Approvals.
- **Review-required** items file a linked **`approvals`** row (`createApproval`, status `pending`)
  with `payload.task_request_id`, source URL, review trigger, requested action, created_at — so they
  appear in the Approvals tab. Approve/reject uses the existing `decideApproval` path.

## Approvals cards (item_type)
`source_capture_review`, `youtube_capture_review`, `uncategorized_source_review`,
`low_confidence_source_review`, `high_risk_source_review`, `promote_source_to_opportunity`,
`send_source_to_creative`, `risky_destination_review`.

## Boundary
Capture Queue (safe) → Source Intake rail only. Review-required → Approvals tab (linked approvals
row) + Capture Queue. Publish/send/trade/deploy gates unchanged; Hermes never auto-approves risky
actions.
