# Inline Document Upload Flow

- Shared component: `src/components/client/InlineDocumentRequirement.jsx`
- Upload engine: `src/components/client/DocumentUploadZone.tsx`
- Storage/metadata behavior preserved: resolved client context, storage upload, `client_documents` insert, `pending_review`, `goclear_review_status=pending_review`, `approval_required=true`, `client_visible=true`.

## Upload Placements

- `/client/profile`: ID, proof of address, credit report, EIN confirmation, business formation, operating agreement, required docs.
- `/client/credit-profile`: credit report.
- `/client/funding-readiness`: bank statements, tax return, P&L, business license, EIN confirmation, formation docs.
- `/client/credit-repair-journey`: credit report and dispute support documents.
- `/client/request-review`: review support attachments.
- `/client/documents`: master upload hub and vault.

## Display Behavior

- Shows Missing, Uploaded, Pending Review, Approved, Needs Replacement, or Optional.
- Shows uploaded file name when available.
- Does not fake file viewing when no safe view URL exists.
