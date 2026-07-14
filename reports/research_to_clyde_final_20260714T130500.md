# Nexus Research-to-Clyde Automation v1 — Final Report

## Executive summary

Research-to-Clyde v1 extends the existing Nexus research inbox, credit strategy tables, canonical credit workflow, Documents Vault, Clyde cards, and admin workbench. Public discovery remains isolated in Alpha; only governed Nexus strategy versions can match structured discrepancies. Client selections, evidence links, safe drafts, exceptions, and audit events are durable and tenant-scoped. No mail or DocuPost action is created.

- Starting commit: `717f4bf40e133fdad31ad7a01db4a075330e794d`
- Branch: `main`
- Ending commit/push: recorded in final delivery closeout after the focused commit
- Migrations: `20260715150000_research_to_clyde_v1.sql`, `20260715151000_research_to_clyde_rls_hardening.sql`
- Migration state: applied to Supabase project `iqjwgpnujbeoyaeuwehj`; local/remote histories agree

## Deployment and Alpha repair

Netlify CLI deployment lookup did not return metadata and hung until terminated; GitHub had no deployment records. Deployment of the starting commit therefore cannot be claimed. Local production preview returned HTTP 200 for `/`, `/admin`, `/admin/credit-specialist`, `/client/documents`, and `/client/credit-profile`.

The prior Alpha failure was reproduced. Root cause: the static guard allowed the same-origin provider/search bridges but omitted the existing same-origin URL-review bridge. The guard now explicitly recognizes that bridge and verifies it contains no provider URL/key. The server URL validator was hardened to reject malformed/relative URLs, credentials, non-HTTP protocols, localhost, loopback, link-local, and private IPv4/IPv6 ranges. Alpha remains unable to access Supabase/client data. Isolated Alpha/security result: 23/23 PASS.

## Reused architecture and registries

The existing Nexus Research adapter/inbox, `credit_strategy_sources`, `credit_strategy_claims`, `credit_strategy_definitions`, bounded research queue, evidence scorer, strategy catalog/matcher, Clyde card engine, recommendation/decision/tool tables, Documents Vault, canonical discrepancies, readiness engine, and workflow events remain canonical.

Source records now carry provenance, hashes/duplicates, authority, reliability, promotional risk, sanitized summaries, and controlled processing states. Claims separately retain excerpts/locations, claim types, authorities/contradictions, deterministic evidence and risk, promotional/guarantee/universal/legal flags, client-safety, approval, and rejection reason. Rejected claims remain in history.

Immutable strategy versions store eligibility/inapplicability, required client facts/evidence, discrepancy/account applicability, evidence/risk, limitations/disclaimers/prohibited wording, permitted outputs, approval/retirement, reviewer, and review date. Client matching requires an approved, non-retired exact version.

## Credit Coach Q and approved strategies

The existing summarized fixture was ingested in place—no parallel source and no transcript invention. Live registry state: one YouTube practitioner/promotional source, reliability 20, promotional risk 90, 20 claims, 12 discovery leads, 8 rejected promotional claims, and zero claims marked client-safe. It was not auto-approved.

Six version-1 frameworks were approved by Ray's explicit sprint directive:

1. Cross-Bureau Balance Review
2. Purchased Debt Documentation Review
3. Original Creditor Information Request
4. Cross-Bureau Status Review
5. Cross-Bureau Date Review
6. Duplicate Account Review

The worker queries these governed versions before matching. Match rows preserve exact strategy version, score/reasons, exclusions, ruleset, report/account/discrepancy, and client visibility. Low-confidence inputs receive no automatic strategy.

## Clyde, client decisions, evidence, and drafts

Clyde Strategy Cards show Nexus-detected facts, exact bureau values, approved strategy/version, why it may apply, evidence level, uncertainty, limitations, evidence needs, readiness impact, client-only factual questions, relevant choices, and permitted tools. Detected values are not turned into client comparison questions.

