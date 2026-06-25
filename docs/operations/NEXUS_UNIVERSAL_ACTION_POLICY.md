# Nexus — Universal Action Policy

Source of truth: `src/config/nexusActionPolicy.ts`. Every tab classifies actions through it.

## Categories
`safe_read` · `safe_queue` · `safe_draft` · `safe_internal_route` · `needs_review` ·
`approval_required` · `disabled` · `dangerous_blocked`.

## Risk triggers
`uncategorized` · `low_confidence` · `high_compliance_risk` · `risky_destination` · `client_facing` ·
`publish_send_trade_deploy` · `scheduler_or_local_command` · `raw_v1_worker` · `sensitive_data` ·
`external_ai_sensitive_text` · `broad_scrape` · `missing_connection`.
**Hard triggers** (always force approval): publish_send_trade_deploy, scheduler_or_local_command,
raw_v1_worker, sensitive_data, external_ai_sensitive_text, broad_scrape, client_facing,
high_compliance_risk, risky_destination.

## Outcomes
`auto_routed` · `queued_safe_work` · `needs_ray_review` · `approval_required` · `parked` ·
`rejected` · `disabled_not_connected`.

## Helpers
`isSafeAdminSubmittedSourceCapture` · `getReviewTriggers` · `getApprovalRequirement` ·
`getActionStatusLabel` · `getActionSafetyCopy` · `shouldShowInApprovals` ·
`shouldShowInOwningQueue` · `classifyCaptureSubmission`.

## Rule
Safe work queues automatically in the owning tab (NOT Approvals). Anything with a hard trigger →
`approval_required` → must appear in Approvals (linked approvals row). Never mark queued items
approved. Never create fake approvals. Publish/send/trade/deploy gates are never weakened.

## Universal copy
"Safe work can queue automatically." · "Ray approval is required for risky actions." · "Hermes can
recommend, but Ray approves risky actions." · "Disabled — not connected yet." · "Queued — waiting for
local runner." · "Needs Ray review."
