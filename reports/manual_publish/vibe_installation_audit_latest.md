# Vibe Installation Audit

Generated: 2026-06-29T23:07:54.820146+00:00

- ok: true
- status: vibe_cli_missing_legacy_backtest_available
- cli_installed: false
- cli_path: None
- python_module_installed: false
- package_installed_this_run: false
- external_action_performed: false

## Install/recovery plan

- Do not install Vibe until the exact trusted package/repository and license are approved.
- Use the recovered legacy Nexus synthetic backtest now; it has no broker dependency.
- If Vibe is later approved, install into an isolated virtual environment and run version/help before adapter tests.

## Legacy components

- /Users/raymonddavis/nexuslive/nexus-strategy-lab/backtest/engine.py
- /Users/raymonddavis/nexuslive/nexus-strategy-lab/trading/paper_trade_executor.py
- /Users/raymonddavis/nexus-os-v2/scripts/trading/vibe_trading_adapter.py
