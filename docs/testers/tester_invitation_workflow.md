# Tester Invitation Workflow

## Overview

The tester invitation system allows administrators to invite specific testers to participate in controlled testing programs. Invitations are single-use, token-based, and include email delivery via Resend.

## Invitation Lifecycle

```
Draft → Awaiting Approval → Approved → Sent → Accepted → Completed
                                              ↓
                                         Expired/Revoked
```

## Creating an Invitation

1. Navigate to `/admin#tester-invitations`
2. Click "Create Invitation"
3. Enter tester name, email, testing level, assignment details
4. Click "Create Invitation"
5. **Copy the raw token** (displayed only once)
6. Share the acceptance URL with the tester

## Token Security

- **32-byte random token** generated per invitation
- **SHA-256 hash stored** in database
- Raw token available only at creation
- Last four characters stored for identification
- Single-use acceptance enforced
- Expired/revoked tokens rejected

## Acceptance Flow

1. Tester receives invitation email with acceptance link
2. Link format: `/tester/invite/{raw_token}`
3. Token validated server-side
4. Tester creates password (min 8 characters)
5. Auth user created via Supabase Auth
6. Invitation status updated to "accepted"
7. Tester redirected to task checklist

## Testing Levels

| Level | Description | Payment |
|-------|-------------|---------|
| `synthetic_internal` | Internal persona testing | None |
| `invited_test_mode` | Human tester, Stripe test mode | Test card only |
| `controlled_live_pilot` | Human tester, real $1 payment | Requires Ray approval |

## Email Delivery

Emails sent via Resend API:
- **Invitation:** Assignment details, acceptance link, test-mode notice
- **Reminder:** Sent before expiration
- **Revoked:** Notification of revocation
- **Accepted:** Welcome confirmation
- **Session Complete:** Thank you

If Resend is not configured, a preview-only path is available.

## Admin Actions

| Action | Available When | Confirmation Required |
|--------|---------------|----------------------|
| Create | Always | No |
| Approve | Draft/Awaiting | Yes |
| Send | Approved/Sent | Yes |
| Resend | Approved/Sent | Yes |
| Revoke | Not revoked/completed | Yes |
| Extend | Approved/Sent | No |
| Mark Completed | Accepted | Yes |

## Security Rules

- Only active admins can create/manage invitations
- Testers cannot access admin routes
- Testers cannot view other invitations
- Testers cannot self-allowlist
- No passwords stored in invitation records
- No raw tokens after initial creation
- All mutations audit-logged
