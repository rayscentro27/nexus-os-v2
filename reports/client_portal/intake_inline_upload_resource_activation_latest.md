# Intake Inline Upload Resource Activation

- Current world-class design preserved: `True`
- Old design restored: `False`
- Inline uploads active: `True`

## Activated Workflow Areas

- Profile & Info: guided intake sections, EIN/entity states, setup-help states, inline ID/address/credit/EIN/business document uploads.
- Credit Health: inline credit report upload and gated credit monitoring card.
- Documents: master document vault plus upload hub.
- Funding Readiness: inline bank statement, tax return, P&L, business license, EIN confirmation, and formation document requirements.
- Credit Repair Journey: inline credit report/supporting dispute document upload and live journey state.
- Request Review: inline review support upload and existing `client_tasks` review request submission.
- Clyde: recommendations generated from client state.

## Remaining Caveats

- Safe document viewing URL is not implemented; uploaded files show status but no fake view link.
- Review attachments are uploaded as `client_documents` with `source_concept=review_support`; direct task-document linking would need a future migration if required.
