# Nexus Overnight Research Activation

## Runtime

RESEARCH_RUNTIME_OWNER=com.nexus.continuous-loop

RESEARCH_RUNTIME_PID=41944 at verification; launchd owner remains enabled and running.

RESEARCH_RUNTIME_ENTRYPOINT=scripts/run_continuous_operating_kernel.py --daemon --interval-seconds 1200

RESEARCH_RUNTIME_INTERVAL=1200 seconds

RESEARCH_RUNTIME_STATUS=RUNNING; one launchd owner verified.

DUPLICATE_RESEARCH_DAEMONS=0 launchd owners; detached research children are bounded executions of the same owner.

## Queue state

QUEUE_STATE_BEFORE=127 total queue records; 50 nonterminal at snapshot: 20 QUEUED, 18 FAILED_RETRYABLE, 12 MONITORING, no active lease at the post-wake snapshot.

QUEUE_HYGIENE_ACTIONS=Safely parked six clearly named historical certification fixtures with `LEGACY_CERTIFICATION_FIXTURE`; evidence and rows were preserved. No queue deletion or bulk reset occurred.

PARKED_WORK_IDS=cert-failure-objective:strategy-change:1; hermes-bridge-cert-appointment-reminder-segment-20260919; hermes-bridge-cert-appointment-reminder-segment-v2-20260919; cert-investigation-funding-readiness-20260919; cert-interpretation-objective-20260919; progressive-level-b-objective-20260919.

VALID_WORK_PRESERVED=YES; current Alpha follow-ups, current investigations, monitored sources, and retry history were retained.

QUEUE_STATE_AFTER=43 nonterminal at the post-hygiene snapshot: 13 QUEUED, 18 FAILED_RETRYABLE, 12 MONITORING; all nonterminal records are ASSIGNED because the operational projection currently uses that class for priority work.

VALID_WORK_AVAILABLE=YES

VALID_WORK_CLAIMABLE=YES; three real jobs claimed immediately after restart.

## Canary and continuous evidence

OVERNIGHT_CANARY_WORK_ID=alpha-followup:alpha_eval_1a111ffee0fa4ae9809149947a0ad4ee / execution research_exec_cae23c213ec44f83931f

AI_INVESTIGATOR=real openai/gpt-4o-mini Research investigator

SELECTED_CAPABILITY=WEB_ACQUISITION

SELECTED_WORKER=research_operator_worker

TOOL=research_document_pipeline.web_page using the selected Reddit public source

INFORMATION_GAIN=The source was acquired and interpreted, but demographic evidence remained insufficient; the result was persisted with an explicit gap.

ALPHA_RESULT=Alpha model review returned REJECT for this weak package; no unsupported business claim was promoted.

FINAL_STATE=FULLY_PROCESSED / Alpha receipt persisted; next action remains governed continuation.

OVERNIGHT_CANARY_STATUS=PASS_REAL_BOUNDED

RECENT_REAL_EXECUTIONS=research_exec_cae23c213ec44f83931f (web evidence + Alpha REJECT); research_exec_2f949664b77b41ee99d9 (Last30Days demand evidence); research_exec_40be860fd4d04801861c (SEO/web duplicate detected). Each had a real AI plan and interpretation.

## Concurrency

TOTAL_CONCURRENCY_LIMIT=3

YOUTUBE_LIMIT=1

WEB_LIMIT=1

DISCOVERY_LIMIT=1

PARALLEL_EXECUTION_IDS=research_exec_cae23c213ec44f83931f, research_exec_2f949664b77b41ee99d9, research_exec_40be860fd4d04801861c

OVERLAP_SECONDS=at least 8.3 seconds based on simultaneous claims at 13:34:25Z before the first completion at 13:34:33Z.

DUPLICATE_CLAIMS=0; distinct execution IDs and distinct queue claims.

PARALLEL_STATUS=PARTIAL_REAL_REPAIRED; the initial overlap exposed two simultaneous web-bucket executions despite WEB_LIMIT=1. The smallest safe repair was applied in `run_continuous_operating_kernel.py` and `research_lane_scheduler.py`: live queue leases and fallback monitored lanes now participate in blocked-bucket selection. After restart, the saturated web bucket produced no additional dispatch. A positive multi-bucket overlap after this repair remains pending the next normal wake and is not fabricated here.

## Overnight behavior and visibility

ALPHA_RETURN_PATH_READY=PASS_REAL_BOUNDED; Alpha follow-up rows remain durable and are eligible for the existing Research router.

FAILURE_RECOVERY=Active failures include 403/timeout YouTube paths and malformed/empty web follow-up URLs. They were preserved for bounded diagnosis; no identical retry was manually forced during activation.

NOVA_CAN_READ_OVERNIGHT_RESEARCH=PASS_REAL_BOUNDED through the canonical Research state/MCP read path; broad reads remain size-sensitive and should use objective-scoped projections.

RESEARCH_LEFT_RUNNING=YES

RAY_REQUIRED_TO_RESTART=NO

CODEX_REQUIRED_TO_CONTINUE=NO

SAFE_TO_LEAVE_RUNNING_OVERNIGHT=NO — the owner is running and the bucket repair is active, but post-repair overlap evidence and remaining retryable malformed-source handling require the next normal wake before an unqualified overnight safety claim.

NEXT_MACHINE_ACTION=At the next normal wake, verify a post-repair multi-bucket overlap and confirm no same-bucket overlap; then classify malformed-source retry records with bounded strategy changes without clearing evidence.
