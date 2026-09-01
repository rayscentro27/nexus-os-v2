# After-Hours Run Plan

Ray-reviewed command: `MAX_CYCLES=8 INTERVAL_SECONDS=3600 scripts/ops/run_wp86_bounded_practice_window.sh`. It runs eight hourly bounded cycles, evaluates the durable Practice cohort, reconciles OANDA first, records receipts, and stops. It does not start automatically and does not permit live trading. Morning review should summarize cycles, signals, vetoes, orders, fills, positions, P/L, anomalies, recovery, and Alpha triggers.
