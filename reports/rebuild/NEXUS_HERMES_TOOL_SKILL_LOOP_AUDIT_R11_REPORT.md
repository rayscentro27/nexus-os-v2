# Nexus / Hermes R11 tool, skill, MCP, and loop audit

## Executive verdict

`NEXUS_HERMES_TOOL_SKILL_LOOP_AUDIT_R11=COMPLETE`. This was an audit and bounded-test run; no routing, model, authority, service, goal, or Portal state was changed. Nexus has real governed executors and Hermes has a broad native source surface, but they are not one capability control plane. The strongest finding is a split: Nexus production work is selected by deterministic goal/criterion/action mappings and hardcoded Active Operator dispatch, while Hermes uses profile/toolset/model-side tool schemas. OpenCode is installed and version-probed (`1.18.25`) but is not proven callable or routable by Nexus/Hermes for a real goal.

R8's runtime-only result remains credible. R11 found no evidence that the present architecture can prevent an R8-style run of repeated AI/receipt activity with zero criterion convergence; no repair was made here.

## Snapshot and safety

- HEAD: `23fc2f8702fdf32bb5945adf83823575194216b6`, branch `main`.
- Worktree: substantially dirty before this audit; unrelated changes were preserved.
- `com.nexus.continuous-loop`: running, PID observed; `com.nexus.active-operator-v2`: loaded/not running between one-shot launches, last exit 0, 900-second interval.
- Nexus MCP bridge, Oracle Hermes tunnel, Telegram Hermes/Nova, and Hermes gateway launchd entries were present.
- Portal remained `READY_FOR_HUMAN_REVIEW`; no business state was modified.
- Trading safety remains paper-only; no consequential external action was performed.

## Master inventory

The machine-readable inventory is [nexus_tool_control_inventory_r11.json](/Users/raymonddavis/nexus-os-v2/reports/runtime/nexus_tool_control_inventory_r11.json). It records 11 CLI registry entries, 11 Nexus manifest capabilities, 105 Hermes tool-discovery paths, 17 Nexus skills, two configured MCP servers, five named worker records, and plugin/runtime families. These are inventory records, not a claim that every item is callable. The CLI registry itself labels all 11 `installed_only` and authenticated `not_proven`.

Operationally, the real used set is smaller: `nexus_ai_workforce`, the allowlisted Nexus Python/CLI broker, Research/SearXNG paths, Modal bounded CPU, Portal engineering, and Nova read-only MCP/communication paths. `frontend.build`, `tests.run`, `research.alpha`, creative, and system capabilities are declared in `configs/nexus_capability_manifest.json`; the manifest is deny-by-default and prohibits arbitrary shell.

## CLI, workers, and OpenCode

The registry contains git, node, npm, python3, supabase, netlify, gh, ollama, opencode, codex, and playwright. Node/npm/git/python have concrete local versions; Supabase, Netlify, GitHub CLI, and OpenCode registry probes were timeout/unproven even though OpenCode itself answered the direct executable probe. OpenCode direct test: `/Users/raymonddavis/.nvm/versions/node/v22.22.3/bin/opencode --version` → `1.18.25`. No OpenCode repo read/edit/test receipt was created in R11, and no Nexus dispatch adapter or allowlisted action was found. Historical certification records show OpenCode as an installed/probed worker, not a current real Nexus-goal route.

Other coding workers: Codex has historical probe evidence but is not a Nexus production route; `nexus_ai_workforce` is the actual engineering receipt worker; Mimo is installed-unproven; Kilo/OpenHands are not proven available. The narrow engineering action `engineering.portal_beta` remains a hardcoded Active Operator path with static `skills_loaded` in its receipt.

## MCP and external surfaces

`config/hermes/nova-profile/config.yaml` configures `nexus_mcp` and `google_mcp`. The cached Nexus schema exposes six read-oriented tools: `nexus_get_reviews`, `nexus_get_work_items`, `nexus_get_blockers`, `nexus_get_opportunities`, `nexus_get_business_state`, and `nexus_get_system_health`, plus MCP utility resource/prompt operations. Nexus MCP is read-only in the profile and has no write authority. The audit environment exposed no direct MCP connector tool namespace, so no live representative MCP call is claimed; cached schemas, bridge process state, and configuration are evidence of configured/discoverable surfaces only.

