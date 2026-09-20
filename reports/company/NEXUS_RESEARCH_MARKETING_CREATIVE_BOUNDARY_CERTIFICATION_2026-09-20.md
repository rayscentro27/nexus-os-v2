# Research → Marketing → Creative Boundary Certification

Date: 2026-09-20. The canonical Research runtime remained enabled throughout
this work. No new company cycle, scheduler, Nova, or Research runtime was
created.

## Research

`ALPHA_RESEARCH_MORE_EXISTING=4`:

- `alpha_receipt_7fda045e30074a0d8bb0e78628ce9ce3` →
  `alpha-model-followup:alpha_eval_49fa304447414e489bef5ee12a753f7e`
- `alpha_receipt_c0cca724f9524c9287b8f27c4037c2cc` →
  `alpha-model-followup:alpha_eval_70f109b9acad4b3f8025a9eabae58d57`
- `alpha_receipt_f995bec936e643f195c439707b1ba973` →
  `alpha-model-followup:alpha_eval_ca342bcd37c84fb69598c3aa5b7b6dfa`
- `alpha_receipt_6802083e60054a5fb2f8c7badc3f7004` →
  `alpha-model-followup:alpha_eval_697193c50dae43fca4e0724773168ef1`

All four valid follow-ups were claimed and completed. Each produced a new
package and a model-backed Alpha re-review:

- `alpha_eval_3305e8fbf06b4655a6c00cc547f57df7`
- `alpha_eval_41c0598dd13b4ae78e01b16afb731dcd`
- `alpha_eval_35c1ed0d8cde48d4878548cdedf6496f`
- `alpha_eval_0c4a382e1d284e28b686bbdacfe1ace2`

`ALPHA_FOLLOWUPS_COMPLETED=4`, `ALPHA_REREVIEWS_COMPLETED=4`,
`ALPHA_RETURN_LOOP_SUCCESS_RATE=100%`.

The earlier zero was an observation-window boundary plus priority delay, not a
worker failure. The remaining systemic weakness is duplicate follow-up
generation for the same objective/source; the duplicates were preserved as
history and not bulk-deleted.

`BROKEN_OBJECTIVE_LINKS_BEFORE=0` for the four queue parent chains. The
execution ledger still omits objective IDs on some execution events:
`OBJECTIVE_LINK_REPAIRS=execution-event linkage remains an internal defect;
queue parent links were preserved`. `BROKEN_OBJECTIVE_LINKS_AFTER=0` in the
queue lineage; execution-event omission remains open.

Queue state after reconciliation: `COMPLETE=94`, `QUEUED=19`,
`MONITORING=12`, `FAILED_RETRYABLE=5`, `PARKED=19`, `IN_PROGRESS=0`.
The queue contains 36 nonterminal rows. `STALE_ITEMS_BEFORE=24` legacy/stale
candidates identified; `STALE_ITEMS_REPAIRED=13 malformed retries parked,
plus previously identified certification fixtures parked`; 
`STALE_ITEMS_REMAINING=24` legacy/monitoring rows remain for deliberate
lineage review. `QUEUE_HEALTH_AFTER=PARTIAL_REAL`.

Customer-demand discovery ran through Last30Days and created zero needs. The
root cause was not a missing queue execution: the demand radar returned
`needs_created=0`, and several public Reddit processors completed without
extracting substantive customer language. One adjacent, low-confidence signal
was preserved rather than promoted as validated demand:

- `CUSTOMER_SIGNAL_ID=need_63cbbd67ce22bc45cb31`
- `CUSTOMER_NEED=possible cash-flow/readiness burden when small businesses take
  on large contracts`
- `AUDIENCE=small business owners taking on contracts and seeking funding readiness`
- `SOURCE_REFS=https://www.reddit.com/r/JCSOperatorSystem3/comments/1vvrabt/the_8500_janitorial_contract_that_almost_put_me/`
- `EVIDENCE_CONFIDENCE=LOW; one anecdote`
- `PROMOTION_STATUS=PERSISTED_OPEN_NEEDS_ALPHA; not validated demand`

`CUSTOMER_SIGNAL_STATUS=PARTIAL_REAL`: evidence was preserved honestly, but
the demand-discovery path did not produce a corroborated signal.

`RESEARCH_LEFT_RUNNING=YES`, `RESEARCH_FINAL_LEVEL=LEVEL_R3_RETURN_LOOPS_OPERATIONAL`.
The owner is `com.nexus.continuous-loop`, running with no active leases at the
final read. `CODEX_REQUIRED_TO_CONTINUE=NO`, `RAY_REQUIRED_TO_RESTART=NO`.

