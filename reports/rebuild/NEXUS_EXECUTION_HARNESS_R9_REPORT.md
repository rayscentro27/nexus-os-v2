# Nexus Execution Harness R9

## Result

R9 proves one normal-runtime, AI-backed, criterion-specific Portal execution
path. R8's `RUNTIME_AUTONOMY_ONLY` result is preserved: this is harness proof,
not a claim of systematic whole-company outcome autonomy.

## Runtime proof

- Normal service selected `portal.client_beta`; it was not selected by Codex:
  `continuous_kernel:portal.client_beta:202609081356`.
- Real AI worker receipt: `reports/runtime/ai_workforce_receipts/aiwf_ddf664c1dab94845aa0b348cf0f384e8.json`.
- First repaired attempt failed with a real Node/tool mismatch and safety
  violation: `reports/runtime/engineering_receipts/engineering_portal_d4a69fc7266f40ba85ff540cef2f2916.json`.
- Material recovery delta: the governed wrapper changed from Node 18 selection
  to highest installed Nexus-controlled Node; the stale unsupported Portal
  wording was corrected. The repaired worker then ran Node v24/npm 11.
- Successful execution receipt:
  `reports/runtime/engineering_receipts/engineering_portal_c7639b9c1f124c1eaf2806e8f9f7df04.json`.
- Its real commands passed: focused Vitest, `npm run build`, and the Portal
  safety verifier. The receipt records `status=PASS` and
  `criterion_verification=VERIFIED` for `Record capability audit`.
- Canonical state now retains the parent active with `Record capability audit`
  fixed and `Verify tenant and approval boundaries` remaining.

## Harness changes

`execution_harness.py` supplies worker-specific environment preflight,
capability readiness rows, failure classification, environment fingerprints,
and material-delta calculation. The launch wrapper repairs launchd's Node
environment without exposing credentials. The Engineering skill is reusable
and explicitly separates tools from operating instructions. Verified criteria
persist `next_task_id` for later continuation.

The executor remains closed-world: repository reads/writes and fixed test,
build, and safety commands are allowlisted; no arbitrary shell, deployment,
external mutation, customer contact, spend, or production data mutation is
available.

## Current contract

R8_RUNTIME_AUTONOMY_ONLY_ACKNOWLEDGED=YES
CYCLE_COUNT_RECONCILED=YES (31 receipts reconciled to one launchd-owned daemon; the separate Active Operator service skips overlap)
SINGLE_CANONICAL_SUPERVISOR=YES
SUPERVISOR_ENVIRONMENT_CONTRACT=PASS_REAL
PORTAL_SUPERVISOR_NODE_AVAILABLE=YES
PORTAL_SUPERVISOR_NPM_AVAILABLE=YES
WORKER_SPECIFIC_CAPABILITY_READINESS=PASS_REAL
CAPABILITY_READINESS_GATE=PASS_REAL
CAPABILITY_ENABLEMENT_TASKS=PASS_REAL (preflight/recovery contract persisted; no missing capability remained after environment repair)
SKILL_REGISTRY=PASS
SKILL_VS_TOOL_DISTINCTION=PASS
ENGINEERING_SKILL=PASS_REAL
MCP_AND_TOOL_DISCOVERY=PASS_REAL (no MCP was required for this Portal criterion)
GENERIC_ARTIFACT_FALLBACK_FOR_EXECUTION_CRITERIA=REMOVED
TASK_LEDGER=PASS (canonical work item and operator receipt)
STATUS_NORMALIZATION=PASS
COMPLETE_DEPENDENCY_RECOGNIZED=YES
WAITING_STATES_ARE_NONTERMINAL_AND_RESUMABLE=YES
FAILURE_CLASSIFICATION=PASS_REAL
RECOVERY_STATE_MACHINE=PASS_REAL
CONTINUATION_PRESERVED=YES
RECOVERY_SCHEDULED=YES
RECOVERY_EXECUTED=YES
RECOVERY_SUCCEEDED=YES
RETRY_REQUIRES_MATERIAL_DELTA=PASS
IDENTICAL_RETRY_SUPPRESSED=PASS_REAL
NO_PROGRESS_CONTROL=PASS_REAL
LEARN_BEFORE_RETRY=PASS_REAL
CONTINUATION_INVARIANT_RUNTIME_ENFORCEMENT=PASS_REAL
REAL_ENGINEERING_HARNESS=PASS_REAL
HARDCODED_SINGLE_PATCH_EXECUTOR_REPLACED_OR_GENERALIZED=YES
PORTAL_UNMET_CRITERION=Record capability audit
PORTAL_REAL_ENGINEERING_EXECUTION=PASS_REAL
PORTAL_MATERIALITY_TO_CRITERION=PASS
PORTAL_CRITERION_SPECIFIC_ACCEPTANCE=PASS_REAL
PORTAL_NEW_CRITERION_VERIFIED=YES
PORTAL_NEXT_TASK_AUTOMATICALLY_PERSISTED=YES_BY_CONTROLLER (next action is persisted as `engineering.portal_beta`; explicit task ID applies on the next verified transition)
SECOND_ATTEMPT_MATERIAL_DELTA=YES
NORMAL_SUPERVISOR_USED=YES
CODEX_SELECTED_CHILD_ACTION=NO
SYSTEMATIC_OUTCOME_AUTONOMY=NOT_YET_CERTIFIED

TRADING_LIVE_EXECUTION_ENABLED=false
AUTO_TRADING=false
TRADING_PAPER_ONLY=true
PRODUCTION_DEPLOYMENT_PERFORMED=NO
SECRET_EXPOSED=NO
UNRELATED_WORKTREE_CHANGES_PRESERVED=YES
TRUE_RAY_BLOCKERS=NONE

## Tests

- `3 passed` focused R9 harness tests.
- focused Portal Vitest: `1 file / 3 tests passed`.
- `npm run build`: passed.
- Portal safety verifier: passed.

## Limitation

The canary verified one new criterion, but the parent goal still has a
separate tenant/approval criterion. Systematic outcome autonomy remains out of
scope for R9 and must not be inferred from this single successful criterion.
