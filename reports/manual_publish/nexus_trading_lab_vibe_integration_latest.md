# Nexus Trading Lab / Vibe Trading Integration

- generated_at: 2026-06-29T17:09:27.467868+00:00
- mode: status
- dry_run: True
- paper_only: true
- live_trading_blocked: true
- scheduler_started: false
- trade_placed: false

## Status

- vibe_trading_found_paper_only

## Found Paths
- nexus-ai/trading-engine
- nexuslive/trading-engine
- .vibe-trading

## Safe Command Templates
- `python3 /Users/raymonddavis/nexus-ai/trading-engine/backtest/backtester.py --signals /Users/raymonddavis/nexus-ai/trading-engine/backtest/sample_signals.json --balance 10000 --report`
- `python3 /Users/raymonddavis/nexuslive/trading-engine/backtest/backtester.py --signals /Users/raymonddavis/nexuslive/trading-engine/backtest/sample_signals.json --balance 10000 --report`

## Blocked Commands
- `python3 auto_executor.py`
- `python3 nexus_trading_engine.py`
- `python3 tournament_service.py`
- `openclaw gateway`
- `curl /signal/manual`
- `curl /webhook/tradingview`

## Warnings
- nexus-ai/trading-engine/auto_executor.py exists and is blocked from Nexus v2 UI/adapter.
- nexus-ai/trading-engine/nexus_trading_engine.py is a persistent/engine path and is blocked here.
- nexus-ai/trading-engine/tournament_service.py has loop/execution paths and is blocked here.
- nexuslive/trading-engine/auto_executor.py exists and is blocked from Nexus v2 UI/adapter.
- nexuslive/trading-engine/nexus_trading_engine.py is a persistent/engine path and is blocked here.
- nexuslive/trading-engine/tournament_service.py has loop/execution paths and is blocked here.
