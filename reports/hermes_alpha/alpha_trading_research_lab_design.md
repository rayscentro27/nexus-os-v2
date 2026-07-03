# Alpha Trading Research Lab Design

## Workflow

Strategy intake → deterministic specification → data/assumption review → backtest plan → offline backtest import → robustness/risk review → improve/reject/continue recommendation → optional future paper/demo proposal → Ray Review.

Required specification: strategy ID/version, hypothesis, instruments, timeframe/session, data source/window, entry/exit, stop/defined exit, sizing, spread/slippage/commission, exclusions, parameter ranges, baseline, in/out-of-sample split, and invalidation criteria.

Metrics: win rate, profit factor, maximum drawdown, risk/reward, sample size, expectancy, return distribution, exposure, consecutive losses, turnover, stability across windows/instruments/parameters, and comparison to baseline. Never advertise a backtest as expected live performance.

Risk review: leverage, gap/liquidity, concentration, correlation, parameter overfit, look-ahead/survivorship/data snooping, execution assumptions, regime dependency, operational failure, and maximum tolerated loss.

Trade receipt future format: receipt ID, strategy/version, practice environment, instrument, units, timestamps, reason, risk rule, stop/exit, requested/filled price, spread/slippage, transaction IDs, P/L, limits before/after, approval, and kill-switch state.

Ranking prioritizes robustness and downside control over raw return. Live/funded trading is blocked. This phase has no broker connection and places zero demo/live trades.
