# Intake Inline Upload Resource Audit

- Current world-class design remains active: `True`
- Old client portal design restored: `False`
- Premium shell, hero, sidebar, cards, Clyde panel preserved: `True`

## Static Areas Found Before Activation

- Profile cards needed guided field sections and inline document requirements.
- Credit Health had upload CTAs but needed in-page credit report status and upload.
- Funding Readiness listed requirements but needed inline status/upload cards.
- Request Review needed inline support attachments.
- Business Setup needed setup-help states for EIN, DUNS, banking, address, website, phone/email, credit profile, and license.
- Clyde needed live-state recommendations instead of fixed preview copy.

## Existing Data Reused

- `client_profiles` through `loadClientProfileIntake` and `saveClientProfileIntake`
- `client_documents` through `DocumentUploadZone`
- `client_tasks` for approval-gated review requests
- `readiness_scores`, `credit_workflow_items`, `business_profile_requirements`, `approved_client_guidance` through existing live helpers
- `credit_report_reviews`, `credit_dispute_items`, `credit_dispute_letters`, and `docupost_mail_jobs` through `loadCreditRepairJourney`

## Security Notes

- No SSN, full DOB, bank account numbers, credit card numbers, or third-party login credentials are collected.
- Credit monitoring connection remains gated until a secure provider/backend exists.
- No schema changes or duplicate tables were created.
