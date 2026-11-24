"""Deterministic Signal Engine R1.

A signal is emitted only by frozen strategy rules evaluated on completed
candles. The latest completed bar must itself be the breakout bar; otherwise
there is no actionable signal (older breakouts are history, not orders).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import wick_rules
from .contracts import SIGNAL_CONTRACT_VERSION, deterministic_signal_id
from .store import TradingStore, utc_now

TIMEFRAME_SECONDS = {"M15": 900, "M30": 1800, "H1": 3600, "H4": 14400}


def parse_time(value: str) -> datetime:
    value = value.replace("Z", "+00:00")
    if "." in value:
        head, tail = value.split(".", 1)
        frac, _, tz = tail.partition("+")
        value = f"{head}.{frac[:6]}+{tz or '00:00'}"
    return datetime.fromisoformat(value)


def _build(version: dict[str, Any], *, direction: int, signal_bar_time: str, reference_price: float, risk_dist: float,
           target_r: float, units: int, origin: str, evidence: dict[str, Any], now: datetime, ttl_seconds: int) -> dict[str, Any]:
    side = "LONG" if direction > 0 else "SHORT"
    stop = reference_price - direction * risk_dist
    target = reference_price + direction * risk_dist * target_r
    return {
        "contract_version": SIGNAL_CONTRACT_VERSION,
        "signal_id": deterministic_signal_id(version["strategy_version_id"], version["instrument"], signal_bar_time, side, origin),
        "strategy_id": version["strategy_id"],
        "strategy_version_id": version["strategy_version_id"],
        "asset_class": version["asset_class"],
        "instrument": version["instrument"],
        "timeframe": version["timeframe"],
        "direction": side,
        "signal_time": now.isoformat(),
        "signal_bar_time": signal_bar_time,
        "reference_price": round(reference_price, 5),
        "stop_price": round(stop, 5),
        "target_price": round(target, 5),
        "proposed_units": int(units),
        "proposed_risk": {"price_distance": round(risk_dist, 6), "quote_ccy_amount": round(risk_dist * units, 6), "r_target": target_r},
        "evidence": evidence,
        "origin": origin,
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "status": "GENERATED",
        "ai_submitted": False,
    }


def generate(version: dict[str, Any], candles: list[dict], *, reference_price: float, units: int, now: datetime | None = None,
             ttl_seconds: int = 120) -> dict[str, Any] | None:
    """Return a GENERATED signal if the last completed candle is a breakout, else None."""
    now = now or datetime.now(timezone.utc)
    if not candles:
        return None
    events = wick_rules.scan(candles, version["parameters"])
    if not events or events[-1]["signal_index"] != len(candles) - 1:
        return None
    ev = events[-1]
    return _build(version, direction=ev["direction"], signal_bar_time=ev["signal_time"], reference_price=reference_price,
                  risk_dist=ev["risk_dist"], target_r=ev["target_multiple_r"], units=units, origin="DETERMINISTIC_STRATEGY",
                  evidence={"rule_event": ev, "bars_evaluated": len(candles), "last_bar_time": candles[-1]["time"]},
                  now=now, ttl_seconds=ttl_seconds)


def latest_rule_state(version: dict[str, Any], candles: list[dict]) -> dict[str, Any]:
    events = wick_rules.scan(candles, version["parameters"])
    return {"bars": len(candles), "last_bar_time": candles[-1]["time"] if candles else None,
            "breakouts_in_window": len(events), "last_breakout": events[-1] if events else None,
            "actionable_now": bool(events and events[-1]["signal_index"] == len(candles) - 1)}


def certification_fixture(version: dict[str, Any], candles: list[dict], *, reference_price: float, units: int, direction: int = 1,
                          now: datetime | None = None, ttl_seconds: int = 120, nonce: str | None = None) -> dict[str, Any]:
    """Controlled deterministic fixture for plumbing certification when the market gives no breakout.

    Uses the frozen version's own stop/target geometry (2x Wilder ATR(14) from
    the live candles, 2R target). Marked origin=CERTIFICATION_FIXTURE so the
    risk gate only accepts it when policy explicitly enables certification.
    """
    now = now or datetime.now(timezone.utc)
    logic = version["parameters"]
    atr = wick_rules.wilder_atr(candles, int(logic["atr"]["period"]))[-1]
    if atr is None:
        raise ValueError("insufficient_candles_for_atr")
    bar_time = candles[-1]["time"] + (f"#{nonce}" if nonce else "")
    return _build(version, direction=direction, signal_bar_time=bar_time, reference_price=reference_price,
                  risk_dist=atr * float(logic["atr"]["stop_multiple"]), target_r=float(logic["atr"]["target_multiple_r"]),
                  units=units, origin="CERTIFICATION_FIXTURE",
                  evidence={"reason": "no breakout on latest completed bar; controlled certification fixture",
                            "atr": atr, "last_bar_time": candles[-1]["time"], "bars_evaluated": len(candles)},
                  now=now, ttl_seconds=ttl_seconds)


def record(store: TradingStore, signal: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Persist a new signal. Returns (record, created). Duplicates are not re-created."""
    existing = store.get("signals", signal["signal_id"])
    if existing:
        return existing, False
    return store.append("signals", {**signal, "created_at": utc_now()}), True
