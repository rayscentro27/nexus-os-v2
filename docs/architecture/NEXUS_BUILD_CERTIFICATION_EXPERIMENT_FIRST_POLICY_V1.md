# Nexus Build Certification — Experiment-First Policy V1

## Purpose

Nexus learns by safe execution, not only by evaluation. While the platform is
being built and certified, `BUILD_CERTIFICATION_MODE` exercises meaningful
internal work through the real department lifecycle so that queues, workers,
reasoning, outputs, reviews, lessons, and state transitions can be proven.

`NORMAL_PRODUCTION_MODE` remains available for mature external workflows. It
keeps normal qualification and gating active.

## Operating modes

The canonical selection is `configs/nexus_operating_mode.json`, with the
environment variable `NEXUS_OPERATING_MODE` available for a bounded invocation.
Only these values are valid:

- `BUILD_CERTIFICATION`
- `NORMAL_PRODUCTION`

The default in this repository is `BUILD_CERTIFICATION`. This is an internal
learning mode, not a production or customer-authorization mode.

## Certification disposition

`CERTIFICATION_TEST` means: safe internal experimentation is authorized because
the item has a meaningful hypothesis and can be tested safely, cheaply,
reversibly, and with learning value. It does not mean customer readiness,
profitability, compliance approval, lender approval, trading profitability,
tool adoption, or public-launch approval.

Before `REJECT`, `RESEARCH_MORE`, `MONITOR`, or `NO_ACTION` is used for a
candidate, the decision record includes:

`CAN_THIS_BE_TESTED_SAFELY`, `CAN_THIS_BE_TESTED_CHEAPLY`,
`CAN_THIS_BE_TESTED_REVERSIBLY`, `CAN_THIS_TEACH_NEXUS_SOMETHING`,
`HARD_BLOCKER_PRESENT`, and `WHY_CERTIFICATION_TEST_NOT_USED`.

In build mode, a candidate with all four positive testability signals and no
hard blocker normally becomes `CERTIFICATION_TEST`. A low score or low
confidence alone cannot terminate safe internal learning. `RESEARCH_MORE`
means a meaningful bounded test cannot yet be constructed; it is not a parking
state caused by ordinary uncertainty.

## Hard safety boundaries

Certification never bypasses illegal activity, fraud or deception, policy or
compliance restrictions, live trading, customer financial applications,
customer outreach, public publishing, paid advertising, purchases, inventory,
funds movement, sensitive-data exposure, uncontrolled security risk,
irreversible production changes, access-control or CAPTCHA bypass, consented
account creation, or paid subscriptions. These remain hard stops or governed
approval boundaries.

Internal research, analysis, planning, drafting, isolated benchmarking,
paper/backtesting, non-PII matching, and internal simulation can proceed when
their boundary is explicit.

## Learning contract

Every certification experiment uses the append-only governed
`certification_experiments` collection. It records the parent goal/project,
department, source finding, Alpha decision, hypothesis, reason to test anyway,
expected and actual results, method, safety/cost/reversibility boundaries,
inputs, variants, metrics, lesson, next test, owner, and completion state.

The lifecycle is:

`INPUT → CLAIMED → AI_REASONING → EXECUTION → OUTPUT → REVIEW → MEASUREMENT → LESSON → NEXT_ACTION → STATE_ADVANCED`

`EXPERIMENT_FAILED` means the experiment produced a useful negative or failed
result; it does not mean the department failed. Certification evaluates whether
the process executed, measured, reviewed, and learned.

## Department expectations

Trading may use paper/backtest work only; Creative may compare internal concept
variants; Clyde may perform non-PII funding matching and gap analysis; Systems
may run isolated compatibility tests; Revenue and Marketing may prepare internal
validation, economics, briefs, and plans. None of these authorize external
spend, publication, customer contact, inventory, or production mutation.

Alpha remains a challenger and advisory qualification layer. It records weak
evidence, risks, unknowns, and expected failure, but is not the sole stop
authority for safe internal work. Ray remains the final business authority.

## Real certification

A department is certified only when a real meaningful item is claimed, receives
real AI reasoning where required, executes, persists output, is reviewed,
measured, produces a lesson and next action, and advances state. Unit tests,
prompt generation, queue rows, and reports alone are insufficient.

External actions remain governed in both modes. Build mode should end when the
platform has trustworthy evidence of department operation and can return to
normal production gating deliberately.