Google MCP is configured with a receipt directory but authenticated/callable status was not proven in this read-only run. No email/calendar mutation occurred. The Nexus MCP layer is a Nova-facing read boundary and does not share the Active Operator's execution registry.

## Browser, research, data, and remote execution

Hermes source contains browser, CDP, Camofox, computer-use, terminal, file, web, and vision modules. Prior remote capability memory records Oracle Hermes `0.20.6`, Oracle browser, Modal CPU, and SearXNG as successful historical paths; R11 does not upgrade that historical evidence into a current Hermes model-visible/callable claim. The local CLI registry marks Playwright installed but not real-tested in this run.

Research is REAL in the Nexus Research path: SearXNG and Alpha adapters exist and prior receipts show real retrieval. However, the R8 downstream-impact audit found real Research refreshes without parent criterion convergence. Supabase has a live certification harness and R10A real synthetic identity/RLS evidence, but the CLI registry labels the CLI itself installed-only; test authority and production authority are separate.

Remote execution has a real certified Modal path and a historically healthy Oracle/SSH/Hermes path. Nexus routing explicitly binds Modal criteria to `ModalRemoteWorkerProvider`; the generic capability broker does not dynamically compare all remote backends.

## Hermes deployed version and native feature matrix

The checked-in Hermes runtime declares `0.20.0` in `pyproject.toml`. The configured remote capability memory expects Oracle Hermes `0.20.6` and reports a historical `HEALTHY_0.20.6`; the actual remote version was not re-probed successfully. The local `hermes` script exists but bounded `--version`/`version` probes timed out, so no false deployed-version claim is made.

The native source surface includes terminal/process management, file read/write/edit, browser/CDP/computer use, web tools, MCP, skills and skill manager/hub, memory/session search, delegated subagents, code execution, cron, messaging, plugins/hooks, and provider/model infrastructure. Presence is not enablement: the Nova profile has `memory_enabled: false`; the profile has two MCP servers; native skill machinery exists but only one optional `SKILL.md` was found in the runtime’s skill trees; actual profile visibility and model tool schemas were not recoverable as a live runtime receipt. The full machine-readable feature matrix is in [hermes_native_feature_inventory_r11.json](/Users/raymonddavis/nexus-os-v2/reports/runtime/hermes_native_feature_inventory_r11.json).

## Skills

Nexus has 17 loadable `skills/nexus/*/SKILL.md` skills and a deny-by-default loader at `loops/skill_resolver.py`. It checks worker, authority, and allowed executors, but the call sites found do not implement dynamic task requirement scoring, failure-triggered skill acquisition, or durable successful-use learning. The Portal engineering receipt proves a static pack: `software-engineering`, `worktree-safety`, `test-debugging`. RLS/authorization/approval concepts are represented in code/tests and task prompts, not proven as native Hermes skills integrated in autonomous goal loops.

Hermes has native `skills_tool`, `skill_manager_tool`, `skills_hub`, `skill_usage`, and `skills_sync` modules, plus README claims of skill creation/improvement. R11 found no real Nexus-goal receipt showing native skill discovery → loading → model use → result-influenced action. Therefore `SKILLS_INTEGRATED_ENGINEERING_LOOP=PARTIAL`, all other major Nexus loops are `NO` or `PARTIAL`, and failure-triggered skill change is `NO` on direct evidence.

## Exact selection call chains

### Nexus

`company_goal_portfolio.json` → Active Operator `discover_attention()` → `select_portfolio_goal()` in `goal_completion.py` → `next_work_for_active_goal()` → `resolve_criterion_capability()` → action ID → `execute_safe_internal_action()` → action-specific executor → receipt/evaluator → `record_goal_progress()`/closure continuation. Goal, criterion, capability family, and worker/action are primarily rule-led. The model may plan within `ai.plan_and_verify`, but it does not own the parent selector or dynamic tool registry.

### Hermes/Nova

Nova’s conversation path uses intent classification/context and `nova_telegram_worker.py`; capability metadata is brokered and receipts expose `model_selected_capability`. Hermes native `model_tools.py` resolves enabled/disabled toolsets and emits schemas; the model can then emit tool calls, which are validated/dispatched by the runtime. This is a hybrid model-led invocation inside rule/profile-led allowlists, not a shared Nexus selector.

