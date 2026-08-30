import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform import department_router


def test_unknown_semantic_read_reaches_front_brain(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.agents.front_brain.classify_message",
        lambda text, context: {"mode": "operational_read", "capability": "repo_intelligence"},
    )
    result = department_router.resolve("Which recent changes matter for reliability?")
    assert result["status"] == "RESOLVED"
    assert result["loop"] == "NEXUS_REPO_INTELLIGENCE"


def test_semantic_health_reaches_health_loop(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.agents.front_brain.classify_message",
        lambda text, context: {"mode": "operational_read", "capability": "system_health"},
    )
    result = department_router.resolve("Is Nexus healthy enough to proceed today?")
    assert result["loop"] == "NEXUS_SYSTEM_HEALTH_RECOVERY"


def test_semantic_review_reaches_governance_loop(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.agents.front_brain.classify_message",
        lambda text, context: {"mode": "operational_read", "capability": "pending_approvals"},
    )
    result = department_router.resolve("Which decisions are waiting on me?")
    assert result["loop"] == "NEXUS_RAY_REVIEW"


def test_unknown_does_not_select_arbitrary_execution(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.agents.front_brain.classify_message",
        lambda text, context: {"mode": "conversation", "capability": None},
    )
    result = department_router.resolve("Do something surprising")
    assert result["status"] == "NO_EXECUTION"
    assert result["intent_class"] == "SEMANTIC_ADVISORY"


def test_governed_action_without_certified_route_stays_blocked(monkeypatch):
    monkeypatch.setattr(
        "nexus_agent_platform.agents.front_brain.classify_message",
        lambda text, context: {"mode": "governed_action", "capability": "unlisted_action"},
    )
    result = department_router.resolve("Change the production system")
    assert result["status"] == "UNKNOWN_INTENT"
