# Nexus Hermes Multi-CLI Execution R16

## Research fallback

The existing `opportunity.engine` goal was not retried through the slow
Nemotron route. Normal failure learning penalized the exact
OpenRouter/Nemotron/Research combination, and the unified selector rerouted to
the existing Research/Alpha executor. That execution completed with six public
sources, but produced zero supported claims and zero governed opportunity
candidates. Therefore the fallback worked as an execution path, but did not
verify the canonical criterion or create material goal progress.

## Live model and CLI evidence

Hermes currently exposes one authenticated route: OpenRouter with
`nvidia/nemotron-3.5-lightning:free`. Its fallback chain is empty. The live
ARM64 container has OpenCode 1.18.29 plus git, Python, Node/npm/npx; Codex,
Claude Code, and Aider are absent. They were not installed blindly because no
durable, authenticated, architecture-approved installation path was available
within this bounded run.

Official references used for the CLI capability comparison: [OpenAI Codex CLI
installation and approval modes](https://help.openai.com/en/articles/11096431),
[OpenCode noninteractive automation](https://opencode.ai/v2/docs/cli), and
[Aider scripting](https://aider.chat/docs/scripting.html).

## Contract

NEXUS_HERMES_MULTI_CLI_EXECUTION_R16=RUN_LIMIT_CHECKPOINT
ALTERNATE_CAPABILITY_FALLBACK_WORKS=PASS_REAL
HERMES_PATH_FAILED_BUT_GOAL_REROUTED=YES
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
MODEL_CANDIDATES_TESTED=1
CURRENT_NEMOTRON_ROUTE_PENALIZED=YES
HERMES_CLI_FAILOVER=PASS_REAL (policy and cross-capability reroute)
NEXUS_VERIFIER_RAN=PASS_REAL (result FAILED_WITH_EVIDENCE_INSUFFICIENT)
MODEL_FAILURE_LEARNING_USED_IN_SCORING=PASS_REAL
OPENCODE=FAIL (installed but not live benchmarked)
CODEX_CLI=NOT_COMPATIBLE (absent in live container)
CLAUDE_CODE=NOT_COMPATIBLE (absent in live container)
AIDER=NOT_COMPATIBLE (absent in live container)
DELEGATED_CLI_REDUCES_HERMES_MODEL_DEPENDENCE=PARTIAL
NORMAL_BROKER_SELECTED_BEST_CLI=NOT_REACHED
REAL_ENGINEERING_TASK_MATERIAL_PROGRESS=NOT_REACHED
TRUE_RAY_BLOCKERS=NONE

No production, customer, financial, trading, or Portal state was changed.
