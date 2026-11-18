"""Order / position lifecycle R1.

SIGNAL -> RISK_APPROVED -> ORDER_SUBMITTED -> ORDER_ACKNOWLEDGED -> (ORDER_FILLED)
-> POSITION_OPEN -> POSITION_UPDATED -> POSITION_CLOSED -> TRADE_FINALIZED

Failures: ORDER_REJECTED, EXECUTION_ERROR -> RECONCILIATION_REQUIRED, STALE_POSITION.
An unknown broker outcome is never retried automatically; it blocks new risk
approvals until reconciliation explains it. Every broker action writes a receipt.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import journal
from .signal_engine import parse_time
from .contracts import ORDER_TRANSITIONS, POSITION_TRANSITIONS, SIGNAL_TRANSITIONS, check_transition, order_client_id
from .oanda_practice_adapter import AdapterRefused, LiveEndpointBlocked, OandaPracticeAdapter
from .store import TradingStore, new_id, utc_now


class LifecycleError(RuntimeError):
    pass


def _set(store: TradingStore, collection: str, table: dict, entity: dict[str, Any], state: str, **changes: Any) -> dict[str, Any]:
    check_transition(table, entity.get("state"), state)
    history = list(entity.get("state_history") or []) + [{"state": state, "at": utc_now()}]
    return store.append(collection, {**entity, **changes, "state": state, "state_history": history})


def _signal_status(store: TradingStore, signal: dict[str, Any], status: str) -> dict[str, Any]:
    check_transition(SIGNAL_TRANSITIONS, signal["status"], status)
    return store.append("signals", {**signal, "status": status})


def receipt(store: TradingStore, payload: dict[str, Any], **links: Any) -> dict[str, Any]:
    return store.append("execution_receipts", {"receipt_id": new_id("rcpt"), **links, **payload, "created_at": utc_now()})


def build_order_request(signal: dict[str, Any]) -> dict[str, Any]:
    units = int(signal["proposed_units"]) * (1 if signal["direction"] == "LONG" else -1)
    return {"environment": "PRACTICE", "instrument": signal["instrument"], "units": units, "client_id": order_client_id(signal["signal_id"]),
            "signal_id": signal["signal_id"], "stop_price": signal["stop_price"], "target_price": signal["target_price"]}


def _approved(store: TradingStore, signal_id: str, now: datetime | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    signal = store.get("signals", signal_id)
    if not signal:
        raise LifecycleError("signal_not_found")
    if signal["status"] != "RISK_APPROVED":
        raise LifecycleError(f"signal_not_risk_approved:{signal['status']}")
    events = [e for e in store.find("risk_events", signal_id=signal_id)]
    approved = [e for e in events if e["decision"] == "APPROVE" and e["risk_event_id"] == signal.get("risk_event_id")]
    # A later re-gate of the same signal is always flagged no_duplicate_signal;
    # that rejection records the duplicate attempt but does not revoke the
    # original point-in-time approval. Any other rejection does.
    revoking = [e for e in events if e["decision"] == "REJECT" and "no_duplicate_signal" not in e["failed_rules"]]
    if not approved or revoking:
        raise LifecycleError("no_valid_approving_risk_event")
    if parse_time(signal["expires_at"]) <= (now or datetime.now(timezone.utc)):
        raise LifecycleError("signal_expired_before_execution")
    if store.find("orders", signal_id=signal_id):
        raise LifecycleError("duplicate_order_blocked")
    return signal, approved[0]


def dry_run(store: TradingStore, signal_id: str, now: datetime | None = None) -> dict[str, Any]:
    signal, event = _approved(store, signal_id, now)
    return {"would_submit": build_order_request(signal), "risk_event_id": event["risk_event_id"], "submitted": False}


def execute(store: TradingStore, adapter: OandaPracticeAdapter, signal_id: str, now: datetime | None = None) -> dict[str, Any]:
    signal, event = _approved(store, signal_id, now)
    req = build_order_request(signal)
    links = {"strategy_version_id": signal["strategy_version_id"], "signal_id": signal_id, "risk_event_id": event["risk_event_id"]}
    order = store.append("orders", {"order_id": new_id("ord"), **links, "strategy_id": signal["strategy_id"], "instrument": signal["instrument"],
                                    "direction": signal["direction"], "units": req["units"], "client_id": req["client_id"],
                                    "state": "ORDER_PENDING_SUBMIT", "state_history": [{"state": "ORDER_PENDING_SUBMIT", "at": utc_now()}],
                                    "created_at": utc_now(), "receipt_ids": []})
    order = _set(store, "orders", ORDER_TRANSITIONS, order, "ORDER_SUBMITTED")
    try:
        result = adapter.submit_paper_order(req)
    except (LiveEndpointBlocked, AdapterRefused) as exc:
        r = receipt(store, {"action": "SUBMIT_PAPER_ORDER", "ok": False, "error": f"{type(exc).__name__}:{exc}", "broker_called": False}, order_id=order["order_id"], **links)
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "ORDER_REJECTED", rejection=str(exc), receipt_ids=[r["receipt_id"]])
        _signal_status(store, store.get("signals", signal_id), "CANCELLED")
        return {"ok": False, "order": order, "receipt": r}
    except Exception as exc:  # unknown outcome -> reconcile, never retry blindly
        r = receipt(store, {"action": "SUBMIT_PAPER_ORDER", "ok": False, "error": f"unexpected:{type(exc).__name__}"}, order_id=order["order_id"], **links)
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "EXECUTION_ERROR", receipt_ids=[r["receipt_id"]])
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "RECONCILIATION_REQUIRED")
        return {"ok": False, "order": order, "receipt": r}

    r = receipt(store, result, order_id=order["order_id"], **links)
    rids = [r["receipt_id"]]
    if result.get("ok") and result.get("trade_id"):
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "ORDER_ACKNOWLEDGED", broker_order_id=result.get("order_id"), receipt_ids=rids)
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "ORDER_FILLED", broker_fill_transaction_id=result.get("fill_transaction_id"))
        position = store.append("positions", {
            "position_id": new_id("pos"), **links, "strategy_id": signal["strategy_id"], "order_id": order["order_id"],
            "instrument": signal["instrument"], "direction": signal["direction"], "units": abs(req["units"]),
            "broker_trade_id": result["trade_id"], "entry_price": result.get("fill_price"), "entry_time": result.get("fill_time"),
            "stop_price": signal["stop_price"], "target_price": signal["target_price"], "half_spread_cost": result.get("half_spread_cost"),
            "commission": result.get("commission"), "receipt_ids": rids, "state": "POSITION_OPEN",
            "state_history": [{"state": "POSITION_OPEN", "at": utc_now()}], "opened_at": utc_now()})
        _signal_status(store, store.get("signals", signal_id), "EXECUTED")
        return {"ok": True, "order": order, "position": position, "receipt": r}
    err = str(result.get("error") or "")
    status = result.get("http_status")
    if err.startswith(("GOVERNOR", "idempotency_precheck")):
        # Request never reached the order endpoint: deterministic rejection, nothing at broker.
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "ORDER_REJECTED", rejection=err, receipt_ids=rids)
        _signal_status(store, store.get("signals", signal_id), "CANCELLED")
        return {"ok": False, "order": order, "receipt": r}
    if status is None or status >= 500:
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "EXECUTION_ERROR", receipt_ids=rids)
        order = _set(store, "orders", ORDER_TRANSITIONS, order, "RECONCILIATION_REQUIRED")
        return {"ok": False, "order": order, "receipt": r}
    order = _set(store, "orders", ORDER_TRANSITIONS, order, "ORDER_REJECTED", rejection=result.get("reject_reason") or result.get("cancel_reason") or result.get("error"),
                 broker_order_id=result.get("order_id"), receipt_ids=rids)
    _signal_status(store, store.get("signals", signal_id), "CANCELLED")
    return {"ok": False, "order": order, "receipt": r}


def refresh_position(store: TradingStore, adapter: OandaPracticeAdapter, position_id: str) -> dict[str, Any]:
    """Read broker truth; a broker-side close (SL/TP) is recorded, never re-traded."""
    pos = store.get("positions", position_id)
    t = adapter.get_trade(pos["broker_trade_id"])
    if not t["ok"]:
        return {"ok": False, "position": pos, "error": t["error"]}
    if t["state"] == "OPEN":
        return {"ok": True, "position": _set(store, "positions", POSITION_TRANSITIONS, pos, "POSITION_UPDATED", broker_current_units=t["current_units"])}
    if t["state"] == "CLOSED":
        close = {"exit_price": t["average_close_price"], "exit_time": t["close_time"], "realized_pl": t["realized_pl"], "financing": t["financing"]}
        r = receipt(store, {"action": "BROKER_CLOSE_OBSERVED", "ok": True, **close, "trade_id": t["trade_id"]},
                    strategy_version_id=pos["strategy_version_id"], signal_id=pos["signal_id"], order_id=pos["order_id"], position_id=position_id)
        return _close_and_finalize(store, pos, {**close, "receipt_id": r["receipt_id"]}, "BROKER_CLOSED_STOP_OR_TARGET")
    return {"ok": False, "position": pos, "error": f"unexpected_trade_state:{t['state']}"}


def close_position(store: TradingStore, adapter: OandaPracticeAdapter, position_id: str, reason: str) -> dict[str, Any]:
    pos = store.get("positions", position_id)
    if pos["state"] not in {"POSITION_OPEN", "POSITION_UPDATED", "STALE_POSITION"}:
        raise LifecycleError(f"position_not_closable:{pos['state']}")
    result = adapter.close_paper_position(pos["broker_trade_id"])
    r = receipt(store, result, strategy_version_id=pos["strategy_version_id"], signal_id=pos["signal_id"], order_id=pos["order_id"], position_id=position_id)
    if not result["ok"]:
        pos = _set(store, "positions", POSITION_TRANSITIONS, pos, "RECONCILIATION_REQUIRED", close_error=result.get("error") or result.get("reject_reason"))
        return {"ok": False, "position": pos, "receipt": r}
    return _close_and_finalize(store, pos, {**result, "receipt_id": r["receipt_id"]}, reason)


def _close_and_finalize(store: TradingStore, pos: dict[str, Any], close: dict[str, Any], reason: str) -> dict[str, Any]:
    pos = _set(store, "positions", POSITION_TRANSITIONS, pos, "POSITION_CLOSED", exit_price=close.get("exit_price"), exit_time=close.get("exit_time"),
               realized_pl=close.get("realized_pl"), receipt_ids=list(pos.get("receipt_ids") or []) + [close["receipt_id"]])
    trade = journal.finalize_trade(store, pos, close, reason)
    pos = _set(store, "positions", POSITION_TRANSITIONS, pos, "TRADE_FINALIZED", trade_id=trade["trade_id"])
    return {"ok": True, "position": pos, "trade": trade}
