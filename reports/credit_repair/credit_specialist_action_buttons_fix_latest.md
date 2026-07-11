# Credit Specialist Action Buttons Fix

## Activated Buttons

- `Review Report`: opens the selected report detail panel, keeps the selected report visible, and shows metadata plus safe file-preview limitation.
- `Run Parser Preview`: opens parser preview explanation for the selected uploaded report. It does not pretend to parse live Supabase files.
- `Create Credit Repair Case`: calls `getOrCreateCreditRepairCaseForDocument` and switches to Case Engine on success.
- `Add Manual Item`: opens a specialist-entered item form.
- `Mark Needs Info`: updates `client_documents.goclear_review_status` and `status` to `needs_info` when permitted.

## Feedback

Every action now shows one of:
- success message
- safe error message
- visible panel
- gated parser limitation

## Preserved Gates

- No dispute letters are created from upload alone.
- No DocuPost jobs are created from upload alone.
- Specialist review remains required.
- Client approval remains required before sending.
