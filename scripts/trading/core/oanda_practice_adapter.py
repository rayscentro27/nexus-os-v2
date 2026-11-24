"""OANDA Practice execution adapter (Trading Core R1).

Wraps the existing certified transport ``scripts/trading/oanda_demo_common.py``
(practice host constant, live-endpoint detection, governed HTTP). Adds the
Trading execution contract: practice-only enforcement, bounded units, broker
idempotency via clientExtensions.id, sanitized errors, and a receipt for every
broker action. Credentials and the full account id are never returned.
"""
from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/trading
import oanda_demo_common as transport  # noqa: E402

BROKER = "OANDA_PRACTICE"
PRACTICE_HOST = "https://api-fxpractice.oanda.com"
ADAPTER_HARD_MAX_UNITS = 1  # R1 ceiling; the risk policy may only be tighter
ORDER_TAG = "NEXUS_TRADING_CORE_R1"


class LiveEndpointBlocked(RuntimeError):
    pass


class AdapterRefused(RuntimeError):
    pass


RequestFn = Callable[..., tuple[bool, int | None, dict, str | None]]


def _sanitize(error: str | None) -> str | None:
    if not error:
        return None
    text = str(error)
    if any(s in text.lower() for s in ("bearer", "authorization", "token")):
        return "SANITIZED_AUTH_ERROR"
    return text[:120]


