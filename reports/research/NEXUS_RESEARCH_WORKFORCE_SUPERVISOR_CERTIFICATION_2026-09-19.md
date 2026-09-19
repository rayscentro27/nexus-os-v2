# Nexus Research Workforce + Queue Supervisor Certification

## Executive summary

Audit window: `2026-09-19T21:39:20Z` through `2026-09-19T21:44:00Z`.

The installed Last30Days adapter, SEO Engine, YouTube pipeline, public web processor, and model-backed Alpha reviewer were exercised with real bounded assignments. Last30Days and SEO produced real public-source outputs; YouTube truthfully preserved incomplete metadata evidence after caption and audio failure; web acquisition created a Research V2 package; Alpha made a real `RESEARCH_MORE` decision and created a linked follow-up.

The current Research execution path does not contain a distinct AI investigator or skill-aware queue supervisor. `research_operator_worker` selects deterministic lane/source work, and the queue priority selector can choose older unrelated assigned work ahead of a newly-created Alpha follow-up. Therefore the highest defensible department level is `LEVEL_1_WORKERS_CAPABLE`: individual capabilities work in bounded form, but AI investigation, Alpha return consumption, capability-based routing, and a complete live queue-to-intelligence flow are not certified.

No production queue rows were deleted or settled. A claim probe briefly leased an older assigned item selected ahead of the certification follow-up and released it without a result; the follow-up remains queued and is explicitly not counted as completed.

## Execution topology

ACTUAL_RESEARCH_WORKER_TOPOLOGY=

| Display name | Type | Executor | Invocation / persistence |
|---|---|---|---|
| Research work queue | WORKER/STORE | `nexus_agent_platform.research_work_queue.ResearchWorkQueue` | `data/runtime/research_work_queue.json`; leases via `claim_next` |
| Continuous Research owner | SUPERVISOR/SCHEDULER | `scripts/run_continuous_operating_kernel.py` + `research_lane_scheduler` | dispatches `research_operator_worker`; execution events in `data/runtime/research_execution_jobs.jsonl` |
| General Research worker | WORKER | `research_operator_worker` / `scripts/research/run_dispatched_research_job.py` | calls `scheduled_research_router.process_scheduled_item` |
| AI Research investigator | NOT DISCOVERED | none | no pre-acquisition model call or investigator executor found |
| Last30Days | CAPABILITY/ADAPTER | `run_demand_radar` | pinned CLI plus governed source persistence |
| SEO Engine | CAPABILITY/ADAPTER | `seo_adapter.adapter` | installed SEO CLI plus Research V2 linkage |
| YouTube | CAPABILITY/ADAPTER | `process_youtube_video` | captions → ASR → metadata fallback artifacts |
| Public web | CAPABILITY/PROCESSOR | `process_scheduled_item` | `research_document_pipeline` → Research V2 |
| Alpha | AGENT/EXECUTOR | `alpha_model_review.review_demand_package` | OpenRouter model call, Alpha evaluation/receipt, queue follow-up |
| Clyde/Funding | DEPARTMENT/HANDOFF | `run_entity_readiness_handoff.py` | readiness reconciliation only; synthetic/demo evidence, not a live public funding researcher |

CURRENT_RESEARCH_EXECUTION_CHAIN=`ResearchWorkQueue → research_lane_scheduler → research_operator_worker → scheduled_research_router → processor/adapter → Research V2 package → Alpha only when explicitly invoked`.

QUEUE_OWNER=`ResearchWorkQueue`
QUEUE_PATH=`data/runtime/research_work_queue.json`
QUEUE_SUPERVISOR=`continuous operating kernel + research_lane_scheduler; no standalone capability-aware supervisor discovered`
SCHEDULER=`nexus_agent_platform.research_lane_scheduler`
CLAIM_IMPLEMENTATION=`ResearchWorkQueue.claim_next`
LEASE_IMPLEMENTATION=`status=IN_PROGRESS, claimed_by, claimed_at, lease_expires_at, attempt_id`
GENERAL_RESEARCH_WORKER=`research_operator_worker`
AI_RESEARCH_INVESTIGATOR=`NONE_DISCOVERED`
ALPHA_EXECUTOR=`nexus_agent_platform.alpha_model_review.review_demand_package`
RESEARCH_PACKAGE_STORE=`data/governed/research_v2_* plus data/runtime research artifacts`
ALPHA_REVIEW_STORE=`data/governed/alpha_evaluations.jsonl and data/runtime/alpha_research`
FOLLOWUP_STORE=`data/runtime/research_work_queue.json plus research_v2_follow_ups`

## Individual certifications

RESEARCH_INVESTIGATOR_STATUS=`FAILED_REAL`

Assignment `cert-investigator-funding-readiness-20260919` was not upgraded: the actual worker path selected/processed sources without a Research AI model call, question plan, tool rationale, or AI follow-up decision. This is a failure of the investigator layer, not of public acquisition.

LAST30DAYS_STATUS=`PASS_REAL_BOUNDED`

