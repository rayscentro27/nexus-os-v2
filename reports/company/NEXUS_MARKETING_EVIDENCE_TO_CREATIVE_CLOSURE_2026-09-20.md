# Nexus Marketing Evidence Return / Creative Boundary Closure

Date: 2026-09-20  
Latest source repair: `e770cb17` plus the event-ordering repair in this run.

## Executive result

The existing Marketing objective was resumed on its original lineage and its
Research-return work was executed by the real Research worker. The returned
evidence was persisted and model-backed Alpha continued to challenge it. The
evidence still does not establish verified customer language, prevalence, or a
repeatable demand pattern. Marketing therefore remains at
`MORE_RESEARCH_REQUIRED`; acceptance was not forced and no Creative handoff was
created.

This is a truthful closure of the current return attempt, not a Marketing pass.
The canonical Research runtime remains running.

## Queue / lineage

`ACTIVE_DUPLICATE_FOLLOWUPS_BEFORE=9` — nine legacy `research-2` Alpha rows
shared the same empty-source/empty-capability shape and had no usable parent
lineage.

`DUPLICATE_FOLLOWUPS_REPAIRED=9` — rows were parked through the existing queue
lifecycle with `STALE_DUPLICATE_FOLLOWUP`; records and evidence were preserved.

`ACTIVE_DUPLICATE_FOLLOWUPS_AFTER=0` for the inspected active lineage groups.
The Alpha model review path now reuses an active row for the same objective,
evidence gap, and source set instead of creating another active row.

`FOLLOWUP_DEDUP_STATUS=PASS_REAL_BOUNDED`

`EVENT_OBJECTIVE_OMISSIONS_BEFORE=10` attributable to the first two lifecycle
events of five newly executed work items. The worker emitted CLAIMED/RUNNING
before reading the queue item.

`EVENT_OBJECTIVE_PROPAGATION_REPAIR=PASS_REAL` — queue context is hydrated
before the first event, and later events carry objective, work, parent, and
package context when available.

`EVENT_OBJECTIVE_OMISSIONS_AFTER=0` for the new event-lineage verification
execution. Historical unscoped events were not rewritten or assigned invented
objectives.

`EVENT_LINEAGE_STATUS=PASS_REAL_BOUNDED`

`STALE_ITEMS_BEFORE=24`  
`STALE_CLASSIFICATION=13 malformed/source-blocked or legacy rows; 9 duplicate
legacy Alpha follow-ups; 1 known CRJ fixture among the preserved lifecycle
records.`

`STALE_REPAIRS=terminalized proven completed rows, parked legacy/invalid rows,
parked exact duplicate follow-ups, and classified provider/video failures as
BLOCKED_EXTERNAL. No evidence was deleted.`

`STALE_ITEMS_AFTER=0` using the >=24-hour nonterminal stale criterion.

Current queue snapshot: `COMPLETE=100`, `PARKED=33`,
`BLOCKED_EXTERNAL=4`, `MONITORING=8`, `QUEUED=13`, `IN_PROGRESS=0`.
`QUEUE_HEALTH_AFTER=PARTIAL_REAL`: no active leases or unexplained >=24-hour
stale rows remain, but monitoring backlog and queued Alpha returns still need
ongoing bounded processing.

## Customer signal

`CUSTOMER_SIGNAL_ID=need_63cbbd67ce22bc45cb31`  
`ORIGINAL_CONFIDENCE=LOW`  
`ADDITIONAL_SOURCES=Reddit small-business/funding discussions, SBA loans,
Federal Reserve Small Business Credit Survey, and the existing public web
sources in the Marketing handoff.`

`CORROBORATION_COUNT=0` for independent customer-language occurrences. The
official SBA/Federal Reserve sources support the funding-readiness context but
do not prove that customers expressed the same pain. The Reddit sources were
processed, but the worker interpretations found no substantive repeated
customer wording.

`REPEATED_PATTERN=NOT_ESTABLISHED`  
`UPDATED_CONFIDENCE=LOW`  
`CUSTOMER_SIGNAL_STATUS=PARTIAL_REAL`

The signal remains useful as a bounded hypothesis, not validated demand.

## Marketing evidence return

`MARKETING_OBJECTIVE_ID=progressive-level-b-objective-20260919`  
`MARKETING_ARTIFACT_ID=mktart_8bbee0c5a71749268471a06caf4a7cf6`  
`MARKETING_EVALUATION_ID=mkteval_2018996de33d4f388e2cf2bb27e5304c`

`MARKETING_EVIDENCE_GAPS=`

1. Verified customer-language evidence about funding-readiness requirements.
2. Independent demand occurrences showing a repeatable pattern rather than one
   anecdote.
3. Frequency/prevalence or outcome evidence.
4. Evidence supporting any approval, eligibility, conversion, or effectiveness
   claim.

The existing Marketing Research-return request was preserved:

`MARKETING_RESEARCH_REQUEST_ID=mkt_research_return_1ba3a9a0ecc7441583f6`  
`RESEARCH_WORK_ID=marketing-research-return:mkt_research_return_1ba3a9a0ecc7441583f6`

That work and its strategy-changing child investigations completed on the same
Marketing objective. Additional source-backed workers executed with the
following packages: `package_24ba050c3d63d535f8c2`,
`package_1eaed1f4e5fbbcdf653e`, `package_0145abfe843c9dec8a48`, and
`package_0d10acd5d5a54971c90f`. The latest event-lineage verification also
persisted `package_24ba050c3d63d535f8c2` and a fresh Alpha receipt
`alpha_receipt_0cf074a0134443b0bcf153f694d55eaa`.

