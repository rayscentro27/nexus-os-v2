# GoClear Auth Email Branding Audit

Status: `MANUAL_CONFIGURATION_REQUIRED`.

The repository owns client-facing login/reset copy, but the Supabase Auth confirmation, password-reset, invitation, and email-change templates are configured outside the repository. No template configuration was found in the inspected source tree, and no provider dashboard mutation was performed.

## Required template contract

- Subject: `Confirm your GoClear account`
- Identity: GoClear Client Portal
- Primary CTA: `Confirm My Account`
- Explanation: confirm the email to activate the portal, then complete a short setup before the Credit & Funding Readiness Review.
- Support: `support@goclearonline.cc`
- No Supabase/internal implementation language in the client copy.
- Responsive HTML and plain-text fallback.

Ray must configure and preview the templates in the existing Supabase Auth project before this item can be marked PASS. No secrets are included here.