Assignment `cert-live-last30days-20260919` invoked the installed pinned Last30Days CLI with the current query `small business funding readiness documentation customer pain`. It acquired two current HN-linked public results and persisted provenance/signals. The adapter returned discovery evidence, not a completed customer-demand interpretation.

SEO_STATUS=`PASS_REAL_BOUNDED`

Assignment `cert-live-seo-20260919` invoked `iannuttall/seo` version `0.2.40` against `https://goclearonline.cc`. It crawled one page and returned 10 live findings, including one high-severity soft-404 and one medium-severity missing meta description. The adapter linked existing findings and reported zero newly inserted findings.

YOUTUBE_STATUS=`PARTIAL_REAL`

Assignment `cert-youtube-zbAmmnMh5ew-20260919` used the approved video watchlist. Public captions failed, local audio acquisition returned HTTP 403, and the pipeline persisted a bounded `PARTIAL_EVIDENCE` artifact with no fabricated transcript or claims.

CLYDE_STATUS=`NOT_IMPLEMENTED_AS_PUBLIC_RESEARCH_EXECUTOR`

The available Clyde script is a readiness handoff reconciler over explicitly synthetic/non-production readiness exports. It is not a live public funding-evidence worker, so no real worker certification was awarded.

WEB_STATUS=`PASS_REAL_BOUNDED`

Assignment `cert-web-assignment-20260919` acquired the SBA public page through the existing web processor, created eight claims, one question, one comparison, and Research V2 package `package_5eb9121f1abed891dbd3` linked to investigation `cert-investigation-funding-readiness-20260919`.

ALPHA_STATUS=`PASS_REAL_BOUNDED`

The model-backed Alpha path called OpenRouter with model `openai/gpt-4o-mini`, evaluated the fresh Last30Days package, challenged its weak evidence, returned `RESEARCH_MORE`, and persisted evaluation `alpha_eval_f8d6847dca0643d691b2e17fbaf4f59b` plus receipt `alpha_receipt_1f2eb7f2b072429bb429f6aa2c7ec69a2`. This is real Alpha execution, not deterministic receipt creation.

## AI investigation and Alpha return loop

AI_INVESTIGATION_LAYER=`FAILED_REAL`
AI_RESEARCH_MODEL=`NONE_CONNECTED_BEFORE_SOURCE_ACQUISITION`
AI_TOOL_SELECTION_PROVEN=`NO`
AI_SOURCE_SELECTION_PROVEN=`NO; deterministic lane/hash/source-pool selection observed`
AI_INTERPRETATION_PROVEN=`NO for Research; YES downstream for Alpha`
AI_FOLLOWUP_DECISION_PROVEN=`NO for Research; YES downstream for Alpha`

RESEARCH_MORE_CREATED=`YES`
FOLLOWUP_WORK_ID=`alpha-model-followup:alpha_eval_f8d6847dca0643d691b2e17fbaf4f59b`
FOLLOWUP_PARENT_LINK_VALID=`YES; objective_id=cert-investigation-funding-readiness-20260919 and parent_request_id=alpha_model_req_5271da8620954ff5b05769140246cd95`
FOLLOWUP_CLAIMED=`NO; older assigned work outranked it in canonical queue`
FOLLOWUP_EXECUTOR=`not reached`
FOLLOWUP_INFORMATION_GAIN=`none appended; follow-up remains queued`
ALPHA_REREVIEW=`NO`
RESEARCH_MORE_LOOP_STATUS=`FAILED_REAL — creation works, consumption and re-review do not`

## Queue supervisor and routing

SUPERVISOR_ASSIGNMENT_ID=`not created as a new production queue item; direct evidence came from existing scheduler/claim path`
REQUIRED_CAPABILITIES=`not represented as a certified executor registry used by queue selection`
SELECTED_WORKER=`research_operator_worker`
WHY_SELECTED=`canonical worker path, not skill certification`
LEASE_CREATED=`YES for a bounded claim probe; target Alpha follow-up was not the selected item`
WORKER_CLAIMED=`YES for an unrelated older assigned item; target follow-up remained QUEUED`
WORK_COMPLETED=`not for target follow-up`
QUEUE_SETTLED=`target not settled; no false completion`
SUPERVISOR_TEST_STATUS=`FAILED_REAL`

SKILL_ROUTING_TEST_A=`PARTIAL_REAL — Last30Days direct adapter works; capability-aware supervisor route not proven`
SKILL_ROUTING_TEST_B=`PASS_REAL_BOUNDED direct SEO adapter; supervisor route not proven`
SKILL_ROUTING_TEST_C=`PARTIAL_REAL direct YouTube pipeline; supervisor route not proven`
SKILL_ROUTING_TEST_D=`NOT_IMPLEMENTED_AS_PUBLIC_RESEARCH_EXECUTOR`
SKILL_ROUTING_TEST_E=`PASS_REAL_BOUNDED direct web processor; supervisor route not proven`
CORRECT_SKILL_ROUTING_RATE=`0% proven by supervisor; direct capability results must not be conflated with routing`

