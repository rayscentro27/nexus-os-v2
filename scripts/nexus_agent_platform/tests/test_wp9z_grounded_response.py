from nexus_agent_platform.grounded_response import ground_response, response_completeness, requires_current_evidence


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
    assert "Finance: AVAILABLE" in response
    assert "Alpha: AVAILABLE" in response
    assert "Runtime: ORACLE Hermes 0.20.6" in response
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


def test_unlabeled_model_contradiction_is_not_carried_into_current_state():
    response, _ = ground_response(
        "Finance and Alpha could not be verified and the Oracle runtime is unavailable.",
        "Give me current Nexus health, Finance and Alpha availability, and the runtime.",
        RUNTIME,
    )
    assert "could not be verified" not in response
    assert "unavailable" not in response
    assert "Finance: AVAILABLE" in response
    assert "Alpha: AVAILABLE" in response


def test_research_running_question_requires_current_evidence():
    assert requires_current_evidence("Is Research still running?") is True


def test_research_state_keeps_heartbeat_scheduler_and_processing_separate(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.grounded_response.collect_verified_current_state",
        lambda runtime: {
            "runtime": RUNTIME,
            "health": {"status": "HEALTHY"},
            "specialists": {},
            "priority": {},
            "research": {
                "heartbeat": "ACTIVE",
                "supervisor": "ACTIVE_DAEMON",
                "scheduler_enabled": True,
                "execution_mode": "DRY_RUN",
                "dry_run": True,
                "task_processing": "IDLE_BETWEEN_CYCLES",
                "queue_state": "NO_CURRENT_WORK",
                "active_jobs": 0,
                "queued_jobs": 0,
                "last_cycle": "2026-09-04T03:21:03Z",
                "recent_activity": {"sources_checked": 2, "items_processed": 0, "new_items_discovered": 0},
            },
        },
    )
    response, _ = ground_response("Research is running.", "Is Research still running?", RUNTIME)
    assert "Research heartbeat: ACTIVE" in response
    assert "Execution mode: DRY_RUN" in response
    assert "Task processing: IDLE_BETWEEN_CYCLES" in response
    assert "Queue/work state: NO_CURRENT_WORK" in response
    assert "running." not in response.lower()
