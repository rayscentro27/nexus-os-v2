# Sample Trading Strategy Pipeline Run

> INTERNAL OPERATIONS — DRAFT ONLY — RAY REVIEW REQUIRED — NO REAL CLIENT DATA

```json
{
  "strategy_id": "alpha-fx-trend-001",
  "market": "forex",
  "hypothesis": "Simple trend-following forex strategy using moving average confirmation and strict stop-loss.",
  "timeframe": "4-hour draft",
  "risk_rules": [
    "demo only",
    "strict predefined stop",
    "include spread/slippage",
    "risk budget required"
  ],
  "blocked_actions": [
    "live/funded trade",
    "automatic order",
    "performance claim"
  ],
  "backtest_plan": [
    "freeze deterministic rules",
    "approved historical data",
    "costs",
    "out-of-sample validation",
    "sensitivity tests"
  ],
  "demo_plan": [
    "read-only practice verification",
    "Ray approval",
    "paper simulation",
    "receipt review"
  ],
  "required_data": [
    "OHLC",
    "spread history",
    "instrument metadata"
  ],
  "oanda_demo_status": "disabled pending safe read-only credential verification",
  "ray_review_required": true,
  "no_live_funded_trading": true,
  "performance_results": null
}
```
