# R12 resumable checkpoint

`NEXUS_HERMES_UNIFIED_CAPABILITY_CONTROL_R12=RUN_LIMIT_CHECKPOINT`

## Completed components

- Added `scripts/nexus_agent_platform/unified_capability_control.py` as a deny-by-default adapter/selector over the existing Nexus manifest, CLI registry, Nexus skills, worker facts, and configured MCP facts.
- Added typed task requirement resolution for engineering, research, browser, remote execution, security/data, and internal-read classes.
- Added deterministic multi-candidate discovery, filtering fields, scoring, selection receipts, skill-selection receipts, and failure material-delta memory.
- Wired `nexus_active_operator_runner.py` to produce a selection receipt during the normal goal-derived Active Operator path.
- Added focused selector tests.

## Tests passed

`12 passed` for the focused Nexus skill/loop, engineering broker, and unified selector tests.

Scenario probes selected and scored multiple candidates for Engineering (internal worker/OpenCode), Research (Research/Oracle), Browser (Playwright/Oracle), and Compute (Modal/Oracle). The canonical Active Operator produced `reports/runtime/nexus_capability_selection/selection_continuous_kernel:clyde.entity_readiness.json`.

## OpenCode state

OpenCode `1.18.25` was invoked through the existing bounded isolated-worktree adapter. The invocation was real and bounded but timed out without a code change: `failure_class=TIMEOUT`, `files_changed=[]`, `independent_verification=false`. It must remain a candidate with a failure penalty, not be declared successful.

## Remaining exact gates

1. Reconcile the OpenCode timeout through the existing provider/configuration path and rerun the same isolated certification until either a real edit/test receipt exists or a precise provider limitation is recorded.
2. Add/validate the Hermes native adapter against the actual Oracle runtime; local source declares Hermes `0.20.0`, while `0.20.6` is only historical remote memory and the bounded CLI probe timed out.
3. Wire the normalized selector into Research/Alpha handoff and prove a real Research receipt changes a downstream parent task strategy/action; no such proof is claimed yet.
4. Add selector negative-path tests and a real bounded non-Engineering canary after the above adapters are proven.
5. Generate the final R12 report and machine-readable selection/failure inventories only after those gates have direct evidence.

## Safety/state

Portal remains `READY_FOR_HUMAN_REVIEW`; no production deployment, customer mutation, spend, publication, live trading, or secret exposure occurred. Unrelated worktree changes were preserved.

`SAFE_TO_RESUME=YES`
