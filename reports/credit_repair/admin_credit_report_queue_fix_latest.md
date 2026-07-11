# Admin Credit Report Queue Fix

Generated: 2026-07-10

## Summary

Fixed the wiring gap between client credit report uploads and admin Credit Specialist Workbench queue.

## What Changed

### src/lib/creditRepairWorkflow.ts
- Added `loadPendingCreditReportReviews()` export
- Queries `client_documents` for pending credit report uploads
- Detects credit reports via multi-field matching (category, suggested_category, document_type, source, title, file_name)
- Returns normalized `PendingCreditReportReview[]` with client info, file metadata, parser status
- Falls back gracefully on RLS/schema errors

### src/components/CreditSpecialistWorkbench.jsx
- Client Queue tab now uses `loadPendingCreditReportReviews()` instead of `credit_report_reviews`
- Tab count is dynamic based on actual pending uploads
- Added Refresh button with last checked timestamp
- Added admin diagnostic: "Queue source: client_documents pending credit_report uploads."
- Detail panel shows file name, client name/email, status, parser status, source, upload date
- Added action buttons: Review Report, Run Parser Preview, Create Credit Repair Case, Add Manual Item, Mark Needs Info
- Parser Preview tab shows live limitation: "Parser preview can read text-based fixtures. Live uploaded file parsing requires a backend extraction worker or storage file access integration."
- Parser Preview tab shows uploaded reports needing review

### src/components/client/SimpleDocumentUploadPanel.jsx
- Updated credit report upload message to mention: "It should appear in the Credit Specialist Workbench for review."

### scripts/checks/check_credit_report_upload_admin_queue.py
- New check script verifying the full wiring chain

## How Uploaded Credit Reports Appear in Admin

1. Client uploads credit report from /client/documents
2. DocumentUploadZone inserts row into `client_documents` with category=credit_report, status=pending_review
3. Admin opens /admin#credit-specialist
4. CreditSpecialistWorkbench calls `loadPendingCreditReportReviews()`
5. Loader queries `client_documents` for pending credit reports
6. Results appear in Client Queue tab with file name, client info, status
7. Specialist can review, run parser preview, create case, or add manual items

## Parser Live Limitation

Parser preview can read text-based fixtures. Live uploaded file parsing requires a backend extraction worker or storage file access integration. This is clearly stated in the Parser Preview tab.

## Specialist Review Gate

All actions require specialist confirmation before proceeding. No letters are generated automatically. No DocuPost is sent without explicit approval chain.

## Manual Test Steps

1. Log in as fake client
2. Go to /client/documents
3. Upload fake credit report
4. Confirm client shows: "Saved and queued for review" + "Pending GoClear Review"
5. Confirm client sees: "It should appear in the Credit Specialist Workbench for review"
6. Log out, log in as admin
7. Go to /admin/credit-specialist
8. Confirm Client Queue count > 0
9. Confirm uploaded file appears with file name, client info, status
10. Click Review Report — confirm no letter auto-created
11. Confirm DocuPost remains gated