### Skills and workers

Nexus skill selection is static/caller-led: a worker action loads a known skill pack; no general criterion→skill scorer was found. Worker selection is hardcoded by action family (`nexus_ai_workforce` for Portal, Modal provider for Modal, Research adapter for Research). Tool selection is criterion/rule-led; no current evidence shows multiple qualified candidates being scored for task fit, health, cost, history, or worker access. Hermes worker/session selection is profile/provider-driven and separate.

## Multi-candidate behavior and failure learning

The system does not generally discover and score multiple candidates. `resolve_criterion_capability()` returns one binding plus fallback labels; `execute_safe_internal_action()` dispatches one action ID. The engineering broker can enumerate workers, but the observed matrix marks OpenCode installed/probe-unfinished and uncertified, so it does not become a selectable candidate. Nova has bounded same-tool loop recovery and suppression tests, but this is turn-local recovery, not a general Nexus goal capability learner.

Selection currently considers task/criterion fit and authority in the deterministic paths; health/readiness is used for some preflights; cost is encoded for Modal/governance. It does not consistently use worker access, past success, failure memory, privacy, latency, or resource availability across all capabilities. Failure can change action in closure-specific code for known criteria, but failure cannot generally trigger a new skill selection or a dynamic alternate worker.

## Safe fit scenarios

| Scenario | Current selected path | Evidence-based fit | Limitation |
|---|---|---|---|
| React Portal feature | `engineering.portal_beta` → `nexus_ai_workforce` | real Portal receipt, tests/build | one hardcoded engineering route; OpenCode not candidate |
| Competitor pricing | `research.refresh` / Alpha | real Research path | no general candidate scoring; downstream impact previously absent |
| Visual UI verification | Portal safety/Playwright or Oracle labels | historical/test surfaces | current worker-callability not live-proven |
| Bounded CPU ingestion | `modal.bounded_job` | real Modal completion proof | explicit Modal binding, not dynamic remote comparison |
| Canonical state read | Nexus MCP read tools / operational reads | configured read-only path | no live MCP call claimed in R11 |
| Supabase RLS | explicit Portal certification script | R10A real 52/52 certification | synthetic identity setup is separate governed path |
| Debug Node build | `frontend.build`/engineering path | manifest and historical engineering receipts | no dynamic worker/tool choice |
| Missing API knowledge | Research adapter | real Research infrastructure | research is not automatically bound back into engineering |

## Underused and not-routable capabilities

Underused ready or historically tested capabilities include OpenCode (installed, version-probed, historical execution probe, zero current Nexus-goal use), Oracle browser, native Hermes browser/terminal/file tools, native Hermes skills, Nexus MCP read tools, Google read MCP, Alpha challenge, and the general frontend/tests capability manifest. The exact reasons are: no Nexus action ID/dispatch adapter, legacy hardcoding, no worker-specific readiness proof, profile/model visibility not established, or separate registry ownership.

Native Hermes capabilities potentially hidden/duplicated by Nexus are terminal, file editing, browser, MCP, skills, subagents, code execution, memory, and cron. They are not proven blocked by a specific Nexus wrapper in every case; the precise finding is parallel duplication and missing integration. Nexus separately duplicates capability registry, MCP read surfaces, scheduler/continuation, skill loading, work receipts, and safety policy.

## Agentic loop benchmark and maturity

The durable state, task/goal receipts, real tool execution, evaluation, criterion verification, human pause/resume, scheduler, and cross-session continuation primitives are implemented and have real evidence in selected paths. Dynamic discovery, dynamic skill loading into Nexus goals, multiple-candidate selection, general failure learning, and native Hermes/Nexus shared routing are partial or not runtime-wired. R8-style stagnation remains possible because a successful AI/receipt path can still return an unsupported generic artifact or closure failure without a general alternate capability/skill route.

Maturity: Active Operator `L3`, Engineering `L3`, Research `L3`, Closure `L3`, Portfolio `L3`, Hermes `L1` for Nexus-goal integration, Whole company `L3`. No L4/L5 is awarded without multi-goal unattended outcome evidence.

## Duplication / architecture verdict

