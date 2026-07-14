# Credit Workflow Foundation Audit — 2026-07-14

## Baseline

- Repository: `/Users/raymonddavis/nexus-os-v2`
- Branch: `main`
- Actual starting commit: `f7f6b1c81116736ad6b62ec6d5ba1c1579e421d2`
- The requested `098dd1e` baseline is an ancestor. Newer committed Research-to-Clyde work is preserved, not expanded or rolled back.
- Existing unrelated runtime, cache, Alpha, Telegram, research, and work-order changes are unstaged and will remain untouched.

## Current tables and status fields

- `client_documents`: generic `status` and `goclear_review_status`; uploads write `pending_review` for all categories.
- `credit_report_parser_results`: parser `status`, `extraction_success`, native JSONB arrays/objects, parser version, document/client/tenant linkage.
- `credit_analysis_jobs`: one `status` field (`queued`, `processing`, `complete`, `failed`, `needs_manual_review`), timestamps, attempt count, result links. Active uniqueness is document-only.
- `credit_report_system_reviews`: review `status`, `needs_specialist_review`, `client_visible`, JSONB review sections.
- Existing strategy, decision, tool, and outcome tables are newer committed functionality and outside this sprint’s implementation boundary.
- Letter and DocuPost tables retain separate gated statuses.

## Current paths

- Upload → `DocumentUploadZone.tsx` uploads storage first, then inserts `client_documents` metadata.
- Upload does not create an analysis job automatically; admin must click Queue Analysis.
- Queue → `creditRepairWorkflow.ts` inserts `credit_analysis_jobs` from the browser under admin RLS.
- Worker → `process_credit_analysis_queue.py` selects queued rows, conditionally patches to processing, invokes the parser subprocess, links newest parser/system-review rows, and marks complete/failed.
- Parser → `parse_uploaded_credit_report.py` downloads storage server-side, parses, saves native JSONB, reads it back, and fails on count mismatch.
- Database → admin uses `loadPendingCreditReportReviews`, `loadLatestAnalysisJob`, `loadParserResultForDocument`, and `loadSystemReviewForDocument`.

## Risks found

- `pending_review` conflates upload, analysis, strategy, client action, exception review, and mail readiness.
- Every uploaded document is presented as pending GoClear review, including successful normal reports.
- No server-side post-upload enqueue mechanism.
- Active uniqueness ignores analysis type/parser version; completed-version idempotency is not enforced.
- Controlled reruns have no parent attempt, reason, or preservation contract.
- Worker claims have no lease owner/expiry, max attempts, worker/ruleset version, structured retry classification, or stale recovery.
- Parser results are updated in place by document, creating stale-result/audit ambiguity even though JSONB count verification is correct.
- Canonical comparison currently exists in code but has no canonical database model preserving source tradelines, match decisions, unmatched rows, and discrepancies.

## Current RLS coverage

- `client_documents` uses tenant membership policies from the portal migrations.
- Parser results, jobs, and system reviews are RLS-enabled with active-admin write policies.
- Clients can read only explicitly client-visible approved review summaries.
- Service-role use is confined to Python/server-side scripts; no frontend service-role credential was found.

## Additive plan

1. Add a one-to-one document workflow row with separate constrained statuses and transition validation.
2. Add a security-definer upload trigger that creates the workflow and exactly one versioned credit analysis job only after valid credit-report metadata persists.
3. Add job idempotency, versioned controlled reruns, leases, attempts, retry classification, and audit events.
4. Add immutable source tradelines, canonical accounts, match decisions, unmatched records, and discrepancies with RLS.
5. Persist deterministic normalization and confidence-based matching from the bounded worker without mutating parser JSONB.
6. Replace automatic “Pending GoClear Review” display with pipeline status and exception-only labels.
7. Verify the Alex Morgan synthetic counts and newest-result integrity with a non-PII verifier.
