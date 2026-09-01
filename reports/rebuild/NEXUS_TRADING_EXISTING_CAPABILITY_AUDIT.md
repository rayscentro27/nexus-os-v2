# Existing Trading Capability Audit

Existing capability includes OANDA Practice configuration/client, scanner,
pricing/account checks, strategy smoke tests, backtest import/dry-run, paper
bridge, risk limits, trade receipts, and Alpha research integration under
`scripts/trading/`. These are `REUSE`/`ADAPT`. The live endpoint remains blocked:
`LIVE_TRADING=false`, `AUTO_TRADING=false`, `PAPER_ONLY=true`.

