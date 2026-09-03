from nexus_agent_platform.grounded_response import ground_response, response_completeness


RUNTIME = {
    "host": "ORACLE",
    "runtime_host": "ORACLE",
    "hermes_version": "0.20.6",
    "profile": "nova_nexus",
    "provider": "openrouter",
    "model": "openai/gpt-4o-mini",
}


def test_current_state_replaces_model_owned_fact_lines(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.grounded_response.collect_verified_current_state",
        lambda runtime: {
            "runtime": {**RUNTIME, "provenance": "CURRENT"},
            "health": {"status": "DEGRADED", "raw": {"active_services": 0, "degraded_services": 1, "failed_services": 0}},
            "specialists": {"finance": {"availability": "AVAILABLE"}, "alpha": {"availability": "AVAILABLE"}},
            "priority": {"classification": "REQUIRES_RAY", "summary": "Approve the first landing page."},
        },
    )
    response, evidence = ground_response(
        "Overall Status: DEGRADED\nPython version: 3.13.5\nFinance: Not checked\nAlpha: configured",
        "Give me current system health, confirm Finance and Alpha availability, and tell me the runtime.",
        RUNTIME,
    )
    assert "3.13.5" not in response
    assert "Not checked" not in response
    assert "Finance availability: AVAILABLE" in response
    assert "Alpha availability: AVAILABLE" in response
    assert "- Hermes runtime: ORACLE Hermes 0.20.6" in response
    assert all(response_completeness(response).values())
    assert evidence["runtime"]["provenance"] == "CURRENT"


def test_unverified_versions_are_explicitly_unknown(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.grounded_response.collect_verified_current_state",
        lambda runtime: {
            "runtime": RUNTIME,
            "health": {"status": "UNKNOWN", "raw": {}},
            "specialists": {"finance": {"availability": "UNKNOWN"}, "alpha": {"availability": "UNKNOWN"}},
            "priority": {"classification": "UNKNOWN", "summary": "Current priority was not verified."},
        },
    )
    response, _ = ground_response(
        "Python version: 3.13.5\nOperating system: Ubuntu 24.04\nPodman version: 5.0",
        "What Python version, operating system version, and Podman version are you running?",
        RUNTIME,
    )
    assert "3.13.5" not in response
    assert "Ubuntu 24.04" not in response
    assert "Podman version: 5.0" not in response
    assert "UNKNOWN unless separately verified" in response


def test_ordinary_conversation_is_not_reformatted():
    value = "I disagree: the largest risk is execution discipline, not tooling."
    response, evidence = ground_response(value, "I disagree with you. Defend your view.", RUNTIME)
    assert response == value
    assert evidence == {}
