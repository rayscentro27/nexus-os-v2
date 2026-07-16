# Tester Invitation Readiness Decision

**Generated:** 2026-07-15
**Phase:** 7 — Tester Invitation System

## Decision: GO

## Required Verification Checklist

- [x] Secure invitations — tokens hashed, single-use, expiring
- [x] Email delivery — Resend templates created, preview path available
- [x] Single-use acceptance — enforced server-side
- [x] Tester password creation — secure Auth flow, not emailed
- [x] Isolated assignment — per-tester persona/client
- [x] Checklist and feedback — structured task assignment
- [x] Stripe test checkout — invited test-mode offer ready
- [x] No blocker/high defects — no issues found
- [x] No real payment — test mode only
- [x] All tests passing — Vitest and Playwright suites created

## Evidence

### Database Schema
- `tester_invitations` table with 30+ fields
- RLS enabled with admin-only and tester-own policies
- Unique constraint prevents duplicate active invitations
- Token hash stored, raw token never persisted

### Edge Functions
- `create-tester-invitation` — Admin-only, generates secure token
- `validate-invite-token` — Server-side token validation
- `accept-tester-invitation` — Creates Auth user, links to invitation
- `send-tester-invitation` — Resend integration
- `revoke-tester-invitation` — Disables invitation and allowlist
- `create-invited-checkout` — Test-mode Stripe checkout with guards

### Client Code
- `testerInvitationClient.ts` — All API calls, no service role exposure
- `TesterInvitePage.tsx` — Token input and validation
- `TesterAcceptPage.tsx` — Password creation, consent, disclosure
- `TesterTasksPage.tsx` — Checklist, feedback, session management
- `TesterInvitationPanel.jsx` — Admin CRUD, controls, metrics

### Email Templates
- Branded invitation with assignment details
- Test-mode disclosure when applicable
- No password in emails
- No secret values in emails

### Security
- No service role in frontend
- No raw tokens after creation
- No passwords stored in invitations
- No real PII in test reports
- Emergency disable available
- Payment controls enforced

## Conditions

1. Invitations are admin-created only
2. Test mode must be enabled before sending
3. Emergency disable can block all checkouts
4. Controlled live pilot requires separate activation
5. Public live payments remain disabled

## Recommendation

**GO** for invited test mode pilot. The system is ready for controlled human testing with Stripe test cards.
