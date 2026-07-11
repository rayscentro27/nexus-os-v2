# Client Upload to Specialist Review Flow

Generated: 2026-07-10

## Flow Diagram

```
Client Upload
  → DocumentUploadZone.handleFiles()
    → Supabase Storage upload
    → writeDocumentMetadata()
      → INSERT INTO client_documents
        (category=credit_report, status=pending_review, source=client_portal_upload)
    → onUploadComplete callback
      → SimpleDocumentUploadPanel shows "Saved and queued for review"
      → Client sees "Pending GoClear Review"
      → Client sees "It should appear in the Credit Specialist Workbench"

Admin Review
  → CreditSpecialistWorkbench mounts
    → loadPendingCreditReportReviews()
      → SELECT FROM client_documents WHERE credit_report + pending_review
      → Returns normalized PendingCreditReportReview[]
    → Client Queue tab renders results
      → File name, client name/email, uploaded date, status
      → Parser status, next action label
    → Specialist clicks Review Report
      → Detail panel shows metadata
      → Action buttons: Run Parser Preview, Create Case, Manual Item, Mark Needs Info
    → No letters generated automatically
    → No DocuPost sent without approval chain
```

## Tables Involved

| Table | Purpose |
|-------|---------|
| client_documents | Client uploads stored here |
| credit_report_reviews | Specialist reviews (not yet wired from upload) |
| credit_dispute_items | Dispute items created by specialist |
| credit_dispute_letters | Draft letters created by specialist |
| docupost_mail_jobs | Mail jobs after full approval chain |

## Safety Gates

1. Upload → client_documents (status=pending_review)
2. Specialist review required before any action
3. Parser preview gated (backend extraction worker needed)
4. Client approval required before DocuPost
5. No auto letters from upload
6. No auto DocuPost from upload
7. No SSN, DOB, or full account numbers
8. RLS not disabled
9. AdminGuard unchanged
