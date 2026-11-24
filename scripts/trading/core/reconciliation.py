"""Deterministic Nexus <-> OANDA Practice reconciliation R1.

Compares expected Nexus orders/positions with actual broker state, records an
immutable reconciliation event, and marks only local state. It NEVER submits,
closes, or modifies broker orders to "fix" a mismatch.
"""
from __future__ import annotations

from typing import Any

from .contracts import POSITION_TRANSITIONS, check_transition
from .oanda_practice_adapter import ORDER_TAG
from .store import TradingStore, new_id, utc_now

LOCAL_OPEN = {"POSITION_OPEN", "POSITION_UPDATED", "STALE_POSITION", "RECONCILIATION_REQUIRED"}
MISMATCH_KINDS = {"MISSING_ORDER", "DUPLICATE_ORDER", "UNEXPECTED_POSITION", "STALE_LOCAL_POSITION", "QUANTITY_MISMATCH", "ORDER_OUTCOME_UNKNOWN"}


def compare(local_positions: list[dict], local_orders: list[dict], broker_trades: list[dict], *, trade_lookup, order_lookup) -> list[dict]:
    """Pure comparison. ``trade_lookup(id)`` / ``order_lookup('@client')`` read broker history."""
    findings: list[dict] = []
    by_id = {str(t["trade_id"]): t for t in broker_trades}
    owned = [t for t in broker_trades if t.get("tag") == ORDER_TAG]
    expected_ids = {str(p["broker_trade_id"]) for p in local_positions if p.get("state") in LOCAL_OPEN}

    for p in local_positions:
        if p.get("state") not in LOCAL_OPEN:
            continue
        tid = str(p["broker_trade_id"])
        if tid in by_id:
            if abs(abs(float(by_id[tid]["units"])) - abs(float(p["units"]))) > 1e-9:
                findings.append({"kind": "QUANTITY_MISMATCH", "position_id": p["position_id"], "local_units": p["units"], "broker_units": by_id[tid]["units"]})
            else:
                findings.append({"kind": "MATCHED", "position_id": p["position_id"], "broker_trade_id": tid})
            continue
        hist = trade_lookup(tid)
        if hist.get("ok") and hist.get("state") == "CLOSED":
            findings.append({"kind": "BROKER_CLOSED_POSITION", "position_id": p["position_id"], "broker_trade_id": tid,
                             "close_time": hist.get("close_time"), "realized_pl": hist.get("realized_pl")})
        else:
            findings.append({"kind": "STALE_LOCAL_POSITION", "position_id": p["position_id"], "broker_trade_id": tid})

    for t in owned:
        if str(t["trade_id"]) not in expected_ids:
            findings.append({"kind": "UNEXPECTED_POSITION", "broker_trade_id": t["trade_id"], "instrument": t["instrument"], "client_id": t.get("client_id")})
    clients: dict[str, int] = {}
    for t in owned:
        if t.get("client_id"):
            clients[t["client_id"]] = clients.get(t["client_id"], 0) + 1
    for cid, count in clients.items():
        if count > 1:
            findings.append({"kind": "DUPLICATE_ORDER", "client_id": cid, "broker_trade_count": count})
    for t in broker_trades:
        if t.get("tag") != ORDER_TAG:
            findings.append({"kind": "EXTERNAL_POSITION", "broker_trade_id": t["trade_id"], "instrument": t["instrument"], "note": "not owned by Trading Core; counted by risk limits"})

    for o in local_orders:
        if o.get("state") in {"ORDER_SUBMITTED", "ORDER_ACKNOWLEDGED", "EXECUTION_ERROR", "RECONCILIATION_REQUIRED"}:
            b = order_lookup(f"@{o['client_id']}")
            if b.get("exists"):
                findings.append({"kind": "ORDER_OUTCOME_UNKNOWN", "order_id": o["order_id"], "broker_order_state": b.get("state"),
                                 "broker_trade_id": b.get("trade_opened_id"), "note": "broker has the order; local outcome unresolved"})
            else:
                findings.append({"kind": "MISSING_ORDER", "order_id": o["order_id"], "note": "local order not found at broker"})
    return findings


def reconcile(store: TradingStore, adapter) -> dict[str, Any]:
    trades = adapter.get_open_trades()
    if not trades["ok"]:
        event = {"reconciliation_id": new_id("recon"), "status": "BROKER_UNAVAILABLE", "error": trades["error"], "findings": [], "created_at": utc_now()}
        return store.append("reconciliation_events", event)
    positions = store.latest("positions"); orders = store.latest("orders")
    findings = compare(positions, orders, trades["trades"], trade_lookup=adapter.get_trade, order_lookup=adapter.get_order)
    mismatches = [f for f in findings if f["kind"] in MISMATCH_KINDS]
    for f in mismatches:
        if f["kind"] in {"STALE_LOCAL_POSITION", "QUANTITY_MISMATCH"}:
            pos = store.get("positions", f["position_id"])
            target = "STALE_POSITION" if f["kind"] == "STALE_LOCAL_POSITION" else "RECONCILIATION_REQUIRED"
            if pos and pos["state"] != target:
                check_transition(POSITION_TRANSITIONS, pos["state"], target)
                store.append("positions", {**pos, "state": target, "state_history": list(pos.get("state_history") or []) + [{"state": target, "at": utc_now()}]})
    event = {
        "reconciliation_id": new_id("recon"),
        "status": "MISMATCH" if mismatches else "MATCHED",
        "findings": findings,
        "mismatch_count": len(mismatches),
        "broker_open_trade_count": len(trades["trades"]),
        "local_open_position_count": sum(1 for p in positions if p.get("state") in LOCAL_OPEN),
        "auto_fix_orders_submitted": 0,
        "strategy_version_ids": sorted({p.get("strategy_version_id") for p in positions if p.get("strategy_version_id")}),
        "created_at": utc_now(),
    }
    return store.append("reconciliation_events", event)
