#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import RUNTIME, now, parse_env, read_json  # noqa: E402

PRACTICE_HOST = "https://api-fxpractice.oanda.com"
LIVE_HOST = "https://api-fxtrade.oanda.com"
LOCAL_RUNTIME = ROOT / ".oanda_demo_runtime"


def environment() -> dict:
    values = dict(os.environ)
    for path in (ROOT / ".env", ROOT / ".env.local", ROOT / ".env.nexus.recovered.local", Path.home() / "nexuslive/.env"):
        values.update(parse_env(path))
    token = values.get("OANDA_API_KEY") or values.get("OANDA_ACCESS_TOKEN") or ""
    account_id = values.get("OANDA_ACCOUNT_ID") or ""
    configured = " ".join(values.get(key, "") for key in ("OANDA_API_HOST", "OANDA_API_URL", "OANDA_ENVIRONMENT")).lower()
    live_toggle = any(values.get(key, "").strip().lower() in {"1", "true", "yes", "enabled", "live"} for key in ("LIVE_TRADING", "TRADING_LIVE"))
    live_configured = LIVE_HOST in configured or "fxtrade" in configured or values.get("OANDA_ENVIRONMENT", "").lower() == "live" or live_toggle
    return {"token": token, "account_id": account_id, "token_present": bool(token), "account_id_present": bool(account_id), "live_endpoint_configured": live_configured, "host": PRACTICE_HOST}


def context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def request(method: str, path: str, payload: dict | None = None, query: dict | None = None) -> tuple[bool, int | None, dict, str | None]:
    env = environment()
    if env["live_endpoint_configured"]:
        return False, None, {}, "live_endpoint_detected_blocked"
    if not env["token"] or not env["account_id"]:
        return False, None, {}, "credentials_missing"
    url = f"{PRACTICE_HOST}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {env['token']}", "Accept-Datetime-Format": "RFC3339", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25, context=context()) as response:
            return True, response.status, json.loads(response.read().decode() or "{}"), None
    except urllib.error.HTTPError as exc:
        return False, exc.code, {}, f"HTTP_{exc.code}"
    except Exception as exc:
        return False, None, {}, exc.__class__.__name__


def account_path(suffix: str = "") -> str:
    account = urllib.parse.quote(environment()["account_id"], safe="")
    return f"/v3/accounts/{account}{suffix}"


def mask(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:3]}***{value[-2:]}" if len(value) > 6 else "***"


def gates() -> dict:
    return {
        "account": read_json(RUNTIME / "oanda_demo_account_check_latest.json", {}).get("ok", False),
        "pricing": read_json(RUNTIME / "oanda_demo_pricing_check_latest.json", {}).get("ok", False),
        "instruments": read_json(RUNTIME / "oanda_demo_instruments_check_latest.json", {}).get("ok", False),
        "live_endpoint_blocked": not environment()["live_endpoint_configured"],
    }


def save_local(name: str, payload: dict) -> None:
    LOCAL_RUNTIME.mkdir(parents=True, exist_ok=True)
    (LOCAL_RUNTIME / f"{name}.local.json").write_text(json.dumps(payload, indent=2) + "\n")


def load_local(name: str) -> dict:
    try:
        return json.loads((LOCAL_RUNTIME / f"{name}.local.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def select_clear_instrument(preferred: str = "AUD_USD") -> tuple[str | None, list[str]]:
    instrument_report = read_json(RUNTIME / "oanda_demo_instruments_check_latest.json", {})
    available = instrument_report.get("safe_major_instruments", [])
    ok, _, data, _ = request("GET", account_path("/openPositions"))
    exposed = {row.get("instrument") for row in data.get("positions", []) if row.get("instrument")} if ok else set()
    order = [preferred, "EUR_USD", "GBP_USD", "USD_CAD", "NZD_USD"]
    for instrument in order:
        if instrument in available and instrument not in exposed:
            return instrument, sorted(exposed)
    return None, sorted(exposed)


def execute_smoke(tag: str, preferred: str, units: int = 1, runtime_name: str = "oanda_demo_smoke") -> dict:
    current_gates = gates()
    if not all(current_gates.values()) or abs(units) != 1:
        return {"ok": False, "status": "smoke_gate_failed", "gates": current_gates, "demo_order_placed": False, "closed": False, "error": "verification_gate_or_units_failed"}
    instrument, existing = select_clear_instrument(preferred)
    if not instrument:
        return {"ok": False, "status": "no_clear_major_instrument", "gates": current_gates, "demo_order_placed": False, "closed": False, "existing_position_instruments": existing}
    payload = {"order": {"type": "MARKET", "instrument": instrument, "units": str(units), "timeInForce": "FOK", "positionFill": "DEFAULT", "clientExtensions": {"tag": tag, "comment": tag}}}
    ok, status_code, data, error = request("POST", account_path("/orders"), payload)
    fill = data.get("orderFillTransaction") or {}
    trade_id = str((fill.get("tradeOpened") or {}).get("tradeID") or "")
    order_id = str((data.get("orderCreateTransaction") or {}).get("id") or "")
    placed = bool(ok and (trade_id or fill))
    closed = False; close_code = None; close_error = None
    if trade_id:
        close_ok, close_code, _, close_error = request("PUT", account_path(f"/trades/{urllib.parse.quote(trade_id, safe='')}/close"), {"units": "ALL"})
        closed = close_ok
    elif order_id and ok:
        close_ok, close_code, _, close_error = request("PUT", account_path(f"/orders/{urllib.parse.quote(order_id, safe='')}/cancel"), {})
        closed = close_ok
    local = {"generated_at": now(), "tag": tag, "instrument": instrument, "units": units, "trade_id": trade_id, "order_id": order_id, "placed": placed, "closed": closed, "open_status_code": status_code, "close_status_code": close_code}
    save_local(runtime_name, local)
    return {"ok": placed and closed, "status": "demo_smoke_placed_and_closed" if placed and closed else "demo_smoke_close_failed" if placed else "demo_smoke_order_failed", "gates": current_gates, "instrument": instrument, "requested_instrument": preferred, "instrument_substituted": instrument != preferred, "units": units, "demo_order_placed": placed, "closed": closed, "open_http_status": status_code, "close_http_status": close_code, "order_id_masked": mask(order_id), "trade_id_masked": mask(trade_id), "error_sanitized": error or close_error, "live_endpoint_used": False, "real_money_trade": False, "tag": tag}
