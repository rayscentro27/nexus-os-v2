from scripts.nova.nova_hermes_shadow import (
    _current_shadow_context,
    _conversation_history_for_model,
    _discover_mcp_with_bounded_recovery,
    _shadow_resource_guidance,
)


def test_mcp_discovery_recovers_once_from_transient_startup_failure():
    calls = []

    def discover():
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError("MCP startup timeout")
        return ["mcp_nexus_mcp_nexus_get_system_health"]

    timing = {}
    assert _discover_mcp_with_bounded_recovery(discover, timing=timing)
    assert len(calls) == 2
    assert timing["mcp_discovery_recovered"] is True
    assert timing["mcp_discovery_attempts"][0]["outcome"] == "TRANSIENT_FAILURE"


def test_mcp_recovery_closes_stale_hermes_connections_before_reconnect():
    calls = []

    def discover():
        calls.append("discover")
        if len(calls) == 1:
            return []
        return ["mcp_nexus_mcp_nexus_get_system_health"]

    def shutdown():
        calls.append("shutdown")

    timing = {}
    assert _discover_mcp_with_bounded_recovery(discover, shutdown_mcp_servers=shutdown, timing=timing)
    assert calls == ["discover", "shutdown", "discover"]
    assert timing["mcp_discovery_attempts"][0]["recovery_action"] == "HERMES_MCP_SHUTDOWN_RECONNECT"


def test_mcp_discovery_does_not_retry_permanent_failure():
    calls = []

    def discover():
        calls.append(1)
        raise ValueError("invalid MCP configuration")

    try:
        _discover_mcp_with_bounded_recovery(discover)
    except ValueError:
        pass
    else:
        raise AssertionError("permanent discovery errors must not be swallowed")
    assert len(calls) == 1


def test_native_conversation_history_survives_with_secret_shaped_text_redacted():
    history = _conversation_history_for_model({"recent_turns": [{
        "user": "Remember the project codename.",
        "assistant": "The codename is HELIOS and the key is sk-test-not-for-use.",
        "source_type": "NATIVE_CONVERSATION",
    }]})
    assert "HELIOS" in history[-1]["content"]
    assert "sk-test-not-for-use" not in history[-1]["content"]
    assert "[REDACTED]" in history[-1]["content"]


def test_shadow_guidance_separates_discovery_from_verification():
    guidance = _shadow_resource_guidance()
    assert "discovery evidence" in guidance
    assert "public_web_retrieval_shadow" in guidance
    assert "simple fact" in guidance


def test_shadow_context_keeps_recent_conversation_and_marks_old_results_stale():
    context = _current_shadow_context({
        "active_request": "What did Research find?",
        "recent_turns": [{"user": "I chose option two", "assistant": "Option two is my recommendation."}],
        "resource_results": [{
            "capability": "alpha_challenge_shadow",
            "request_id": "old-request",
            "result_id": "old-result",
            "current_for_turn": False,
        }],
    })
    assert "I chose option two" in context
    assert '"current_for_turn": false' in context
    assert "What did Research find?" in context
