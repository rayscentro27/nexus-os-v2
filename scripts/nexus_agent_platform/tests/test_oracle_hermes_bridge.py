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
