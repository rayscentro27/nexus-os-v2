# Nexus Research Continuation Doctrine Certification

Date: 2026-09-20

## Result

The Research purpose layer is implemented above the existing queue. The
canonical company-goal portfolio is reused; a durable Research charter and
goal-generated objective ledger were added. The scheduler invokes this layer
only when no eligible useful queue work remains.

`RESEARCH_PURPOSE_LAYER_STATUS=PASS_REAL_BOUNDED`

This certifies continuation mechanics and one bounded goal-generated execution;
it does not claim the `$1,000/month` goal is achieved.

## Existing architecture audit

```text
CURRENT_COMPANY_GOAL_STORE=data/runtime/company_goal_portfolio.json via goal_completion.ensure_company_goal_portfolio
CURRENT_RESEARCH_MISSION_STORE=data/governed/research_charter.json (new canonical charter)
CURRENT_RESEARCH_OBJECTIVE_STORE=data/runtime/research_work_queue.json plus governed Research V2 records
CURRENT_DEPARTMENT_REQUEST_STORE=Research queue department_target/parent_request_id and governed handoffs
CURRENT_STANDING_DISCOVERY_INPUTS=research_v2 questions/investigations, lane registry, approved monitors
CURRENT_FALLBACK_PROMPTS=lane scheduler generic discovery and governed demand clustering
CURRENT_CONTINUATION_MODEL=queue/lane fallback; previously no goal/charter-driven objective generation
EMPTY_QUEUE_CURRENT_BEHAVIOR=return generic/no-source-selected lane after bounded demand seeding
EMPTY_QUEUE_ROOT_GAP=active company goals and Research charter were not inspected before fallback
```

## Contracts

`COMPANY_GOAL_CONTRACT=` existing goal portfolio fields are normalized to
`goal_id`, title/description, status, priority, success condition, owner,
timestamps, evidence, and missing criteria. The bounded certification goal is
stored in the same canonical portfolio:

```text
TEST_COMPANY_GOAL_ID=research.continuation_revenue
TEST_COMPANY_GOAL=Reduce uncertainty around a bounded path to $1,000/month in legitimate recurring or repeatable revenue; planning only, not revenue earned.
```

`RESEARCH_CHARTER_STORE=data/governed/research_charter.json`

`RESEARCH_CHARTER_ID=research-charter-nexus-continuous-intelligence-v1`

`RESEARCH_CHARTER_STATUS=ACTIVE`

`GOAL_TO_RESEARCH_PLANNER=scripts/nexus_agent_platform/research_continuation.py`

`GOAL_TO_RESEARCH_MODEL=openai/gpt-4o-mini via the existing Research AI model path`

`GOAL_GENERATION_SCHEMA=objective_id, parent_goal_id, question, why_it_matters,
unknown_to_resolve, required_evidence, likely_capabilities, priority,
stop_condition, dedup_key`

`GOAL_OBJECTIVE_DEDUP_MODEL=normalized goal_id + question + unknown_to_resolve,
checked against active queue rows and generated-objective history`

`DUPLICATE_GOAL_OBJECTIVES_CREATED=0` in the repeat-generation test.

## Goal generation evidence

The real model planner was called twice with HTTP 200 and
`model_calls=1` per planning run. Three distinct bounded objectives were
generated in the isolated certification queue. Representative outputs were:

```text
GENERATED_OBJECTIVE_1=What specific customer needs or pain points can be identified that would justify a recurring revenue model?
GENERATED_OBJECTIVE_2=Which existing alternatives are customers currently using to address their needs, and what are their limitations?
GENERATED_OBJECTIVE_3=What remaining uncertainties exist regarding the path to achieving $1,000/month in recurring revenue?
PARENT_GOAL=research.continuation_revenue
DUPLICATE_CHECK=passed; distinct dedup keys
QUEUE_STATUS=GENERATED in isolated certification queue
```

`EMPTY_QUEUE_TRIGGER=read active goals and charter, plan one bounded objective,
deduplicate, enqueue through ResearchWorkQueue`

`EMPTY_QUEUE_GENERATED_OBJECTIVE_ID=goal-research-c2eec5607e7e202d7419` in the
isolated empty-queue test; it was generated from the active canonical goal
selection available in that test and entered the same queue contract.

`NO_GOAL_CONTINUATION_MODEL=charter-backed bounded generation with no active
goal; verified with research-charter-standing-mission`

`NO_GOAL_TEST_STATUS=PASS_REAL_BOUNDED`

`BLOCKED_GOAL_POLICY=record missing dependency/uncertainty, stop repeated
generation for that path, continue independent active goals and charter duties`

`GOAL_TERMINAL_POLICY=only ACTIVE/READY/QUEUED goals drive generation;
COMPLETE/PAUSED/CANCELLED and explicit terminal states do not`

