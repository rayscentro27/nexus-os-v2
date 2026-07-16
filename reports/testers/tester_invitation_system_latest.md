# Tester Invitation System — Latest Report

**Generated:** 2026-07-15
**Phase:** 7 — Tester Email Invitations + Invited Stripe Test-Mode Pilot + Hidden $1 Controlled-Live Pilot Foundation

## Testing Levels

| Level | Label | Description |
|-------|-------|-------------|
| `synthetic_internal` | Synthetic Internal | Personas A/B/C/D, no external email, no real payment, internal controlled testing |
| `invited_test_mode` | Invited Test Mode | Real human tester, email invitation, Stripe test card only, no real charge |
| `controlled_live_pilot` | Controlled $1 Pilot | Real human tester, email invitation, allowlisted, hidden $1 offer, requires Ray approval |

## Invitation Lifecycle

1. **Draft** — Admin creates invitation with tester name, email, level, assignment
2. **Awaiting Approval** — Optional approval gate before sending
3. **Approved** — Admin approves the invitation for sending
4. **Sent** — Email sent via Resend (or preview generated)
5. **Accepted** — Tester accepts via token, creates password, links Auth user
6. **Completed** — Tester finishes all assigned tasks
7. **Expired** — Token expired before acceptance
8. **Revoked** — Admin revoked the invitation

## Token Security

- Tokens are 32-byte cryptographically random hex strings
- Only SHA-256 hash stored in database
- Raw token displayed only once at creation
- Single-use acceptance enforced
- Expired tokens rejected
- Revoked tokens rejected
- Token last-four stored for identification

## Schema

- `tester_invitations` — Core invitation table with 30+ fields
- `payment_pilot_allowlist` — Pilot purchase allowlist entries
- `payment_pilot_controls` — Singleton row for system-wide controls
- `pilot_disclosures` — Pilot disclosure acceptances
- `invitation_events` — Audit log for all invitation state changes
- `invite_email_drafts` — Email draft tracking

## RLS Policies

- **Admin:** Full CRUD on all invitation tables
- **Tester:** Can read only their own accepted invitation
- **Anonymous:** Cannot list, enumerate, or access invitation data
- **Client:** Cannot access tester invitations unless they are the assigned tester

## Email Templates

- `tester_invitation` — Branded invitation with assignment details
- `invitation_reminder` — Reminder before expiration
- `invitation_revoked` — Revocation notification
- `invitation_accepted` — Welcome confirmation
- `test_session_complete` — Completion confirmation

## Current Status

- **Invitations:** Foundation created, ready for admin creation
- **Test Mode Purchases:** Enabled after certification
- **Controlled Live Pilot:** Disabled, requires separate activation
- **Public Live:** Disabled, requires separate launch process
- **Emergency Disable:** Available, admin-only toggle

## Security Verification

- No raw tokens in logs or reports
- No passwords stored in invitation records
- No service-role credentials in frontend
- No real payment processed
- No public live checkout enabled
- No automatic email without admin action
- All state changes audit-logged
