# Nexus / Hermes R15.6 live execution certification

## Result

`NEXUS_HERMES_LIVE_EXECUTION_CERTIFICATION_R15_6=RUN_LIMIT_CHECKPOINT`

The healthy Oracle Hermes 0.20.6 workstation was preserved. Test profiles were
given the profile-local `terminal` toolset so the dispatcher could expose the
already-installed workstation CLIs to real workers.

## Proven in this run

- `jq`, `gh`, `supabase`, and `netlify` were executed by real Hermes Kanban
  workers and completed. `fd` was invoked by a real worker; its first search
  expression returned no path, so it is recorded as partial rather than a
  clean verification.
- The corrected native prerequisite graph completed automatically:
  research `t_62994938` → engineering `t_052a07eb` → reviewer `t_8a3414bd`.
- A worker-side `kanban_task_completed` hook emitted three independent,
  machine-readable skill receipts with resolved skill paths and hashes.
- Hermes worker identity was recovered from the durable `claimed` event after
  completion cleared `claim_lock`.

## Exact failures / boundaries

- OpenCode was not actually called. The worker performed the scratch edit
  itself; `HERMES_CAN_CALL_OPENCODE=FAIL` with failure class `TOOL_NOT_SELECTED`.
- Playwright was present in the image, but the worker entered a Python API /
  browser-install fallback and was bounded before a browser result. No browser
  capability is advertised as proven.
- The normal Nexus broker currently has no Hermes Kanban executor for an
  existing business criterion. No real-goal progress is claimed and no
  business child action was manually forced.
- The first research-chain attempt exceeded its 120-second task budget because
  the `grounded-citations` skill expanded into web retrieval; it was stopped
  and replaced with a bounded read-only research node, a material strategy
  change.

## Safety

No production deployment, customer mutation, outreach, spending, live trading,
secret exposure, or Portal goal reopening occurred. The live Hermes container
and workstation image were not rebuilt or replaced.

## Required continuation

1. Add the governed normal-broker Hermes Kanban executor.
2. Run explicit OpenCode-through-worker edit/test proof.
3. Run the Playwright Node/CLI test with the existing Chromium cache.
4. Run restart persistence after a completed research node.
5. Route one existing unresolved Nexus criterion through the broker-selected
   Hermes stack and verify a canonical criterion delta.
