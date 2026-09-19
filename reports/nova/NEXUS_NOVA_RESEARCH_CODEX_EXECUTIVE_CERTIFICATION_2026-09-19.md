# Nexus Nova / Hermes Executive Control Certification

Date: 2026-09-19  
Runtime: Hermes 0.20.6, profile `nova_nexus`, Oracle host, model `openai/gpt-4o-mini`  
Canonical Research queue: `data/runtime/research_work_queue.json`

## Executive result

`FINAL_NOVA_LEVEL=LEVEL_3_NOVA_RESEARCH_CONTROL_OPERATIONAL_BOUNDED`

Nova can read bounded Research state, create a durable Research assignment,
monitor objective-scoped evidence, receive the Research/Alpha result, and send
an Alpha `RESEARCH_MORE` result back through the existing Research queue. A
fresh natural-language assignment completed through the real AI investigator,
Last30Days acquisition, interpretation, Research package, Alpha review, and
Alpha follow-up execution.

The certification does not pass the Codex escalation levels. No existing
governed Nova→Codex action currently creates a durable coding work item with a
completion receipt and automatic dependent-objective resume. Codex is installed
(`codex-cli 0.154.0`), but availability is not an assignment bridge.

## Level evidence

### Level 1 — Nova reads Research state

`NOVA_RESEARCH_STATE_READ=PASS_REAL_BOUNDED`

Hermes read `nexus_get_research_state` through the live MCP bridge. The local
canonical projection reports queue depth 19, all 19 currently nonterminal items
in `ASSIGNED`, zero running, zero blocked, 18 retryable historical queue rows,
and Alpha follow-ups present. The initial executive wording over-weighted the
legacy Research V2 counters; this was corrected by exposing the canonical queue
projection and adding `nexus_get_research_queue`. The dedicated tool was
registered and observed by the remote Hermes MCP schema, but the model still
occasionally selected the broader state tool.

`NOVA_QUEUE_READ=PARTIAL_REAL`  
`NOVA_QUEUE_READ_SOURCE=live Nexus MCP → research_operational_state → ResearchWorkQueue`  
`NOVA_QUEUE_COUNTS_MATCH_CANONICAL=PARTIAL_REAL`  
`NOVA_STATE_READ_STATUS=PASS_REAL_BOUNDED`

### Level 2 — Nova explains queue condition

`LEVEL_2_STATUS=PARTIAL_REAL`

Nova correctly distinguished current/legacy Research state and identified no
active lease in the tested snapshot, but some responses reported 84 open V2
investigations as queue depth. This is a model/tool-selection grounding defect,
not a queue mutation. The canonical queue now exposes explicit class/status
counts to prevent that ambiguity.

### Level 3 — Nova assigns and controls Research

`NOVA_RESEARCH_ASSIGNMENT=PASS_REAL`  
`NOVA_RESEARCH_PROJECT_MONITORING=PASS_REAL_BOUNDED`  
`NOVA_RESEARCH_RESULT_READ=PASS_REAL`  
`NOVA_RESEARCH_FOLLOWUP=PASS_REAL`

Fresh objective:

- `NOVA_OBJECTIVE_ID=nova_research_ee61348b4e47c681a9c5`
- `NOVA_CREATED_WORK_ID=nova_research_work_ee61348b4e47c681a9c5`
- queue class/status: `ASSIGNED / QUEUED`
- MCP receipt: `bf25380e1b5a655d9e636ece6c4208ccab1caaf1ea4b4fc3b1ddfad2d12e31f4`
- AI plan: `rai_20260919T233440494492Z`
- Research execution: `nova_exec_ee6134`
- Research package: `research_package_0db12daee2f642fcae6d1c5ff3b65b1c`
- initial Alpha receipt: `alpha_receipt_7aecbbdf72d14346a440f70ac1313df0`
- initial Alpha decision: `RESEARCH_MORE`
- follow-up work: `alpha-model-followup:alpha_eval_3c5c4f68f53e4597b11fcf06bbf24007`
- follow-up execution: `nova_followup_exec_3c5c4f`
- follow-up re-review receipt: `alpha_receipt_3e57b2a82ed64beab9acf60c12222bd1`

Research selected and invoked the certified executor
`nexus_agent_platform.research.last30days_adapter.run_demand_radar`, acquired
public evidence, interpreted it with the real model, and persisted the package.
The finding was a current funding-readiness pain point involving cash-flow and
reputation pressure around a small-business janitorial contract. Alpha correctly
challenged the evidence as weak and requested more research.

`NOVA_RESULT_MATCHES_CANONICAL=YES` for package, Alpha receipt, decision,
follow-up existence, and next action. Nova reported missing evidence as
quantitative financial impact, stronger corroboration, and effectiveness/user
feedback for relevant education or systems.

### Level 4 — Nova → Codex escalation

`NOVA_CODEX_CLASSIFICATION=PASS_REAL_BOUNDED`

Nova correctly classified the real queue metadata-loss issue as a software
defect rather than a Research question:

`DEFECT_ID=RESEARCH-QUEUE-METADATA-PROJECTION-001`

Observed defect: after settlement, `ai_plan_id`, `selected_executor_id`, and
AI interpretation are present only in `last_result`, while the queue item's
top-level monitor fields remain empty.

