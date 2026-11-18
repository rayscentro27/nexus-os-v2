"""Read-only normalized options market-data adapter (Alpaca provider).

No order endpoint exists in this module. Data calls require APCA credentials;
paper trading is reported separately and never invoked automatically.
"""
from __future__ import annotations

import os
import json
import ssl
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from typing import Any, Callable

DATA_BASE = "https://data.alpaca.markets/v1beta1/options"
LIVE_TRADING_ENABLED = False


def normalize_snapshot(underlying: str, option_symbol: str, row: dict[str, Any], underlying_price: float | None = None) -> dict[str, Any]:
    quote = row.get("latestQuote") or row.get("latest_quote") or {}
    trade = row.get("latestTrade") or row.get("latest_trade") or {}
    greeks = row.get("greeks") or {}
    contract = row.get("details") or row.get("contract") or {}
    bid, ask = quote.get("bp", quote.get("bid_price")), quote.get("ap", quote.get("ask_price"))
    mid = ((float(bid) + float(ask)) / 2) if bid is not None and ask is not None else None
    expiry = contract.get("expiration_date") or contract.get("expirationDate")
    dte = (date.fromisoformat(str(expiry)[:10]) - date.today()).days if expiry else None
    daily_bar = row.get("dailyBar") or row.get("daily_bar") or {}
    return {"provider": "ALPACA", "underlying": underlying, "option_symbol": option_symbol,
            "timestamp": quote.get("t") or trade.get("t"), "source_timestamp": quote.get("t") or trade.get("t"),
            "expiration": expiry, "dte": dte, "strike": contract.get("strike_price", contract.get("strikePrice")),
            "call_put": contract.get("type"), "bid": bid, "ask": ask, "mid": mid,
            "last": trade.get("p", trade.get("price")), "iv": row.get("impliedVolatility", row.get("iv")),
            "delta": greeks.get("delta"), "gamma": greeks.get("gamma"), "theta": greeks.get("theta"),
            "vega": greeks.get("vega"), "volume": daily_bar.get("v", daily_bar.get("volume", trade.get("s", trade.get("size")))),
            "open_interest": contract.get("open_interest", contract.get("openInterest")),
            "underlying_price": underlying_price,
            "quality_flags": [k for k, v in {"MISSING_BID": bid is None, "MISSING_ASK": ask is None,
                            "MISSING_IV": row.get("impliedVolatility", row.get("iv")) is None,
                            "MISSING_GREEKS": not greeks, "MISSING_VOLUME": trade.get("s", trade.get("size")) is None,
                            "MISSING_OPEN_INTEREST": contract.get("open_interest", contract.get("openInterest")) is None}.items() if v]}


class AlpacaOptionsData:
    def __init__(self, key: str | None = None, secret: str | None = None, transport: Callable[..., Any] | None = None,
                 paper_endpoint: str = "https://paper-api.alpaca.markets"):
        self.key = key or os.getenv("APCA_API_KEY_ID")
        self.secret = secret or os.getenv("APCA_API_SECRET_KEY")
        self.paper_endpoint = paper_endpoint.rstrip("/")
        self.transport = transport or self._get

    @property
    def configured(self) -> bool:
        return bool(self.key and self.secret)

    def _get(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        try:
            from alpha.alpha_live_research import http_json
            ok, _status, payload, error, _latency = http_json("GET", url, headers, timeout=20)
            if not ok: raise RuntimeError(error or "ALPACA_GOVERNOR_DENIED")
            return payload if isinstance(payload, dict) else {}
        except Exception:
            raise

    def _read(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("ALPACA_OPTIONS_CREDENTIALS_NOT_CONFIGURED")
        url = DATA_BASE + path + "?" + urllib.parse.urlencode(params)
        return self.transport(url, {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret})

    def chain(self, underlying: str, *, feed: str = "indicative", limit: int = 100) -> dict[str, Any]:
        if feed not in {"indicative", "opra"}:
            raise ValueError("UNSUPPORTED_OPTIONS_FEED")
        return self._read("/snapshots/" + urllib.parse.quote(underlying, safe=""), {"feed": feed, "limit": str(limit)})

    def snapshots(self, symbols: list[str], *, feed: str = "indicative") -> dict[str, Any]:
        if feed not in {"indicative", "opra"}:
            raise ValueError("UNSUPPORTED_OPTIONS_FEED")
        return self._read("/snapshots", {"symbols": ",".join(symbols[:100]), "feed": feed})

    def contracts(self, underlying: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = {"underlying_symbols": underlying, "status": "active", **(params or {})}
        return self._trading_get("/v2/options/contracts", query)

    def contract(self, symbol: str) -> dict[str, Any]:
        return self._trading_get("/v2/options/contracts/" + urllib.parse.quote(symbol, safe=""), {})

    def underlying_quote(self, symbol: str, *, feed: str = "iex") -> dict[str, Any]:
        return self._market_get("/v2/stocks/" + urllib.parse.quote(symbol, safe="") + "/quotes/latest", {"feed": feed})

    def _trading_get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self._get_json(self.paper_endpoint + path, params)

    def _market_get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self._get_json("https://data.alpaca.markets" + path, params)

    def _get_json(self, base: str, params: dict[str, str]) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("ALPACA_OPTIONS_CREDENTIALS_NOT_CONFIGURED")
        url = base + ("?" + urllib.parse.urlencode(params) if params else "")
        return self.transport(url, {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret})

    def historical_quotes(self, symbols: list[str], start: str, end: str, *, feed: str = "indicative") -> dict[str, Any]:
        return self._read("/quotes", {"symbols": ",".join(symbols[:100]), "start": start, "end": end, "feed": feed})

    def historical_bars(self, symbols: list[str], start: str, end: str, timeframe: str = "1Day", *, feed: str = "indicative") -> dict[str, Any]:
        return self._read("/bars", {"symbols": ",".join(symbols[:100]), "start": start, "end": end, "timeframe": timeframe})

    def historical_trades(self, symbols: list[str], start: str, end: str, *, feed: str = "indicative") -> dict[str, Any]:
        return self._read("/trades", {"symbols": ",".join(symbols[:100]), "start": start, "end": end})


def material_test_gate(*, adapter: bool, chain: bool, bid_ask: bool, iv: bool, greeks: bool, liquidity: bool,
                       execution_feasibility: bool, historical_data: bool = False) -> dict[str, Any]:
    missing = [name for name, value in (("OPTIONS_DATA_ADAPTER_PASS", adapter), ("CURRENT_CHAIN_READ_PASS", chain),
              ("BID_ASK_PASS", bid_ask), ("IV_OR_VOLATILITY_DATA_PASS", iv), ("GREEKS_PASS", greeks),
              ("LIQUIDITY_DATA_PASS", liquidity), ("EXECUTION_FEASIBILITY_PASS", execution_feasibility),
              ("HISTORICAL_DATA_SUFFICIENT", historical_data)) if not value]
    return {"options_material_test_ready": not missing, "missing_capabilities": missing,
            "live_trading_enabled": False}
