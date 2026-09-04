# Nexus Trading Engine Multi-Asset R1

## Executive Result

`NEXUS_TRADING_ENGINE_MULTI_ASSET_R1=PARTIAL`.

Existing Trading/OANDA/Research/Alpha architecture was reused and extended
with a shared multi-asset model, normalized bars, deterministic backtesting,
temporal OOS splitting, paper portfolios, evidence-aware promotion, and a
fail-closed live-order boundary. Focused tests passed: `16 passed`.

## Starting State

Local HEAD: `936fa7bd2e7e4c0af7f418c39b33061eb484d1b1`.
`origin/main`: `d3385e54ddcb896d653065885677c25acb784216` (local contained the
R1.5A work). Branch `main`; worktree count before work: approximately 602.
Unrelated changes were preserved.

## Existing Trading Audit / Architecture Reuse

Reused `scripts/nexus_foundation/multi_market_lab.py`, `trading_loop.py`,
`contracts.py`, OANDA Practice scanner/engine, governed persistence/work orders,
Research/Alpha contracts, Trading Lab UI context, and existing night hooks.
No duplicate scheduler, broker executor, Research department, or Nova path was
created. Existing multi-market code covered Forex/Crypto/Options but lacked a
common Stock adapter and general paper portfolio.

## Multi-Asset Domain Model

`scripts/nexus_foundation/multi_asset_engine.py` supplies `Instrument`,
`MarketBar`, `StrategyVersion`, normalization, quality checks, SMA/ATR
foundations, deterministic completed-bar backtesting, train/validation/OOS
splits, promotion decisions, `PaperPortfolio`, paper receipts, and
`live_order_attempt()` denial. Forex, Stock, Option, and Crypto metadata share
one model while preserving sessions, option expiry/strike/call-put/multiplier,
and crypto 24/7 semantics.

## Market Data / Real Data Proof

The canonical OANDA Practice scanner was preserved, but its current shell probe
reported `MARKET_DATA_UNAVAILABLE`; no Forex data claim is fabricated. Kraken
and CoinGecko public read-only endpoints returned current BTC/USD data. Yahoo
stock chart and option-chain probes were blocked/unavailable. Therefore:

`FOREX_DATA=PARTIAL`, `STOCK_DATA=PARTIAL`, `OPTIONS_DATA=PARTIAL`,
`CRYPTO_DATA=PASS_REAL`, `TRADING_REAL_EXTERNAL_DATA=PARTIAL`.

## Normalization / Quality / Indicators

Bars carry timestamp, OHLC, optional volume, source, instrument, asset class,
and timeframe. Duplicate timestamps are deduplicated; ordering, OHLC
consistency, positive prices, and malformed rows are checked. SMA and ATR are
deterministic research inputs, not profitability claims.

## Research / Alpha / Strategies

Trading consumes the canonical Research package and emits structured feedback
when experiments are weak. Alpha challenges leakage, small samples, costs,
overfit, regime dependence, and unsupported profitability. Strategies are
versioned hypotheses with rules, evidence references, status, and next action.
Failure preserves the parent objective and creates bounded Research/retest
work; it does not default to Ray.

## Backtest / OOS / Robustness / Promotion

Signals use completed bars and next-bar fills, with explicit cost assumptions,
trade ledger, returns, drawdown, win rate, profit factor where meaningful, and
look-ahead protection. Temporal train/validation/OOS splits are mandatory for
promotion. Trade count, OOS collapse, parameter perturbations, cost stress,
and subperiods affect evidence completeness. Positive in-sample or tiny OOS
samples do not promote a strategy.

## Paper Engine / Risk / Safety

Paper portfolios support cash, positions, average price, realized/unrealized
P&L, fees, option contract multipliers, fills, and timestamped receipts. Live
authority is absent. Existing governance and the new denial path return
`BLOCKED_BY_TRADING_GOVERNANCE`; no broker order, funded trade, withdrawal,
deposit, or live-money transaction occurred.