The architecture is `PARTIAL_MULTI_LOOP_ARCHITECTURE` with `PARTIAL_FRAGMENTED_ROUTING`. Hermes is a capable native agent harness; Nexus is a durable governed portfolio/execution layer; Nova is a communication/advisory broker. They are complementary at the boundaries, but there are parallel registries and routers rather than one coherent capability plane. The current design is stronger on safety and durable evidence than on adaptive tool/skill learning.

## Recommended R12 repair plan — not implemented

1. Define one normalized capability contract and adapter registry, preserving deny-by-default authority.
2. Add worker-specific readiness receipts and make selectors compare qualified candidates using fit, access, authority, health, cost, latency, success/failure memory, and privacy.
3. Add a criterion→skill resolver that loads Nexus or native Hermes skills only after worker/tool readiness, persists provenance, and lets bounded failure analysis request a materially different skill/tool path.
4. Add explicit OpenCode adapter/action only after its unattended environment, authority, repo scope, and test execution are independently certified; do not make it default.
5. Feed Research/Alpha evidence back into the parent task ledger and require downstream criterion impact.
6. Make Hermes native MCP/skills/subagents opt-in through the same Nexus capability broker instead of parallel hidden surfaces.
7. Add a cross-loop stagnation guard that suppresses receipt-only progress and requires criterion state/evidence deltas.
8. Re-run a focused real Portal and a second non-Portal canary, then conduct a new multi-goal unattended outcome validation only after those repairs.

## Required contract

`NEXUS_HERMES_TOOL_SKILL_LOOP_AUDIT_R11=COMPLETE`

`TOTAL_CAPABILITIES_DISCOVERED=176` (normalized audit records, including registry, manifest, Hermes modules, skills, MCP, workers, plugins, and scheduler families; not a claim of unique callable tools)

`TOTAL_INSTALLED=27`, `TOTAL_CONFIGURED=18`, `TOTAL_AUTHORIZED=12`, `TOTAL_REAL_TESTED=16`

`TOTAL_HERMES_CALLABLE=0`, `TOTAL_NOVA_CALLABLE=8`, `TOTAL_NEXUS_CALLABLE=18`, `TOTAL_ENGINEERING_CALLABLE=7`, `TOTAL_RESEARCH_CALLABLE=5`

`TOTAL_ROUTABLE=18`, `TOTAL_USED_IN_REAL_AUTONOMOUS_GOALS=8`

`OPENCODE_INSTALLED=YES`, `OPENCODE_REAL_TESTED=YES`, `OPENCODE_UNATTENDED_CALLABLE=NO`, `OPENCODE_HERMES_CALLABLE=NO`, `OPENCODE_NEXUS_CALLABLE=NO`, `OPENCODE_ENGINEERING_CALLABLE=NO`, `OPENCODE_ROUTABLE=NO`, `OPENCODE_USED_IN_REAL_NEXUS_GOAL=NO`

`HERMES_VERSION=0.20.0 local source; Oracle expected 0.20.6, actual not re-probed`

`HERMES_NATIVE_FEATURES_DISCOVERED=18`, `HERMES_NATIVE_TOOLS_DISCOVERED=105`, `HERMES_NATIVE_TOOLS_ENABLED=not determinable`, `HERMES_NATIVE_TOOLS_REAL_TESTED=0 in R11`, `HERMES_NATIVE_TOOLS_VISIBLE_TO_NOVA=not determinable`, `HERMES_NATIVE_TOOLS_VISIBLE_TO_NEXUS=0 proven`

`HERMES_TERMINAL=UNAVAILABLE`, `HERMES_FILE_EDIT=UNAVAILABLE`, `HERMES_BROWSER=UNAVAILABLE`, `HERMES_MCP=UNAVAILABLE`, `HERMES_SKILLS=PARTIAL`, `HERMES_SUBAGENTS=UNAVAILABLE`, `HERMES_EXECUTE_CODE=UNAVAILABLE`, `HERMES_CRON=PARTIAL`, `HERMES_MEMORY_LEARNING=PARTIAL`, `HERMES_PLUGINS=PARTIAL`

`NEXUS_SKILLS_DISCOVERED=17`, `NEXUS_SKILLS_REAL_USED=3`

