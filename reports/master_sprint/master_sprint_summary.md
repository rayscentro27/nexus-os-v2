# Master Sprint — Website Business-Model Alignment

**Start:** `131226e` (origin/main)
**Status:** `NEXUS_WEBSITE_BUSINESS_MODEL_ALIGNMENT_RETEST_READY`

This sprint audited the existing website against the new operating model and implemented the
highest-priority changes in the same pass:

> **GoClear** = public brand / lead gen / education / sales · **Nexus OS** = CRM, portal, compliance,
> workflow, billing verification, business foundation, funding readiness, funding pipeline ·
> **CRJ / DisputeForMe** = outsourced credit-dispute fulfillment · **Hermes** = client guidance
> (client-facing brand **Clyde**) · **Alpha** = marketing research without client PII.

## What was already in the working tree (preserved)
`ClientPortalShell.jsx` and `WorldClassClientPortal.jsx` carried uncommitted work that introduced the
five-stage nav and the outsourced-fulfillment language. It was preserved, completed, tested, and
committed as part of this sprint. No unrelated dirty files were reset.

## Implemented this sprint

- **Five-stage client journey** wired end to end: Credit Review → Credit Improvement → Business
  Foundation → Funding Readiness → Funding Access (+ Documents, Messages, Resources, Billing).
  Legacy routes remain routable as aliases for deep links and certification flows.
- **Dashboard** = guided command center (five-stage progress, Your Next Step, Clyde guidance,
  monthly progress, contextual upload).
- **Credit Review** aligned: Nexus analyzes; the fulfillment provider fulfills. No dispute is
  written/mailed from this page.
- **Credit Improvement (NEW)** — client-facing outsourced fulfillment status page: simplified states,
  current round, expected milestone, documents needed, next client action, verified outcomes,
  outcome verification (Verified deletion / Non-deletion change / Review required), next step
  toward funding. Rendered via `buildFulfillmentView` in `src/lib/clientStageModel.ts`.
- **Funding Access (NEW)** — readiness confirmation gate, recommended funding sequence,
  application status (no live submissions — labeled), offers tracked only when verified, next step.
- **Billing (NEW)** — readiness-review payment records + proposed pay-per-delete charges gated by
  outcome verification (`billingVisibility`); a deletion is never billable without verified support.
- **Messages & Clyde (NEW)** — Hermes guidance hub; chat drawer on every page.
- **Admin Outsourced Fulfillment Center (NEW)** — manual controlled bridge (no automated CRJ API):
  13 internal workflow states, case table with all Phase 14 fields, synthetic demo records only,
  local-state status updates.
- **Compliance foundation (NEW)** — `src/lib/clientComplianceModel.ts` data contract
  (agreement version, disclosures, signatures, cancellation, payment authorization, consents,
  marketing source, vendor authorization, retention date). Placeholders only; nothing certified.
- **Language audit** — old Nexus-performs-disputes wording removed from visible surfaces; no
  guarantees promised. Client-facing advisor surfaces branded **Clyde** per the existing naming
  policy test.

## Tests

- `tsc --noEmit` + `vite build` pass (pre-existing chunk-size warning only).
- Unit suite: **107 passed / 2 failed (pre-existing)** — `alpha_telegram_worker` and
  `nexus_telegram_inbound_router` fail identically on clean HEAD (live telegram runtime data);
  verified via worktree. Flaky timeouts (`seed_validation`, `supabase_connection_truth`) also
  reproduce on HEAD.
- Sprint-fixed: `phase3_1_and_phase4` nav assertion (8→10 five-stage nav), `client_clyde_naming_upgrade`
  (Hermes→Clyde rebrand), and a build-blocking `FulfillmentInput.resultsReceived` TS error.
- Infra-gated e2e certification specs updated to the new model and parse-clean; full run needs
  `E2E_ENABLE_AUTHENTICATED` + synthetic personas.
- Browser smoke test (preview): Dashboard, Credit Improvement, Funding Access, Billing, Messages all
  render with zero console errors and no horizontal overflow.

## Security

Supabase Auth, RLS, tenant isolation, AdminGuard/ClientPortalGate, and admin allowlist all
unchanged. The new admin panel renders behind existing guards; demo records are labeled synthetic;
CRJ vendor notes are admin-only; client-facing states are simplified.

## Next phase

**MARKETING DEPARTMENT** — connect campaigns to landing pages, offers, lead capture, readiness
review, and client onboarding. Later: persist CRJ bridge records; compliance e-sign with
attorney-approved documents.
