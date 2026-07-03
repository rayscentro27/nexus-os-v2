# Hermes Access Map Live Verification

Date: 2026-07-02

Local verification covers registry completeness, route behavior, safe action metadata, UI allowlisting, build, and automated tests. No production mutation or paid API was used.

Live authenticated verification remains required for:

- `client_profiles` access and row status
- `task_requests` and `approvals` current counts
- research runs and sources
- Stripe and Resend configuration status
- deployed Netlify commit/version
- live specialist runtime inventory

Recommended production sequence: sign in through the approved app flow; ask “what can Hermes access”; open Reports and Ray Review actions; check system health in CEO then audit mode; verify clients and provenance; confirm buttons only navigate; compare the access matrix against authenticated read results.