class OandaPracticeAdapter:
    def __init__(self, request_fn: RequestFn | None = None, environment_fn: Callable[[], dict] | None = None) -> None:
        self._request = request_fn or transport.request
        self._environment = environment_fn or transport.environment
        if transport.PRACTICE_HOST != PRACTICE_HOST or "fxtrade" in transport.PRACTICE_HOST:
            raise LiveEndpointBlocked("transport_host_not_practice")
        env = self._environment()
        if env.get("live_endpoint_configured"):
            raise LiveEndpointBlocked("live_endpoint_configured_in_environment")
        self.host = PRACTICE_HOST

    # ---- helpers -------------------------------------------------------
    def _acct(self, suffix: str = "") -> str:
        account = urllib.parse.quote(self._environment()["account_id"], safe="")
        return f"/v3/accounts/{account}{suffix}"

    def _call(self, method: str, path: str, payload: dict | None = None, query: dict | None = None) -> tuple[bool, int | None, dict, str | None]:
        ok, status, data, error = self._request(method, path, payload, query)
        return bool(ok), status, data if isinstance(data, dict) else {}, _sanitize(error)

    @staticmethod
    def _require_practice(environment: str) -> None:
        if str(environment).upper() != "PRACTICE":
            raise LiveEndpointBlocked(f"environment_{environment}_blocked")

    # ---- read contract -------------------------------------------------
    def health_check(self, instrument: str = "EUR_USD") -> dict[str, Any]:
        env = self._environment()
        if not env.get("token_present") or not env.get("account_id_present"):
            return {"healthy": False, "broker": BROKER, "host": self.host, "health_reason": "credentials_missing"}
        acct = self.get_account_state()
        price = self.get_pricing(instrument)
        healthy = acct["ok"] and price["ok"] and bool(price.get("tradeable"))
        reason = "ok" if healthy else ("account_unreachable" if not acct["ok"] else "pricing_unavailable_or_not_tradeable")
        return {"healthy": healthy, "broker": BROKER, "host": self.host, "health_reason": reason,
                "account": acct, "pricing": price, "live_endpoint_configured": bool(env.get("live_endpoint_configured"))}

    def get_account_state(self) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct("/summary"))
        a = data.get("account") or {}
        keys = ("currency", "balance", "NAV", "unrealizedPL", "marginUsed", "openTradeCount", "openPositionCount", "pendingOrderCount")
        return {"ok": ok, "http_status": status, "error": error, "account_id_masked": transport.mask(self._environment().get("account_id")),
                **{k: a.get(k) for k in keys}}

    def get_pricing(self, instrument: str) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct("/pricing"), query={"instruments": instrument})
        row = (data.get("prices") or [{}])[0]
        bid = (row.get("bids") or [{}])[0].get("price"); ask = (row.get("asks") or [{}])[0].get("price")
        return {"ok": ok and bid is not None and ask is not None, "http_status": status, "error": error, "instrument": row.get("instrument"),
                "bid": float(bid) if bid else None, "ask": float(ask) if ask else None, "time": row.get("time"),
                "tradeable": row.get("tradeable"), "status": row.get("status")}

    def get_instrument(self, instrument: str) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct("/instruments"), query={"instruments": instrument})
        row = (data.get("instruments") or [{}])[0]
        return {"ok": ok and row.get("name") == instrument, "http_status": status, "error": error, "name": row.get("name"),
                "type": row.get("type"), "pip_location": row.get("pipLocation"), "minimum_trade_size": row.get("minimumTradeSize"),
                "display_precision": row.get("displayPrecision")}

    def get_candles(self, instrument: str, granularity: str, count: int = 500) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", f"/v3/instruments/{urllib.parse.quote(instrument)}/candles",
                                             query={"price": "M", "granularity": granularity, "count": int(count)})
        return {"ok": ok, "http_status": status, "error": error, "candles": data.get("candles") or []}

    def get_open_trades(self) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct("/openTrades"))
        trades = []
        for t in data.get("trades") or []:
            ext = t.get("clientExtensions") or {}
            trades.append({"trade_id": t.get("id"), "instrument": t.get("instrument"), "units": float(t.get("currentUnits") or 0),
                           "price": float(t.get("price") or 0), "open_time": t.get("openTime"), "client_id": ext.get("id"),
                           "tag": ext.get("tag"), "unrealized_pl": t.get("unrealizedPL"),
                           "stop_loss": (t.get("stopLossOrder") or {}).get("price"), "take_profit": (t.get("takeProfitOrder") or {}).get("price")})
        return {"ok": ok, "http_status": status, "error": error, "trades": trades}

    def get_open_positions(self) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct("/openPositions"))
        rows = [{"instrument": p.get("instrument"), "long_units": (p.get("long") or {}).get("units"), "short_units": (p.get("short") or {}).get("units"),
                 "unrealized_pl": p.get("unrealizedPL")} for p in data.get("positions") or []]
        return {"ok": ok, "http_status": status, "error": error, "positions": rows}

    def get_order(self, order_specifier: str) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct(f"/orders/{urllib.parse.quote(order_specifier, safe='@')}"))
        o = data.get("order") or {}
        return {"ok": ok, "http_status": status, "error": error, "exists": bool(o), "order_id": o.get("id"), "state": o.get("state"),
                "filling_transaction_id": o.get("fillingTransactionID"), "trade_opened_id": o.get("tradeOpenedID"),
                "client_id": (o.get("clientExtensions") or {}).get("id")}

    def get_trade(self, trade_id: str) -> dict[str, Any]:
        ok, status, data, error = self._call("GET", self._acct(f"/trades/{urllib.parse.quote(str(trade_id), safe='')}"))
        t = data.get("trade") or {}
        return {"ok": ok, "http_status": status, "error": error, "trade_id": t.get("id"), "state": t.get("state"),
                "instrument": t.get("instrument"), "initial_units": t.get("initialUnits"), "current_units": t.get("currentUnits"),
                "price": t.get("price"), "average_close_price": t.get("averageClosePrice"), "realized_pl": t.get("realizedPL"),
                "financing": t.get("financing"), "close_time": t.get("closeTime"), "open_time": t.get("openTime")}

    # ---- write contract ------------------------------------------------
    def submit_paper_order(self, req: dict[str, Any]) -> dict[str, Any]:
        """req: environment, instrument, units (signed int), client_id, signal_id, stop_price, target_price."""
        self._require_practice(req.get("environment", ""))
        units = int(req["units"])
        if units == 0 or abs(units) > ADAPTER_HARD_MAX_UNITS:
            raise AdapterRefused(f"units_out_of_bounds:{units}")
        client_id = str(req["client_id"])
        if not client_id or len(client_id) > 128:
            raise AdapterRefused("bad_idempotency_key")
        receipt: dict[str, Any] = {"action": "SUBMIT_PAPER_ORDER", "broker": BROKER, "host": self.host, "idempotency_key": client_id,
                                   "instrument": req["instrument"], "units": units, "live_endpoint_used": False}
        prior = self.get_order(f"@{client_id}")
        if not prior["exists"] and prior["http_status"] != 404:
            # Cannot prove the key is unused -> do not risk a duplicate submit.
            return {**receipt, "ok": False, "idempotent_replay": False, "http_status": prior["http_status"],
                    "error": f"idempotency_precheck_unverified:{prior['error']}"}
        if prior["exists"]:
            return {**receipt, "ok": True, "idempotent_replay": True, "http_status": prior["http_status"], "order_id": prior["order_id"],
                    "trade_id": prior["trade_opened_id"], "fill_transaction_id": prior["filling_transaction_id"], "order_state": prior["state"]}
        ext = {"id": client_id, "tag": ORDER_TAG, "comment": f"signal {req.get('signal_id', '')}"[:120]}
        order: dict[str, Any] = {"type": "MARKET", "instrument": req["instrument"], "units": str(units), "timeInForce": "FOK",
                                 "positionFill": "DEFAULT", "clientExtensions": ext, "tradeClientExtensions": ext}
        if req.get("stop_price") is not None:
            order["stopLossOnFill"] = {"price": f"{float(req['stop_price']):.5f}", "timeInForce": "GTC"}
        if req.get("target_price") is not None:
            order["takeProfitOnFill"] = {"price": f"{float(req['target_price']):.5f}", "timeInForce": "GTC"}
        ok, status, data, error = self._call("POST", self._acct("/orders"), {"order": order})
        create = data.get("orderCreateTransaction") or {}
        fill = data.get("orderFillTransaction") or {}
        cancel = data.get("orderCancelTransaction") or {}
        reject = data.get("orderRejectTransaction") or {}
        opened = fill.get("tradeOpened") or {}
        return {**receipt, "ok": ok and bool(opened), "idempotent_replay": False, "http_status": status, "error": error,
                "order_id": create.get("id") or reject.get("id"), "fill_transaction_id": fill.get("id"), "trade_id": opened.get("tradeID"),
                "fill_price": float(fill["price"]) if fill.get("price") else None, "fill_time": fill.get("time"),
                "units_filled": opened.get("units"), "half_spread_cost": opened.get("halfSpreadCost") or fill.get("halfSpreadCost"),
                "commission": fill.get("commission"), "cancel_reason": cancel.get("reason"), "reject_reason": reject.get("rejectReason"),
                "last_transaction_id": data.get("lastTransactionID")}

    def close_paper_position(self, trade_id: str, environment: str = "PRACTICE") -> dict[str, Any]:
        self._require_practice(environment)
        ok, status, data, error = self._call("PUT", self._acct(f"/trades/{urllib.parse.quote(str(trade_id), safe='')}/close"), {"units": "ALL"})
        fill = data.get("orderFillTransaction") or {}
        closed = (fill.get("tradesClosed") or [{}])[0]
        return {"action": "CLOSE_PAPER_POSITION", "broker": BROKER, "host": self.host, "trade_id": str(trade_id), "ok": ok and bool(fill),
                "http_status": status, "error": error, "close_transaction_id": fill.get("id"), "close_order_id": fill.get("orderID"),
                "exit_price": float(fill["price"]) if fill.get("price") else None, "exit_time": fill.get("time"),
                "realized_pl": closed.get("realizedPL") or fill.get("pl"), "financing": closed.get("financing") or fill.get("financing"),
                "half_spread_cost": closed.get("halfSpreadCost") or fill.get("halfSpreadCost"), "commission": fill.get("commission"),
                "reject_reason": (data.get("orderRejectTransaction") or {}).get("rejectReason"), "live_endpoint_used": False}
