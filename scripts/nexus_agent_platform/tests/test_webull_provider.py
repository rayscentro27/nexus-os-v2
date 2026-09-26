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
