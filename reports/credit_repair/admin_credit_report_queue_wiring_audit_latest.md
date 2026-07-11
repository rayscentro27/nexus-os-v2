# Admin Credit Report Queue Wiring Audit

Generated: 2026-07-10

## Root Cause

Client credit report uploads are saved to `client_documents` table, but the Admin Credit Specialist Workbench Client Queue reads from `credit_report_reviews` table. No bridge code existed to connect these two tables.

## Upload Table & Fields

**Table:** `client_documents`

| Field | Value |
|-------|-------|
| client_id | From auth context |
| tenant_id | From auth context |
| category | `credit_report` (inferred) |
| title | File name |
| status | `pending_review` |
| goclear_review_status | `pending_review` |
| source | `client_portal_upload` |
| client_visible | `true` |
| approval_required | `true` |

## Admin Queue Source (Before Fix)

**Table:** `credit_report_reviews`
**Filter:** `.eq('client_id', context.clientId)` — resolved for admin user, not target client

## Mismatch

1. Uploads → `client_documents` (category=credit_report, status=pending_review)
2. Admin Queue → `credit_report_reviews` (different table, no bridge)
3. `loadCreditRepairJourney()` resolved context for admin user, not target client

## Fix Applied

1. Created `loadPendingCreditReportReviews()` in `creditRepairWorkflow.ts`
   - Queries `client_documents` where credit_report + pending_review
   - Detects credit reports via category/suggestedCategory/documentType/source/fileName
   - Returns normalized objects with reviewId, client info, file name, parser status
2. Updated `CreditSpecialistWorkbench.jsx` Client Queue tab to use new loader
3. Added Refresh button, last checked timestamp, diagnostic text
4. Added Review Report, Parser Preview, Create Case, Manual Item, Mark Needs Info buttons
5. Updated Parser Preview tab with live limitation notice
6. Updated client upload copy to mention specialist workbench

## Safety Gates Preserved

- AdminGuard unchanged
- No auto letter generation from upload
- No auto DocuPost from upload
- Parser preview gated with backend extraction worker limitation
- Specialist review required before any action
- Client approval required before DocuPost
- No SSN, DOB, or full account numbers
- RLS not disabled
- Service role not used in frontend
