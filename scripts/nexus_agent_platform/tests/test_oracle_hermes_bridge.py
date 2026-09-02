from scripts.nexus_agent_platform.bridge.oracle_hermes import BridgeRequest, OracleHermesBridge


def request(**kwargs):
    return BridgeRequest(request_type="classify_request", purpose="synthetic certification",
                         safe_context=kwargs.pop("safe_context", {"state": "SAFE_SYNTHETIC"}),
                         **kwargs)


def test_success_is_correlated_and_advisory():
    seen = {}

    def transport(method, path, payload, headers, timeout):
        seen.update(method=method, path=path, payload=payload, headers=headers, timeout=timeout)
        return {"id": "resp-1", "model": "synthetic", "choices": [{"message": {"content": "advice"}}]}

    bridge = OracleHermesBridge("http://127.0.0.1:18642", api_key="test", transport=transport)
    response = bridge.ask(request())
    assert response.status == "SUCCEEDED"
    assert response.request_id in seen["headers"]["X-Nexus-Request-Id"]
    assert response.warnings == ["ADVISORY_ONLY"]
    assert seen["path"] == "/v1/chat/completions"
    assert seen["payload"]["max_tokens"] == 256
    assert seen["payload"]["temperature"] == 0


def test_timeout_or_transport_failure_fails_closed():
    def transport(*args, **kwargs):
        raise TimeoutError("synthetic")

    response = OracleHermesBridge("http://127.0.0.1:18642", api_key="test", transport=transport).ask(request())
    assert response.status == "UNAVAILABLE"
    assert response.error == "TimeoutError"
    assert "FAIL_CLOSED" in response.warnings


def test_transient_read_timeout_retries_once_and_records_attempts():
    calls = {"count": 0}

    def transport(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("transient")
        return {"model": "synthetic", "choices": [{"message": {"content": "ok"}}]}

    response = OracleHermesBridge("http://127.0.0.1:18642", api_key="test",
                                 transport=transport).ask(request())
    assert response.status == "SUCCEEDED"
    assert calls["count"] == 2
    assert response.model_provider_metadata["bridge_attempts"] == 2
    assert "RETRIED_TRANSIENT_PROVIDER_READ" in response.warnings


def test_malformed_response_fails_closed():
    bridge = OracleHermesBridge("http://127.0.0.1:18642", api_key="test",
                                transport=lambda *args, **kwargs: {"choices": []})
    assert bridge.ask(request()).status == "UNAVAILABLE"


def test_pii_is_denied_by_default():
    response = OracleHermesBridge("http://127.0.0.1:18642", api_key="test",
                                  transport=lambda *args, **kwargs: {}).ask(
                                      request(safe_context={"email": "ray@example.com"}))
    assert response.status == "UNAVAILABLE"
    assert response.error == "BridgeError"


def test_public_endpoint_is_rejected():
    try:
        OracleHermesBridge("https://oracle.example/v1", api_key="test")
    except Exception as exc:
        assert "loopback/private" in str(exc)
    else:
        raise AssertionError("public Hermes endpoint was accepted")


def test_keychain_lookup_is_used_when_environment_is_absent(monkeypatch):
    monkeypatch.delenv("NEXUS_ORACLE_HERMES_API_KEY", raising=False)
    monkeypatch.setattr(
        "scripts.nexus_agent_platform.bridge.oracle_hermes._keychain_secret",
        lambda service: "keychain-test",
    )
    bridge = OracleHermesBridge("http://127.0.0.1:18642",
                               transport=lambda *args, **kwargs: {})
    assert bridge.api_key == "keychain-test"


def test_model_route_is_explicitly_configurable(monkeypatch):
    monkeypatch.setenv("NEXUS_ORACLE_HERMES_MODEL", "synthetic-model")
    seen = {}

    def transport(method, path, payload, headers, timeout):
        seen.update(payload=payload)
        return {"choices": [{"message": {"content": "ok"}}]}

    bridge = OracleHermesBridge("http://127.0.0.1:18642", api_key="test",
                               transport=transport)
    bridge.ask(request())
    assert seen["payload"]["model"] == "synthetic-model"
