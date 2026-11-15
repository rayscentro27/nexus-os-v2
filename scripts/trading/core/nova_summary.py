"""Trading -> Nova summary contract R1 (read-only projection of durable state).

Nova consumes this; it does not compute Trading truth. Answers: what is
Trading doing, what traded today, why a trade was entered, why a signal was
rejected, strategy performance, and whether risk limits are breached.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import CORE_VERSION, TRADING_MODE
from .store import TradingStore

CONTRACT_VERSION = "nexus.trading.nova_summary.v1"


def _today(ts: str | None) -> bool:
    return bool(ts) and ts[:10] == datetime.now(timezone.utc).date().isoformat()


def build(store: TradingStore, *, policy: dict[str, Any], engine_health: str, broker_health: dict[str, Any] | None) -> dict[str, Any]:
    versions = [v for v in store.latest("strategy_versions") if v["strategy_version_id"] in policy.get("authorized_strategy_versions", [])]
    active = versions[0] if versions else None
    positions = [p for p in store.latest("positions") if p.get("state") in {"POSITION_OPEN", "POSITION_UPDATED", "STALE_POSITION", "RECONCILIATION_REQUIRED"}]
    trades_today = [t for t in store.latest("trades") if _today(t.get("exit_time"))]
    risk_today = [e for e in store.latest("risk_events") if _today(e.get("timestamp"))]
    signals = {s["signal_id"]: s for s in store.latest("signals")}
    perf = None
    if active:
        snaps = sorted(store.find("performance_snapshots", strategy_version_id=active["strategy_version_id"]), key=lambda s: s.get("computed_at") or "")
        perf = snaps[-1] if snaps else None
    recon = sorted(store.latest("reconciliation_events"), key=lambda r: r.get("created_at") or "")
    attention = []
    if recon and recon[-1]["status"] != "MATCHED":
        attention.append({"kind": "RECONCILIATION", "status": recon[-1]["status"], "reconciliation_id": recon[-1]["reconciliation_id"]})
    attention += [{"kind": "POSITION_STATE", "position_id": p["position_id"], "state": p["state"]} for p in positions if p["state"] in {"STALE_POSITION", "RECONCILIATION_REQUIRED"}]
    if broker_health and not broker_health.get("healthy"):
        attention.append({"kind": "BROKER_UNHEALTHY", "reason": broker_health.get("health_reason")})
    pnl_today = round(sum(float(t.get("realized_pnl") or 0) for t in trades_today), 6)
    breached = pnl_today <= -policy["max_daily_paper_loss_usd"]
    if breached:
        attention.append({"kind": "DAILY_LOSS_LIMIT_BREACHED", "pnl_today": pnl_today})
    if attention:
        nxt = "Operator review of attention items before further paper signals."
    elif not active:
        nxt = "No authorized strategy version; certification required."
    else:
        nxt = "Continue monitoring the frozen strategy on completed bars; no edge claim until sample >= 30 trades."
    return {
        "contract_version": CONTRACT_VERSION,
        "core_version": CORE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "TRADING_MODE": TRADING_MODE,
        "LIVE_TRADING_ENABLED": False,
        "ENGINE_HEALTH": engine_health,
        "BROKER_HEALTH": {"broker": "OANDA_PRACTICE", "healthy": bool(broker_health and broker_health.get("healthy")),
                          "reason": (broker_health or {}).get("health_reason")},
        "ACTIVE_STRATEGY": {k: active.get(k) for k in ("strategy_id", "strategy_version_id", "name", "instrument", "timeframe", "status")} if active else None,
        "OPEN_POSITIONS": [{k: p.get(k) for k in ("position_id", "instrument", "direction", "units", "entry_price", "stop_price", "target_price", "state", "signal_id")} for p in positions],
        "TRADES_TODAY": [{"trade_id": t["trade_id"], "instrument": t["instrument"], "direction": t["direction"], "realized_pnl": t["realized_pnl"],
                          "r_multiple": t.get("r_multiple"), "exit_reason": t["exit_reason"], "origin": t.get("origin"),
                          "why_entered": (signals.get(t["signal_id"]) or {}).get("evidence"), "risk_event_id": t["risk_event_id"]} for t in trades_today],
        "PAPER_PNL_TODAY": pnl_today,
        "RISK_EVENTS": {"today_total": len(risk_today), "approved": sum(e["decision"] == "APPROVE" for e in risk_today),
                        "rejected": [{"signal_id": e["signal_id"], "risk_event_id": e["risk_event_id"], "why": e["failed_rules"]} for e in risk_today if e["decision"] == "REJECT"]},
        "RISK_LIMITS_BREACHED": breached,
        "STRATEGY_PERFORMANCE": {k: perf.get(k) for k in ("total_trades", "wins", "losses", "win_rate", "net_pnl", "profit_factor", "expectancy", "max_drawdown", "statistical_edge_claim", "sample_note")} if perf else None,
        "ATTENTION_ITEMS": attention,
        "NEXT_RECOMMENDATION": nxt,
    }
