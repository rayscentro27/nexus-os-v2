# Strategy Tournament Build Report

**Generated:** 2026-07-05  
**Status:** Framework Initialized — Demo Only

---

## Findings

### Tournament Model
- Round-robin format: each strategy competes against all others
- Entry fee: configurable per tournament (default: $0 for demo)
- Winner determination: highest risk-adjusted return (Sharpe ratio)
- Maximum participants: configurable (default: 10)

### Strategy Hypothesis
- Each entry requires a written hypothesis before competition
- Hypothesis includes: thesis, timeframe, risk parameters, expected edge
- Hypothesis stored for post-tournament analysis

### Rules
- All strategies must be documented before tournament begins
- No mid-tournament strategy changes
- All trades simulated (no real money)
- Position sizing: fixed percentage of simulated portfolio
- Stop-loss: mandatory, configurable per strategy

### Risk Management
- Maximum drawdown limit: -20% (auto-elimination)
- Position size limit: 5% per trade
- Correlation check: strategies with >0.8 correlation capped
- Leverage limit: 2x (demo mode)

### Backtest
- Historical data: configurable date range
- Slippage model: 0.1% per trade
- Commission model: $0.01 per share / 0.1% per trade (configurable)
- Performance metrics: Sharpe, Sortino, max drawdown, win rate, profit factor

### Comparison
- Side-by-side strategy comparison dashboard
- Metrics table: return, risk, Sharpe, drawdown, win rate
- Equity curve overlay chart
- Trade log with entry/exit details

### Demo-Only Boundary
- **No real money is used or accepted**
- All trading is simulated on historical or paper data
- No brokerage integration in demo mode
- Results are for educational/analytical purposes only
- Clear "DEMO MODE" watermark on all tournament outputs

## Next Actions

1. Build tournament entry CLI: `nexus tournament enter`
2. Create strategy hypothesis input form
3. Implement backtest engine with configurable parameters
4. Build comparison dashboard
5. Add "DEMO MODE" watermark to all outputs
6. Create tournament receipt template
