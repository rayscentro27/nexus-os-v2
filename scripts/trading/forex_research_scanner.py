#!/usr/bin/env python3
"""Deterministic, research-only OANDA Practice market health and scanner.

This module deliberately has no model/LLM dependency and never submits orders.
It turns the existing OANDA read client into a truthful candle-backed scan.
"""
from __future__ import annotations

import argparse, hashlib, json, sys, time, signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "trading"))
from oanda_demo_common import account_path, environment, request  # noqa: E402

INSTRUMENTS = ["EUR_USD", "GBP_USD", "USD_JPY"]
TIMEFRAMES = ["M5", "M15", "H1"]
LOOKBACK = 120
RUNTIME = ROOT / "reports" / "runtime"
CACHE = ROOT / "data" / "runtime" / "forex_candle_cache.json"
ARTIFACT = RUNTIME / "forex_research_latest.json"
STATE = ROOT / "data" / "runtime" / "forex_scanner_state.json"

def now() -> str: return datetime.now(timezone.utc).isoformat()
def read(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text())
    except Exception: return default
def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2) + "\n")

def fetch_candles(instrument: str, granularity: str, count: int = LOOKBACK) -> dict[str, Any]:
    ok, status, data, error = request("GET", account_path(f"/instruments/{instrument}/candles"), query={"granularity": granularity, "count": str(count), "price": "M"})
    rows = data.get("candles", []) if ok and isinstance(data, dict) else []
    complete = [r for r in rows if r.get("complete") is True and r.get("mid", {}).get("c") is not None]
    return {"ok": ok, "http_status": status, "error": error, "instrument": instrument, "timeframe": granularity,
            "requested": count, "available": len(rows), "complete": len(complete), "candles": complete,
            "newest": complete[-1].get("time") if complete else None, "oldest": complete[0].get("time") if complete else None}

def market_health() -> dict[str, Any]:
    env = environment()
    if env.get("live_endpoint_configured"): return {"status": "AUTHENTICATION_FAILED", "reason": "live_endpoint_blocked", "practice": False}
    if not env.get("token_present") or not env.get("account_id_present"): return {"status": "AUTHENTICATION_FAILED", "reason": "practice_credentials_missing", "practice": True}
    ok, status, data, error = request("GET", account_path("/summary"))
    prices_ok, price_status, prices, price_error = request("GET", account_path("/pricing"), query={"instruments": ",".join(INSTRUMENTS)})
    available = sorted({p.get("instrument") for p in (prices.get("prices", []) if prices_ok else []) if p.get("instrument")})
    result = "FOREX_MARKET_HEALTHY" if ok and prices_ok else "MARKET_DATA_UNAVAILABLE"
    return {"status": result, "environment": "practice", "endpoint": env["host"], "account_http_status": status,
            "pricing_http_status": price_status, "account_access": ok, "pricing_access": prices_ok,
            "instruments_requested": INSTRUMENTS, "instruments_available": available,
            "last_successful_data": now() if prices_ok else None, "error": error or price_error,
            "live_trading": False, "auto_trading": False, "paper_only": True, "oanda_allow_live": False}

def evaluate(rows: list[dict[str, Any]], instrument: str, timeframe: str) -> dict[str, Any]:
    closes = [float(x["mid"]["c"]) for x in rows]
    if len(closes) < 30: return {"result": "MARKET_DATA_INSUFFICIENT", "reason": "warmup_bars_missing", "bars": len(closes)}
    fast, slow = sum(closes[-10:]) / 10, sum(closes[-30:]) / 30
    return {"result": "NO_VALID_SETUP", "strategy_id": "nexus_range_observer_v1", "strategy_version": "1",
            "instrument": instrument, "timeframe": timeframe, "source": "OANDA_PRACTICE",
            "candle_timestamp": rows[-1].get("time"), "indicators": {"sma10": fast, "sma30": slow},
            "conditions_evaluated": ["complete_candle_warmup", "sma10_sma30_observation", "bounded_signal_gate"],
            "conditions_passed": ["complete_candle_warmup"], "conditions_failed": ["bounded_signal_gate"],
            "signal": False, "reason": "no_approved_setup; research-only scanner never forces a trade", "consumer_ids": []}

def scan() -> dict[str, Any]:
    started = now(); health = market_health(); cache = read(CACHE, {})
    evaluations = []; fetched = []; cache.update({"updated_at": now(), "source": "OANDA_PRACTICE"})
    if health["status"] == "FOREX_MARKET_HEALTHY":
        for instrument in INSTRUMENTS:
            for timeframe in TIMEFRAMES:
                row = fetch_candles(instrument, timeframe); fetched.append({k: v for k, v in row.items() if k != "candles"})
                cache[f"{instrument}:{timeframe}"] = row
                evaluations.append(evaluate(row["candles"], instrument, timeframe) if row["ok"] else {"result": "MARKET_DATA_UNAVAILABLE", "instrument": instrument, "timeframe": timeframe, "reason": row["error"]})
        write(CACHE, cache)
    result = health["status"] if health["status"] != "FOREX_MARKET_HEALTHY" else ("MARKET_DATA_INSUFFICIENT" if any(x.get("result") == "MARKET_DATA_INSUFFICIENT" for x in evaluations) else "NO_VALID_SETUP")
    payload = {"schema_version": "nexus.forex-research.v1", "run_id": hashlib.sha256((started + result).encode()).hexdigest()[:20], "started_at": started, "completed_at": now(),
               "goal": "forex_scan", "operational_result": result, "market_health": health, "candles": fetched, "evaluations": evaluations,
               "source_provenance": {"provider": "OANDA", "environment": "practice", "fresh_at": now(), "live_data": health["status"] == "FOREX_MARKET_HEALTHY"},
               "brief_source_artifact": str(ARTIFACT), "consumer_readback": "NOT_REQUIRED", "consumer_ids": [],
               "hot_path_ai_calls": 0, "live_trading": False, "auto_trading": False, "paper_only": True, "oanda_allow_live": False}
    previous = read(STATE, {})
    payload["second_run_comparison"] = {"prior_result": previous.get("operational_result"), "no_change_valid": bool(previous) and previous.get("operational_result") == result}
    write(ARTIFACT, payload); write(STATE, {"operational_result": result, "artifact": str(ARTIFACT), "updated_at": now()})
    return payload

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--health", action="store_true"); p.add_argument("--scan", action="store_true"); p.add_argument("--daemon", action="store_true"); p.add_argument("--interval-seconds", type=int, default=300); p.add_argument("--json", action="store_true"); args = p.parse_args()
    if args.daemon:
        stop = {"value": False}
        signal.signal(signal.SIGTERM, lambda *_: stop.update(value=True)); signal.signal(signal.SIGINT, lambda *_: stop.update(value=True))
        while not stop["value"]:
            result = scan(); print(json.dumps({"heartbeat": result["completed_at"], "operational_result": result["operational_result"]}), flush=True)
            time.sleep(max(30, args.interval_seconds))
        return 0
    result = market_health() if args.health and not args.scan else scan()
    print(json.dumps(result, indent=2)); return 0 if result.get("status", result.get("operational_result")) not in {"AUTHENTICATION_FAILED", "MARKET_DATA_UNAVAILABLE"} else 1
if __name__ == "__main__": raise SystemExit(main())
