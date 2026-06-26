# Nexus Vibe Trading Integration

## Local Inspection

Read-only inspection found:

- `~/nexus-ai/trading-engine`
- `~/nexuslive/trading-engine`
- `~/.vibe-trading`

No standalone `vibe-trading` CLI was found in PATH. `~/.vibe-trading` exists as a local memory directory, but no executable package metadata was found there.

## Safe Command Templates

The only safe command templates identified are bounded backtest simulations:

```bash
python3 ~/nexus-ai/trading-engine/backtest/backtester.py --signals ~/nexus-ai/trading-engine/backtest/sample_signals.json --balance 10000 --report
```

```bash
python3 ~/nexuslive/trading-engine/backtest/backtester.py --signals ~/nexuslive/trading-engine/backtest/sample_signals.json --balance 10000 --report
```

The adapter reports these templates. It does not run them automatically.

## Blocked Commands

- `python3 auto_executor.py`
- `python3 nexus_trading_engine.py`
- `python3 tournament_service.py`
- `openclaw gateway`
- manual signal webhook/API calls
- TradingView webhook receiver paths

## Adapter

`scripts/trading/vibe_trading_adapter.py` supports:

```bash
python3 scripts/trading/vibe_trading_adapter.py --dry-run --mode status --no-live-trading
```

It writes local status reports only and returns safe JSON. It does not place trades, call broker APIs, modify credentials, start loops, or start schedulers.

## Feeder

`scripts/automation/feeders/trading_lab_demo_research_feeder.py` creates paper-only Trading Lab cards from safe local reports and read-only trading research tables when available.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live research-card creation:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --no-dry-run --limit 5 --no-external-ai
```

Live feeder writes are limited to `task_requests` and `nexus_events` proof. No trade, broker call, scheduler, or executor is run.

## Next Safe Test

Review the paper-only Trading Lab status card in Nexus. The next implementation should add a bounded backtest import command that writes a local JSON report without calling broker APIs or starting persistent services.