Selections preserve tenant/client/report/account/discrepancy/match/strategy/version, option, answers, consent/authorization, revision, and immutable history. RLS requires membership plus a client-visible match to an approved, non-retired exact version. Clients cannot alter research, approval, matches, discrepancies, or mail.

Inline evidence upload reuses Documents Vault validation/storage. Successful metadata inserts now return the document ID so it can be linked to the selection. Evidence-link RLS verifies membership, selection ownership, and document tenant/client ownership. Alpha receives no evidence.

Safe outputs use structured detected facts, client-confirmed facts, masked references, exact strategy/template versions, provenance, and disclaimers. The validator blocks guarantees, universal deletion, automatic damages, “must delete,” blanket disputes, and universal original-contract claims. Drafts require client review, start unauthorized, and structurally keep `mail_created=false`.

## Funding readiness and exceptions

Cards use only `ready_to_review`, `almost_ready`, `action_needed`, or `insufficient_information`; v1 cards show `action_needed` for an unresolved discrepancy. They explain Credit Profile and Tier 1/Tier 2 relevance without promising score, deletion, approval, or funding.

Research-to-Clyde exceptions include no approved strategy for a high-impact discrepancy, conflicts, low-confidence discrepancy/match, contradictory evidence, identity-theft signals, complaints/legal threats, generation/integrity failure, blocked drafts, and explicit client requests. Ordinary negatives, collections, balance differences, approved selections, evidence requests, and safe drafts remain automated normal cases.

The admin Research & Strategies workspace displays sources, claims, governed versions, client activity, and genuine exceptions. Approve/reject/request-changes/retire actions require confirmation and notes and write an audit event.

## Synthetic end-to-end proof

The new entirely synthetic fixture has six bureau tradelines:

- Account A: three bureau rows → one canonical account; balance, status, and reporting-date discrepancies
- Account B: same creditor, different suffix/date → separate canonical account
- Account C: two collector rows → one canonical account; ownership/reporting-date differences and bureau omission

Totals: 6 tradelines → 3 canonical accounts → 6 objective discrepancies → 5 approved strategy matches. Formatting-only masked suffix differences are normalized and do not create false discrepancies. Normal case exception count is 0. A low-confidence/no-approved-strategy case produces a clear exception and no match. Clyde guidance, selection state, evidence link schema, masked safe draft, readiness status, and audit event contracts are covered deterministically. No live mail job or DocuPost submission was created.

## Verification

- `npm run build`: PASS, 1,799 modules; existing chunk-size warning only
- `npx tsc --noEmit`: PASS (included by build and run directly during implementation)
- Full Vitest: 76 files, 1,215 tests PASS
- First full run had three transient 5-second import timeouts; all 70 affected tests passed isolated and the complete rerun passed 1,215/1,215
- New Research-to-Clyde synthetic tests: 8 PASS
- Alpha URL/guard tests: PASS
- New static RLS/boundary check: PASS
- 19 existing parser, readiness, strategy, authentication, admin, and security checks: PASS
- Credit Coach Q dry/live ingestion: PASS; duplicate hash reused
- Bounded worker: PASS, no queued job; exited normally
- Worker/preview process state: stopped
- Secrets/bundle scan and staged-diff scan: recorded before commit

## Known limitations and manual actions

- Netlify deployment metadata could not be verified; Ray should confirm the deploy commit in Netlify after push.
- The full production-backed client selection/evidence interaction still requires an authenticated synthetic browser session; local deterministic integration and production schema/RLS were verified.
- The worker remains manually bounded: `source .venv-credit/bin/activate && python3 scripts/credit/process_credit_analysis_queue.py --once`.
- Real sensitive reports, autonomous research approval, legal conclusions, automatic mailing, and paid-client launch are not approved.

Recommended next sprint: authenticated synthetic browser certification plus outcome analytics—exercise the deployed Strategy Card selection/evidence/draft lifecycle under client and admin JWTs, verify signed evidence access expiration, and begin non-causal strategy outcome reporting.
