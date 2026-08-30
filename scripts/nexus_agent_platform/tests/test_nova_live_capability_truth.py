def test_embedded_capability_envelope_is_interceptable():
    from nexus_agent_platform.agents.nova import _extract_model_capability_request
    value = 'I will check that now: {"nova_capability_request":{"capability":"PUBLIC_WEB_SEARCH","arguments":{"query":"credit repair affiliate programs"}}}'
    request = _extract_model_capability_request(value)
    assert request["capability"] == "PUBLIC_WEB_SEARCH"


def test_worker_never_delivers_capability_envelope():
    from nova import nova_telegram_worker as worker
    value, reason = worker._response_integrity('{"nova_capability_request":{"capability":"PUBLIC_WEB_SEARCH"}}')
    assert value is None
    assert reason == "raw_capability_request"


def test_live_capability_truth_is_status_not_model_claim():
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    result = execute_shared_capability("hermes_nova", "get_live_capability_status", {})
    capabilities = result["data"]["capabilities"]
    assert "public_web_search" in capabilities
    assert capabilities["email_send"]["authority_required"] == "APPROVAL"
    assert capabilities["calendar_event_create"]["available_now"] is False
    assert result["data"]["google_workspace"]["refresh_token"] in {"CONFIGURED", "NOT_CONFIGURED"}
