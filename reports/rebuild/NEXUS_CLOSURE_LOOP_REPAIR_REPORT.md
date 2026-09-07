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
