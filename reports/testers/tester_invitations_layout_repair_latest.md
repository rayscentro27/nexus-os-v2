# Tester Invitations Layout Repair Certification

Timestamp: 2026-07-16T21:25:42Z

Starting commit: `1d1b144f07c059d2dc6495398c73c4cbabe2a22b`

Recovery checkpoint: crash recovery decision was `SAFE TO CONTINUE AFTER SMALL REPAIR`; the compact invitation-page worktree was preserved and continued in place.

## Files Continued

- `src/components/TesterInvitationPanel.jsx`
- `src/admin/NexusAdminUI.jsx`
- `src/admin/nexusAdminUI.css`
- `src/pages/tester/TesterTasksPage.tsx`
- `tests/e2e/tester-invitations-layout-certification.spec.ts`
- `tests/e2e/tester-invitation-certification.spec.ts`
- `tests/e2e/friends-family-preview-certification.spec.ts`
- `tests/e2e/human-invited-tester-certification.spec.ts`
- `tests/e2e/invited-payment-pilot-certification.spec.ts`
- `tests/tester_invitation.test.ts`

Left uncommitted by decision:

- `playwright.config.ts`: global timeout increase was not required for the verified release scope.
- `tests/e2e/authenticated-certification.spec.ts`: unrelated wait-time adjustment was not required for this layout repair.
- `reports/testers/tester_invitations_layout_crash_recovery_latest.md`: preserved as crash-audit history.

## Root Causes And Fixes

Hermes overlap root cause: the floating Hermes launcher occupied the same desktop content plane as the compact tester invitation panel and drawer.

Hermes fix: route-scoped the tester invitations admin page, compacted the Hermes launcher on that route, moved page content above the topbar interception plane, preserved focus visibility, and hid the launcher while the create drawer is open. Geometry tests prove zero intersection with primary content and drawer surfaces.

Mobile shift root cause: the admin sidebar was hidden on mobile, but the shell content still retained the desktop second-column placement. This shifted the tester invitation panel horizontally off viewport.

Mobile shell fix: route-scoped the mobile shell grid and content placement so the sidebar reserves no width and content starts at x >= 0. The route now asserts no horizontal overflow.

Drawer behavior: desktop uses a right-side drawer with sticky header/footer; mobile uses a full-screen sheet with safe-area footer padding.

Form behavior: desktop keeps two-column fields where appropriate; mobile forces a single-column form below the mobile breakpoint.

Create-flow preview: creation now runs through details, email preview, and confirmation states. Preview includes sender, masked recipient, subject, rendered copy, invitation type disclosure, personal message, canonical `goclearonline.cc` badge, and a safe acceptance-link preview without raw tokens, passwords, localhost, or Netlify links. Sending remains approval-gated.

## Viewport Certification

Visual screenshots were captured outside the repository under `/tmp/nexus-os-v2-layout-cert`.

| Viewport | Horizontal overflow | Panel in viewport | Hermes overlap | Bottom bar overlap | Drawer in viewport | Mobile single column |
| --- | --- | --- | --- | --- | --- | --- |
| 1920x1080 | none | pass | 0 intersection | 0 intersection | pass | n/a |
| 1440x900 | none | pass | 0 intersection | 0 intersection | pass | n/a |
| 1280x720 | none | pass | 0 intersection | 0 intersection | pass | n/a |
| iPhone 390x844 | none | pass | 0 intersection | 0 intersection | pass | pass |

## Regression Classification

Starting invitation regression result from the recovery handoff: 76 passed, 17 failed.

Observed rerun before repair: 98 passed, 26 failed across the expanded six-suite invitation set.

Failure classes:

- Genuine layout defect: topbar/Hermes content-plane overlap affecting the Create Invitation button and invitation content.
- Genuine mobile defect: mobile admin shell kept desktop column offset.
- Expected UI contract update: inline create form became a drawer/sheet.
- Obsolete source-string expectations: payment config fields, email template wording, plain-text representation, compact payment-control labels.
- Route expectation mismatch: legacy `/tester/invite` and `/tester/accept` manual-token tests were updated to the one-click `/invite/:token` and `/invite/accept?token=...` flow.

No valid RLS, canonical-domain, raw-token, live-payment, tester/admin isolation, hidden-offer, or allowlist safety expectations were removed.

## Verification Results

- TypeScript: `npm run typecheck` PASS.
- Build: `npm run build` PASS; existing Vite chunk-size warnings only.
- Vitest: `npx vitest run` PASS, 83 files and 1,389 tests.
- Outcome checker: `python3 scripts/checks/check_outcome_analytics.py` PASS.
- Layout Playwright: `tests/e2e/tester-invitations-layout-certification.spec.ts` PASS, 6 tests.
- Invitation Playwright: six invitation-related suites PASS, 124 tests.

Security and payment state:

- Canonical customer-facing domain remains `goclearonline.cc`.
- Netlify and localhost customer-facing links were rejected by certification tests.
- Raw invitation tokens are not exposed in email delivery or create-flow preview.
- No frontend service-role, Stripe live key, or webhook secret exposure was detected by the targeted tests.
- Live payment state remains disabled.
- Controlled live pilot remains disabled by default.
- Public live remains disabled.

## Release Decision

GO.

The tester invitations admin layout is compact on desktop, mobile-aligned, free of Hermes and bottom-bar overlap, backed by authenticated browser geometry assertions, and invitation regressions are passing.
