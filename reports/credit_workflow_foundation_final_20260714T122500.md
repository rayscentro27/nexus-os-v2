# Credit Workflow Foundation — Final Implementation Report

Date: 2026-07-14 (America/Phoenix)

## Scope and baseline

- Branch: `main`
- Starting commit: `f7f6b1c81116736ad6b62ec6d5ba1c1579e421d2`
- The requested `098dd1e9e1e23489ab6c8ac8440d37e08802267c` baseline was older than the actual branch. Existing later research-to-Clyde work was preserved and was not expanded in this sprint.
- Ending commit: the focused commit containing this report (recorded in the delivery closeout).
- Synthetic data only. No real report, raw report content, full account number, secret, or environment file is included.

## Architecture implemented

The upload pipeline now separates document, analysis, strategy, client-action, exception-review, and mail state. A valid `credit_report` metadata insert creates one versioned analysis job after the document row exists. Unrelated document types are not queued. A current completed version blocks an ordinary duplicate; a controlled admin rerun requires a reason and creates a preserved child attempt.

Migration `20260715140000_credit_workflow_canonical_foundation.sql` adds constrained workflows, versioned/leased job fields, automatic queueing, controlled reruns, durable sanitized events, original bureau tradelines, canonical accounts, match decisions, unmatched tradelines, and report discrepancies. It retains legacy fields for compatibility. The migration is applied to Supabase project `iqjwgpnujbeoyaeuwehj`; local and remote migration lists agree.

Every new table has RLS enabled. Client reads use existing tenant-membership ownership rules. Canonical decisions and analysis mutations are admin/server-side only. Anonymous access is not granted. No frontend service-role credential was added.

## Status and exception policy

The six status domains and their constraints match the sprint contract. Successful parsed reports backfill to `analysis_status = complete` and `exception_review_status = not_required` unless an actual exception exists. State transitions are validated by a trigger.

The shared TypeScript and Python exception policy treats ordinary collections, late payments, inquiries, utilization issues, and negative accounts as normal automated work. Low parser confidence, unreadable input, ambiguous matching, integrity failures, identity-theft assertions, complaints/legal threats, unsupported overrides, and explicit admin review are defined exceptions.

## Worker and canonical model

The worker remains bounded. Supported controls are `--once`, capped `--max-jobs`, `--dry-run`, `--job-id`, `--requeue-stale`, and `--verify-result`. It atomically claims queued work, records a lease/worker/version/attempt, recovers stale leases safely, classifies retryable versus permanent failures, uses native JSONB arrays/objects, sanitizes failures, and exits nonzero on unrecoverable processing errors. It does not contain a daemon loop or mail/DocuPost call.

Canonical matching preserves original bureau values and stores normalized values separately. Weighted factors include masked suffix, opened date, account type, creditor/original-creditor similarity, balance, status, and ownership. Creditor similarity alone can never merge records. Conflicting suffix, incompatible type, materially conflicting opened date, collector/original-creditor relationships, and ownership conflicts prevent automatic grouping. Decisions retain component scores, reasons, conflicts, threshold version, and engine version.

Initial deterministic discrepancy storage supports balance, limit, high-balance, past-due, opened date, last-reported date, account/payment status, suffix, original creditor, ownership, duplicate reporting, and bureau omission. Explanations describe differences without legal or outcome claims. Strategy matching remains intentionally out of scope.

## Synthetic fixtures and end-to-end result

Fifteen fixtures cover exact three-bureau matches, abbreviations, minor numeric/date changes, masked formats, same-creditor separate accounts, collector/original relationships, purchased debt, duplicates, omission, ambiguous suffixes, conflicting dates, incompatible types, authorized-user ownership, and unrelated accounts. All 15 passed preservation, masking, confidence, reasons, safe grouping, ambiguous retention, and rejection assertions.

Production-backed synthetic pipeline result:

- Exactly one automatically created job; status `complete`; attempt count 1
- Workflow: uploaded / complete / not_started / not_ready / not_required / not_requested
- Parser counts: 26 accounts, 3 inquiries, 26 funding-impact candidates, 2 personal-information variations, 21 structured drafts, 42 recommendations, 3 bureaus
- Native JSONB: verified
- Original bureau tradelines persisted: 26
- Canonical accounts persisted: 26
- Unmatched tradelines: 26
- Discrepancies: 0 for this source fixture
- Exceptions: 0
- Events: document_uploaded, analysis_queued, analysis_claimed, canonical_matching_completed, analysis_completed

The Alex fixture's parser output contains one extracted record per account rather than three bureau-specific copies, so the safe matcher correctly retained 26 separate/unmatched canonical records. Cross-bureau grouping and discrepancy behavior is proven by the 15 explicit synthetic fixtures without fabricating values in the uploaded fixture.

## User experience

The existing admin page now presents pipeline stages and live counts. `Pending GoClear Review` is used only when exception review is required. A completed normal report displays `Analysis Complete` and `No GoClear exception required`. Queue Analysis is a disabled recovery action while an active/current completed attempt exists. Run Report Analysis is a reasoned, confirmed, preserved rerun. Profile Review Case is exception-only, and Mark Needs Info requires a specific reason.

The client Documents Vault shows safe progress language without job IDs, raw errors, formulas, or admin notes. Credit-report uploads show Waiting for analysis / Analysis in progress / Analysis complete and only show specialist review for real exceptions.

## Verification

- `npm run build`: PASS (1,799 modules; existing large-chunk warning only)
- `npx tsc --noEmit`: PASS
- New foundation checks: 6/6 PASS
- Relevant existing parser, JSONB, environment, queue, system review, positioning, letter gate, admin guard, and authentication checks: PASS
- Static checks updated from obsolete all-reports-manual wording to the automatic/exception-only contract: PASS
- Result verifier: PASS with exact expected counts
- Supabase migration list: local/remote `20260715140000` present
- Route smoke: `/admin`, `/admin/credit-specialist`, `/client/documents`, `/client/credit-profile` all HTTP 200
- Full Vitest suite: 1,196 PASS, 1 unrelated pre-existing Alpha guard failure. The failure is in `hermes_alpha_no_supabase_guard.test.ts`, which rejects an existing same-origin `fetch('/api/alpha/url-review')` in `alphaUrlReview.ts`; neither file is part of this sprint.
- Changed-frontend scan: no service-role key or private credential
- Mail state remained `not_requested`; no mail job or DocuPost submission was created
- Worker process after testing: stopped; no daemon or scheduler created

## Known limitations and manual operation

- The bounded worker must still be invoked manually:
  `source .venv-credit/bin/activate && python3 scripts/credit/process_credit_analysis_queue.py --once`
- The current uploaded synthetic parser representation cannot demonstrate real three-row bureau grouping; dedicated fixtures cover that behavior.
- Hosted permanent parsing, research strategy matching, Clyde Strategy Cards, client strategy decisions, automated letters, DocuPost transmission, real sensitive reports, and paid launch remain out of scope/not approved.
- No production UI deployment was performed by this sprint; the database migration was applied and local production-preview routes were verified.

## Recommended next sprint

`NEXUS RESEARCH-TO-CLYDE AUTOMATION`: connect approved reusable research strategies to persisted discrepancies, Clyde Strategy Cards, client evidence/choices, gated drafts, and durable action tracking while retaining exception-only GoClear handling.
