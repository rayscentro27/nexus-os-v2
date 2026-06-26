# Nexus Trading Backtest Importer

- generated_at: 2026-06-26
- dry_run_passed: true
- live_sample_import_ran: true
- paper_only: true
- live_trading_blocked: true
- trade_placed: false
- broker_api_called: false
- auto_executor_called: false
- scheduler_started: false
- persistent_loop_started: false

## Source

- `tests/fixtures/trading/sample_backtest_report.json`

## Parsed Metrics

- win_rate_pct: 57.8
- profit_factor: 1.62
- total_return_pct: 8.4
- max_drawdown_pct: 6.9
- trade_count: 64

## Enrichment

- score: 92
- recommendation: Continue paper demo and compare against a baseline; do not live trade.
- next_action: Create a paper-demo comparison plan and request a second backtest window.

## Write Result

- sample live import created: 1
- duplicate check: passed; second live run skipped as duplicate
- task_request_id: `5d1728de-7431-4d1b-a1ee-166d921673c1`
- nexus_event_id: `3ae917b8-2b39-459b-8799-cdc82e27019a`

## Safety Confirmation

No trade, broker API, `auto_executor`, scheduler, persistent loop, publish, send, or deploy action was run by the importer.
