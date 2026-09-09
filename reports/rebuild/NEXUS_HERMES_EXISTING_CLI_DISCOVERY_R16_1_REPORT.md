# Nexus / Hermes R16.1 — Existing CLI Discovery

Status: `RUN_LIMIT_CHECKPOINT`

## Environment findings

- Mac control plane: MiMo, OpenCode, Codex, Claude Code, Kilo, Ollama, Git, Python 3, Node and npm were found. MiMo is at `~/.mimocode/bin/mimo`; its bounded discovery probe entered interactive startup, so it is present but not routable or benchmarked.
- Oracle host: Ollama 0.21.2, Git 2.52.0, Python 3.9.25 and jq 1.6 were found.
- Hermes container: OpenCode 1.18.29, gh 2.46.0, jq 1.7, fd 10.2.0, Supabase 2.117.0, Netlify 27.5.1, Playwright 1.62.0, Git 2.47.3, Python 3.13.5, Node 26.5.1, npm/npx 11.17.0 and Hermes 0.20.6 were found.

Presence is kept distinct from authenticated AI execution. No credentials were printed, inspected, or persisted.

## MiMo-first result

MiMo is an existing Mac installation, not an Oracle/Hermes-container installation. Official MiMo material documents macOS/Linux installation and an npm package, but this run did not establish ARM64 Oracle compatibility or a safe noninteractive authenticated invocation. Therefore `HERMES_CAN_CALL_MIMO=NOT_REACHED`, not `INCOMPATIBLE`.

## Coding backend benchmark

An identical disposable AI-edit benchmark was not run: no safe authenticated route was available for the required model-mediated edits, and interactive probes were bounded. OpenCode is present in the container but remains `PRESENT_NOT_TESTED`; MiMo is `PRESENT_ON_MAC_NOT_ROUTABLE_TO_HERMES`. No backend winner is claimed.

Official interface references used for the capability comparison: [MiMo Code](https://github.com/XiaomiMiMo/MiMo-Code), [OpenCode CLI](https://opencode.ai/v2/docs/cli), [Codex CLI](https://help.openai.com/en/articles/11096431), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/cli-usage), and [Aider options](https://aider.chat/docs/config/options.html). These document interfaces, not live Hermes 0.20.6 certification.

## Research/Alpha fallback

The existing fallback was exercised for `opportunity.engine / opportunity-scoring`. It produced six public search sources but zero supported claims and zero governed candidates. The exact code-level cause is `CLAIM_EXTRACTION_FAILURE`: `execute_alpha_request` invokes `run_alpha_research` with `model_calls=0` and without `claim_specs` or `opportunities`; consequently the pack can contain source rows but no findings or candidates. A narrower query did not change that pipeline gap. No unsupported claim was fabricated.

The next repair is a governed claim-extraction stage with source-bound evidence, followed by candidate generation and deterministic opportunity scoring. This is not complete in R16.1, so `REAL_GOAL_MATERIAL_PROGRESS=NO` and `NEW_CRITERIA_VERIFIED=0`.

## Contract

```text
NEXUS_HERMES_EXISTING_CLI_DISCOVERY_R16_1=RUN_LIMIT_CHECKPOINT
MAC_AI_CLIS_DISCOVERED=mimo,opencode,codex,claude,kilo,ollama,gh,git,python3,node,npm
ORACLE_AI_CLIS_DISCOVERED=ollama
HERMES_CONTAINER_AI_CLIS_DISCOVERED=opencode
MIMO_FOUND=YES
MIMO_HOST=MAC
MIMO_VERSION=UNKNOWN_INTERACTIVE_PROBE
MIMO_ARM64_ORACLE_COMPATIBLE=UNKNOWN
HERMES_CAN_CALL_MIMO=NOT_REACHED
HERMES_CAN_CALL_OPENCODE=NOT_REACHED
OTHER_EXISTING_CLI_PASS_REAL=gh,jq,supabase,netlify,fd,playwright,git,python,node,npm,npx,curl,rg
HERMES_CLI_FAILOVER=PASS_REAL
BEST_SMALL_EDIT_CLI=NOT_DETERMINED
BEST_BUG_FIX_CLI=NOT_DETERMINED
BEST_REPO_ANALYSIS_CLI=NOT_DETERMINED
BEST_CODE_REVIEW_CLI=NOT_DETERMINED
BEST_LOW_LATENCY_CLI=NOT_DETERMINED
BEST_STRUCTURED_OUTPUT_CLI=NOT_DETERMINED
BEST_GENERAL_CODING_BACKEND=NOT_DETERMINED
MIMO_VS_OPENCODE_WINNER_BY_TASK_CLASS=NOT_DETERMINED
CLI_DELEGATION_REDUCES_NEMOTRON_DEPENDENCE=NOT_TESTED
RESEARCH_ZERO_CLAIMS_ROOT_CAUSE=CLAIM_EXTRACTION_FAILURE
REAL_RESEARCH_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
NORMAL_BROKER_SELECTED_CODING_BACKEND=NOT_REACHED
REAL_ENGINEERING_TASK_MATERIAL_PROGRESS=NOT_REACHED
TRUE_RAY_BLOCKERS=NONE
```

The R16.1 checkpoint is deliberate: the discovery evidence is complete, but live AI edit benchmarking and the Alpha claim-extraction repair require a safe authenticated execution path or a bounded implementation pass. 
