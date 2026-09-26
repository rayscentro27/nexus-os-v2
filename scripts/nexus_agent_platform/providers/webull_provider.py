"""Governed Webull OpenAPI adapter.

This adapter is deliberately limited to authenticated reads and capability
metadata.  It never exposes credential values and never implements an order,
funds, or account-mutation request path.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import ssl
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Mapping

from scripts.nexus_agent_platform import credential_control_plane as credentials


CREDENTIAL_ID = "credential.webull.openapi.prod.v1"
PRODUCTION_BASE_URL = "https://api.webull.com"
SANDBOX_BASE_URL = "https://api.sandbox.webull.com"
API_VERSION = "v3"
SIGNATURE_ALGORITHM = "HMAC-SHA1"
SIGNATURE_VERSION = "1.0"


class WebullProviderError(RuntimeError):
    """Sanitized provider failure; response bodies are intentionally omitted."""

    def __init__(self, error_class: str, message: str, *, http_status: int | None = None, provider_code: str | None = None, provider_message: str | None = None):
        super().__init__(message)
        self.error_class = error_class
        self.http_status = http_status
        self.provider_code = provider_code
        self.provider_message = provider_message

    def receipt(self) -> dict[str, Any]:
        return {
            "provider": "WEBULL",
            "status": "ERROR",
            "error_class": self.error_class,
            "http_status": self.http_status,
            "provider_code": self.provider_code,
            "provider_message": self.provider_message,
            "values_included": False,
        }


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tls_context() -> ssl.SSLContext:
    """Use a verified system/Certifi trust bundle; never disable TLS checks."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def build_signature(
    path: str,
    query_params: Mapping[str, Any],
    body_string: str | None,
    app_key: str,
    app_secret: str,
    host: str,
    timestamp: str,
    nonce: str,
) -> str:
    """Build the official Webull HMAC-SHA1 signature without logging inputs."""
    signing = {
        **{str(key): str(value) for key, value in query_params.items()},
        "host": host,
        "x-app-key": app_key,
        "x-signature-algorithm": SIGNATURE_ALGORITHM,
        "x-signature-nonce": nonce,
        "x-signature-version": SIGNATURE_VERSION,
        "x-timestamp": timestamp,
    }
    pairs = "&".join(f"{key}={signing[key]}" for key in sorted(signing))
    message = f"{path}&{pairs}"
    if body_string:
        message += "&" + hashlib.md5(body_string.encode("utf-8")).hexdigest().upper()
    encoded = urllib.parse.quote(message, safe="")
    return base64.b64encode(
        hmac.new((app_secret + "&").encode("utf-8"), encoded.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")


class WebullProvider:
    """Read-only Webull OpenAPI client with a hard execution boundary."""

    def __init__(self, *, environment: str = "sandbox", timeout: float = 15.0):
        if environment not in {"production", "sandbox"}:
            raise ValueError("environment must be production or sandbox")
        self.environment = environment
        self.base_url = PRODUCTION_BASE_URL if environment == "production" else SANDBOX_BASE_URL
        self.host = urllib.parse.urlsplit(self.base_url).netloc
        self.timeout = timeout

    def _credentials(self) -> tuple[str, str]:
        resolved = credentials.resolve(CREDENTIAL_ID)
        if resolved.get("result") != "AVAILABLE":
            raise WebullProviderError("CREDENTIAL_MISSING", "Webull credential resolver did not find both components")
        credentials.apply_to_process(CREDENTIAL_ID)
        app_key = os.environ.get("WEBULL_APP_KEY")
        app_secret = os.environ.get("WEBULL_APP_SECRET")
        if not app_key or not app_secret:
            raise WebullProviderError("CREDENTIAL_RUNTIME_INACCESSIBLE", "Webull credentials were not available in process memory")
        return app_key, app_secret

    def _request(self, method: str, path: str, *, query_params: Mapping[str, Any] | None = None, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        if method.upper() not in {"GET", "HEAD"}:
            raise WebullProviderError("POLICY_DENIED", "Webull adapter allows read-only HTTP methods only")
        query_params = query_params or {}
        app_key, app_secret = self._credentials()
        timestamp = _utc_timestamp()
        nonce = uuid.uuid4().hex
        body_string = json.dumps(body, separators=(",", ":"), ensure_ascii=False) if body else None
        signature = build_signature(path, query_params, body_string, app_key, app_secret, self.host, timestamp, nonce)
        url = self.base_url + path
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        headers = {
            "accept": "application/json",
            "x-app-key": app_key,
            "x-timestamp": timestamp,
            "x-signature": signature,
            "x-signature-algorithm": SIGNATURE_ALGORITHM,
            "x-signature-version": SIGNATURE_VERSION,
            "x-signature-nonce": nonce,
            "x-version": API_VERSION,
        }
        if body_string:
            headers["content-type"] = "application/json"
        request = urllib.request.Request(url, data=body_string.encode("utf-8") if body_string else None, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=_tls_context()) as response:
                raw = response.read()
                try:
                    return response.status, json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise WebullProviderError("INVALID_PROVIDER_RESPONSE", "Webull returned a non-JSON response", http_status=response.status) from exc
        except urllib.error.HTTPError as exc:
            error_class = {
                401: "AUTH_REJECTED",
                403: "PERMISSION_OR_MARKET_DATA_SUBSCRIPTION",
                408: "PROVIDER_TIMEOUT",
                429: "RATE_LIMITED",
            }.get(exc.code, "PROVIDER_HTTP_ERROR")
            provider_code = None
            provider_message = None
            try:
                error_body = json.loads(exc.read().decode("utf-8", "replace"))
                if isinstance(error_body, dict):
                    provider_code = error_body.get("error_code") or error_body.get("code")
                    provider_message = error_body.get("message") or error_body.get("msg")
            except (UnicodeDecodeError, json.JSONDecodeError, OSError):
                pass
            raise WebullProviderError(error_class, "Webull read request rejected", http_status=exc.code, provider_code=provider_code, provider_message=provider_message) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise WebullProviderError("NETWORK_FAILURE", "Webull read request was not reachable") from exc

    def health(self) -> dict[str, Any]:
        try:
            status, _ = self._request("GET", "/trading/accounts/list")
            return {"provider": "WEBULL", "status": "PASS_REAL", "http_status": status, "values_included": False}
        except WebullProviderError as exc:
            return {**exc.receipt(), "status": "FAIL", "environment": self.environment}

    def capability_discovery(self) -> dict[str, Any]:
        return {
            "provider": "WEBULL",
            "environment": self.environment,
            "market_data": {"snapshot": True, "historical_bars": True, "streaming": "NOT_ENABLED"},
            "account_metadata": "READ_ONLY_ENDPOINT_AVAILABLE",
            "paper_capability": "DISCOVER_ONLY_NOT_EXECUTED",
            "execution": {"place_order": "DENIED", "modify_order": "DENIED", "cancel_order": "DENIED", "funds": "DENIED", "account_mutation": "DENIED", "live_trading": "DENIED"},
            "values_included": False,
        }

    def market_data_snapshot(self, symbol: str = "AAPL") -> dict[str, Any]:
        if not symbol or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for ch in symbol.upper()):
            raise ValueError("invalid symbol")
        status, payload = self._request(
            "GET",
            "/market-data/stocks/snapshots/list",
            query_params={"symbols": symbol.upper(), "category": "US_STOCK", "extend_hour_required": "false", "overnight_required": "false"},
        )
        return {"provider": "WEBULL", "status": "PASS_REAL", "http_status": status, "symbol": symbol.upper(), "payload": payload, "values_included": False}

    def account_metadata(self) -> dict[str, Any]:
        status, payload = self._request("GET", "/trading/accounts/list")
        accounts = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
        return {"provider": "WEBULL", "status": "PASS_REAL", "http_status": status, "account_count": len(accounts), "account_types_present": sorted({str(item.get("account_type")) for item in accounts if isinstance(item, dict) and item.get("account_type")}), "values_included": False}

    def paper_capability(self) -> dict[str, Any]:
        return {"provider": "WEBULL", "status": "DISCOVERY_ONLY", "paper_endpoint": SANDBOX_BASE_URL, "paper_account": "NOT_QUERIED", "paper_order": "NOT_CERTIFIED", "values_included": False}

    # Explicit policy boundary: these methods exist so callers receive a
    # deterministic denial instead of falling through to any future SDK.
    def place_order(self, *_: Any, **__: Any) -> dict[str, Any]:
        raise WebullProviderError("POLICY_DENIED", "Webull live and paper order placement is disabled")

    modify_order = place_order
    cancel_order = place_order
    withdraw = place_order
    deposit = place_order
    transfer = place_order
    live_trade = place_order
    mutate_account_settings = place_order
