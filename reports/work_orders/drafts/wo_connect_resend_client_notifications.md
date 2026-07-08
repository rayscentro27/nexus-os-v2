# Work Order: Connect Resend Client Notifications

**Status:** Draft
**Priority:** Medium
**Created:** 2026-07-07

## Goal
Send client-facing emails via Resend for key portal events.

## Why It Matters
Testers need welcome emails, status updates, and review completion notifications.

## Scope
- Welcome email on signup/account creation
- Document upload confirmation
- Admin review request confirmation
- Review completion notification
- Status update notifications

## Acceptance Criteria
- Emails sent via Resend API
- Templates stored and versioned
- Unsubscribe link included
- Client email preferences respected
- No emails sent in preview/demo mode

## Files Involved
- `supabase/functions/` (Edge Function for email sending)
- `src/services/` (email service)
- Resend templates

## Risk Level
Low — email only, no external actions

## Test Plan
1. Create test account
2. Verify welcome email
3. Upload document, verify confirmation
4. Test unsubscribe
