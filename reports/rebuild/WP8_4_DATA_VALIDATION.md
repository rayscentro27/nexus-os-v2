# WP8.4 Data Validation

Source: `OANDA_PRACTICE`; instrument `EUR_USD`; timeframe `H1`.

Data window: `2026-08-04T01:00:00Z` through `2026-09-01T19:00:00Z`; 499
complete bars. The bounded fetch returned ordered timestamps and usable OHLC
mid closes. No duplicate or missing-bar anomaly was observed in the consumed
series. The GBP/USD unavailable probe was treated as dependency failure, not
filled or inferred.

