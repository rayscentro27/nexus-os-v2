# WP8.4 Trading Baseline Audit

The WP8.3.5 component map was loaded. Nexus remains the canonical backtest,
state, authority, receipt, and recovery plane. OANDA environment was verified
as Practice; EUR/USD, GBP/USD, and USD/JPY are scanner instruments, with H1
used for this run. The OANDA Practice health/read path succeeded for EUR/USD;
GBP/USD data was unavailable in the separate bounded probe and was not
fabricated.

Safety: `LIVE_TRADING=false`, `AUTO_TRADING=false`, `PAPER_ONLY=true`,
`LIVE_TRADING_AUTHORITY=NONE`. Legacy auto-executors and live paths were not
started.

