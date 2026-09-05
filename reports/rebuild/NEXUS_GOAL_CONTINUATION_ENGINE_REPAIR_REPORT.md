# Nexus Goal Continuation Engine Repair

## Root cause repaired

The Active Operator selected durable goals but collapsed non-Research work into
`generate_internal_report`. It also allowed two continuously open P1 goals to
starve the rest of the portfolio. A report was recorded as child progress,
but no department-specific next action was selected.

## Repair

The existing architecture was extended in place:

- `goal_completion.select_portfolio_goal` now promotes one genuinely starved
  eligible peer, then returns to the normal priority lane on the next cycle.
- `next_work_for_active_goal` maps existing capable lanes to bounded actions:
  Research → `research.refresh`; Trading → `trading.research_cycle`; Portal /
  Systems → `internal.capability_verify`; unsupported departments receive a
  queued work-order boundary rather than a false execution claim.
- Active Operator now recognizes `department.work_order` as an internal
  dispatch state, not an approval request and not a successful execution.
- The existing paper-only Trading loop is callable through the canonical
  operator and retains live-order denial.
- Portal local verification reuses the existing client-portal backend builder;
  it does not deploy or mutate customer-facing production.
- Goal receipts now preserve a bounded result summary and next step without
  marking the parent complete.

No new scheduler, queue, objective store, model, Telegram worker, or autonomy
architecture was created.

## Real bounded proof

Observed canonical operator cycles after the repair:

1. `operator_10965e31e5b2459989859a785200876f` selected
   `business_plans.customer_goals` and created work order
   `awo_fd01d46f74516e1b8f3e` with
   `WAITING_CAPABLE_DEPARTMENT_EXECUTOR`. This proves honest dispatch without
   claiming execution.
2. The next Research cycle selected `research.company_intelligence`, ran the
   existing private SearXNG adapter in REAL mode, returned 18 public source
   results, and advanced the goal with a real receipt.
3. The existing Trading paper loop then ran against real OANDA Practice data.
   It recorded 500 EUR/USD H1 candles, deterministic IS/validation/OOS
   results, cost stress, an Alpha-style critique, and a
   `RESEARCH_AND_RETEST` follow-up. The candidate was rejected honestly because
   OOS trade count was 2 and robustness/cost evidence was insufficient. No
   order was placed.
4. A later canonical cycle selected `research.company_intelligence` again and
   continued without manually feeding a child question.

The first operator attempt to invoke Trading exposed a runtime import-path
failure; adding the repository root to the existing runner path removed that
internal packaging defect. The direct canonical loop then completed as
described above.

## Tests

Focused compile and contract checks passed:

- Python compilation of the modified goal and operator modules;
- starvation selection assertion;
- Trading and Portal action mapping assertions;
- existing goal-completion tests remain structurally compatible.

The full repository test command was not used as a certification shortcut
because this worktree contains a large unrelated change set and the broad
test collector is not bounded in this environment.

## Remaining limitation

Several roadmap departments still have no registered safe autonomous
implementation executor in the canonical Active Operator. They now remain
visible as queued work with an explicit capability boundary instead of being
silently represented by a report. Portal local verification is available, but
the observed cycles had not yet selected it before this report was written.

This is not a reason to stop Research, Trading, or other eligible work. It is a
remaining engineering capability gap, not a Ray-only blocker.

## Safety state

`TRADING_LIVE_EXECUTION_ENABLED=false`

`AUTO_TRADING=false`

`TRADING_PAPER_ONLY=true`

No external consequential action was performed.
