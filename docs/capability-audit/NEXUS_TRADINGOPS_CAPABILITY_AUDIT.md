# Nexus TradingOps Capability Audit

## Current Nexus position

Nexus has Oanda practice/demo adapters, read-only account/pricing checks,
trading briefs, Alpha research hooks, approval cards, and paper-only safety
contracts. That is **ADEQUATE for safe Forex practice** and **PARTIAL for a
reusable Trading Research OS**. There is no authorization for funded trading.

## Framework comparison

| Framework | Forex | Options | Crypto | Equities/ETF | Futures | Decision |
|---|---|---|---|---|---|---|
| VectorBT | GOOD research | POOR without custom data/model | GOOD research | GOOD research | GOOD research | ADAPT for vectorized research |
| NautilusTrader | GOOD | GOOD/strongest open candidate | GOOD | GOOD | GOOD | PILOT research/paper only |
| LEAN | GOOD | GOOD broad modeling | GOOD | GOOD | GOOD | WATCH; data/cloud coupling review |
| Freqtrade | POOR/indirect | NONE | GOOD crypto bot | NONE | LIMITED | REJECT for Nexus core |
| Backtrader | ADEQUATE | POOR | ADEQUATE | ADEQUATE | ADEQUATE | REFERENCE_ONLY |
| Options Portfolio Backtester | NONE/indirect | PILOT candidate | NONE | GOOD | NONE | PILOT research-only after provenance review |

NautilusTrader documents multi-asset support, deterministic event-driven
research/live architecture, option chains/Greeks, and option spreads through
its adapters. Its LGPL-3.0 license and ability to live trade mean it must be
isolated behind a paper/research adapter. LEAN is broad and mature but would
need a clear data/licensing and deployment decision. Freqtrade is explicitly a
crypto bot with dry/live modes, which is the wrong default authority model.

## Research architecture

`market-data adapter → immutable normalized dataset → strategy spec → backtest → robustness → walk-forward → Monte Carlo → risk report → paper/demo → Ray review`.

Market data is a source, not a strategy authority. Every result gets dataset
version, timestamp, corporate-action assumptions, fee/slippage model, and
reproducibility hash.

## Compute placement

Small exploratory vectorized research can run locally. Multi-asset backtests,
large parameter sweeps, and Monte Carlo belong on isolated remote CPU workers.
GPU is not justified by default; use it only for a measured ML workload.

## Safety

No live broker credentials, funded trading, or autonomous order submission are
part of this audit. Paper/demo execution remains the maximum permitted stage.
