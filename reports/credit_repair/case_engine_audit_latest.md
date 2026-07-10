# Credit Repair Case Engine Audit

- Starting commit: `f1c52d3`
- Current world-class client portal design preserved: `True`
- Old design restored: `False`

## Existing Tables Found

- `credit_report_reviews`
- `credit_dispute_items`
- `credit_dispute_letters`
- `docupost_mail_jobs`
- Earlier generic tables: `dispute_cases`, `dispute_letter_drafts`, `credit_workflow_items`
- Canonical client tables still used: `client_documents`, `client_tasks`, `readiness_scores`, `client_profiles`

## Existing Helpers / Routes Found

- `src/lib/creditRepairWorkflow.ts`: journey load, dispute item create, letter draft create, specialist review, client approval, DocuPost send request, mail job tracking.
- `/client/credit-repair-journey`: world-class premium route.
- `/client/dispute-review`: world-class shell route after prior repair.
- `/admin/credit-specialist`: existing Credit Specialist Workbench.

## What Already Worked

- Credit report upload and support document upload through shared inline upload.
- Dispute item and letter draft backbone.
- Specialist/client approval statuses.
- Approval-gated DocuPost job creation.
- Premium client shell and Clyde panel.

## Missing Before Patch

- Active case container and round tracking.
- Structured client-selected report items.
- Dispute reason selector.
- Multiple deterministic letter options.
- Strategy metadata and evidence-needed tracking.
- Outcome history and next-round learning summary.

## Migration Decision

Migration needed: `True`. Existing tables covered the letter/DocuPost backbone but not case rounds, strategy options, or outcome learning. Added an additive migration only.

## Patch Plan

- Add `credit_repair_cases`, `credit_report_items`, `credit_dispute_strategies`, `credit_dispute_letter_options`, and `credit_dispute_outcomes`.
- Add `creditRepairCaseEngine.ts` as the workflow adapter.
- Add `disputeStrategyKnowledge.ts` for deterministic strategy/option mapping.
- Embed the case engine into the current world-class Credit Repair Journey page.
- Extend the existing admin Credit Specialist Workbench.
- Add regression checks and reports.