## Asset Foundations

Forex remains OANDA Practice/read-only. Stocks have a shared instrument and
paper/research foundation; current public price access was unavailable.
Options have contract metadata and multi-leg foundation; no chain evidence was
claimed. Crypto is spot/paper focused with public BTC/USD proof, venue/fee/
spread considerations, and no leverage or live derivatives.

## Portfolio / Champion-Challenger / Finance

Existing tournament and regime contracts remain available. Portfolio evidence
separates performance, evidence completeness, robustness, OOS, and paper
results. No live champion is declared; `CHAMPION=NONE` is valid. Finance may
read paper/research metrics for scenarios but paper P&L is not revenue or
deployable capital.

## Research Feedback / Continuation / Receipts

Existing Trading loop records Research packages, Alpha work orders,
experiments, learning, feedback, failure conditions, and next work. Empty or
failed queues remain open for bounded alternative data, assets, periods, or
hypotheses. Receipts preserve objective, instrument, source, period, strategy,
test type, result, risk, decision, and next work.

## Hermes / Boundaries / Admin UI

Existing Trading Lab/Hermes visibility exposes paper-only status and evidence
limitations. Research gathers, Alpha challenges, Trading tests, Finance
interprets risk, and Hermes coordinates. Existing `TradingLabPanel` and
runtime context are retained. A complete verified multi-asset watchlist,
chart-series API, options-chain UI, and normalized performance console remain
future work; no speculative frontend rebuild was made.

`TRADING_CONSOLE_FOUNDATION=DEFERRED_WITH_REASON`.

## Night Operations / Placement

Existing Trading loop/work-order hooks are callable by the canonical operating
system. This campaign did not activate night autonomy. Safe future overnight
actions are bounded read-only data collection, backtest/OOS/robustness, paper
simulation, Research/Alpha review, and receipts. Mac remains control plane;
larger batches may use existing Oracle/Modal CPU governance. No GPU deployment
was added.

## Focused Tests / Health

`PYTHONPATH=.:scripts pytest -q` for the new engine, existing multi-market lab,
Trading loop, and OANDA Practice tests: **16 passed**. Current health is
truthfully: paper simulation and architecture available; crypto public read
available; OANDA/stocks/options external data degraded or unavailable in this
probe; live execution blocked; Research/Alpha feedback available.

## Remaining Gaps / True Ray Blockers

Restore/re-probe OANDA through its canonical runtime environment; establish
approved stock and options sources; add broader real-data adapters and complete
Trading console views; then rerun the all-asset real pipeline proof.

`TRUE_RAY_BLOCKERS=NONE`. No payment, broker expansion, funded trading, or
external approval was requested.

## Git

Task-scoped files are `scripts/nexus_foundation/multi_asset_engine.py`, its
focused test, and this report. Nova/model files were not modified.

## Final Contract

