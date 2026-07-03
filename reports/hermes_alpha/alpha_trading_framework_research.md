# Alpha Trading and Backtesting Framework Research

| Project | Runtime/license | Strengths | Weaknesses / complexity | Recommendation |
|---|---|---|---|---|
| [backtesting.py](https://github.com/kernc/backtesting.py) | Python; AGPL-3.0 | Compact API, fast strategy prototyping, familiar DataFrame workflow, optimization/plots | Bar-based assumptions, licensing review needed for embedding, less suited to complex portfolios/execution | First reference; run isolated later or copy concepts, not code |
| [Backtrader](https://github.com/mementum/backtrader) | Python; GPL-3.0 | Mature event-driven model, indicators, feeds, broker simulation | Larger/older ecosystem, steeper object model, copyleft considerations | Wrap later only if multi-feed/event detail is needed |
| [QuantConnect LEAN](https://github.com/QuantConnect/Lean) | C# + Python; Apache-2.0 | Professional event engine, multi-asset models, research/backtest/live architecture, brokerage plugins | Heavy .NET/Docker/data setup; live capabilities increase risk | Long-term architecture reference; do not install for v1 |
| [Oanda v20 API](https://developer.oanda.com/rest-live-v20/development-guide/) and official examples | REST/various | Dedicated practice endpoint, account/instrument/pricing/transaction primitives | Credential/broker risk; order endpoint is an external side effect; CFD risk | Documentation reference only; no adapter or calls now |

## First approach

Define strategy specs and metrics in Alpha, export an offline backtest packet, and later run a separate Python backtesting.py adapter against approved historical files. Require out-of-sample testing, costs/spread, minimum sample, baseline comparison, parameter-sensitivity review, and deterministic receipts. LEAN remains the heavier future reference. Oanda practice execution comes only after brain, backtest evidence, limits, kill switch, and Ray Review pass.