CAPABILITY_BASED_ROUTING_CURRENTLY_EXISTS=`NO`
CAPABILITY_CERTIFICATION_USED_FOR_ROUTING=`NO`
ROUTING_MODEL_STATUS=`FAILED_REAL — class/priority queue selection exists, capability registry matching does not`

## Live queue end-to-end certification

LIVE_QUEUE_WORK_ID=`alpha-model-followup:alpha_eval_f8d6847dca0643d691b2e17fbaf4f59b`
LIVE_QUEUE_OBJECTIVE_ID=`cert-investigation-funding-readiness-20260919`
LIVE_QUEUE_WORK_CLASS=`ASSIGNED`
LIVE_QUEUE_SELECTED_WORKER=`not claimed; older assigned queue item selected first`
LIVE_QUEUE_LEASE=`not created for target`
LIVE_QUEUE_MODEL=`none`
LIVE_QUEUE_TOOLS=`none for target`
LIVE_QUEUE_ARTIFACT=`Alpha follow-up receipt exists; no follow-up Research artifact`
LIVE_QUEUE_ALPHA_RESULT=`RESEARCH_MORE created; re-review absent`
LIVE_QUEUE_FINAL_STATUS=`QUEUED`
LIVE_QUEUE_END_TO_END=`FAILED_REAL`

## Certification matrix

| Name | Type | Executor ID | Assignment | Claimed | AI model | Real public data | Artifact | Persisted | Terminal | Certification |
|---|---|---|---|---|---|---|---|---|---|---|
| Research Investigator | AGENT | none discovered | cert-investigator-funding-readiness-20260919 | no valid investigator claim | no | indirect processor data | investigation linkage | partial | no | FAILED_REAL |
| Last30Days | CAPABILITY | run_demand_radar | cert-live-last30days-20260919 | direct adapter | no | yes | radar + signals | yes | PASS | PASS_REAL_BOUNDED |
| SEO Engine | CAPABILITY | seo_adapter.adapter | cert-live-seo-20260919 | direct adapter | no | yes, live GoClear | operational state/findings | yes/linkage | PASS | PASS_REAL_BOUNDED |
| YouTube | CAPABILITY | process_youtube_video | cert-youtube-zbAmmnMh5ew-20260919 | direct pipeline | no | yes, public metadata path | partial evidence JSON | yes | bounded partial | PARTIAL_REAL |
| Clyde/Funding | DEPARTMENT/HANDOFF | run_entity_readiness_handoff | none | no public research assignment | no | no | synthetic readiness handoff only | yes | bounded | NOT_IMPLEMENTED |
| Web processor | CAPABILITY | process_scheduled_item | cert-web-assignment-20260919 | direct processor | no | yes, SBA | package_5eb9121f1abed891dbd3 | yes | PASS | PASS_REAL_BOUNDED |
| Alpha | AGENT | review_demand_package | cert-research-package-last30days-20260919 | yes | openai/gpt-4o-mini | supplied fresh public evidence | evaluation + receipt + follow-up | yes | RESEARCH_MORE | PASS_REAL_BOUNDED |

## Findings and failure classification

PRIMARY_FAILURES=`AI_INVESTIGATION_LAYER; no capability-based supervisor; Alpha follow-up priority/consumption gap; Clyde public-research executor absent; YouTube external 403/caption limitation`

REPAIRS_COMPLETED=`none; this was certification-first and no ordinary defect was changed without a bounded failed retest`

REMAINING_INTERNAL_DEFECTS=`Research model is not connected before source acquisition; queue selection is class/priority based rather than capability based; Alpha follow-up can be starved by older assigned work; Alpha re-review linkage is not consumed by the worker`

TRUE_EXTERNAL_BLOCKERS=`YouTube public captions/audio returned provider-side failures; no additional YouTube content claim can be made without another legitimate evidence path`

INDIVIDUAL_WORKERS_CAPABLE=`YES, bounded for Last30Days, SEO, web processor, and partial YouTube`
QUEUE_SUPERVISOR_CAPABLE=`NO`
SKILL_ROUTING_CAPABLE=`NO`
ALPHA_RETURN_LOOP_CAPABLE=`NO; creation yes, consumption/re-review no`
LIVE_QUEUE_CAPABLE=`NO`

FINAL_DEPARTMENT_LEVEL=`LEVEL_1_WORKERS_CAPABLE`

CERTIFICATION_REGISTRY_PATH=`data/governed/research_worker_capability_certifications.jsonl`
REPORT_PATH=`reports/research/NEXUS_RESEARCH_WORKFORCE_SUPERVISOR_CERTIFICATION_2026-09-19.md`

RAY_ACTION_REQUIRED=`NO for this certification run`

NEXT_RECOMMENDED_ARCHITECTURE=`Keep the existing queue and worker owners. Add a bounded Research Investigator stage before source acquisition, add capability requirements and certified-executor matching to the existing scheduler, reserve priority for objective-linked Alpha follow-ups, then rerun Level 2 through Level 6. Do not create parallel agents or queues.`
