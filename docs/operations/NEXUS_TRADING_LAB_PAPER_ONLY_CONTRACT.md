# Nexus Trading Lab Paper-Only Contract

Trading Lab is a demo research department. It may review strategy ideas, backtests, paper/demo signals, risk notes, and proof history. It must not expose live trading controls.

## Allowed

- Strategy research.
- Bounded backtest review.
- Paper/demo result import.
- Explicit backtest report import from a safe selected local file.
- Ray-selected paper/backtest files under `reports/trading/imports/`.
- Paper-only report generation.
- Risk scoring and strategy scorecards.
- Hermes advisory review.
- Internal task creation.
- `nexus_events` proof logging.

## Blocked

- Live broker orders.
- Funded-account execution.
- Raw `auto_executor` exposure.
- Persistent trading loops.
- Scheduler activation.
- Unbounded strategy runs.
- Copying, printing, storing, or modifying secrets/tokens.
- Broker credentials, tokens, private keys, live order instructions, funded-account statements, or customer/private financial data in `reports/trading/imports/`.
- Broker credential changes.
- Webhook/manual signal execution paths.

## Broker Segregation

Nexus OS v2 may show paper/demo status, but it must not connect a live broker account or expose execution commands. Demo/paper reports can be reviewed as research evidence only.

## Proof Requirements

Every Trading Lab card created by Nexus v2 must include:

- `paper_only=true`
- `live_trading_blocked=true`
- source/report reference
- imported metrics when available
- risk notes
- proof event id

## Approval Requirements

Any proposal to schedule, run a demo loop, connect a broker, modify credentials, or bridge to Vibe Trading execution requires a separate approval and a separate implementation pass. Approval still must not enable live trading without a new contract.

## Hermes Limits

Hermes may summarize, recommend, compare pros/cons, and propose paper-only next steps. Hermes may not approve trades, place trades, run executors, start loops, or modify broker settings.

## Vibe Trading Boundary

The first integration is status/report/import only:

- safe status discovery
- safe backtest command templates
- explicit selected backtest report import
- blocked command list
- local reports
- Trading Lab research cards

The adapter does not import or execute the Vibe Trading engine, `auto_executor`, tournament service, webhooks, or broker APIs.
