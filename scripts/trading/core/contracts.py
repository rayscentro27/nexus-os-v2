"""Canonical Trading Core R1 contracts and state machines."""
from __future__ import annotations

import hashlib
import json
from typing import Any

SIGNAL_CONTRACT_VERSION = "nexus.trading.signal.v1"
SIGNAL_STATES = {"GENERATED", "RISK_APPROVED", "RISK_REJECTED", "EXPIRED", "EXECUTED", "CANCELLED"}
SIGNAL_TRANSITIONS = {
    "GENERATED": {"RISK_APPROVED", "RISK_REJECTED", "EXPIRED", "CANCELLED"},
    "RISK_APPROVED": {"EXECUTED", "EXPIRED", "CANCELLED"},
    "RISK_REJECTED": set(),
    "EXPIRED": set(),
    "EXECUTED": set(),
    "CANCELLED": set(),
}
# Only deterministic code may originate a signal. A certification fixture is a
# controlled deterministic input, allowed only when the policy says so.
SIGNAL_ORIGINS = {"DETERMINISTIC_STRATEGY", "CERTIFICATION_FIXTURE"}
DIRECTIONS = {"LONG", "SHORT"}
SIGNAL_REQUIRED = (
    "signal_id", "strategy_id", "strategy_version_id", "asset_class", "instrument", "timeframe",
    "direction", "signal_time", "reference_price", "stop_price", "target_price", "proposed_units",
    "proposed_risk", "evidence", "status", "origin", "expires_at",
)

ORDER_STATES = {"ORDER_PENDING_SUBMIT", "ORDER_SUBMITTED", "ORDER_ACKNOWLEDGED", "ORDER_FILLED", "ORDER_REJECTED", "EXECUTION_ERROR", "RECONCILIATION_REQUIRED"}
ORDER_TRANSITIONS = {
    "ORDER_PENDING_SUBMIT": {"ORDER_SUBMITTED", "EXECUTION_ERROR"},
    "ORDER_SUBMITTED": {"ORDER_ACKNOWLEDGED", "ORDER_REJECTED", "EXECUTION_ERROR", "RECONCILIATION_REQUIRED"},
    "ORDER_ACKNOWLEDGED": {"ORDER_FILLED", "ORDER_REJECTED", "RECONCILIATION_REQUIRED"},
    "ORDER_FILLED": set(),
    "ORDER_REJECTED": set(),
    # An unknown broker outcome is never retried blindly; it waits for reconciliation.
    "EXECUTION_ERROR": {"RECONCILIATION_REQUIRED"},
    "RECONCILIATION_REQUIRED": {"ORDER_FILLED", "ORDER_REJECTED"},
}

POSITION_STATES = {"POSITION_OPEN", "POSITION_UPDATED", "POSITION_CLOSED", "TRADE_FINALIZED", "STALE_POSITION", "RECONCILIATION_REQUIRED"}
POSITION_TRANSITIONS = {
    "POSITION_OPEN": {"POSITION_UPDATED", "POSITION_CLOSED", "STALE_POSITION", "RECONCILIATION_REQUIRED"},
    "POSITION_UPDATED": {"POSITION_UPDATED", "POSITION_CLOSED", "STALE_POSITION", "RECONCILIATION_REQUIRED"},
    "POSITION_CLOSED": {"TRADE_FINALIZED"},
    "TRADE_FINALIZED": set(),
    "STALE_POSITION": {"POSITION_CLOSED", "RECONCILIATION_REQUIRED"},
    "RECONCILIATION_REQUIRED": {"POSITION_OPEN", "POSITION_UPDATED", "POSITION_CLOSED", "STALE_POSITION"},
}


class TransitionError(RuntimeError):
    pass


def check_transition(table: dict[str, set[str]], current: str | None, target: str) -> None:
    if current is None:
        return
    if target not in table.get(current, set()):
        raise TransitionError(f"illegal_transition:{current}->{target}")


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def deterministic_signal_id(strategy_version_id: str, instrument: str, signal_bar_time: str, direction: str, origin: str) -> str:
    """Same inputs always yield the same id -> natural duplicate prevention."""
    return "sig_" + canonical_hash([strategy_version_id, instrument, signal_bar_time, direction, origin])[:24]


def order_client_id(signal_id: str) -> str:
    """Broker idempotency key (OANDA clientExtensions.id, <=128 chars)."""
    return "ntc-" + canonical_hash(["order", signal_id])[:28]


def validate_signal(signal: dict[str, Any]) -> list[str]:
    errors = [f"missing:{k}" for k in SIGNAL_REQUIRED if signal.get(k) in (None, "")]
    if errors:
        return errors
    if signal["direction"] not in DIRECTIONS:
        errors.append("bad_direction")
    if signal["status"] not in SIGNAL_STATES:
        errors.append("bad_status")
    if signal["origin"] not in SIGNAL_ORIGINS:
        errors.append("origin_not_deterministic")
    ref, stop, target = float(signal["reference_price"]), float(signal["stop_price"]), float(signal["target_price"])
    if signal["direction"] == "LONG" and not (stop < ref < target):
        errors.append("long_stop_target_geometry")
    if signal["direction"] == "SHORT" and not (target < ref < stop):
        errors.append("short_stop_target_geometry")
    if int(signal["proposed_units"]) <= 0:
        errors.append("units_not_positive")
    return errors
