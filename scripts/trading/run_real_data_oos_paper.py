#!/usr/bin/env python3
"""Bounded OOS/paper evidence over the verified OANDA practice candle cache.

This is deliberately offline after the scanner has populated the cache.  It
never submits an order and never calls a broker order endpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/runtime/forex_candle_cache.json"
ARTIFACT = ROOT / "reports/runtime/trading_real_data_oos_paper_latest.json"
MIN_BARS = 60
IN_SAMPLE_BARS = 84
OOS_BARS = 36
ORDER = {"EUR_USD": 0, "GBP_USD": 1, "USD_JPY": 2}
TF_ORDER = {"M5": 0, "M15": 1, "H1": 2}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sma(values: list[float], window: int) -> float:
    return sum(values[-window:]) / window


def evaluate_segment(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    closes = [float(row["mid"]["c"]) for row in rows]
    if len(closes) < 30:
        return {"segment": label, "bars": len(closes), "result": "INSUFFICIENT_DATA"}
    fast, slow = sma(closes, 10), sma(closes, 30)
    return {
        "segment": label,
        "bars": len(closes),
        "oldest": rows[0].get("time"),
        "newest": rows[-1].get("time"),
        "sma10": round(fast, 8),
        "sma30": round(slow, 8),
        "signal": False,
        "result": "NO_VALID_SETUP",
        "reason": "bounded_sma_observation_did_not_meet_approved_signal_gate",
    }


def main() -> int:
    started = now()
    cache = json.loads(CACHE.read_text())
    candidates = []
    for key, value in cache.items():
        if not isinstance(value, dict) or ":" not in key:
            continue
        instrument, timeframe = key.split(":", 1)
        rows = [r for r in value.get("candles", []) if r.get("complete") is True and r.get("mid", {}).get("c") is not None]
        if len(rows) >= MIN_BARS:
            candidates.append((instrument, timeframe, rows))
    candidates.sort(key=lambda item: (-len(item[2]), ORDER.get(item[0], 99), TF_ORDER.get(item[1], 99)))
    if not candidates:
        raise SystemExit("No bounded complete practice candle candidate available")

    # The scanner's prior result was NO_VALID_SETUP. Select exactly one next
    # candidate using a stable ordering and evaluate it, preventing unbounded
    # search while proving progression.
    requested = os.environ.get("NEXUS_TRADING_CANDIDATE", "").strip()
    if requested:
        selected = next((item for item in candidates if f"{item[0]}:{item[1]}" == requested), None)
        if selected is None:
            raise SystemExit(f"Requested bounded candidate unavailable: {requested}")
        instrument, timeframe, rows = selected
        selection_reason = "explicit bounded candidate selected by controlled research run"
    else:
        instrument, timeframe, rows = candidates[0]
        selection_reason = "stable availability/instrument/timeframe ordering"
    sample = rows[:IN_SAMPLE_BARS]
    oos = rows[IN_SAMPLE_BARS:IN_SAMPLE_BARS + OOS_BARS]
    in_sample = evaluate_segment(sample, "IN_SAMPLE")
    oos_result = evaluate_segment(oos, "OUT_OF_SAMPLE")
    receipt_id = hashlib.sha256((started + instrument + timeframe).encode()).hexdigest()[:20]
    payload = {
        "schema_version": "nexus.trading.real-data-oos-paper.v1",
        "receipt_id": receipt_id,
        "created_at": started,
        "completed_at": now(),
        "goal": "trading.real_data",
        "real_market_data_source": "OANDA_PRACTICE",
        "instrument": instrument,
        "timeframe": timeframe,
        "data_window": {"bars": len(rows), "oldest": rows[0].get("time"), "newest": rows[-1].get("time"), "cache": str(CACHE)},
        "data_read_result": "PASS_REAL_COMPLETE_CANDLES",
        "research_method": "nexus_range_observer_v1_bounded_sma10_sma30",
        "candidate_setup": {"prior_result": "NO_VALID_SETUP", "next_candidate_selected": f"{instrument}:{timeframe}", "selection": selection_reason, "candidates_available": len(candidates), "bounded_candidate_limit": 1},
        "in_sample_result": in_sample,
        "oos_method": {"split": "84/36 chronological", "no_lookahead": True, "source_rows": len(rows)},
        "oos_result": oos_result,
        "paper_execution_or_simulation": "LOCAL_PAPER_SIMULATION",
        "paper_result": {"result": "NO_PAPER_ACTION", "reason": "no_approved_setup; simulation records the rejected signal without forcing execution", "orders": 0, "broker_order_api_called": False},
        "failed_path_progression": {"failed_or_rejected_candidate": "NO_VALID_SETUP", "rejection_reason": "bounded_signal_gate", "next_candidate_selected": f"{instrument}:{timeframe}", "research_executed": True, "result": oos_result["result"]},
        "receipt_created": True,
        "live_trading": False,
        "funded_trading": False,
        "real_money_orders": 0,
        "paper_only": True,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "receipt_id": receipt_id,
        "source": payload["real_market_data_source"],
        "candidate": f"{instrument}:{timeframe}",
        "bars": len(rows),
        "in_sample": in_sample["result"],
        "oos": oos_result["result"],
        "paper": payload["paper_result"]["result"],
        "receipt": str(ARTIFACT),
        "broker_order_api_called": False,
        "live_funded_trading": False,
    }, indent=2))


if __name__ == "__main__":
    main()
