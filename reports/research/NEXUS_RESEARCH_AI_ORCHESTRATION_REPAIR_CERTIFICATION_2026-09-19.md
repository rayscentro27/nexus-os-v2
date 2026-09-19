# Nexus Research AI Orchestration Repair Certification

## Executive result

The broken orchestration layer was repaired without replacing the certified workers, queue classes, Research V2 stores, Alpha model adapter, or bounded concurrency limits.

The new path is:

`queue item → model-backed investigation plan → certification-registry route → existing worker/processor → model interpretation → Alpha → priority-0 follow-up → worker → Alpha re-review`

Real evidence proves the investigator model was called before acquisition and after acquisition, capability routing works for eligible capabilities, Alpha follow-up work is no longer starved by older assigned items, and the follow-up was claimed, executed, persisted, and re-reviewed. YouTube remains correctly blocked from routing because its certification is only `PARTIAL_REAL`, not an eligible certified executor.

FINAL_RESEARCH_LEVEL=`LEVEL_4_LIVE_RESEARCH_OPERATIONAL_BOUNDED`

## Root cause and repair

AI_INVESTIGATOR_ROOT_CAUSE=`FAILED_REAL — the queue worker called deterministic source selection and processing directly; no model-backed investigator was called before acquisition, and queue normalization discarded capability metadata.`

CURRENT_AI_INVESTIGATOR_IMPLEMENTATION=`none before repair; now scripts/nexus_agent_platform/research_ai_orchestrator.py`
CURRENT_AI_INVESTIGATOR_PROVIDER=`OpenRouter`
CURRENT_AI_INVESTIGATOR_MODEL=`openai/gpt-4o-mini`
CURRENT_AI_INVESTIGATOR_ENTRYPOINT=`research_ai_orchestrator.investigate → route → interpret`
CURRENT_AI_INVESTIGATOR_DISCONNECT=`run_dispatched_research_job.py bypassed planning and interpretation; Alpha was downstream only.`

AI_INVESTIGATOR_CONNECTED=`YES`
AI_INVESTIGATOR_MODEL=`openai/gpt-4o-mini via OpenRouter`
AI_INVESTIGATION_PLAN_SCHEMA=`nexus.research-ai-investigation.v1; investigation_goal, questions_to_answer, required_capabilities, preferred_capability, tool_selection_reason, source_selection_strategy, evidence_needed, stop_condition, followup_policy`
AI_INVESTIGATOR_RECEIPT_PATH=`data/runtime/research_ai_orchestration/plan_*.json`
AI_RESULT_INTERPRETATION=`nexus.research-ai-interpretation.v1; information_gain, objective_progress, evidence_quality, contradictions, remaining_gaps, recommended_followup, next_capability, ready_for_alpha`
AI_INFORMATION_GAIN_PROVEN=`YES; real model interpretation receipts persisted`
AI_FOLLOWUP_DECISION_PROVEN=`YES; model recommended additional evidence and Alpha readiness state`

## Certification registry and routing

CERTIFICATION_REGISTRY_LOADED=`YES — data/governed/research_worker_capability_certifications.jsonl`
CERTIFIED_EXECUTORS_FOUND=`4 eligible executor records: Last30Days, SEO Engine, Research web processor, Alpha; YouTube excluded because PARTIAL_REAL`

CAPABILITY_ROUTER=`research_ai_orchestrator.route; registry-gated, alias-normalized, objective-family guarded, exact certified executor fit preferred`
ROUTING_INPUT_SCHEMA=`work_id, objective_id, work_class, question/objective, declared required_capabilities, model plan, certification registry`
ROUTING_DECISION_RECEIPT=`embedded in AI_INVESTIGATION_PLAN execution events and persisted plan receipt`
LEASE_PATH=`existing research_lane_scheduler.select_priority_work → ResearchWorkQueue.claim_next; no second queue or lease system`

