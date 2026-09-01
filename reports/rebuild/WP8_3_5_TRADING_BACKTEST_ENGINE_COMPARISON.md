# Trading Backtest Comparison

The legacy engine supports deterministic replay, configurable slippage, risk
parameters, trade results, equity curves, and summary metrics. Its synthetic
assumptions and separate runtime/storage make it unsuitable as the authority.
The Nexus engine already owns strategy contracts, work orders, receipts,
current safety, and paper boundaries.

Recommendation: `KEEP_NEXUS`, with selective adaptation of legacy test ideas
such as transaction-cost/spread coverage, out-of-sample fixtures, and metric
assertions. WP8.4 should benchmark both on identical bounded inputs before any
component reuse. No look-ahead/OOS superiority claim is made by this audit.

