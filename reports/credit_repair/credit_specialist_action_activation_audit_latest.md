# Credit Specialist Action Activation Audit

- Starting commit inspected: `cb1d70a`
- Current design/security posture preserved: `True`
- AdminGuard weakened: `False`
- Auto letters from upload: `False`
- Auto DocuPost from upload: `False`

## Root Cause

The uploaded credit report queue was wired to `client_documents`, but the workbench action buttons were not active workflow controls. The queue row could select a report, and the detail panel displayed disabled or non-persistent actions. Clicking the buttons did not open a useful review workflow, create/open a case, open manual item entry, update document review status, or show clear parser limitations.

## Buttons Audited

- `Review Report`: needed to open report detail and show metadata.
- `Run Parser Preview`: needed to show live parser limitation instead of silently doing nothing.
- `Create Credit Repair Case`: needed to call a safe get/create case helper.
- `Add Manual Item`: needed to open a non-sensitive manual item form.
- `Mark Needs Info`: needed to update review status or show a safe error.
- Tabs: needed meaningful counts/empty states across Client Queue, Case Engine, Parser Preview, Dispute Items, Letters, and DocuPost.

## Existing Helpers

- `loadPendingCreditReportReviews`: loads pending credit report uploads from `client_documents`.
- `createManualReportItem`: inserts structured `credit_report_items`.
- `listCreditReportItems`: loads case report items.
- Existing letter and DocuPost helpers remain approval-gated.

## Patch Plan

- Add visible action feedback state.
- Make `Review Report` open a detail panel.
- Add `getOrCreateCreditRepairCaseForDocument`.
- Make `Create Credit Repair Case` open/create a case without creating letters.
- Make `Add Manual Item` open and submit a non-sensitive form.
- Make `Run Parser Preview` open a gated explanation for live uploads.
- Make `Mark Needs Info` update `client_documents` review status.
