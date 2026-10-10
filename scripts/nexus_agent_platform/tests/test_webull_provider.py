import base64
import hashlib
import hmac
import urllib.parse

import pytest

from scripts.nexus_agent_platform.providers.webull_provider import (
    WebullProvider,
    WebullProviderError,
    build_signature,
)


def test_official_signature_fixture():
    signature = build_signature(
        "/trade/place_order",
        {"a1": "webull", "a2": "123", "a3": "xxx", "q1": "yyy"},
        '{"k1":123,"k2":"this is the api request body","k3":true,"k4":{"foo":[1,2]}}',
        "776da210ab4a452795d74e726ebd74b6",
        "0f50a2e853334a9aae1a783bee120c1f",
        "api.webull.com",
        "2022-01-04T03:55:31Z",
        "48ef5afed43d4d91ae514aaeafbc29ba",
    )
    assert signature == "kvlS6opdZDhEBo5jq40nHYXaLvM="


def test_capability_discovery_denies_execution():
    capability = WebullProvider().capability_discovery()
    assert capability["execution"]["live_trading"] == "DENIED"
    assert capability["execution"]["place_order"] == "DENIED"
    assert capability["values_included"] is False
    assert capability["market_data"]["snapshot"] == "ADAPTER_IMPLEMENTED"
    assert capability["market_data"]["historical_bars"] == {
        "provider_api": "DOCUMENTED",
        "adapter": "READ_ONLY_METHOD_AVAILABLE",
        "entitlement": "UNVERIFIED",
    }


def test_historical_bars_uses_bounded_read_only_get(monkeypatch):
    provider = WebullProvider(environment="sandbox")
    captured = {}

    def fake_request(method, path, *, query_params=None, body=None):
        captured.update({"method": method, "path": path, "query": query_params, "body": body})
        return 200, {"data": [{"open": "1", "volume": "10"}]}

    monkeypatch.setattr(provider, "_request", fake_request)
    result = provider.historical_bars("tsla", "m30", 300)
    assert captured == {"method": "GET", "path": "/market-data/stocks/bars/get",
                        "query": {"symbol": "TSLA", "category": "US_STOCK", "interval": "M30", "count": "300"},
                        "body": None}
    assert result["http_status"] == 200
    assert result["interval"] == "M30"


@pytest.mark.parametrize("symbol,interval,count", [("", "M30", 5), ("TSLA", "M3", 5), ("TSLA", "M30", 1201)])
def test_historical_bars_rejects_invalid_requests(symbol, interval, count):
    with pytest.raises(ValueError):
        WebullProvider().historical_bars(symbol, interval, count)


def test_execution_methods_are_hard_denied():
    provider = WebullProvider()
    with pytest.raises(WebullProviderError, match="disabled"):
        provider.place_order({"symbol": "AAPL"})
    with pytest.raises(WebullProviderError, match="disabled"):
        provider.cancel_order("order-id")


def test_non_read_method_is_denied_before_network():
    provider = WebullProvider()
    with pytest.raises(WebullProviderError, match="read-only"):
        provider._request("POST", "/trading/orders/place", body={})
