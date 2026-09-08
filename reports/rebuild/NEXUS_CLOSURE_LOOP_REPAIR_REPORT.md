# Nexus Closure Loop Repair Report

## Scope

This is a continuation of the prior real-goal finisher validation. It does
not re-certify autonomous wake, work selection, execution, or generic
finalization. It addresses the narrower defect: a failed final package was
recorded as a generic rejection/rework hint and the goal could return to the
portfolio before a dedicated closure session had been persisted.

## Root cause

The final reviewer already returned useful `remaining_work`, but the runtime
did not normalize each failed success criterion into a durable failure
contract. `record_goal_rework()` stored a list of strings and set
`CONTINUE_MISSING_CRITERIA`; it did not retain expected-versus-observed
conditions, a criterion identity, acceptance test, or a closure-session
identity. Consequently, the next attempt was repairable in practice but
looked like ordinary scheduler rework rather than continuation of the same
closure.

The failure was not a false terminal transition and not an evaluator bypass.
The evidence-bound finalizer correctly rejected incomplete packages.

## Repair implemented

`ai_workforce_executor.py` now writes `finalization_failure.criteria` into
the AI receipt. Each criterion contains a stable criterion ID and failure ID,
expected condition, observed condition, delta, missing component/information,
quality/source/validation gaps, repairability, repair strategy, acceptance
test, and blocker type. The failure report also names the failed finalization
attempt and required bounded repair action.

`goal_completion.py` now persists:

- `closure_session` with session ID, round counts, failure history, remaining
  criteria, strategy, and bounded `max_rounds=4`;
- normalized `finalization_failures`;
- criterion-specific `repair_contracts` with allowed worker/tools, evidence
  constraints, completion condition, failure conditions, and acceptance test.

The selector prioritizes an open bounded closure session before other
eligible work. The round limit prevents infinite monopolization; an exhausted
session remains diagnosable through its persisted state rather than silently
disappearing.

## Before / after

Before:

```text
FINALIZATION -> FAILED -> remaining_work: [strings]
             -> generic CONTINUE_MISSING_CRITERIA
```

After:

```text
FINALIZATION
  -> failure record per criterion (expected / observed / delta)
  -> closure session REPAIR_REQUIRED
  -> criterion repair contract
  -> same-goal closure-priority selection
  -> repair / verification / finalization retry
```

## Existing real-goal evidence used

The prior and immediately subsequent runtime evidence remains authoritative:

- `systems.oracle_browser`: finalization receipt
  `aiwf_676bfb20a8784ec68b16f9f15dff60e8` rejected the package because the
  Oracle path, bounded browser result, and stale-session recovery criteria
  were not substantiated. Its prior bounded artifact was
  `deliverable_2ae5c8a25f6d449e82c82b79438bcd25`.
- `commerce.billing_accounting`: retry receipt
  `aiwf_ad904ccc371143d891dbd8c0bc5482cf` rejected the package because the
  invoice lifecycle, receivables/expense views, and external-invoice gate
  criteria remained unmet.

These are real failures and real rework inputs; no synthetic goal, score,
artifact, or terminal transition was created. A new runtime cycle is
required to populate the new structured fields in a fresh production receipt;
the code-level smoke test below verifies the normalization contract.

## Verification

```text
PYTHON_COMPILE=PASS
STRUCTURED_FAILURE_SMOKE=PASS
```

The existing focused finisher tests previously passed (`26 passed`), and the
new code preserves the evidence-bound no-false-terminal behavior. Full pytest
execution was not used as the sole proof because the long-lived local runtime
and its file activity caused the repository test process to hang; compilation
and direct contract assertions completed successfully.

## Required contract status

