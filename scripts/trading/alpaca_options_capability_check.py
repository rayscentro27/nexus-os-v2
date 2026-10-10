#!/usr/bin/env python3
"""Read-only Alpaca paper account/options capability check with Supabase evidence."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/trading"))
from options_data_adapter import AlpacaOptionsData, normalize_snapshot  # noqa: E402

KEYCHAIN_SERVICES = {
    "key": "nexus.alpaca.paper.api_key",
    "secret": "nexus.alpaca.paper.secret_key",
    "endpoint": "nexus.alpaca.paper.endpoint",
}
LIVE_TRADING_ENABLED = False


def _keychain(service: str) -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", service, "-w"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _ssl_context():
    try:
        import certifi
        import ssl
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        import ssl
        return ssl.create_default_context()


def _request(url: str, headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
    try:
        from alpha.alpha_live_research import http_json
        ok, status, payload, error, _latency = http_json("GET", url, headers, timeout=25)
        if ok: return int(status or 200), payload if isinstance(payload, dict) else {}
        return int(status or 0), {"error": error or "GOVERNOR_DENIED"}
    except Exception as exc:  # only the exception class is safe to report
        return 0, {"error": type(exc).__name__}


def _url(base: str, path: str, params: dict[str, Any] | None = None) -> str:
    return base.rstrip("/") + path + (("?" + urllib.parse.urlencode(params)) if params else "")


def _count(payload: dict[str, Any], key: str) -> int:
    values = payload.get(key, {})
    return sum(len(v) for v in values.values()) if isinstance(values, dict) else len(values) if isinstance(values, list) else 0


def _evidence_state(http: int, count: int) -> str:
    if http == 200:
        return "PASS" if count else "PARTIAL"
    if http == 403:
        return "BLOCKED_BY_PLAN"
    if http in {401, 403}:
        return "BLOCKED_BY_AUTH"
    return "NO"


def _load_supabase_env() -> None:
    sys.path.insert(0, str(ROOT / "scripts/ops"))
    from nexus_runtime_env import load_runtime_env
    load_runtime_env()


def _supabase_request(path: str, method: str = "GET", body: Any = None, prefer: str | None = None) -> tuple[int, Any]:
    base = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        raise RuntimeError("SUPABASE_CONFIGURATION_REQUIRED")
    headers = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(base + "/rest/v1/" + path,
        data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35, context=_ssl_context()) as response:
            return response.status, json.loads(response.read().decode() or "[]")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SUPABASE_HTTP_{exc.code}") from None


def _bank_writeback(report: dict[str, Any]) -> bool:
    _load_supabase_env()
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    evidence = {
        "auth_status": "PASS" if report.get("account_access") == "PASS" else "BLOCKED_BY_AUTH",
        "data_mode": "ENABLED" if report.get("chain_read") == "PASS" else "DEGRADED",
        "paper_mode": "ENABLED" if report.get("paper_environment_confirmed") and report.get("account_access") == "PASS" else "OFF",
        "live_mode": "OFF", "live_trading_enabled": False,
        "capabilities": report.get("capabilities", {}),
        "historical": report.get("historical", {}),
        "current_chain_tests": report.get("strategy_checks", {}),
        "account_status": report.get("account_status"),
        "account_options_trading_level": report.get("account_options_trading_level"),
        "paper_account_confirmed_by_endpoint": report.get("paper_environment_confirmed"),
        "last_tested_at": stamp,
        "secrets_persisted": False,
    }
    status = "PASS" if report.get("chain_read") == "PASS" and report.get("account_access") == "PASS" else "DEGRADED"
    data_row = {
        "source_id": "ALPACA_OPTIONS_DATA", "source_or_engine": "Alpaca Options Data",
        "purpose": "Read-only options data; paper account capability only",
        "active_status": "ENABLED", "data_support": "PASS" if report.get("chain_read") == "PASS" else "DEGRADED",
        "option_chain_support": "PASS" if report.get("chain_read") == "PASS" else "NO",
        "greeks_support": report["capabilities"].get("greeks", "NO"),
        "iv_support": report["capabilities"].get("iv", "NO"),
        "historical_options_support": "PARTIAL", "open_interest_support": report["capabilities"].get("open_interest", "NO"),
        "volume_support": report["capabilities"].get("volume", "NO"),
        "paper_trading_support": "AVAILABLE_NOT_EXERCISED" if report.get("account_access") == "PASS" else "NOT_CONFIRMED",
        "multi_leg_support": "CAPABLE_BUT_DISABLED", "live_trading_capability": "CAPABLE_BUT_DISABLED",
        "nexus_tested": True, "nexus_compatibility": status, "use_class": "DATA_AND_PAPER_ONLY",
        "status": status, "last_tested_at": stamp, "evidence": evidence,
    }
    engine_row = {
        "engine_id": "ALPACA_OPTIONS_DATA_READONLY", "source_or_engine": "Alpaca Paper Trading API",
        "purpose": "Paper account read access; no order submission in this certification",
        "active_status": "PAPER_AVAILABLE", "data_support": data_row["data_support"],
        "option_chain_support": data_row["option_chain_support"], "greeks_support": data_row["greeks_support"],
        "iv_support": data_row["iv_support"], "historical_options_support": "PARTIAL",
        "open_interest_support": data_row["open_interest_support"], "volume_support": data_row["volume_support"],
        "paper_trading_support": data_row["paper_trading_support"], "multi_leg_support": "CAPABLE_BUT_DISABLED",
        "live_trading_capability": "CAPABLE_BUT_DISABLED", "order_flow_support": "NO",
        "nexus_tested": True, "nexus_compatibility": status, "use_class": "PAPER_ONLY",
        "status": status, "last_tested_at": stamp, "evidence": evidence,
    }
    for table, row, key in [
        ("options_data_source_bank", data_row, "source_id"),
        ("options_execution_engine_bank", engine_row, "engine_id"),
    ]:
        _supabase_request(f"{table}?on_conflict={key}", "POST", row, "resolution=merge-duplicates,return=representation")
        _, readback = _supabase_request(f"{table}?{key}=eq.{row[key]}&select={key},nexus_tested,status,evidence,last_tested_at")
        if not readback or readback[0].get(key) != row[key] or readback[0].get("nexus_tested") is not True:
            return False
        if readback[0].get("evidence", {}).get("secrets_persisted") is not False:
            return False
    return True


def run() -> dict[str, Any]:
    values = {k: _keychain(s) for k, s in KEYCHAIN_SERVICES.items()}
    endpoint = values["endpoint"]
    parsed = urlparse(endpoint if "://" in endpoint else "https://" + endpoint)
    paper = parsed.hostname == "paper-api.alpaca.markets"
    report: dict[str, Any] = {
        "api_key_present": bool(values["key"]), "secret_key_present": bool(values["secret"]),
        "endpoint_present": bool(endpoint), "paper_environment_confirmed": paper,
        "live_endpoint_detected": parsed.hostname == "api.alpaca.markets",
        "live_trading_enabled": False, "mercury_live_order_authority": False,
        "capabilities": {}, "historical": {}, "strategy_checks": {},
    }
    if not paper:
        report["status"] = "BLOCKED_BY_SAFETY"
        return report
    if not values["key"] or not values["secret"]:
        report["status"] = "BLOCKED_BY_AUTH"
        return report

    account_base = f"{parsed.scheme}://{parsed.netloc}"
    client = AlpacaOptionsData(values["key"], values["secret"], paper_endpoint=account_base)
    ah, account = _request(_url(account_base, "/v2/account"), {
        "APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"],
    })
    report["account_access"] = "PASS" if ah == 200 else "FAIL"
    report["account_status"] = account.get("status") if ah == 200 else None
    report["account_options_trading_level"] = account.get("options_trading_level") if ah == 200 else None
    # Alpaca's account response does not identify paper/live. The validated configured API host is authoritative.
    report["paper_account"] = "YES" if paper and ah == 200 else "NO"
    quote_status, uq = _request(_url("https://data.alpaca.markets", "/v2/stocks/SPY/quotes/latest", {"feed": "iex"}), {
        "APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"],
    })
    underlying_quote = uq.get("quote", {}) if quote_status == 200 else {}
    underlying_price = None
    if underlying_quote.get("bp") is not None and underlying_quote.get("ap") is not None:
        underlying_price = (float(underlying_quote["bp"]) + float(underlying_quote["ap"])) / 2
    report["underlying_quote_read"] = "PASS" if underlying_price is not None else "NO"

    now = dt.date.today()
    contracts_by_underlying: dict[str, list[dict[str, Any]]] = {}
    underlying_prices: dict[str, float | None] = {"SPY": underlying_price}
    for underlying in ("SPY", "CRDO"):
        if underlying != "SPY":
            uq_status, uq_payload = _request(_url("https://data.alpaca.markets", f"/v2/stocks/{underlying}/quotes/latest", {"feed": "iex"}), {
                "APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"],
            })
            q = uq_payload.get("quote", {}) if uq_status == 200 else {}
            underlying_prices[underlying] = (float(q["bp"]) + float(q["ap"])) / 2 if q.get("bp") is not None and q.get("ap") is not None else None
        params = {"underlying_symbols": underlying, "status": "active", "limit": "10000",
                  "expiration_date_gte": now.isoformat(), "expiration_date_lte": (now + dt.timedelta(days=60)).isoformat()}
        cs, payload = _request(_url(account_base, "/v2/options/contracts", params), {
            "APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"],
        })
        contracts_by_underlying[underlying] = payload.get("option_contracts", []) if cs == 200 else []
        report.setdefault("contract_reads", {})[underlying] = "PASS" if cs == 200 and contracts_by_underlying[underlying] else "NO"
        report.setdefault("contract_counts", {})[underlying] = len(contracts_by_underlying[underlying])

    spy_contracts = contracts_by_underlying["SPY"]
    report["strikes_read"] = "PASS" if any(c.get("strike_price") is not None for c in spy_contracts) else "NO"
    report["expirations_read"] = "PASS" if any(c.get("expiration_date") for c in spy_contracts) else "NO"
    report["calls_read"] = "PASS" if any(c.get("type") == "call" for c in spy_contracts) else "NO"
    report["puts_read"] = "PASS" if any(c.get("type") == "put" for c in spy_contracts) else "NO"
    report["contract_detail_read"] = "NO"
    if spy_contracts:
        dh, _ = _request(_url(account_base, "/v2/options/contracts/" + urllib.parse.quote(spy_contracts[0]["symbol"], safe="")), {
            "APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"],
        })
        report["contract_detail_read"] = "PASS" if dh == 200 else "NO"

    # Use the current indicative snapshot feed; OPRA requires an exchange data agreement.
    snapshot_by_underlying: dict[str, dict[str, Any]] = {}
    for underlying, contracts in contracts_by_underlying.items():
        if not contracts:
            snapshot_by_underlying[underlying] = {}
            continue
        spot = underlying_prices.get(underlying)
        today = dt.date.today()
        # Pick an in-window expiration and relevant put/call slices before requesting snapshots.
        put_target = 35 if underlying == "SPY" else 30
        call_target = 20
        def dte_for(c: dict[str, Any]) -> int:
            return (dt.date.fromisoformat(c["expiration_date"]) - today).days
        selected: list[dict[str, Any]] = []
        for typ, low, high, target in (("put", 25, 45, put_target), ("call", 15, 25, call_target)):
            choices = [c for c in contracts if c.get("type") == typ and c.get("expiration_date")
                       and low <= dte_for(c) <= high]
            if choices:
                expiration = min({c["expiration_date"] for c in choices},
                                 key=lambda exp: abs((dt.date.fromisoformat(exp) - today).days - target))
                dated = [c for c in choices if c["expiration_date"] == expiration]
                dated.sort(key=lambda c: abs(float(c.get("strike_price") or 0) - spot) if spot is not None else 0)
                selected.extend(dated[:100])
        subset = list({c["symbol"]: c for c in selected}.values())
        symbols = [x["symbol"] for x in subset if x.get("symbol")]
        try:
            snapshots = client.snapshots(symbols, feed="indicative").get("snapshots", {}) if symbols else {}
        except Exception:
            snapshots = {}
        snapshot_by_underlying[underlying] = snapshots

    spy_snaps = snapshot_by_underlying["SPY"]
    report["chain_read"] = "PASS" if spy_snaps else "NO"
    contract_lookup = {c["symbol"]: c for c in spy_contracts if c.get("symbol")}
    normalized = [normalize_snapshot("SPY", symbol, snap, underlying_price) for symbol, snap in spy_snaps.items()]
    def present(field: str) -> bool:
        return any(item.get(field) is not None for item in normalized)
    for field, label in [("bid", "bid"), ("ask", "ask"), ("last", "last"), ("iv", "iv"),
                         ("delta", "delta"), ("gamma", "gamma"), ("theta", "theta"),
                         ("vega", "vega"), ("volume", "volume")]:
        report["capabilities"][label] = "PASS" if present(field) else "NOT_AVAILABLE_FROM_CURRENT_ENDPOINT"
    # Open interest is not included in snapshot payloads; check real contract metadata.
    report["capabilities"]["open_interest"] = "PASS" if any(c.get("open_interest") is not None for c in spy_contracts) else "NOT_AVAILABLE_FROM_CURRENT_ENDPOINT"
    report["capabilities"]["mid_computable"] = "PASS" if any(x.get("mid") is not None for x in normalized) else "NO"
    report["capabilities"]["execution_feasibility_data"] = "PASS" if report["capabilities"]["mid_computable"] == "PASS" else "NO"
    report["capabilities"]["spread_width"] = next((round(float(x["ask"]) - float(x["bid"]), 4) for x in normalized if x.get("bid") is not None and x.get("ask") is not None), None)
    opra_status, _ = _request(_url("https://data.alpaca.markets", "/v1beta1/options/snapshots", {
        "symbols": next(iter(spy_snaps), ""), "feed": "opra",
    }), {"APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"]}) if spy_snaps else (0, {})
    report["opra_status"] = "AVAILABLE" if opra_status == 200 else "BLOCKED_BY_PLAN" if opra_status == 403 else "NO"

    # Historical fields tested on a specific current contract over a recent closed interval.
    sample_symbol = next(iter(spy_snaps), None)
    if sample_symbol:
        start = (now - dt.timedelta(days=6)).isoformat()
        end = (now - dt.timedelta(days=5)).isoformat()
        for label, path, key, extra in [
            ("bars", "/bars", "bars", {"timeframe": "1Day"}),
            ("trades", "/trades", "trades", {}),
            ("quotes", "/quotes", "quotes", {}),
        ]:
            params = {"symbols": sample_symbol, "start": start, "end": end, "limit": "10", **extra}
            hs, historical = _request(_url("https://data.alpaca.markets", "/v1beta1/options" + path, params), {
                "APCA-API-KEY-ID": values["key"], "APCA-API-SECRET-KEY": values["secret"],
            })
            report["historical"][label] = _evidence_state(hs, _count(historical, key))
            report["historical"].setdefault("http", {})[label] = hs
        report["historical"].update({"chain_reconstruction": "NO", "iv": "NO", "greeks": "NO",
                                     "open_interest": "NO", "volume": report["historical"].get("bars", "NO")})
    else:
        report["historical"] = {k: "NO" for k in ("bars", "trades", "quotes", "chain_reconstruction", "iv", "greeks", "volume", "open_interest")}

    # Current-chain test for the custom multi-leg structure. All legs use one expiration.
    custom: dict[str, Any] = {"status": "NO_MATCHING_CHAIN"}
    if spy_contracts and spy_snaps and underlying_price:
        puts = [c for c in spy_contracts if c.get("type") == "put" and c.get("expiration_date")
                and 25 <= (dt.date.fromisoformat(c["expiration_date"]) - now).days <= 45]
        expiry_counts: dict[str, int] = {}
        for c in puts: expiry_counts[c["expiration_date"]] = expiry_counts.get(c["expiration_date"], 0) + 1
        for expiry in sorted(expiry_counts, key=lambda exp: abs((dt.date.fromisoformat(exp)-now).days-35)):
            dated = sorted((c for c in puts if c["expiration_date"] == expiry), key=lambda c: float(c.get("strike_price") or 0))
            near = sorted(dated, key=lambda c: abs(float(c.get("strike_price") or 0) - underlying_price))
            candidate = None
            for mid in near:
                km = float(mid.get("strike_price") or 0)
                lower = sorted((c for c in dated if 5 <= km - float(c.get("strike_price") or 0) <= 25),
                               key=lambda c: km - float(c.get("strike_price") or 0))
                upper = [c for c in dated if float(c.get("strike_price") or 0) > km]
                for lo in lower:
                    dl = km - float(lo.get("strike_price") or 0)
                    hi = min(upper, key=lambda c: abs((float(c.get("strike_price") or 0) - km) - 2 * dl), default=None)
                    if hi and abs((float(hi.get("strike_price") or 0) - km) - 2 * dl) <= max(1, dl * .2):
                        candidate = [lo, mid, hi]; break
                if candidate: break
            if candidate and all(c["symbol"] in spy_snaps for c in candidate):
                lo, mid, hi = candidate
                legs = [(lo, "BUY", 2), (mid, "SELL", 3), (hi, "BUY", 1)]
                leg_data = []
                net_credit = 0.0
                for contract, side, qty in legs:
                    normalized_leg = normalize_snapshot("SPY", contract["symbol"], spy_snaps[contract["symbol"]], underlying_price)
                    px = normalized_leg.get("mid")
                    if px is None: break
                    net_credit += (1 if side == "SELL" else -1) * qty * float(px)
                    leg_data.append({"side": side, "quantity": qty, "symbol": contract["symbol"], "strike": contract.get("strike_price"), "mid": px,
                                     "bid": normalized_leg.get("bid"), "ask": normalized_leg.get("ask"), "iv": normalized_leg.get("iv"),
                                     "greeks": {g: normalized_leg.get(g) for g in ("delta", "gamma", "theta", "vega")},
                                     "volume": normalized_leg.get("volume"), "open_interest": contract.get("open_interest")})
                if len(leg_data) == 3:
                    custom = {"status": "PASS", "expiration": expiry, "dte": (dt.date.fromisoformat(expiry)-now).days,
                              "legs": leg_data, "net_credit_per_share": round(net_credit, 4),
                              "net_debit_per_share": round(-net_credit, 4), "net_debit_total_per_1x_ratio": round(-net_credit * 100, 2),
                              "net_debit_or_credit": "CREDIT" if net_credit > 0 else "DEBIT" if net_credit < 0 else "EVEN",
                              "indicative_feed": True, "order_placed": False,
                              "execution_feasibility": "PARTIAL_INDICATIVE_QUOTES" if all(x["bid"] is not None and x["ask"] is not None for x in leg_data) else "NO"}
                    break
    report["strategy_checks"]["custom_multi_leg"] = custom

    # Read-only CRDO wheel candidate checks with real current chain data.
    crdo_contracts = contracts_by_underlying["CRDO"]
    crdo_snaps = snapshot_by_underlying["CRDO"]
    wheel: dict[str, Any] = {"status": "NO_MATCHING_CHAIN"}
    if crdo_contracts and crdo_snaps:
        def dte(c: dict[str, Any]) -> int:
            return (dt.date.fromisoformat(c["expiration_date"]) - now).days
        choices = []
        for contract in crdo_contracts:
            symbol = contract.get("symbol")
            snap = crdo_snaps.get(symbol)
            if not snap or not contract.get("expiration_date"):
                continue
            norm = normalize_snapshot("CRDO", symbol, snap)
            if norm.get("mid") is None: continue
            target = 30 if contract.get("type") == "put" else 20
            delta = norm.get("delta")
            score = abs(dte(contract)-target) + (abs(abs(float(delta))-0.25)*100 if delta is not None else 50)
            choices.append((score, contract, norm))
        selected: dict[str, Any] = {}
        for typ in ("put", "call"):
            candidates = [(s,c,n) for s,c,n in choices if c.get("type")==typ and
                          ((25 <= dte(c) <= 35) if typ=="put" else (15 <= dte(c) <= 25))]
            if candidates:
                _, c, n = min(candidates, key=lambda x: x[0])
                selected[typ] = {"symbol": c.get("symbol"), "expiration": c.get("expiration_date"), "dte": dte(c),
                    "strike": c.get("strike_price"), "bid": n.get("bid"), "ask": n.get("ask"), "mid": n.get("mid"),
                    "delta": n.get("delta"), "iv": n.get("iv"), "volume": n.get("volume"),
                    "open_interest": c.get("open_interest"), "capital_required_per_contract":
                        float(c.get("strike_price") or 0)*100 if typ=="put" else (underlying_prices.get("CRDO") or 0)*100,
                    "assignment_exposure": float(c.get("strike_price") or 0)*100 if typ=="put" else "100 shares if assigned"}
        wheel = {"status": "PASS" if selected else "PARTIAL", "selected_candidates": selected,
                 "current_chain_only": True, "historical_profitability_tested": False,
                 "execution_feasibility": "PARTIAL_INDICATIVE_QUOTES" if selected and all(x.get("bid") is not None and x.get("ask") is not None for x in selected.values()) else "PARTIAL",
                 "orders_placed": False}
    report["strategy_checks"]["crdo_wheel"] = wheel
    report["paper_options_order_capability"] = "AVAILABLE_NOT_EXERCISED" if ah == 200 else "NOT_CONFIRMED"
    report["current_paper_validation_ready"] = bool(
        report.get("account_access") == "PASS" and report.get("chain_read") == "PASS"
        and report["capabilities"].get("bid") == "PASS" and report["capabilities"].get("ask") == "PASS"
        and report["capabilities"].get("mid_computable") == "PASS"
        and report["capabilities"].get("iv") == "PASS" and all(report["capabilities"].get(g) == "PASS" for g in ("delta", "gamma", "theta", "vega"))
        and report["capabilities"].get("volume") == "PASS" and report["capabilities"].get("open_interest") == "PASS"
        and report.get("opra_status") == "AVAILABLE"
    )
    report["historical_material_test_ready"] = all(report["historical"].get(k) == "PASS" for k in ("bars", "quotes", "trades", "chain_reconstruction", "iv", "greeks", "volume", "open_interest"))
    report["options_material_test_ready"] = bool(report["current_paper_validation_ready"] and report["historical_material_test_ready"])
    report["status"] = "PASS" if report["account_access"] == "PASS" and report["chain_read"] == "PASS" else "DEGRADED"
    try:
        report["supabase_readback_pass"] = _bank_writeback(report)
    except Exception as exc:
        report["supabase_readback_pass"] = False
        report["supabase_error"] = str(exc) if str(exc).startswith("SUPABASE_HTTP_") else type(exc).__name__
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
