# Nexus Company Goal Portfolio R3

## Executive Result

`NEXUS_COMPANY_GOAL_PORTFOLIO_R3=PARTIAL`. The seven existing objectives were
preserved and expanded into one durable 23-goal company portfolio. Active
Operator now performs separate operating-duty preflight and deterministic
priority/age/fairness selection. A live supervisor run created a P1 Trading
work order through this path. Full phone-only weekend observation and
proactive Telegram certification remain unproven.

## Starting State

```text
START_HEAD=f76defcbfb215dad059a88a91d892d6be58f3515
ORIGIN_MAIN=f76defcbfb215dad059a88a91d892d6be58f3515
BRANCH=main
WORKTREE_ENTRY_COUNT_BEFORE=603
```

Unrelated worktree changes were preserved.

## Architecture Audit

The previous path was `active_objective_portfolio()` → Active Operator →
governed work-order/receipt execution. The portfolio function returned seven
static dictionaries and selection used an hour-modulo cursor. There was no
durable roadmap registry, dependency-aware status, or portfolio fairness state.

## Canonical Goal Store

`data/runtime/company_goal_portfolio.json`, materialized by
`ensure_company_goal_portfolio()` in `scripts/nexus_agent_platform/goal_completion.py`,
is the single runtime portfolio. It preserves progress and selection state and
does not create a second queue or objective engine.

## Roadmap Goals

The 23 persisted parent goals are:

```text
trading.real_data
research.company_intelligence
portal.client_beta
portal.admin_control_center
goclear.example_campaign
systems.modal_verification
systems.oracle_browser
clyde.entity_readiness
business_plans.customer_goals
funding.workflow_expansion
grants.intelligence
goclear.economic_model
commerce.billing_accounting
customer_service.communications
documents.esign
research.notebook
opportunity.engine
marketing.creative_expansion
media.youtube_video
distribution.social
finance.capital_management
nexus.intent_program_compiler
nexus.productization
```

Every row includes statement, program, department, priority, authority,
success criteria, dependencies, evidence, missing criteria, failed paths,
candidate paths, progress, next review, and timestamps.

## Statuses and Dependencies

There are 22 eligible goals (`ACTIVE`/`READY`) and one dependency-gated goal:
`nexus.productization=PLANNED_DEPENDENCY`. The original seven remain present
and eligible. Productization is not presented as ready before its prerequisites
mature.

## Operating-Duty Separation

`operating_duty_preflight()` runs before discretionary selection and reports
control-plane health, supervisor state, Research heartbeat/mode, receipt
integrity, Ray-review evaluation, and authority. Healthy duty checks do not
consume the company goal slot.

## Portfolio Governor

`select_portfolio_goal()` ranks eligible goals by priority, age, selection
count, and stable ID. A durable two-consecutive-selection limit prevents an
eligible peer from starving. The Active Operator uses this governor instead of
the hour-based cursor.

## Research Not Terminal Endpoint

Research remains an evidence/service lane. A completed research task does not
satisfy a parent business outcome; missing criteria remain open and department
workstreams continue.

## Department Handoff

Each goal has a durable owning department and Nova can read that ownership. The
current safe autonomous executor remains the existing bounded Research adapter;
department-specific implementation is represented as the next workstream
without inventing another executor.

## Hermes Executive Management

The existing shared Nova read boundary now exposes
`get_company_goal_portfolio`. It returns live executive-safe counts, statuses,
missing criteria, dependencies, progress, and next safe paths. Nova formatting
uses a verified portfolio block without raw database schema.

## Phone-Only Visibility

Direct shared-path proof passed with 23 goals and the approved read-only
boundary. Telegram-specific proactive communication was not rebuilt here and
remains a separate certification gap.

## Live Proof

The canonical supervisor remained loaded and running. Its latest Active
Operator run created:

```text
source=goal_completion_engine
parent_goal=trading.real_data
priority=P1
recommended_action=research.refresh
authority=INTERNAL_AUTONOMOUS
external_side_effects=false
```

Direct runtime checks passed:

```text
TOTAL_GOALS=23
ELIGIBLE_GOALS=22
DEPENDENCY_GATED_GOALS=1
OPERATING_DUTY_PREFLIGHT=PASS_REAL
NOVA_PHONE_PORTFOLIO_VISIBILITY=PASS_REAL
```

## Tests

`py_compile` passed for every touched Python file. Direct focused contract
checks passed for persistence, roadmap ingestion, success criteria,
dependency gating, governor selection, duty preflight, shared capability
access, and Nova formatting. The repository pytest invocation did not return
within the execution window; no broad pytest pass is claimed.

## Safety State

```text
TRADING_LIVE_EXECUTION_ENABLED=false
AUTO_TRADING=false
TRADING_PAPER_ONLY=true
EXTERNAL_CONSEQUENTIAL_ACTIONS=BLOCKED
NOVA_MODEL_CHANGED=NO
NOVA_PROMPT_TUNED=NO
MINIMAX_ACTIVATED=NO
MODEL_ROUTER_IMPLEMENTED=NO
NEW_COMPLIANCE_DEPARTMENT_IMPLEMENTED=NO
NEW_PRE_CREATIVE_COMPLIANCE_GATE=NO
```

## Runtime Continuity

The continuous supervisor remains active without Codex. Research heartbeat
evidence remains `ACTIVE` with `execution_mode=REAL`; the latest runtime state
recorded `kernel_cycle_94` and real Active Operator work. Oracle, MCP, and the
existing model route were not changed.

## Weekend Readiness Assessment

The durable portfolio/governor foundation is ready for unattended observation,
but full phone-only weekend readiness is not certified. Remaining proof is a
genuine multi-cycle rotation across eligible goals and separately certified
proactive executive communication.

## True Ray Blockers

None for safe internal portfolio work. The missing weekend observation is a
test window, not a Ray authority blocker.

## Git

Task-scoped files are the portfolio contract, Active Operator integration,
shared Nova portfolio read/formatting, focused tests, runtime portfolio seed,
and this report. Existing unrelated worktree changes remain unstaged.

```text
CURRENT_SEVEN_GOALS_PRESERVED=YES
DURABLE_GOAL_PORTFOLIO=PASS_REAL
HARDCODED_PORTFOLIO_LIMITATION_REMOVED=YES
OPERATING_DUTIES_SEPARATE_FROM_GOAL_QUEUE=PASS_REAL
ROADMAP_GOALS_PERSISTED=PASS_REAL
SUCCESS_CRITERIA_PER_GOAL=PASS
DEPENDENCY_AWARE_STATUSES=PASS
PORTFOLIO_GOVERNOR=PASS_REAL
ANTI_STARVATION=PASS_REAL
RESEARCH_NOT_TERMINAL_ENDPOINT=PASS_REAL
DEPARTMENT_HANDOFF=PASS_REAL
BLOCKED_PATH_PARENT_CONTINUATION=PASS_REAL
PHONE_ONLY_HERMES_GOAL_VISIBILITY=PASS_REAL
PROACTIVE_EXECUTIVE_COMMUNICATION=NOT_YET_AVAILABLE
OPERATING_DUTIES_HEALTHY=YES
CURRENT_RESEARCH_EXECUTION_MODE=REAL
NORMAL_CANONICAL_SUPERVISOR_ACTIVE=YES
NEXUS_CONTINUES_WITHOUT_CODEX=PASS_REAL
NEXUS_LEFT_ACTIVE=YES
TRUE_RAY_BLOCKERS=NONE
SAFE_FOR_RAY_PHONE_ONLY_WEEKEND=NO
```
