# Phase 15C final certification

## Result: PARTIAL

The live client-count blocker is cleared through the existing project runtime
environment. Using `~/.config/nexus/runtime.env` through the existing loader,
the canonical governed Supabase read returned:

- 14 production profiles
- 14 active profiles
- 0 onboarding profiles
- 24 demo/certification profiles excluded
- 38 total rows observed

No credential values were printed or copied into the repository.

Temporal is also resolved: `temporalio` is declared in
`requirements-agent-platform.txt`, installed in `.venv-agent-platform`, and
the existing Temporal worker is running. No package installation was performed.

Automated operator certification remains Hermes **25/25** and Nova **25/25**;
focused Phase 15C tests pass (**12 passed**). Session.table, source precedence,
taxonomy, governance, payment, journey, AI cost, workforce, and grounded
recommendation checks remain passing.

## Live Nova regression and repair

Ray's Telegram transcript exposed a real routing defect: Nova's schema query
planner ran before the canonical awareness gate. It therefore returned legacy
process/action objects and the August 12 study snapshot for current status,
clients, opportunities, research, Alpha, loop history, worker taxonomy, and
the highest-value action. The live worker was confirmed to use this checkout;
the issue was routing precedence, not a stale deployment.

The repair places the narrow canonical-awareness gate after write and approval
guards but before planner execution. Internal rechecks for the nine affected
question families now select the shared canonical capabilities and current
source paths. A new live Telegram response is still required before marking
the live path PASS.

## Remaining environmental blockers

The full suite was run with the project interpreter and had zero collection
errors. It reached 8 passes, then stalled in
`test_builder_abstraction::test_unavailable_worker_is_skipped` during external
CLI worker health probing. It was stopped after 36.21 seconds: 8 passed, 0
failed, 0 skipped, 0 collection errors. This is classified ENVIRONMENTAL, not a
Phase 15C regression.

`npm run typecheck` was bounded with Node `v22.22.3` / npm `10.9.8`; `tsc`
entered an uninterruptible state without diagnostics. `npm run build` was
bounded at its Tailwind pre-step; `tailwindcss` entered the same state, so Vite
was not reached. No stale diagnostic process remains.

Actual inbound Telegram certification remains `MANUAL_REQUIRED`. Hermes and
Nova worker-path self-checks passed. No fake inbound update and no outbound
test message was sent. The exact 16-question Hermes and 18-question Nova
checklists are stored in this report's JSON companion for Ray to execute.

Protected state is unchanged: client portal, production Telegram behavior,
Nova authority, and tool-install state.

Exact resume point: **PHASE 15C — SHARED NEXUS AWARENESS COMPLETION CONTINUED**.