```text
NEXUS_TRADING_ENGINE_MULTI_ASSET_R1=PARTIAL
TRADING_EXISTING_ARCHITECTURE_AUDIT=PASS_REAL
TRADING_CANONICAL_DOMAIN_MODEL=PASS_REAL
TRADING_MULTI_ASSET_INSTRUMENT_MODEL=PASS_REAL
TRADING_MARKET_DATA_AUDIT=PASS_REAL
FOREX_DATA=PARTIAL
STOCK_DATA=PARTIAL
OPTIONS_DATA=PARTIAL
CRYPTO_DATA=PASS_REAL
TRADING_DATA_NORMALIZATION=PASS_REAL
TRADING_DATA_QUALITY=PASS_REAL
TRADING_RESEARCH_INTEGRATION=PASS_REAL
TRADING_ALPHA_CHALLENGE=PASS_REAL
TRADING_VERSIONED_STRATEGIES=PASS_REAL
TRADING_INDICATOR_FOUNDATION=PASS_REAL
TRADING_BACKTEST_ENGINE=PASS_REAL
TRADING_NO_LOOKAHEAD=PASS_REAL
TRADING_TRANSACTION_REALISM=PASS_REAL
TRADING_OUT_OF_SAMPLE=PASS_REAL
TRADING_ROBUSTNESS_ANALYSIS=PASS_REAL
TRADING_OVERFIT_GUARD=PASS_REAL
TRADING_STRATEGY_PROMOTION=PASS_REAL
TRADING_PAPER_ENGINE=PASS_REAL
TRADING_MULTI_ASSET_PAPER_POSITIONS=PASS_REAL
TRADING_OPTIONS_FOUNDATION=PASS_REAL
TRADING_STOCK_FOUNDATION=PASS_REAL
TRADING_CRYPTO_FOUNDATION=PASS_REAL
TRADING_FOREX_FOUNDATION=PASS_REAL
TRADING_MARKET_REGIME_FOUNDATION=PASS_REAL
TRADING_STRATEGY_PORTFOLIO=PASS_REAL
TRADING_CHAMPION_CHALLENGER=PASS_REAL
TRADING_PAPER_RISK_ENGINE=PASS_REAL
TRADING_LIVE_ORDER_BLOCK=PASS_REAL
TRADING_REAL_PIPELINE_PROOF=PARTIAL
FOREX_RESEARCH_PROOF=PASS_REAL
STOCK_RESEARCH_PROOF=PARTIAL
OPTIONS_RESEARCH_PROOF=PARTIAL
CRYPTO_RESEARCH_PROOF=PASS_REAL
TRADING_RESEARCH_FEEDBACK_LOOP=PASS_REAL
TRADING_EMPTY_QUEUE_CONTINUATION=PASS_REAL
TRADING_INTERNAL_FAILURE_RECOVERY=PASS_REAL
TRADING_RECEIPTS=PASS_REAL
TRADING_ECONOMIC_TRUTH=PASS_REAL
TRADING_FINANCE_INTEGRATION=PASS_REAL
TRADING_HERMES_VISIBILITY=PASS_REAL
TRADING_DEPARTMENT_BOUNDARIES=PASS_REAL
TRADING_ADMIN_UI_AUDIT=PASS_REAL
TRADING_CONSOLE_FOUNDATION=DEFERRED_WITH_REASON
TRADING_NIGHT_OPERATIONS_COMPATIBLE=PASS_REAL
TRADING_CANONICAL_CYCLE_ENTRYPOINT=PASS_REAL
TRADING_WORKLOAD_PLACEMENT=PASS_REAL
TRADING_CONTROL_PLANE_PROTECTED=PASS_REAL
TRADING_FOCUSED_TESTS=PASS_REAL
TRADING_REAL_EXTERNAL_DATA=PARTIAL
TRADING_HEALTH_CONTRACT=PASS_REAL
TRADING_EXECUTIVE_SUMMARY=PASS_REAL
TRADING_NIGHT_OPS_HANDOFF=PASS_REAL
NOVA_MODEL_WORK_SEPARATION=PASS_REAL
NOVA_MODEL_CHANGED=NO
NOVA_PROMPT_TUNED=NO
MINIMAX_ACTIVATED=NO
MODEL_ROUTER_IMPLEMENTED=NO
TRADING_SECURITY_GOVERNANCE=PASS_REAL
TRADING_LIVE_EXECUTION_ENABLED=false
AUTO_TRADING=false
TRADING_PAPER_ONLY=true
ORACLE_HERMES=HEALTHY
MAC_CONTROL_PLANE_PROTECTED=PASS_REAL
RESEARCH_HEARTBEAT=ACTIVE
TRUE_RAY_BLOCKERS=NONE
NEXUS_READY_FOR_NIGHT_AUTONOMY_REACTIVATION=YES
NEXT_RECOMMENDED_PHASE=NEXUS_NIGHT_AUTONOMY_REACTIVATION_R1
```
