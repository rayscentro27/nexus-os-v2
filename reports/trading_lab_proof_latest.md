# Trading Lab Proof Latest

**Generated:** 2026-07-01T19:45:00Z
**Mode:** paper_only

---

## Status

| Item | Status | Proof |
|------|--------|-------|
| Mode | paper_only | Verified |
| Live Trading | Disabled | Verified |
| Funded Broker | Not connected | Verified |
| Trading Engine Process | Active | PID 588, uptime 20:17:39 |
| Demo Trading Loop Scheduler | Loaded | com.nexus.demo-trading-loop |
| Tournament Service | Active | PID 622, uptime 20:17:39 |

---

## Process Proof

- **PID 588** — `nexus_trading_engine.py`
  - Uptime: 20:17:39
  - Proof: `ps -axo PID 588 uptime 20:17:39`
  - Last log: 2026-07-01T19:01:00Z

- **PID 622** — `tournament_service.py`
  - Uptime: 20:17:39
  - Proof: `ps -axo PID 622 uptime 20:17:39`
  - Last log: 2026-07-01T19:38:00Z

## Scheduler Proof

- **com.nexus.demo-trading-loop** — loaded, last output 2026-07-01T19:01:01Z
- **com.nexus.trading-engine** — loaded, last output 2026-07-01T19:01:00Z
- **com.nexus.tournament** — loaded, last output 2026-07-01T19:38:00Z

## Oanda Demo Status

- Last checked: 2026-07-01
- Demo account: not_proven_live
- Last pricing check: not_proven_live
- Last trade execution: not_proven_live

## Blockers

1. No proof of recent backtest execution
2. No proof of recent strategy report generation
3. Oanda demo account status not proven live
4. Trading engine active but paper_only mode
5. No Supabase table for trading data

## Next Safe Action

Verify trading engine logs for recent paper trades; check Oanda demo account connectivity.

---

**Critical:** Trading engine process is active (pid-588) in paper_only mode. Do not enable live trading without explicit approval.
