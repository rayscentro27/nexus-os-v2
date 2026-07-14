# Client Readiness Experience

Before approval, a client with an uploaded report sees that analysis occurred and GoClear is reviewing recommendations. Raw system classifications remain hidden by RLS. After a system review is marked `approved_summary` and `client_visible`, the canonical client adapter can read only the approved summary, utilization actions, report items, evidence requests, next steps, and Tier impacts.

Business Profile shows deterministic Tier 1/Tier 2 profile status. Funding Readiness combines Credit Profile and Business Profile. Clyde can explain utilization, evidence needs, report-item review, Credit Profile completion, and Tier blockers without claiming inaccuracy, score change, item removal, or approval.

## Windows manual test

1. Sign in to `/admin/login`, open `/admin/credit-specialist`, and select the fake uploaded report.
2. In DevTools Network, confirm Supabase requests use `iqjwgpnujbeoyaeuwehj.supabase.co`.
3. Open Report Analysis and verify 26 accounts, 3 inquiries, and 26 review candidates; refresh once.
4. Verify the system review shows 31 funding-impact items, 3 inquiry reviews, 31 evidence requests, and 28 specialist exceptions.
5. Exercise Confirm, Edit, Reject, and Request Client Evidence; verify Prepare Draft Letter is disabled until a letter-eligible recommendation is confirmed.
6. Confirm Draft Letters and Mail Queue still require review/client authorization and nothing is auto-sent.
7. Test `/client/credit-profile`, `/client/business-setup`, and `/client/funding-readiness`; confirm readiness language and no guarantee claims.
8. Smoke `/admin`, `/admin/command-center`, `/admin#credit-specialist`, `/client/dashboard`, `/client/credit-utilization`, `/client/credit-repair-journey`, `/client/dispute-review`, `/client/documents`, and `/client/resources`.
