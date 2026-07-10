# World Class Client Portal Activation Audit

- Current active design file: `src/pages/client/WorldClassClientPortal.jsx`
- Current design stylesheet: `src/styles/world-class-client-portal.css`
- Hero asset path preserved: `/assets/client-portal/nexus-funding-path-hero.png`
- Clyde panel preserved: `True`
- Premium sidebar/cards/upload hub/funding flow preserved: `True`

## Static Gaps Found

- Profile page cards were visual-only; Edit buttons did not load or save profile intake.
- Documents page used premium upload hub visuals but did not embed the live `DocumentUploadZone`.
- Quick Upload buttons were static.
- Request Review form was static and did not insert a review request into `client_tasks`.
- Credit Repair Journey used static progress, not `loadCreditRepairJourney`.
- Clyde recommendations were fixed preview text, not generated from current client state.
- Several Resources and recommendation buttons lacked route actions.
- Live document/business/partner offer rows were only partially normalized into the premium UI.

## Existing Live Helpers Reused

- `loadClientPortalLiveData`
- `loadClientProfileIntake`
- `saveClientProfileIntake`
- `checkProfileIntakeComplete`
- `DocumentUploadZone`
- `resolveClientContextForCurrentUser`
- `loadCreditRepairJourney`
- `generateClientGuidance`
- Existing `/client/dispute-review` shell remains preserved for DocuPost approval-gated review.

## Repair Plan Applied

- Keep `WorldClassClientPortal.jsx` as the active client portal shell.
- Add route helpers with `onNavigate` plus browser fallback.
- Keep real routes for sidebar navigation and `/client/credit-utilization`.
- Embed live profile intake form inside the premium Profile page.
- Embed `DocumentUploadZone` inside the premium Documents upload hub.
- Add suggested-upload CTAs that route to `/client/documents?from=...&suggested=...`.
- Add Request Review submit flow that inserts `pending_admin_review` rows into `client_tasks`.
- Load Credit Repair Journey state and reflect current/completed steps in the premium journey.
- Generate Clyde recommendations from live client state and route each recommendation to the relevant page.
- Keep `/client/dispute-review` on the existing workflow shell so DocuPost is never auto-sent.

## Safety Notes

- No schema changes were made.
- No RLS changes were made.
- No service role was added to frontend code.
- No SSN, full DOB, bank account number, or credit card collection was added.
- Client-facing UI continues to use `Resources` and `Recommended Tools`, not affiliate language.