ROUTING_TEST_A=`PASS_REAL — current funding-demand assignment; selected Last30Days demand radar, PASS_REAL_BOUNDED`
ROUTING_TEST_B=`PASS_REAL — GoClear SEO assignment; selected SEO Engine, PASS_REAL_BOUNDED`
ROUTING_TEST_C=`BLOCKED_EXTERNAL/BOUNDED — approved YouTube objective correctly refused because no YouTube executor met PASS_REAL or PASS_REAL_BOUNDED; existing YouTube status is PARTIAL_REAL`
ROUTING_TEST_D=`PASS_REAL — independent public evidence assignment; selected Research web/source processor, PASS_REAL_BOUNDED`
CORRECT_ROUTING_RATE=`100% for 3 routable assignments; 75% across all four requested assignments because YouTube was correctly blocked rather than misrouted`

The first routing probe found that broad model aliases could cause an SEO/YouTube objective to fall back to Last30Days. The repair added capability normalization and explicit objective-family guards. The final routing probe selected Last30Days for demand, SEO for SEO, web for independent evidence, and no executor for YouTube.

## Alpha return loop

ALPHA_RETURN_ROOT_CAUSE=`Alpha created priority-2 follow-ups without capability metadata; queue priority allowed older assigned work to win, and the assigned Research bridge skipped model re-review when an earlier evaluation existed.`
ALPHA_FOLLOWUP_PARENT_LINK_REPAIRED=`YES — existing follow-up preserved alpha_receipt_id, alpha_evaluation_id, research_package_id/source identity, objective_id, parent_request_id, and followup_work_id`
ALPHA_FOLLOWUP_PRIORITY=`0 / assigned`
ALPHA_FOLLOWUP_CAPABILITY_REQUIREMENT=`WEB_ACQUISITION`
ALPHA_FOLLOWUP_ROUTED=`YES — Research web/source processor`
ALPHA_FOLLOWUP_CLAIMED=`YES — work id alpha-model-followup:alpha_eval_f8d6847dca0643d691b2e17fbaf4f59b`
ALPHA_FOLLOWUP_COMPLETED=`YES — package_dd7ac6c037c4745241aa persisted`
ALPHA_REREVIEW_TRIGGERED=`YES — force_rereview applies only to Alpha-return work and does not remove normal idempotency`
ALPHA_REREVIEW_RESULT=`PASS_REAL — alpha_eval_3e0dc08fbe3241d89bd6a9b02a58770f, alpha_receipt_d589f9fa520140e8a6bcabb64a4e4214, decision RESEARCH_MORE`

The second `RESEARCH_MORE` is honest: the model still requested independent validation. Its new follow-up remains queued at priority 0 and was not falsely marked complete.

QUEUE_REPAIRS_PERFORMED=`preserved queue classes; extended normalization with required_capabilities/plan/executor/interpretation fields; repaired existing Alpha follow-up priority and web capability metadata; corrected missing source URL on the existing GoClear company-cycle investigation; no rows deleted`

## Parallel concurrency proof

The existing bounded limits were preserved: total 3, YouTube 1, web 1, discovery 1.

PARALLEL_TEST_EXECUTION_1=`cert-parallel-last30days-final-20260919; Last30Days; PASS`
PARALLEL_TEST_EXECUTION_2=`cert-parallel-seo-final-20260919; SEO Engine; SUCCESS`
PARALLEL_LEASE_OVERLAP=`4.35 seconds observed; distinct execution/request IDs`
PARALLEL_DUPLICATE_CLAIM=`NO`
PARALLEL_RESULT_1=`real Last30Days run completed with PASS`
PARALLEL_RESULT_2=`real GoClear SEO run completed with SUCCESS`
PARALLEL_EXECUTION_STATUS=`PASS_REAL_BOUNDED`

## Live existing queue item

The live item was the existing GoClear company-cycle funding-readiness investigation, not a certification fixture:

