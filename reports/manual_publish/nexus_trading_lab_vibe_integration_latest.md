# Nexus Trading Lab / Vibe Trading Integration

- generated_at: 2026-06-26
- mode: paper/demo research integration plus explicit backtest report import
- paper_only: true
- live_trading_blocked: true
- scheduler_started: false
- trade_placed: false
- broker_modified: false
- auto_executor_called: false

## Local Inspection

Found:

- `~/nexus-ai/trading-engine`
- `~/nexuslive/trading-engine`
- `~/.vibe-trading`

No standalone `vibe-trading` CLI was found. `~/.vibe-trading` exists as a memory directory with no executable package metadata found.

## Safe Command Templates

The adapter identified bounded backtest command templates only:

- `python3 ~/nexus-ai/trading-engine/backtest/backtester.py --signals ~/nexus-ai/trading-engine/backtest/sample_signals.json --balance 10000 --report`
- `python3 ~/nexuslive/trading-engine/backtest/backtester.py --signals ~/nexuslive/trading-engine/backtest/sample_signals.json --balance 10000 --report`

The adapter reports these templates. It does not run them automatically.

## Blocked

- `auto_executor.py`
- `nexus_trading_engine.py`
- `tournament_service.py`
- OpenClaw gateway startup
- TradingView webhook receiver paths
- manual signal endpoint calls
- broker order paths
- scheduler activation
- funded/live trading

## Adapter Verification

Command:

```bash
python3 scripts/trading/vibe_trading_adapter.py --dry-run --mode import-report --no-live-trading --json
```

Result: passed. Wrote local reports only and listed safe templates/blocked commands.

## Backtest Importer

New command:

```bash
python3 scripts/trading/import_backtest_report.py --sample --dry-run --no-live-trading --json
```

The importer reads one explicit safe local file, parses JSON/CSV/Markdown/text reports, computes deterministic paper-only enrichment, writes local reports, and can create a Trading Lab `task_requests` card plus `nexus_events` proof when `--no-dry-run` is explicitly used.

Sample live import result:

- created: 1
- duplicate prevention: passed on second run
- task_request_id: `5d1728de-7431-4d1b-a1ee-166d921673c1`
- proof_event_id: `3ae917b8-2b39-459b-8799-cdc82e27019a`
- trade_placed: false
- broker_api_called: false
- scheduler_started: false
- auto_executor_called: false

## Feeder Verification

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --dry-run --limit 5 --no-external-ai
```

Initial result: passed. Found one safe candidate from the local adapter status report.

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --no-dry-run --limit 5 --no-external-ai
```

Result:

- scanned: 1
- eligible: 1
- created: 1
- skipped: 0
- duplicates: 0
- failed: 0
- task_request_id: `fb08214a-1663-45b1-8e82-42c5e8a0f480`
- proof_event_id: `5e8b2cb4-7ac5-4302-8f86-e38920de2408`

## UI / Project Card Behavior

Trading Lab uses the department workspace model with paper-only actions:

- Run Backtest: disabled/not connected unless a future bounded backtest runner is approved.
- Generate Report.
- Create Task.
- Send to Ops.
- Paper Demo Only.
- Park Strategy.

There is no live trading, broker execute, or auto-executor button.

## Watch Verification

`npm run nexus:watch` passed. It reported scheduler not installed/started, `trade_placed=false`, demo/paper trading status, and Facebook publish still blocked.

## Next Recommendation

Add a Ray-selected safe import folder such as `reports/trading/imports/`, then import one real paper/backtest report through `scripts/trading/import_backtest_report.py` with `--dry-run` first.
