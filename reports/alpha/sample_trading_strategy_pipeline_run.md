# Sample Trading Strategy Pipeline Run

> INTERNAL ACTIVATION EVIDENCE — RAY REVIEW REQUIRED

```json
{
  "strategy_id": "alpha-fx-trend-001",
  "market": "forex",
  "hypothesis": "Simple trend-following forex strategy using moving average confirmation and strict stop-loss.",
  "strategy_score": {
    "total": 58,
    "scale": 100,
    "status": "research hypothesis only"
  },
  "risk_classification": "high-risk research; execution blocked",
  "entry_logic": "moving-average alignment plus close confirmation; periods not yet frozen",
  "exit_logic": "predefined volatility stop, opposite confirmation, or time exit",
  "risk_rules": [
    "demo only",
    "stop required",
    "cost/slippage model",
    "risk budget before demo"
  ],
  "backtest_plan": [
    "freeze rules",
    "approved historical data",
    "costs",
    "out-of-sample split",
    "sensitivity checks"
  ],
  "demo_plan": [
    "read-only practice check",
    "Ray approval",
    "paper simulation",
    "receipt comparison"
  ],
  "required_data": [
    "OHLC",
    "spread history",
    "instrument metadata"
  ],
  "oanda_demo_status": "disabled pending approved read-only verification",
  "blocked_actions": [
    "automatic order",
    "live/funded trade",
    "performance claim"
  ],
  "ray_review_required": true,
  "no_live_funded_trading": true,
  "performance_results": null
}
```
