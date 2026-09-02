# WP8.14 Finance Architecture

Finance is an advisory/governance department over existing governed receipts. It owns measurement, estimates, preflight, budget checks, optimization recommendations, and post-run reconciliation; it cannot purchase, pay, change billing, authorize ad spend, or authorize live trading capital.

The canonical flow is `preflight -> approved envelope -> execution receipt -> resource/cash rollup -> variance -> learning`. Actual, estimated, projected, paper, synthetic, and unknown provenance are retained separately. Unknown balances are never inferred.

Implemented in `scripts/nexus_agent_platform/finance/engine.py`; durable collections were added to governed persistence. The Operator Console exposes `/operator/finance` as an advisory view.
