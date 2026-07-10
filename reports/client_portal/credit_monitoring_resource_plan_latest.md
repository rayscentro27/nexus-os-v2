# Credit Monitoring Resource Plan

- Current status: gated frontend card.
- Secure provider configured: `False`
- Backend/OAuth provider route verified: `False`

## Active Client Experience

- Shows “Credit monitoring connection is coming soon.”
- Offers “Upload credit report instead.”
- Offers “View recommended monitoring resources.”
- Secure connect button is disabled until backend/provider support exists.

## Security Boundaries

- No credit bureau usernames/passwords are collected.
- No SSN or full DOB is collected.
- No claim is made that live credit score linking is active.

## Future Integration Needed

- Secure provider contract.
- Backend/OAuth initiation endpoint.
- RLS-safe storage of provider status, not raw credentials.
