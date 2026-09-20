# Nexus Marketing AI Orchestration Certification

This certification uses the real consumed Research/Alpha handoff
`marketing_handoff_54ddeed5a3334177a42768b3b22513f9`, package
`package_2578bc0f94aebe300515`, and Alpha receipt
`alpha_receipt_85658d643ec84dfa91a7e90a32171cae`. No external publication,
outreach, spend, or campaign approval occurred.

## Topology and root cause

- `MARKETING_AI_EXISTING_IMPLEMENTATION`: no connected current planner/router/
  evaluator was found above the existing deterministic Marketing worker.
- `MARKETING_AI_ENTRYPOINT`: new bounded
  `scripts/nexus_agent_platform/marketing_ai_orchestrator.py`.
- `MARKETING_AI_PROVIDER=OpenRouter`
- `MARKETING_AI_MODEL=openai/gpt-4o-mini`
- `MARKETING_ROUTER`: governed GROWTH specialist contract with persisted
  routing receipt; required capabilities `CAMPAIGN_STRATEGY` and `COPY` are
  mapped to the certified GROWTH execution boundary.
- `MARKETING_EVALUATOR`: same bounded Marketing AI module, strict evidence and
  draft-only policy.
- `MARKETING_RESEARCH_RETURN_PATH`: durable `research_requests` record plus
  existing Research queue item, awaiting the next canonical wake.
- `MARKETING_CREATIVE_HANDOFF_PATH`: not executed because the evaluator found
  a genuine evidence gap.

`MARKETING_AI_ROOT_CAUSE=workers and a prior artifact existed, but no model-
backed plan/evaluation/return seam connected the Research handoff to governed
Marketing work.`

## Real orchestration evidence

- `MARKETING_PLAN_ID=mktplan_0c95c299d93a41b4854167d6442ac9b4`
- `MARKETING_MODEL_CALLED=openai/gpt-4o-mini; model_calls=1`
- `MARKETING_PLAN_STATUS=PASS_REAL`
- `MARKETING_CERTIFIED_CAPABILITIES=GROWTH analytics boundary; routing receipt
  mktroute_050ef0444dd24b0a9c7bce14293033d1`
- `MARKETING_WORK_ID=wo_2980da6d64ed4542a2c79ce9cefd534d`
- `MARKETING_EXECUTOR=GROWTH`
- `MARKETING_CLAIM=governed work order transitioned ASSIGNED → IN_PROGRESS`
- `TOOLS_USED=existing governed persistence/work-order contracts`
- `AI_MODEL_CALLED=openai/gpt-4o-mini`
- `ARTIFACT_ID=mktart_8bbee0c5a71749268471a06caf4a7cf6`
- `ARTIFACT_PATH=data/runtime/marketing_ai_orchestration/artifact_mktart_8bbee0c5a71749268471a06caf4a7cf6.json`
- `RESULT_PERSISTED=PASS_REAL`

The first evaluator returned `REVISION_REQUIRED` with specific weaknesses:
insufficient complaint-frequency evidence, no conversion/outcome data, and no
direct audience feedback. A real model-backed revision was generated and
re-evaluated. The re-evaluation returned `MORE_RESEARCH_REQUIRED`; that is a
truthful failure of evidence sufficiency, not a routing failure.

## Marketing → Research return

`MARKETING_RESEARCH_REQUEST_ID=mkt_research_return_1ba3a9a0ecc7441583f6`
and queued work
`marketing-research-return:mkt_research_return_1ba3a9a0ecc7441583f6` preserve
the same Marketing objective, Research package, Alpha receipt, and evidence
gap. The requested evidence is direct current customer-language evidence on
funding-readiness documentation complaints. It has not yet been consumed by a
canonical wake.

`MARKETING_RESEARCH_RETURN_STATUS=PASS_REAL_BOUNDED` for durable request and
queue insertion; execution and Marketing resume are pending.

## Final artifact and Creative boundary

`FINAL_MARKETING_ARTIFACT_ID=mktart_8bbee0c5a71749268471a06caf4a7cf6` is a
real internal draft with Research/Alpha lineage, audience, problem,
transformation, offer, message, channels, CTA, limitations, and next step.
It is not accepted for Creative because the evaluator returned
`MORE_RESEARCH_REQUIRED`.

- `MARKETING_AI_ACCEPTED=NO — more research required`
- `CREATIVE_HANDOFF_ID=NONE`
- `CREATIVE_RECEIPT=NOT_RUN; correctly withheld pending evidence`
- `FINAL_MARKETING_LEVEL=LEVEL_3_MARKETING_ROUTING_CAPABLE_BOUNDED`

The level is above the previous worker-only state because real model planning,
capability routing, governed execution, evaluation, revision, and a durable
Research return now exist. It is below Marketing operational/Creative-handoff
levels because the same objective has not yet returned with sufficient evidence
and no Creative consumer was invoked.

## Files and tests

`FILES_CHANGED=scripts/nexus_agent_platform/marketing_ai_orchestrator.py;
reports/research/NEXUS_OVERNIGHT_RESEARCH_MORNING_AUDIT_2026-09-20.md;
reports/marketing/NEXUS_MARKETING_AI_ORCHESTRATION_CERTIFICATION_2026-09-20.md`

`TESTS_RUN=py_compile; real OpenRouter Marketing plan; real OpenRouter
evaluation; real model-backed revision; governed GROWTH work-order execution;
durable Research return insertion`

`TEST_RESULTS=PASS_REAL for plan/route/worker/evaluation/revision and durable
return; MORE_RESEARCH_REQUIRED for acceptance`

`RAY_ACTION_REQUIRED=NO for this internal draft/return step`

`NEXT_MACHINE_ACTION=next canonical Research wake consumes the Marketing return,
updates the same package/Alpha lineage, then Marketing re-evaluates; only after
acceptance should Nexus create a Creative handoff.`

