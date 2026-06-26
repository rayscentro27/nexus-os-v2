# Nexus Trading Backtest Importer

The Trading Backtest Importer converts one explicit paper/backtest report file into Trading Lab project-card metadata. It is research-only and does not run Vibe Trading, broker APIs, execution services, schedulers, or persistent loops.

## Command

Dry-run with the bundled fixture:

```bash
python3 scripts/trading/import_backtest_report.py --sample --dry-run --no-live-trading --json
```

Dry-run with a Ray-selected local report:

```bash
python3 scripts/trading/import_backtest_report.py --input-file tests/fixtures/trading/sample_backtest_report.json --dry-run --no-live-trading --json
```

Dry-run with a file Ray places in the safe import folder:

```bash
python3 scripts/trading/import_backtest_report.py --input-file reports/trading/imports/<file>.json --dry-run --no-live-trading --json
```

Bounded live import from an explicit safe file:

```bash
python3 scripts/trading/import_backtest_report.py --input-file tests/fixtures/trading/sample_backtest_report.json --no-dry-run --no-live-trading --json
```

Bounded live metadata import from the safe import folder:

```bash
python3 scripts/trading/import_backtest_report.py --input-file reports/trading/imports/<file>.json --no-dry-run --no-live-trading --json
```

Live import only writes Trading Lab research metadata. It does not place trades, call brokers, start schedulers, run `auto_executor`, or publish/send/deploy anything.

## Accepted Inputs

The importer reads only the explicit file passed with `--input-file` or the bundled `--sample` fixture. It does not recursively scan directories.

Supported formats:

- JSON backtest reports.
- CSV metrics tables or trade/result exports.
- Markdown/text reports that are already local reports.

Allowed file roots are intentionally narrow: `tests/fixtures/trading`, `reports`, and `samples`. Ray-selected paper/backtest files should be placed under `reports/trading/imports/`.

`reports/trading/imports/` is for paper/backtest reports only. Do not place broker credentials, tokens, private keys, live order instructions, funded-account statements, account-sensitive data, or customer/private financial data in this folder. The importer still does not scan folders automatically.

## Parsed Fields

The importer extracts or infers:

- strategy name
- market/instrument/timeframe
- backtest date range
- win rate
- profit factor
- total return
- max drawdown
- trade count
- summary
- risk notes

Missing metrics are represented as: `Metric not available in imported report.`

## Deterministic Enrichment

`scripts/trading/trading_enrichment.py` scores the imported report without external AI. The score rewards positive risk-adjusted metrics, contained drawdown, sufficient trade count, and positive returns. It penalizes missing risk data, high drawdown, low trade count, negative return, and overfit-looking results.

Recommendations are limited to paper-only next steps:

- continue paper demo
- run another bounded backtest
- request more research
- park strategy
- send to Ops for risk review
- compare against baseline

The importer never recommends live trading.

## Writes

Every successful run writes local reports:

- `reports/runtime/trading_backtest_import_latest.json`
- `reports/runtime/nexus_trading_backtest_importer_latest.md`
- `reports/manual_publish/trading_backtest_import_latest.md`
- `reports/manual_publish/nexus_trading_backtest_importer_latest.md`

When `--no-dry-run` is used and Supabase is configured, it may create:

- `task_requests.task_type = trading_lab_backtest_import`
- `task_requests.payload.department = trading_lab`
- `task_requests.payload.project_type = paper_backtest_report`
- `task_requests.payload.paper_only = true`
- `task_requests.payload.live_trading_blocked = true`
- `task_requests.payload.metrics`
- `task_requests.payload.project_enrichment`
- `nexus_events.action = trading_backtest_report_imported`

Duplicate prevention checks the same report hash and the same strategy/source reference before creating a new task.

## UI Verification

Trading Lab reads `trading_lab_backtest_import` task requests through the existing project-card adapter. Imported cards should show strategy name, score, summary, risk notes, Hermes recommendation, proposed schedule, next action, proof event, and paper-only/no-live-execution status.

## Blocked

- live broker orders
- funded account execution
- broker API calls
- `auto_executor`
- Vibe Trading engine startup
- trading schedulers
- persistent loops
- credential edits
- publish/send/deploy

## Next Recommendation

Place one sanitized paper/backtest report in `reports/trading/imports/`, run the dry-run command first, then decide whether to do a bounded metadata import.