## Real goal-generated execution

```text
GOAL_OBJECTIVE_WORK_ID=goal-objective:goal-research-a520c979ee1c034ba37c
GOAL_OBJECTIVE_ID=goal-research-a520c979ee1c034ba37c
PARENT_GOAL_ID=research.continuation_revenue
SELECTED_CAPABILITY=LAST30DAYS_DEMAND
SELECTED_WORKER=nexus_agent_platform.research.last30days_adapter.run_demand_radar
TOOL=Last30Days demand radar
REAL_AI_MODEL=openai/gpt-4o-mini
AI_PLAN_ID=rai_20260920T165819983888Z
EVIDENCE=real public-source demand-radar result; research_package_42e9e1c0807a4ebe913423d6eac40059
ALPHA_RECEIPT=alpha_receipt_ee11f5e745484c8188884e5eca45f357
ALPHA_RESULT=RESEARCH_MORE
GOAL_PROGRESS_IMPACT=PARTIAL; evidence reduced uncertainty but Alpha identified a need for corroboration
GOAL_GENERATED_RESEARCH_STATUS=PASS_REAL_BOUNDED
```

The result was not inflated: the interpretation recorded a Reddit-derived
customer pain signal, no contradiction, and a remaining gap around retention
impact and broader-market corroboration. The source content was imperfectly
aligned with the broad revenue question, so the next objective should narrow
the customer segment and cross-check with a second source type.

`GOAL_PROGRESS_EVALUATION=PARTIAL`

`GOAL_UNCERTAINTY_REDUCED=YES, bounded`

`NEXT_KNOWLEDGE_GAP=quantify/reconfirm the customer pain in the intended
market and test whether it supports a legitimate value path`

`NEXT_ACTION=Alpha RESEARCH_MORE follow-up and cross-source validation`

## Self-continuation and empty queue

`GENERATION_1_OBJECTIVE=goal-research-a520c979ee1c034ba37c`

`GENERATION_1_RESULT=real package plus AI interpretation and Alpha
RESEARCH_MORE`

`GENERATION_2_OBJECTIVE=goal-research-c4ad0ab663c256c1a590`

`GENERATION_2_REASON=real model planner read the completed first-result context
and generated a new question about desired features/services for a recurring
revenue model`

`SELF_CONTINUATION_STATUS=PASS_REAL_BOUNDED`

`QUEUE_EMPTY_OBSERVED=YES` in an isolated bounded queue using the canonical
ResearchWorkQueue implementation; production work was not deleted or hidden.

`RESEARCH_STOPPED=NO`

`GOAL_OR_CHARTER_READ=YES`

`NEW_OBJECTIVE_CREATED=YES`

`RESEARCH_CONTINUED=YES` — the new item entered `QUEUED` state and the normal
claim path is used. The production daemon remains separate and uninterrupted.

## Nova and standard integration

`NOVA_GOAL_LIST=PASS_REAL_BOUNDED`

`NOVA_GOAL_RESEARCH_STATUS=PASS_REAL_BOUNDED` through the existing
`get_research_operational_state` capability's `research_continuation` payload.

`NOVA_GENERATED_OBJECTIVE_READ=PASS_REAL_BOUNDED`

`NOVA_NEXT_RESEARCH_REASON=PASS_REAL_BOUNDED` — charter/goal reason and recent
goal feedback are persisted, not hardcoded in chat.

`NOVA_GOAL_VISIBILITY_STATUS=PASS_REAL_BOUNDED`

`GOAL_WORK_USES_STANDARD_QUEUE=YES`

`STANDARD_QUEUE_INTEGRATION=PASS_REAL_BOUNDED`

## Runtime

`RESEARCH_RUNTIME_OWNER=com.nexus.continuous-loop`

`RESEARCH_LEFT_RUNNING=YES`

`RAY_REQUIRED_TO_RESTART=NO`

`CODEX_REQUIRED_TO_CONTINUE=NO`

## Remaining limitations

- The broad certification goal needs narrower market scoping; one demand-radar
  result was not sufficient to establish a recurring-revenue opportunity.
- The next generated objective should be completed through Alpha re-review and
  then evaluated for a Marketing/Clyde handoff.
- The empty-queue proof used an isolated queue to avoid clearing live work;
  the production trigger is wired into the canonical lane scheduler and should
  be observed on a future naturally empty wake.
- Generic legacy lane fallback remains only after goal/charter continuation
  and governed demand seeding.

`PRIMARY_REMAINING_DEFECTS=none blocking continuation; improve goal-context
source alignment and observe a naturally empty production wake`

`RAY_ACTION_REQUIRED=NO`

`NEXT_MACHINE_ACTION=allow the canonical daemon to continue; consume the Alpha
RESEARCH_MORE child, then use the next goal-generated objective for independent
cross-source validation before any commercial conclusion.`