`NOVA_CODEX_ASSIGNMENT=FAILED_REAL`
`CODEX_REAL_REPAIR=NOT_STARTED`
`LEVEL_4_STATUS=FAILED_REAL`

No governed `nexus_assign_codex` action, durable Codex work-item ledger, or
Nova-observable Codex completion receipt exists in the current architecture.
The installed Codex CLI is not treated as proof of an operational bridge.

### Levels 5–12 — dependent executive repair loop

`NOVA_CODEX_COMPLETION_READ=NOT_IMPLEMENTED`  
`NOVA_OBJECTIVE_RESUME=NOT_PROVEN`  
`LEVEL_5_STATUS=BLOCKED_BY_MISSING_CODEX_BRIDGE`

These levels were not falsely passed. No Codex assignment was fabricated and no
repair was executed on Ray's behalf.

### Level 13 — final report

`NOVA_FINAL_REPORT=PASS_REAL_BOUNDED`

The objective-scoped Hermes response returned the Research package ID, Alpha
receipt ID, `RESEARCH_MORE` decision, missing evidence, follow-up existence, and
next action. This was returned through the real Oracle Hermes transport.

`NOVA_FINAL_REPORT_CHANNEL=Oracle Hermes CLI transport for canonical Hermes 0.20.6/profile nova_nexus`  
`TELEGRAM_NOVA_STATUS=NOT_TESTED_THIS RUN`  
`ADMIN_NOVA_STATUS=NOT_TESTED_THIS RUN`

### Levels 14–15 — commands and governance

`TELEGRAM_COMMAND_MATRIX=PARTIAL_REAL`: the underlying Hermes runtime accepts
natural-language status, assignment, objective-scoped result, and follow-up
requests; direct Telegram delivery was not exercised in this run.

`NOVA_AUTHORITY_BOUNDARY=PASS_REAL_BOUNDED`: Research assignment and follow-up
are internal Nexus actions. Campaign publication, spend, credentials,
contracts, regulated actions, and Ray-reserved approvals remain outside Nova's
authority.

## Repairs completed

- Added the governed `nexus_assign_research` MCP action with idempotent queue
  assignment receipts.
- Connected selected certified Last30Days execution to the existing Research
  worker instead of falling through to deterministic source processing.
- Added explicit objective-scoped queue read projection and
  `nexus_get_research_queue`.
- Preserved parent/objective IDs through Research and Alpha follow-up work.
- Added exact-work queue claiming for controlled assigned execution.
- Fixed Hermes prompt classification so natural “Have Research investigate …”
  requests use the assignment action, while ordinary queue/status questions do
  not create work and objective IDs remain objective-scoped.
- Extended objective evidence resolution to expose Alpha deficiencies and
  required follow-up as missing evidence.

## Tests and runtime evidence

`services/nexus_mcp/tests/test_server.py`: 21 passed.  
Python compile checks: passed for changed bridge/worker modules.  
Real Hermes assignment: passed on Oracle, Hermes 0.20.6/profile `nova_nexus`.  
Real Research execution: passed; model plan, Last30Days invocation, public
source acquisition, interpretation, package persistence, Alpha review.  
Real Alpha return: passed; follow-up claim, web execution, evidence append,
Alpha re-review.  
Objective-scoped Nova result read: passed with matching package/receipt.  
Research queue monitor projection: locally verified against
`data/runtime/research_work_queue.json`.

`RAY_ACTION_REQUIRED=NO` for the completed Research-control branch. The Codex
bridge is an internal repair still required before executive-control Level 4/5.

`EXTERNAL_BLOCKERS=NONE_IDENTIFIED`  
`INTERNAL_DEFECTS_REPAIRED=Research-dispatch seam; queue read projection; Nova assignment prompt classification; evidence-bridge missing-evidence projection`

`TONIGHT_UNATTENDED_TEST_READY=PARTIAL`: Nova can assign and monitor Research;
automatic Nova→Codex escalation and Telegram acceptance remain uncertified.

## Final summary

```text
NOVA_RESEARCH_STATE_READ=PASS_REAL_BOUNDED
NOVA_QUEUE_READ=PARTIAL_REAL
NOVA_RESEARCH_ASSIGNMENT=PASS_REAL
NOVA_RESEARCH_PROJECT_MONITORING=PASS_REAL_BOUNDED
NOVA_RESEARCH_RESULT_READ=PASS_REAL
NOVA_RESEARCH_FOLLOWUP=PASS_REAL
NOVA_CODEX_CLASSIFICATION=PASS_REAL_BOUNDED
NOVA_CODEX_ASSIGNMENT=FAILED_REAL
CODEX_REAL_REPAIR=NOT_STARTED
NOVA_CODEX_COMPLETION_READ=NOT_IMPLEMENTED
NOVA_OBJECTIVE_RESUME=NOT_PROVEN
NOVA_FINAL_REPORT=PASS_REAL_BOUNDED
TELEGRAM_NOVA_STATUS=NOT_TESTED_THIS_RUN
ADMIN_NOVA_STATUS=NOT_TESTED_THIS_RUN
FINAL_NOVA_LEVEL=LEVEL_3_NOVA_RESEARCH_CONTROL_OPERATIONAL_BOUNDED
RAY_ACTION_REQUIRED=NO
NEXT_MACHINE_ACTION=Implement one governed Nova→Codex assignment/receipt bridge using the existing coding-worker executor, then certify completion-read, dependent Research resume, and Telegram delivery.
```
