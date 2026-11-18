"""Immutable trade journal + Performance Engine R1."""
from __future__ import annotations

import math
from typing import Any

from .signal_engine import parse_time
from .store import TradingStore, new_id, utc_now

MIN_SAMPLE_FOR_EDGE_CLAIM = 30


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def finalize_trade(store: TradingStore, position: dict[str, Any], close: dict[str, Any], exit_reason: str) -> dict[str, Any]:
    """Write one immutable journal record for a closed position (once per position)."""
    existing = store.find("trades", position_id=position["position_id"])
    if existing:
        return existing[0]
    signal = store.get("signals", position["signal_id"]) or {}
    direction = 1 if position["direction"] == "LONG" else -1
    entry, exit_ = _f(position["entry_price"]), _f(close.get("exit_price"))
    stop = _f(position.get("stop_price"))
    risk_dist = abs(entry - stop) if stop else None
    units = abs(_f(position["units"]))
    open_cost = _f(position.get("half_spread_cost"))
    close_cost = _f(close.get("half_spread_cost"))
    financing = _f(close.get("financing"))
    commission = _f(position.get("commission")) + _f(close.get("commission"))
    ref = _f(signal.get("reference_price"))
    record = {
        "trade_id": new_id("trd"),
        "strategy_id": position["strategy_id"],
        "strategy_version_id": position["strategy_version_id"],
        "signal_id": position["signal_id"],
        "order_id": position["order_id"],
        "position_id": position["position_id"],
        "risk_event_id": position["risk_event_id"],
        "instrument": position["instrument"],
        "direction": position["direction"],
        "entry_time": position["entry_time"],
        "entry_price": entry,
        "exit_time": close.get("exit_time"),
        "exit_price": exit_,
        "stop": position.get("stop_price"),
        "target": position.get("target_price"),
        "position_size": units,
        "realized_pnl": _f(close.get("realized_pl")),
        "pnl_currency": position.get("account_currency", "USD"),
        "r_multiple": (direction * (exit_ - entry) / risk_dist) if risk_dist else None,
        "execution_costs": {"half_spread_open": open_cost, "half_spread_close": close_cost, "financing": financing,
                            "commission": commission, "total": open_cost + close_cost - financing + commission},
        "entry_slippage_price": (direction * (entry - ref)) if ref else None,
        "duration_seconds": (parse_time(close["exit_time"]) - parse_time(position["entry_time"])).total_seconds() if close.get("exit_time") else None,
        "exit_reason": exit_reason,
        "broker_receipts": list(dict.fromkeys(r for r in (position.get("receipt_ids") or []) + [close.get("receipt_id")] if r)),
        "broker_trade_id": position.get("broker_trade_id"),
        "origin": signal.get("origin"),
        "mode": "PAPER",
        "live_trading": False,
        "created_at": utc_now(),
    }
    return store.append("trades", record)


def performance(store: TradingStore, strategy_version_id: str, *, persist: bool = True) -> dict[str, Any]:
    trades = sorted(store.find("trades", strategy_version_id=strategy_version_id), key=lambda t: t.get("exit_time") or "")
    pnls = [_f(t["realized_pnl"]) for t in trades]
    wins = [p for p in pnls if p > 0]; losses = [p for p in pnls if p < 0]
    equity = peak = max_dd = 0.0
    for p in pnls:
        equity += p; peak = max(peak, equity); max_dd = max(max_dd, peak - equity)
    rs = [t["r_multiple"] for t in trades if t.get("r_multiple") is not None]
    snap = {
        "snapshot_id": new_id("perf"),
        "strategy_version_id": strategy_version_id,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else None,
        "net_pnl": round(sum(pnls), 6),
        "average_win": (sum(wins) / len(wins)) if wins else None,
        "average_loss": (sum(losses) / len(losses)) if losses else None,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses else (None if not wins else math.inf),
        "expectancy": (sum(pnls) / len(pnls)) if trades else None,
        "expectancy_r": (sum(rs) / len(rs)) if rs else None,
        "max_drawdown": round(max_dd, 6),
        "certification_fixture_trades": sum(1 for t in trades if t.get("origin") == "CERTIFICATION_FIXTURE"),
        "statistical_edge_claim": "NONE" if len(trades) < MIN_SAMPLE_FOR_EDGE_CLAIM else "SAMPLE_SUFFICIENT_FOR_REVIEW_ONLY",
        "sample_note": f"n={len(trades)} < {MIN_SAMPLE_FOR_EDGE_CLAIM}: no edge claim" if len(trades) < MIN_SAMPLE_FOR_EDGE_CLAIM else "review required",
        "trade_ids": [t["trade_id"] for t in trades],
        "computed_at": utc_now(),
    }
    if snap["profit_factor"] == math.inf:
        snap["profit_factor"] = "INF"
    return store.append("performance_snapshots", snap) if persist else snap