LIVE_WORK_ID=`investigation:company_cycle_ddc1b360d7a64a3085b819bec48554f1:goclear-funding-readiness-demand`
LIVE_OBJECTIVE_ID=`company_cycle_ddc1b360d7a64a3085b819bec48554f1:goclear-funding-readiness-demand`
LIVE_WORK_CLASS=`ASSIGNED`
LIVE_AI_PLAN_ID=`rai_20260919T215711772053Z / final repaired rerun plan`
LIVE_REQUIRED_CAPABILITIES=`WEB_ACQUISITION`
LIVE_SELECTED_EXECUTOR=`research.scheduled_research_router.process_scheduled_item`
LIVE_LEASE=`research_ai_live_queue_certification_rerun; existing ResearchWorkQueue lease`
LIVE_TOOL=`research_document_pipeline.web_page via scheduled_research_router`
LIVE_ARTIFACT=`existing Research V2 package package_11f5f5fc15dfbb62c86c; final rerun correctly recognized unchanged evidence`
LIVE_INFORMATION_GAIN=`AI interpreted the SBA funding guidance and explicitly reported duplicate/no-new-information limitation and remaining gaps`
LIVE_ALPHA_RESULT=`initial full pass reached Alpha RESEARCH_MORE with alpha_eval_08c71369017841809585a4cfc773bb72; repaired follow-up was then routed and settled as duplicate with Alpha correctly skipped`
LIVE_FINAL_QUEUE_STATUS=`MONITORING / DUPLICATE_UNCHANGED after repaired rerun`
LIVE_END_TO_END_STATUS=`PASS_REAL_BOUNDED — AI plan, certified web route, lease, worker, evidence readback, AI interpretation, and governed duplicate settlement all proven; no new intelligence was claimed from unchanged evidence`

## Monitor visibility

RESEARCH_MONITOR_QUEUE_VISIBLE=`YES — monitor_latest.json reads canonical ResearchWorkQueue counts`
RESEARCH_MONITOR_ACTIVE_WORKERS_VISIBLE=`YES — active lease projection from canonical queue`
RESEARCH_MONITOR_AI_STAGE_VISIBLE=`YES — AI_INVESTIGATION_PLAN and AI_RESULT_INTERPRETATION stages in execution events and monitor snapshot`
RESEARCH_MONITOR_ALPHA_RETURNS_VISIBLE=`YES — alpha_return_items count and queue items with alpha_followup_required`
RESEARCH_MONITOR_CONCURRENCY_VISIBLE=`YES — existing concurrency_limits() values persisted in monitor snapshot`

Monitor artifact: `data/runtime/research_ai_orchestration/monitor_latest.json`. This is a read-only projection; it is not a second queue.

## Final certification

WORKERS_CAPABLE=`YES — bounded individual certifications remain valid`
AI_INVESTIGATOR_CAPABLE=`YES — real model plan and interpretation calls persisted`
CAPABILITY_ROUTING_CAPABLE=`YES for eligible capabilities; YouTube correctly blocked until certification improves`
ALPHA_RETURN_LOOP_CAPABLE=`YES — follow-up creation, priority, claim, execution, package persistence, and model re-review proven`
CONCURRENCY_CAPABLE=`YES — two independent real capability calls overlapped within configured limits`
LIVE_QUEUE_CAPABLE=`YES_BOUNDED — existing company-cycle queue item completed the repaired plan/route/worker/interpretation/settlement path; duplicate result was preserved honestly`

PRIMARY_FAILURES_REMAINING=`YouTube remains PARTIAL_REAL due provider caption/audio limitation; Alpha follow-up may continue issuing RESEARCH_MORE where evidence remains incomplete; no certified AI investigator executor exists for video-specific work; existing legacy queue contains unrelated stale items outside this bounded repair.`

FINAL_RESEARCH_LEVEL=`LEVEL_4_LIVE_RESEARCH_OPERATIONAL_BOUNDED`

FILES_CHANGED=`scripts/nexus_agent_platform/research_ai_orchestrator.py; scripts/nexus_agent_platform/research_work_queue.py; scripts/nexus_agent_platform/alpha_model_review.py; scripts/nexus_agent_platform/research_alpha_pipeline.py; scripts/research/run_dispatched_research_job.py; this report`
TESTS_RUN=`real OpenRouter investigator/routing/interpretation calls; real Last30Days/SEO parallel run; real existing company-cycle queue item; real Alpha return/re-review; Python compile; targeted Research/Alpha tests`
TEST_RESULTS=`20/20 targeted tests passed; real bounded orchestration and return-loop evidence passed; YouTube correctly blocked as uncertified`
COMMITS=`pending`

RAY_ACTION_REQUIRED=`NO for this repair certification`

NEXT_MACHINE_ACTION=`Allow the canonical continuous Research owner to consume the priority-0 Alpha follow-up, or repair the remaining evidence gap through the same certified web/Last30Days route. Do not route YouTube work until its certification advances beyond PARTIAL_REAL.`
