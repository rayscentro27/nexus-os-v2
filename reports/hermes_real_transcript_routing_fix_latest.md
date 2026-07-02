# Hermes Real Transcript Routing Fix

The supplied transcript exposed three priority defects rather than isolated answer defects: source questions ran after ordinal memory, trace questions could replace the trace they intended to inspect, and natural domain wording fell into the internal diagnostic fallback. The final architecture now governs these routes through a strict RouteDecision and deny-by-default context packet.

The router now applies safety first, then a dedicated source/trace classifier and handler, followed by casual/status/domain classification, memory eligibility, retrieval, reasoning, and approval handling. Trace questions do not update the selected item or current topic and always target the last non-trace answer unless the user explicitly asks about the current question.

Trading now has list, recommendation, last-test, status, and execution sub-intents. The strategy list comes from the rendered Trading Lab context. A specific recommendation is withheld because `trading_lab_proof_latest` has no recent backtest timestamp or latest strategy report. No profitability or running-strategy claim is inferred from static labels.

Revenue questions use a dedicated 30-day reasoner with conservative, realistic, and stretch assumptions. The monthly price is explicitly identified as an assumption. Supabase is attempted for opportunity context, but live access is claimed only after a successful authenticated query.

The exact transcript and generalized source, database, AI, trading-list, and revenue variants are covered. All 488 tests pass. The RouteDecision policy suite and 11-message Workroom policy flow also pass, including context isolation, diagnostic suppression, and zero model calls on forbidden routes.

Remaining blockers are authenticated live opportunity-row verification, production deployment verification, and fresh comparable paper backtest evidence before Hermes can select a specific trading strategy.