`SKILLS_INTEGRATED_ACTIVE_OPERATOR=NO`, `SKILLS_INTEGRATED_ENGINEERING_LOOP=PARTIAL`, `SKILLS_INTEGRATED_RESEARCH_LOOP=NO`, `SKILLS_INTEGRATED_CLOSURE_LOOP=PARTIAL`, `SKILLS_INTEGRATED_PORTFOLIO_LOOP=NO`, `SKILLS_INTEGRATED_HERMES_LOOP=NO`

`FAILED_ATTEMPT_CAN_TRIGGER_SKILL_CHANGE=NO`, `FAILED_ATTEMPT_CAN_TRIGGER_TOOL_CHANGE=YES`, `FAILED_ATTEMPT_CAN_TRIGGER_WORKER_CHANGE=NO`

`HERMES_TOOL_SELECTION_MECHANISM=HYBRID`, `NEXUS_TOOL_SELECTION_MECHANISM=RULE_LED`, `NEXUS_SKILL_SELECTION_MECHANISM=STATIC`, `HERMES_SKILL_SELECTION_MECHANISM=HYBRID`

`HERMES_AND_NEXUS_SHARE_ONE_CAPABILITY_ROUTER=NO`

`TOOL_SELECTION_CONSIDERS_MULTIPLE_CANDIDATES=NO`, `TOOL_SELECTION_USES_TASK_FIT=YES`, `TOOL_SELECTION_USES_HEALTH=PARTIAL`, `TOOL_SELECTION_USES_WORKER_ACCESS=PARTIAL`, `TOOL_SELECTION_USES_AUTHORITY=YES`, `TOOL_SELECTION_USES_COST=PARTIAL`, `TOOL_SELECTION_USES_PAST_SUCCESS=NO`, `TOOL_SELECTION_USES_FAILURE_MEMORY=PARTIAL`

`SKILL_SELECTION_USES_TASK_REQUIREMENTS=NO`, `SKILL_SELECTION_USES_FAILURE_MEMORY=NO`

`UNDERUSED_READY_CAPABILITIES=OpenCode, Oracle browser, Hermes native terminal/file/browser, Nexus MCP read tools, Google read MCP, Alpha challenge, frontend/tests manifest`

`NOT_ROUTABLE_READY_CAPABILITIES=OpenCode, native Hermes coding/terminal, native Hermes skills, Oracle browser from Nexus goal selector, Google MCP from Active Operator, generic alternative engineering workers`

`NATIVE_HERMES_CAPABILITIES_BLOCKED_BY_NEXUS=not proven as direct blocks; missing integration is proven`

`NATIVE_HERMES_CAPABILITIES_DUPLICATED_BY_NEXUS=terminal/file execution, MCP read boundary, skills, scheduler/continuation, memory/context, safety/receipts`

`MISSING_ROUTER_INTEGRATIONS=normalized adapter registry, OpenCode action, Hermes native skill bridge, Hermes MCP bridge into Active Operator, multi-candidate worker scorer, failure-to-skill acquisition`

`ACTIVE_OPERATOR_LOOP_LEVEL=L3`, `ENGINEERING_LOOP_LEVEL=L3`, `RESEARCH_LOOP_LEVEL=L3`, `CLOSURE_LOOP_LEVEL=L3`, `PORTFOLIO_LOOP_LEVEL=L3`, `HERMES_LOOP_LEVEL=L1`, `WHOLE_COMPANY_LOOP_LEVEL=L3`

`R8_STYLE_STAGNATION_STILL_POSSIBLE=YES`

`TOOL_CONTROL_PLANE_VERDICT=PARTIAL_FRAGMENTED_ROUTING`, `SKILL_CONTROL_PLANE_VERDICT=PARTIAL_INTEGRATION`, `LOOP_ARCHITECTURE_VERDICT=PARTIAL_MULTI_LOOP_ARCHITECTURE`, `TRUE_RAY_BLOCKERS=NONE`

## Conclusion

Today Hermes can expose a large native tool/harness surface in its own runtime, and Nexus can safely execute a smaller set of real governed capabilities. Skills are mostly static Nexus instructions or native Hermes machinery that is not proven in Nexus production loops. OpenCode is usable interactively at the executable level but not unattended-routable. Tool selection is mostly rule-led in Nexus and hybrid/profile/model-led in Hermes; they do not share one router or routinely compare multiple candidates. R12 should unify capability contracts and worker-specific readiness before exposing more tools. R11 intentionally did not implement those repairs.