## Marketing return

The original return was preserved:

- `MARKETING_OBJECTIVE_ID=progressive-level-b-objective-20260919`
- `MARKETING_RESEARCH_REQUEST_ID=mkt_research_return_1ba3a9a0ecc7441583f6`
- `PARENT_MARKETING_ARTIFACT=marketing_artifact_068881fa0a104a3a9a26f32be472fbda`
- `RESEARCH_FOLLOWUP_WORK_ID=marketing-research-return:mkt_research_return_1ba3a9a0ecc7441583f6`
- `RESEARCH_OBJECTIVE_ID=progressive-level-b-objective-20260919`

The return completed with package `package_24ba050c3d63d535f8c2`. A missing
source-candidate defect was repaired in place, and three further public-source
strategy changes plus one Last30Days attempt were executed under the same
parent request. They produced packages `package_1eaed1f4e5fbbcdf653e`,
`package_0145abfe843c9dec8a48`, and `package_0d10acd5d5a54971c90f`; the
Last30Days attempt created zero needs.

The model-backed Marketing re-evaluation was
`mkteval_8470cfcb80d041d6889224a929d278e8` and returned
`MORE_RESEARCH_REQUIRED`: no substantive customer language, prevalence,
conversion, approval, or eligibility evidence was found.

- `MARKETING_RETURN_RESEARCH_COMPLETED=PASS_REAL_BOUNDED`
- `MARKETING_SAME_OBJECTIVE_RESUMED=NO — correctly held at evidence gate`
- `MARKETING_RETURN_STATUS=PARTIAL_REAL`
- `MARKETING_REEVALUATION_DECISION=MORE_RESEARCH_REQUIRED`
- `MARKETING_REEVALUATION_REASON=the evidence set does not support a responsible marketing claim`

`MULTI_CAPABILITY_MARKETING_STATUS=NOT_PROVEN`; the current evidence gate
prevented a second capability from being assigned. `SECONDARY_VALUE_STATUS=PARTIAL_REAL`.

`FINAL_MARKETING_ARTIFACT_ID=none accepted`; the best current internal draft
remains `mktart_8bbee0c5a71749268471a06caf4a7cf6`, but
`MARKETING_AI_ACCEPTED=NO` because the real evaluator requested more evidence.
`MARKETING_FINAL_LEVEL=LEVEL_M4_MARKETING_LOOP_CAPABLE_BOUNDED` for plan,
routing, execution, evaluation, revision, and same-objective Research return;
not operational acceptance.

## Creative boundary

The Creative boundary was intentionally not crossed:

- `CREATIVE_HANDOFF_ID=NONE`
- `CREATIVE_INBOX_RECEIVED=NO`
- `CREATIVE_CLAIMED=NO`
- `CREATIVE_MARKETING_ARTIFACT_READ=NO`
- `CREATIVE_RESEARCH_PACKAGE_READ=NO`
- `MARKETING_TO_CREATIVE_BOUNDARY_STATUS=NOT_READY — Marketing AI correctly
  withheld handoff pending evidence`

This complies with the gate requiring Marketing acceptance before Creative.

## Nova and current company flow

`NOVA_RESEARCH_STATUS=canonical queue/owner state readable`; 
`NOVA_MARKETING_STATUS=plan, work order, evaluation, and Research-return state
readable`; `NOVA_CREATIVE_HANDOFF_STATUS=not applicable; no handoff exists`.

`CURRENT_COMPANY_FLOW=CUSTOMER SIGNAL (low-confidence, not validated) →
RESEARCH → AI INVESTIGATOR → ALPHA → RESEARCH_MORE → FOLLOW-UP RESEARCH →
ALPHA RE-REVIEW → MARKETING PLAN/ROUTING/REVISION → MORE_RESEARCH_REQUIRED →
Research return remains open; Creative correctly waiting.`

`PRIMARY_REMAINING_DEFECTS=duplicate Alpha follow-up generation; incomplete
objective IDs in execution events; stale legacy monitoring rows; Reddit/source
processor often returns no substantive customer language; Marketing cannot
accept without stronger evidence.`

`EXTERNAL_BLOCKERS=none required for the internal loop; some public-source
content is unavailable or non-substantive.`

`RAY_ACTION_REQUIRED=NO`.

`NEXT_DEPARTMENT_TO_CERTIFY=Creative, only after a future Marketing
re-evaluation returns GOOD_ENOUGH or an explicitly qualified bounded internal
artifact.`

