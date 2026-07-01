# Nexus Process Activity Latest

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** nexus_process_inventory, nexus_scheduler_inventory, nexus_operations_status

---

## Summary

| Proof Level | Count |
|-------------|-------|
| active_process | 14 |
| recent_output | 1 |
| loaded_only | 0 |
| installed_only | 0 |
| available_script_only | 0 |
| not_found | 0 |
| unknown | 1 |
| **Total** | **16** |

---

## Process Activity

### hermes_agent

- **PID:** 538 | **Uptime:** 20:18:41
- **Proof Level:** active_process
- **Scheduler:** Not applicable (GUI app)
- **Risk:** Low
- **Command:** `/Applications/Hermes Agent.app/Contents/MacOS/Hermes Agent`

### tradingview_router

- **PID:** 580 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.signal-router (loaded)
- **Last Output:** 2026-07-01T19:00:03Z
- **Risk:** Low
- **Command:** `python3 tradingview_router.py`

### nexus-orchestrator

- **PID:** 582 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.orchestrator (loaded)
- **Last Output:** 2026-07-01T19:37:40Z
- **Risk:** Low

### nexus-research-worker

- **PID:** 586 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.research-worker (loaded)
- **Last Output:** 2026-06-30T23:37:40Z
- **Risk:** Low

### cloudflared_tunnel

- **PID:** 587 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.cloudflare-tunnel (loaded)
- **Last Output:** 2026-06-30T23:39:15Z
- **Risk:** Low

### nexus_trading_engine

- **PID:** 588 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.trading-engine (loaded)
- **Last Output:** 2026-07-01T19:01:00Z
- **Risk:** Medium
- **Note:** Do not enable live trading

### dashboard

- **PID:** 590 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.raymonddavis.nexus.dashboard (loaded)
- **Last Output:** 2026-06-30T23:40:37Z
- **Risk:** Low

### research_signal_bridge

- **PID:** 598 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.research-signal-bridge (loaded)
- **Last Output:** 2026-07-01T19:39:30Z
- **Risk:** Low

### auto_executor

- **PID:** 607 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.auto-executor (loaded)
- **Last Output:** 2026-07-01T19:39:10Z
- **Risk:** Medium
- **Note:** Do not enable live execution

### operations_center_scheduler

- **PID:** 613 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Risk:** Low

### hermes_cli_gateway

- **PID:** 618 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Risk:** Low

### tournament_service

- **PID:** 622 | **Uptime:** 20:17:39
- **Proof Level:** active_process
- **Scheduler:** com.nexus.tournament (loaded)
- **Last Output:** 2026-07-01T19:38:00Z
- **Risk:** Low

### hermes-gateway-adapter

- **PID:** 6514 | **Uptime:** 19:55:54
- **Proof Level:** active_process
- **Risk:** Low

### control_center_server

- **PID:** 8840 | **Uptime:** 00:05
- **Proof Level:** active_process
- **Scheduler:** com.raymonddavis.nexus.control-center (loaded)
- **Last Output:** 2026-07-01T19:39:26Z
- **Risk:** Low

### youtube-channel-poller

- **PID:** None | **Status:** Not found in process inventory
- **Proof Level:** recent_output
- **Scheduler:** com.nexus.youtube-channel-poller (loaded)
- **Last Output:** 2026-07-01T15:40:23Z
- **Risk:** Low
- **Note:** No active PID proof. No proof of recent metadata fetch.

---

## Critical Note

Proof level is based on process evidence (`ps -axo`), log timestamps, and scheduler state. Never claim a process is active without PID proof.
