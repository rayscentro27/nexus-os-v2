# Admin Trading Replay Architecture

Admin navigation now includes Trading Lab. The page presents persisted WP8.5 tournament records, provenance, evidence tier, paper-only safety, bounded replay controls, and a read-only SVG review chart. Replay records contain experiment/strategy/version/market/timeframe/mode/metrics and `lookahead_protected=true`; future execution authority is `NONE`. TradingView Lightweight Charts remains the preferred production library for a later dependency-reviewed enhancement; the current foundation has no new runtime dependency.
