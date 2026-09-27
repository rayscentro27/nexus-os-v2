# Nexus Project Advancement and Department Consumption Audit

Date: 2026-09-27

## Executive result

The systemic break was a missing consumer boundary, not a missing scheduler.
Research and Alpha produced durable records, but qualified/TEST handoffs did
not become canonical work orders with an owner, worker execution, review, next
action, and project-state transition. The real Trading TEST result now crosses
that chain through the existing governed work-order persistence and the
existing deterministic Trading intake. It truthfully ends in
`WAITING_DEPENDENCY` because no supported strategy ruleset was supplied.

## Sources of truth

| Concern | Canonical source | Finding |
|---|---|---|
| Company goals | `data/runtime/company_goal_portfolio.json` | 24 rows; 12 non-terminal readiness records. |
| Research projects | `data/runtime/research_work_queue.json`, `research_project_portfolio.py` | Research-objective read model, not a universal project ledger. |
| Handoffs | `data/governed/research_v2_handoffs.jsonl` | Append-only Research/Alpha/department handoffs. |
| Work orders | `data/governed/work_orders.jsonl` via `governed.persistence` | Canonical governed lifecycle; Trading canary is the current department-intake record. |
| Approvals | `data/governed/approvals.jsonl` via `governed.approvals`/`policy_gate` | Internal canary requires no approval. |

## Active portfolio

The goal ledger has 12 non-terminal records: three `READY_FOR_HUMAN_REVIEW`
items (client beta, admin control center, GoClear campaign), eight `ACTIVE`
items (Clyde/entity readiness, customer communications, marketing creative
expansion, YouTube, social distribution, capital management, intent program
compiler, and revenue research), and one `PLANNED_DEPENDENCY` productization
item. The Research projection has 14 objective projects, currently all
`NEEDS_MORE_RESEARCH`; this is a separate read model and must not be counted
again as company projects.

`WAITING_ON_RAY`: the three explicit human-review goal records.

`WAITING_ON_EXTERNAL`: Trading’s missing supported strategy ruleset and
Systems’ missing compatibility/benchmark evidence.

`NO_NEXT_ACTION`: `nexus.productization` and `research.continuation_revenue`
have no durable goal-ledger next action. Current Research follow-up records do
have owners and questions.

## Advancement chain

Before repair, `GOAL→PROJECT` was PARTIAL because the goal ledger and Research
projection were separate. `PROJECT→WORK_ORDER` was FAIL for department
handoffs. `WORK_ORDER→DEPARTMENT` and `DEPARTMENT→WORKER` were PARTIAL/FAIL
globally; only the independent Research operator and specialized Trading
intake were proven executors. Output and review existed in Research/Alpha, but
review did not reliably create a department next action or project transition.

For the real Trading canary, every edge now passes:

`TEST handoff → wo_949ae09e4e6e41ef9d48e662d04c3425 → TRADING_ENGINE →
BLOCKED_DEPENDENCY output → TRADING_ENGINE_INTAKE_GATE review → Research
ruleset next action → WAITING_DEPENDENCY state`.

This is `PASS_REAL_PARTIAL`: it proves truthful advancement to a dependency,
not a fabricated successful backtest.

## Ranked defects

1. No canonical handoff-consumer/work-order bridge for qualified or TEST
   Research/Alpha results.
2. Goal, Research, and handoff state were split, so reports could exist without
   lifecycle transitions.
3. Department registry entries overstated execution; several workers have
   empty executor permissions and no connected consumer.
4. Handoffs lacked durable worker/output/review/next-action linkage.
5. Reports and queue existence were being mistaken for advancement.

## Department consumption

| Department | Real state |
|---|---|
| Research | PASS: continuous operator with real AI-backed outputs. |
| Alpha | PASS: OpenRouter `openai/gpt-4o-mini` reviews persist. |
| Clyde/Funding | PARTIAL/PASS for its established intelligence return path; not universal. |
| Trading | PASS for deterministic intake canary; blocked honestly without rules. |
| Systems | PARTIAL: Research can own evidence, but no connected benchmark consumer. |
| Marketing/Creative | PARTIAL: planning modules exist, no canonical handoff consumer. |
| Operations | PARTIAL: bounded scripts, no generic handoff consumer. |
| Finance | FAIL for this handoff path; no real consumer. |
| Revenue/Opportunity | FAIL for this handoff path; no real consumer. |

Passive ownership is department metadata on queue items or registry roles
without a claim path. Real execution ownership is the Research operator and
the Trading canary’s `TRADING_ENGINE` order.

## Approvals and safety

Internal research, analysis, planning, benchmarking, and paper/backtest
preparation are not Ray blockers. Valid gates remain spending, purchases,
publication, customer outreach, live trading, and material production changes.
The canary used zero budget, `approval_required=false`,
`external_action_allowed=false`, and `live_trading=false`.

## Reporting and repair

The existing two-hour reporter now reads the bridge and reports work orders
created/claimed/completed, deterministic executions, reviewed outputs, next
actions, state transitions, consumed handoffs, and department activity. It
remains read-only and does not create a scheduler or consume Research jobs.

Focused tests: 20 passed. `py_compile` and `git diff --check` passed.
