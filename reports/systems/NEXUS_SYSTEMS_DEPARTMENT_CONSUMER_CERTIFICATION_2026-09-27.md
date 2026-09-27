# Nexus Systems Department Consumer Certification

Date: 2026-09-27

## Certification result

`PASS_REAL_BOUNDED`.

Systems now has a real governed consumer and AI reasoning worker. The real
Needle/Jev lineage was claimed, executed through the Oracle-hosted
`openrouter:openai/gpt-4o-mini` transport, persisted, reviewed, and returned to
Research with a concrete evidence gap. Alpha remains `RESEARCH_MORE`; this
certification does not force a TEST or QUALIFY decision.

## Architecture

- Department target: `SYSTEMS` / `SYSTEM_ENGINEERING`.
- Consumer: `scripts/nexus_agent_platform/systems_consumer.py`.
- Work-order bridge: `create_systems_work_order`, over the existing governed
  `data/governed/work_orders.jsonl` collection.
- Claim path: CREATED → ASSIGNED → IN_PROGRESS → COMPLETED, owned by
  `SYSTEMS_AI_WORKER`.
- AI output path: governed `systems_ai_analyses` collection, with model receipt,
  source references, lineage, judgment, and safety boundary.
- Review path: `SYSTEMS_AI_REVIEW` persisted in the work-order result.
- Next-action path: Research follow-up for missing identity/license/
  compatibility evidence, or Alpha return after a future isolated-test-ready
  assessment.
- Existing work-order contract was extended with the additive
  `SYSTEMS_AI_WORKER` specialist and `systems_ai_analyses` governed collection.

The consumer accepts Alpha `TEST`/`QUALIFY` for isolated-test planning. It also
supports a narrowly bounded assessment mode for the current Alpha
`RESEARCH_MORE` case; assessment mode does not change Alpha’s disposition or
authorize installation.

## Real lineage

Research package: `package_929140eea4df5a409edc`.

Alpha receipt: `alpha_receipt_33de1addbf224fd08f1edf4decaff75c`.

Handoff: `handoff_alpha_model_req_ddfb9541d6674732a781268c9c096d6c_package_929140eea4df5a409edc`.

Systems work order: `wo_5085bac6cea544228c212afddf6b79ee`.

Systems analysis: `systems_analysis_b9cea45eef4a49c2b701fdcf5a25a6e0`.

The work order was claimed by `SYSTEMS_AI_WORKER`. The real model call
succeeded on Oracle/Hermes 0.20.6 using `openrouter:openai/gpt-4o-mini`.
Systems returned `NEEDS_MORE_EVIDENCE`, selected Oracle as the future isolated
host, and created a Research next action. The project/capability state moved
from unresolved Research-only handling to `SYSTEMS_ASSESSED_NEEDS_EVIDENCE`.

## Systems decision

The model found the candidate identity insufficiently bound for a benchmark.
It did not claim a license, runtime, resource requirement, or compatibility
that was not established. The safe disposition is:

`NEEDS_MORE_EVIDENCE` → Research verifies the intended Jev identity, license/
terms, runtime/dependencies, and compatibility → same opportunity returns to
Alpha.

If Alpha later returns `TEST` or `QUALIFY`, the Systems bridge can create a
`systems_isolated_test_planning` order. No isolated benchmark was executed in
this certification.

## Host and safety contract

Preferred future host: `ORACLE`, because it is remote Linux/Hermes 0.20.6 and
keeps the Intel Mac control plane untouched. A future test requires candidate
identity, pinned version, license, runtime/dependencies, resource limits,
benchmark metrics, rollback, cleanup, network requirements, zero budget, and
`production_touch=false`.

Needle/Jev were not installed. No paid action, customer message, publication,
fund movement, live trade, or production change occurred.

## Proactive mission

Systems has the durable mission to identify and safely validate technology that
makes Nexus faster, cheaper, more capable, autonomous, reliable, or easier to
operate. Proactive candidates must persist why the research matters, expected
system value, cost to test, risk, and owner. The current active candidate is
`Needle / Jev`.

## Reporting and tests

The existing two-hour reporter now includes Systems work received/claimed,
AI analyses, tests planned/executed/blocked, Research/Alpha returns, project
transitions, and active candidate names. It remains a reporting observer and
does not create a scheduler or select work.

Focused Systems and regression tests: 13 passed. Python compilation and
`git diff --check` passed.
