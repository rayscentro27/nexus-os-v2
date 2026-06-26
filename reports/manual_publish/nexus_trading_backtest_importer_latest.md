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
- proposed_schedule: Manual paper-research review only; no scheduler or live execution.

## Write Result

- local_json_report: `reports/runtime/trading_backtest_import_latest.json`
- local_markdown_report: `reports/runtime/nexus_trading_backtest_importer_latest.md`
- manual_report: `reports/manual_publish/trading_backtest_import_latest.md`
- sample live import created: 1
- duplicate check: passed; second live run skipped as duplicate
- task_request_id: `5d1728de-7431-4d1b-a1ee-166d921673c1`
- nexus_event_id: `3ae917b8-2b39-459b-8799-cdc82e27019a`

## Tables Written

- `task_requests.task_type = trading_lab_backtest_import`
- `task_requests.payload.department = trading_lab`
- `task_requests.payload.project_type = paper_backtest_report`
- `task_requests.payload.paper_only = true`
- `task_requests.payload.live_trading_blocked = true`
- `task_requests.payload.metrics`
- `task_requests.payload.project_enrichment`
- `nexus_events.action = trading_backtest_report_imported`

## Safety Confirmation

No trade, broker API, `auto_executor`, scheduler, persistent loop, publish, send, or deploy action was run by the importer.

## Next Recommendation

Create a Ray-selected `reports/trading/imports/` folder and import one real paper/backtest report from that folder with `--dry-run` first.
