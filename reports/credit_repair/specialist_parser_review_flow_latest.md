# Specialist Parser Review Flow

The admin Credit Specialist Workbench now includes a preview section called `Credit Report Parser Preview`.

## Current Admin Behavior

- Shows parser preview status for local/test fixture validation.
- Explains that live report parsing requires a backend extraction worker.
- Shows statuses:
  - Suggested extraction ready
  - OCR required
  - Needs specialist split/verify
- Shows disabled preview actions:
  - Confirm selected item
  - Edit item before creating case item
  - Reject or request full report
  - No auto letters

## Required Live Worker Before Production

- Download uploaded credit report from Supabase Storage on the backend.
- Extract text using a reliable PDF/OCR stack.
- Store parser result as suggested/unverified.
- Present suggestions to specialist for confirmation.
- Create case items only after specialist confirmation.

## Preserved Safety

- Specialist review remains required.
- Client approval remains required.
- DocuPost remains approval-gated.
- Parser preview does not send or mail anything.