```text
DESCRIPTIVE_FAILURES=YES
EXPECTED_VS_OBSERVED_DELTA=YES
REPAIRABLE_FAILURE_STAYS_IN_CLOSURE_LOOP=YES
AUTOMATIC_SECOND_ATTEMPT=NOT_YET_RE-PROVEN_THIS_RUN
CRITERION_VERIFICATION=PARTIAL (review path exists; per-criterion verification is now represented)
STRATEGY_CHANGE_ON_REPEAT_FAILURE=NOT_YET_PROVEN
STALE_STATE_DEFECT_FOUND=NO
UNATTENDED_CLOSURE_RESUME=YES by persisted session/selector design; fresh post-patch runtime proof pending
REAL_GOAL_CONVERGENCE_PROVEN=NO
NEW_REAL_GOAL_TERMINAL_TRANSITION=NO
SYSTEMATIC_OUTCOME_AUTONOMY=NO
```

The precise remaining boundary is runtime convergence: existing evidence
shows rework artifacts and retries, but not yet a criterion changing from
failed to verified and then a new terminal transition under this closure
session implementation. The system now records enough information to make
that next attempt actionable and auditable without falsely claiming success.

## Live closure convergence observation — 2026-09-07

Using the normal operator entry point on the existing
`systems.modal_verification` goal, the runtime produced this same-session
sequence:

```text
FINALIZATION ATTEMPT 1: 202609071723 -> failed; 3 criteria unresolved
REPAIR ROUND 1: 202609071738 -> bounded artifact persisted
FINALIZATION ATTEMPT 2: 202609071753 -> failed; same 3 criteria unresolved
REPAIR ROUND 2: closure session retained
FINALIZATION ATTEMPT 3: closure_live_20260907_04 -> failed; 3 criteria unresolved
REPAIR ROUND 3: closure_live_20260907_05 -> artifact persisted
FINALIZATION ATTEMPT 4: closure_live_20260907_06 -> failed; 3 criteria unresolved
```

The durable session ID was `closure_d55547e5aec91e3a7184`. Runtime state
recorded `current_round=4`, `finalization_attempt_count=4`, and
`repair_attempt_count=4`. Every attempt used the same real goal and the same
evidence-bound AI planner/reviewer; no Codex-authored deliverable or synthetic
goal was inserted. This proves automatic retries and session continuity, but
not convergence: the model repeatedly produced explanatory report text
without evidence that satisfies Modal health, bounded-job, and cost/authority
criteria. The final retry remains correctly non-terminal.

The bounded-exhaustion guard is now implemented: when a new failure reaches
the configured fourth round, the session is written as `CLOSURE_STALLED` and
excluded from ordinary portfolio selection, preventing silent infinite retry.
The live session reached round four just before that guard was installed, so
its persisted pre-guard label remains `REPAIR_REQUIRED`; this is intentionally
not rewritten by Codex as a business result.

## Second live validation — 2026-09-08

The normal runtime then exercised a second existing real goal,
`opportunity.engine`, using closure session `closure_92664a4ffb62454460b1`:

```text
closure_validation_01: repair artifact persisted; 3 criteria remained
closure_validation_02: automatic FINALIZATION retry failed descriptively
closure_validation_03: repair artifact persisted; same criteria remained
closure_validation_04: automatic FINALIZATION retry failed descriptively
final state: CLOSURE_STALLED after bounded round 4
```

The four operator receipts and AI receipts are persisted under
`reports/runtime/nexus_active_operator_receipts/` and
`reports/runtime/ai_workforce_receipts/`. No human or Codex business action
was supplied between cycles. This confirms the second-attempt and additional
retry behavior on a second real goal, while also confirming non-convergence
detection. The remaining delta is substantive evidence for evidence-bound
scoring, experiment/routing design, and rejection of hype/weak economics;
the AI repeatedly produced descriptive plans rather than proof of those
criteria.

Updated live status:

```text
AUTOMATIC_SECOND_ATTEMPT=YES
CRITERION_VERIFICATION=PARTIAL (review runs and records criterion failures; no criterion passed)
STRATEGY_CHANGE_ON_REPEAT_FAILURE=NO (same model strategy remained descriptive)
UNATTENDED_CLOSURE_RESUME=YES
REAL_GOAL_CONVERGENCE_PROVEN=NO
NEW_REAL_GOAL_TERMINAL_TRANSITION=NO
SYSTEMATIC_OUTCOME_AUTONOMY=NO
```
