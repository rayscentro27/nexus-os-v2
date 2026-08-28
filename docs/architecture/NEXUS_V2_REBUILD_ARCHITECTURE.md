# Nexus V2 Rebuild Architecture

Status: bootstrap contract; implementation intentionally limited to durable program state.

## Boundary

Python remains the deterministic execution foundation. It owns calculations, business rules, security, approvals, workflow/process state, receipts, and verification. Hermes is the intelligent operator/interface for communication, reasoning, research, prioritization, review, bounded delegation, and human-facing explanation. AI must not replace deterministic authority or safety controls.

The old 19-row process registry and certification campaign remain historical, scope-limited evidence. They are not the executable topology and are not rewritten by this bootstrap.

## Durable program

`data/runtime/nexus_rebuild_program.json` is the resumable program state. `data/runtime/nexus_rebuild_work_packages.json` is the dependency-aware work registry. Every completed package appends a receipt containing start/end SHA, files inspected/changed, commands, tests, canaries, results, evidence paths, known limits, classification, and next action.

The continuation policy is automatic for safe independent work: after a package passes, update evidence and state, checkpoint coherently, select the next READY package, and continue. Stop only at a genuine human gate, exhausted READY work, or safety condition. A blocker on one package does not block independent packages.

## Canonical loop contract

Every future Nexus loop must define:

`loop_id`, `purpose`, `trigger`, `intake`, `context`, `authority`, `dependencies`, `python_executor`, `inputs`, `outputs`, `verification`, `expected_side_effect`, `side_effect_verification`, `receipt`, `Hermes_review`, `improvement_policy`, `rerun_policy`, `recovery_policy`, `human_escalation_policy`, `autonomy_level`, `health_contract`, and `freshness_contract`.

Lifecycle:

`TRIGGER → INTAKE → CONTEXT → AUTHORITY → DEPENDENCY CHECK → REAL PYTHON EXECUTION → RESULT VERIFICATION → SIDE-EFFECT VERIFICATION → EVIDENCE/RECEIPT → HERMES REVIEW → IMPROVEMENT DECISION → VERIFY IMPROVEMENT → RERUN/SCHEDULE → HUMAN ESCALATION ONLY WHEN REQUIRED → COMPLETION`

### Daily Operations sample

- `loop_id`: `daily_operations`
- `trigger`: governed manual trigger or a future validated schedule
- `intake`: normalize request and create correlation ID
- `context`: load current program/process/evidence state
- `authority`: allow only internal read/report actions
- `dependencies`: Python runtime, local state, approved read sources
- `python_executor`: one named canonical daily-operations executor
- `outputs`: deterministic report and receipt
- `verification`: validate schema, freshness, result, and no forbidden side effects
- `expected_side_effect`: internal report/receipt only
- `Hermes_review`: summarize what happened, truth now, next action, and whether Ray is needed
- `improvement_policy`: propose bounded changes; never silently apply consequential changes
- `rerun_policy`: rerun only with idempotent correlation and explicit evidence lineage
- `recovery_policy`: inspect and escalate; do not restart services automatically
- `human_escalation_policy`: only for authority, credential, destructive, external, or irreversible decisions
- `autonomy_level`: A1 automatic execution, progressing only after evidence
- `health_contract`: executor responds, result validates, receipt persists
- `freshness_contract`: evidence must be newer than the trigger and correlated to the run

## Autonomy ladder

A0 MANUAL → A1 AUTOMATIC_EXECUTION → A2 AUTOMATIC_REVIEW → A3 BOUNDED_IMPROVEMENT → A4 AUTONOMOUS_ITERATION → A5 EXCEPTION_ONLY_HUMAN.

Nexus starts this bootstrap at A0/A1 under Codex human supervision. Codex is not authorized as a future autonomous production worker.

## Hermes integration decision

The official Nous Hermes Agent documentation/repository describes native messaging gateways, Bot Mode with per-bot model/memory/skills/routines/chats, tools/toolsets, skills, persistent memory, MCP, cron scheduling, context files, voice mode, multiple providers/backends, command approval, and container isolation. Sources: https://github.com/NousResearch/hermes-agent and https://hermes-agent.nousresearch.com/docs.

Initial design decision: USE_AS_IS or WRAP native Hermes capabilities where they satisfy the interface; EXTEND only at a Nexus/Python evidence boundary; DO_NOT_USE any native path that bypasses deterministic authority, receipts, or safety gates. No runtime upgrade is authorized in Sprint 0.

## Future operational truth contract

Every process must eventually expose `canonical_entrypoint`, `dependency_contract`, `authority_contract`, `data_source_contract`, `output_contract`, `receipt_contract`, `freshness_contract`, `health_contract`, `scheduler_contract`, `real_world_proof_required`, `latest_real_run_id`, `latest_real_run_at`, `latest_real_result`, `current_operational_state`, `simulation_allowed`, `simulation_state`, and `test_fixture_allowed` in addition to identity and trigger.

Validation rule: **No process may be marked operational without fresh real execution evidence appropriate to its purpose.**
