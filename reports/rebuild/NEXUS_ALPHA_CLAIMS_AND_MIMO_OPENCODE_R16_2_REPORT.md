# Nexus / Hermes R16.2 — Alpha Claims + Coding Backends

Status: `RUN_LIMIT_CHECKPOINT`

## Alpha repair

The missing handoff was in `execute_alpha_request()`: it collected evidence but called `run_alpha_research()` without `claim_specs` or `opportunities`. The intended contract is pre-built inputs to `run_alpha_research`; the ordinary executor had no producer. The repair adds a deterministic extractor for non-empty search-result title/snippet observations, binds each observation to its evidence ID, and creates an advisory candidate only when at least two claims exist.

The real run for `opportunity.engine / opportunity-scoring` produced six sources, six extracted claims, six supported direct-observation claims, and one governed candidate. The candidate has an inspectable score of 28, evidence confidence 85, and unknown economics. The canonical verifier ran and verified `opportunity scoring is evidence-bound`, producing one new verified criterion. The remaining two criteria are not claimed complete.

## Coding CLI result

MiMo was found on the Mac at `~/.mimocode/bin/mimo`. Official MiMo documentation exposes `mimo run` as a headless surface, but the documented unattended example uses `--dangerously-skip-permissions`; no safe permission allowlist plus authenticated route was established here. It remains `AUTH_REQUIRED`, not incompatible. OpenCode 1.18.29 is present in the Hermes container and supports `opencode run --format json`, but the only available Hermes model route is the previously penalized slow Nemotron route. Neither backend performed the required disposable edit, so neither is certified.

The existing R16 CLI failure-learning/failover path remains authoritative; no unproven CLI was registered as routable.

## Contract

```text
NEXUS_ALPHA_CLAIMS_AND_MIMO_OPENCODE_R16_2=RUN_LIMIT_CHECKPOINT
CLAIM_EXTRACTION_ROOT_CAUSE_CONFIRMED=YES
CLAIM_EXTRACTION_REPAIRED=PASS_REAL
CLAIM_EXTRACTION_EXECUTED=YES
CLAIMS_EXTRACTED=6
SUPPORTED_CLAIMS=6
GOVERNED_OPPORTUNITY_CANDIDATES=1
NEXUS_VERIFIER_RAN=PASS_REAL
REAL_RESEARCH_GOAL_MATERIAL_PROGRESS=YES
NEW_CRITERIA_VERIFIED=1
RESEARCH_RESULT_TO_NEXT_ACTION_CONTINUATION=NOT_NEEDED
MIMO_AUTOMATION_MODE_IDENTIFIED=YES
MIMO_AUTH_STATE=AUTH_REQUIRED
HERMES_CAN_CALL_MIMO=NOT_REACHED
HERMES_CAN_CALL_OPENCODE=NOT_REACHED
BEST_SMALL_EDIT_CLI=NOT_DETERMINED
BEST_BUG_FIX_CLI=NOT_DETERMINED
BEST_TEST_REPAIR_CLI=NOT_DETERMINED
BEST_REPO_ANALYSIS_CLI=NOT_DETERMINED
BEST_CODE_REVIEW_CLI=NOT_DETERMINED
NORMAL_BROKER_SELECTED_CODING_BACKEND=NOT_REACHED
REAL_ENGINEERING_TASK_MATERIAL_PROGRESS=NOT_REACHED
TRUE_RAY_BLOCKERS=NONE
```