`REQUIRED_CAPABILITIES=WEB_ACQUISITION`  
`SELECTED_EXECUTORS=research.scheduled_research_router.process_scheduled_item`
  
`SOURCES_USED=Last30Days attempt, Reddit/public web, SBA loans, Federal Reserve
Small Business Credit Survey, and strategy-changing small-business sources.`

`NEW_EVIDENCE=public sources were acquired and persisted; the worker’s AI
interpretations consistently reported that the sources did not contain enough
substantive customer language to validate the hypothesis.`

`UPDATED_RESEARCH_PACKAGE_ID=package_24ba050c3d63d535f8c2`  
`ALPHA_DECISION=RESEARCH_MORE`  
`ALPHA_EVIDENCE_ASSESSMENT=source processing succeeded, but evidence remains
insufficient for a validated demand claim.`  
`ALPHA_SECONDARY_VALUE=education/readiness content remains a possible bounded
secondary use, but it is not evidence of demand or a basis for external claims.`

`ORIGINAL_MARKETING_OBJECTIVE_ID=progressive-level-b-objective-20260919`  
`RESUMED_MARKETING_OBJECTIVE_ID=progressive-level-b-objective-20260919`  
`SAME_OBJECTIVE=YES`  
`MARKETING_RESUMED=YES_FOR_REEVALUATION; NOT_ACCEPTED`

`MARKETING_REEVALUATION_ID=mkteval_2018996de33d4f388e2cf2bb27e5304c`  
`MARKETING_REEVALUATION_DECISION=MORE_RESEARCH_REQUIRED`  
`MARKETING_REEVALUATION_REASON=direct complaint frequency, independent demand
pattern, and outcome/conversion evidence remain unverified.`

`FINAL_MARKETING_EVALUATION_ID=mkteval_2018996de33d4f388e2cf2bb27e5304c`  
`FINAL_MARKETING_DECISION=MORE_RESEARCH_REQUIRED`  
`FINAL_MARKETING_ACCEPTANCE=NO`

## Marketing capability and Creative boundary

`MULTI_CAPABILITY_MARKETING_STATUS=NOT_PROVEN_IN_THIS_CLOSURE`

`PRIMARY_THESIS=educational funding-readiness guidance for new LLC owners.`  
`PRIMARY_DECISION=not sufficiently evidenced for acceptance or external use.`
  
`SECONDARY_VALUE_OPTIONS=education, SEO/content, comparison, referral/lead
generation, and customer-language discovery.`  
`SELECTED_SECONDARY_USE=bounded internal education hypothesis only.`  
`SECONDARY_ARTIFACT=none newly accepted because the evidence gate remained
open.`  
`SECONDARY_VALUE_STATUS=PARTIAL_REAL`

`FINAL_MARKETING_ARTIFACT_ID=mktart_8bbee0c5a71749268471a06caf4a7cf6`  
`FINAL_MARKETING_ARTIFACT_PATH=data/runtime/marketing_ai_orchestration/artifact_mktart_8bbee0c5a71749268471a06caf4a7cf6.json`  
`MARKETING_AI_ACCEPTED=NO`

`MARKETING_FINAL_LEVEL=LEVEL_M4_MARKETING_LOOP_CAPABLE_BOUNDED`

Because Marketing did not accept the evidence, the required safety gate held:

`CREATIVE_HANDOFF_ID=NONE`  
`CREATIVE_HANDOFF_STATUS=NOT_CREATED_BY_POLICY`  
`CREATIVE_WORK_ID=NONE`  
`MARKETING_TO_CREATIVE_BOUNDARY_STATUS=NOT_RUN — correctly blocked at the
Marketing acceptance gate.`

## Nova and runtime

`NOVA_RESEARCH_RETURN_VISIBLE=PASS_REAL_BOUNDED` through canonical Research
queue/package/Alpha state.  
`NOVA_MARKETING_OBJECTIVE_VISIBLE=PASS_REAL_BOUNDED` through the persisted
Marketing plan/evaluation/artifact lineage.  
`NOVA_MARKETING_DECISION_VISIBLE=PASS_REAL_BOUNDED` — current decision is
`MORE_RESEARCH_REQUIRED`.  
`NOVA_CREATIVE_HANDOFF_VISIBLE=NOT_APPLICABLE — no handoff exists.`

`RESEARCH_RUNTIME_OWNER=com.nexus.continuous-loop`  
`RESEARCH_LEFT_RUNNING=YES`  
`CURRENT_QUEUE_DEPTH=21` (13 queued plus 8 monitoring; no active leases)  
`CURRENT_ACTIVE_LEASES=0`  
`LAST_PRODUCTIVE_RESEARCH=research_exec_event_lineage_46e293cafc` with package
`package_24ba050c3d63d535f8c2`  
`LAST_ALPHA_RESULT=alpha_receipt_0cf074a0134443b0bcf153f694d55eaa / RESEARCH_MORE`

`CODEX_REQUIRED_TO_CONTINUE=NO`  
`RAY_REQUIRED_TO_RESTART=NO`

## Remaining work

`PRIMARY_REMAINING_DEFECTS=public-source extraction is too often
non-substantive; customer-demand promotion has no independently corroborated
signal; monitoring/queued Alpha work needs bounded continuation; historical
execution records remain unscoped but are preserved.`

`EXTERNAL_BLOCKERS=some provider/source content is inaccessible or too thin to
establish customer language; no credential or Ray approval is needed for the
next internal research attempts.`

`RAY_ACTION_REQUIRED=NO for this internal repair; Marketing remains blocked by
evidence, not by a Ray decision.`

`NEXT_DEPARTMENT_TO_CERTIFY=CREATIVE only after Marketing AI accepts a
research-grounded artifact.`

