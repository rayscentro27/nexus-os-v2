"""Regression test suite for NOVA_RESEARCH_ROOM_ROUTING_R1.

Verifies:
1. Exact Admira command routes to Research Room tools directly (no legacy job).
2. Exact deep research command routes to bounded deep Research (RESEARCH_MISSION).
3. Complete separation between RESEARCH_ROOM_INTENT and DEEP_RESEARCH_INTENT.
4. End-to-end execution through Nova's telegram worker and live MCP tool contracts.
"""
from __future__ import annotations

import pytest

from nova import nexus_mcp_status
from nova import nova_telegram_worker as worker
from nova.research_intent import route_research_intent
from nova.semantic_orchestration import resolve_owner_request


ADMIRA_ROOM_PROMPT = (
    "Nova, create a Research Room for Admira and have Alpha research how it could help Nexus Marketing and Creative. "
    "Score it, but do not promote or create downstream work yet."
)

ADMIRA_DEEP_PROMPT = "Nova, research Admira deeply, including competitors and current pricing."


def test_admira_natural_request_resolves_to_research_room():
    semantic = resolve_owner_request(ADMIRA_ROOM_PROMPT)
    assert semantic["intent"] == "RESEARCH_ROOM_REQUEST"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_create_research_room"
    assert semantic["execution_mode"] == "RESEARCH_ROOM_MODE"
    assert semantic["confidence"] >= 0.95
    assert semantic["intent_object"]["research_required"] is True
    assert semantic["intent_object"]["dispatch_path"] == "NOVA_TO_RESEARCH_ROOM"


def test_admira_deep_request_resolves_to_deep_research_mission():
    semantic = resolve_owner_request(ADMIRA_DEEP_PROMPT)
    assert semantic["intent"] == "RESEARCH_MISSION"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_assign_research"
    assert semantic["execution_mode"] == "DEEP_RESEARCH_MODE"
    assert semantic["likely_destination"] == "RESEARCH"


def test_admira_end_to_end_execution_through_nova_worker(monkeypatch):
    delivered = []

    def mock_deliver(update_id, chat_id, response, mission_id=None):
        delivered.append({
            "update_id": update_id,
            "chat_id": chat_id,
            "response": response,
            "mission_id": mission_id,
        })
        return {"state": "DELIVERED", "message_ids": [10001]}

    monkeypatch.setattr(worker, "_deliver_response", mock_deliver)
    monkeypatch.setattr(worker, "is_authorized", lambda *args, **kwargs: True)

    handled = worker._process_message_inner(
        update={},
        message={},
        chat={"id": 1288928049},
        user={"id": 1288928049},
        chat_id=1288928049,
        user_id=1288928049,
        username="ray",
        text=ADMIRA_ROOM_PROMPT,
        update_id=500001,
    )

    assert handled is True
    assert len(delivered) == 1
    reply = delivered[0]["response"]

    # Required contract assertions
    assert "RESEARCH_ROOM_CREATED=YES" in reply
    assert "ROOM_ID=room_" in reply
    assert "ALPHA_INVOKED=YES" in reply
    assert "ALPHA_RESULT_RETURNED=YES" in reply
    assert "PRELIMINARY_SCORE_RETURNED=YES" in reply
    assert "PRELIMINARY_SCORE=" in reply

    assert "LEGACY_RESEARCH_JOB_CREATED=NO" in reply
    assert "PROMOTED=NO" in reply
    assert "PROJECT_CREATED=NO" in reply
    assert "MARKETING_DIRECTIVE_CREATED=NO" in reply
    assert "CREATIVE_DIRECTIVE_CREATED=NO" in reply
    assert "COMMERCE_DIRECTIVE_CREATED=NO" in reply
    assert "SPEND=0" in reply
    assert "PUBLISH=NO" in reply

    # Ensure no legacy durable job was returned
    assert "job_" not in reply


def test_admira_deep_end_to_end_execution_creates_bounded_research_job(monkeypatch):
    delivered = []
    assigned_tasks = []

    def mock_assign_research(task, parent_id, **kwargs):
        assigned_tasks.append({"task": task, "parent_id": parent_id, "kwargs": kwargs})
        return ({
            "status": "queued",
            "durable_job_id": "job_admira_deep_test99",
            "durable_job_state": "READY",
            "job_id": "job_admira_deep_test99",
        }, 1)

    def mock_deliver(update_id, chat_id, response, mission_id=None):
        delivered.append({
            "update_id": update_id,
            "chat_id": chat_id,
            "response": response,
            "mission_id": mission_id,
        })
        return {"state": "DELIVERED", "message_ids": [10002]}

    monkeypatch.setattr(nexus_mcp_status, "assign_research_task", mock_assign_research)
    monkeypatch.setattr(worker, "_deliver_response", mock_deliver)
    monkeypatch.setattr(worker, "is_authorized", lambda *args, **kwargs: True)

    handled = worker._process_message_inner(
        update={},
        message={},
        chat={"id": 1288928049},
        user={"id": 1288928049},
        chat_id=1288928049,
        user_id=1288928049,
        username="ray",
        text=ADMIRA_DEEP_PROMPT,
        update_id=500002,
    )

    assert handled is True
    assert len(assigned_tasks) == 1
    assert "Admira" in assigned_tasks[0]["task"]
    assert len(delivered) == 1
    reply = delivered[0]["response"]
    assert "job_admira_deep_test99" in reply
    assert "REQUESTED_INTENT=RESEARCH_MISSION" in reply
    assert "EXECUTION_PATH=nexus_assign_research" in reply


@pytest.mark.parametrize("phrase", [
    "create research room",
    "open research room",
    "add source",
    "ask Alpha",
    "research this in a room",
    "discuss this source",
    "score this room",
    "compare research rooms",
    "research this idea",
])
def test_research_room_intent_phrases(phrase):
    intent = route_research_intent(phrase)
    assert intent is not None
    assert intent["primary_mode"] == "RESEARCH_ROOM_MODE"
    semantic = resolve_owner_request(phrase)
    assert semantic["intent"] == "RESEARCH_ROOM_REQUEST"
    assert semantic["department"] == "RESEARCH"


@pytest.mark.parametrize("phrase", [
    "research this deeply",
    "validate the market",
    "perform competitive research",
    "verify pricing",
    "conduct full business research",
    "perform deep investigation",
])
def test_deep_research_intent_phrases(phrase):
    intent = route_research_intent(phrase)
    assert intent is not None
    assert intent["primary_mode"] == "DEEP_RESEARCH_MODE"
    semantic = resolve_owner_request(phrase)
    assert semantic["intent"] == "RESEARCH_MISSION"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_assign_research"


RAY_LIVE_PROMPT = (
    "Nova, create a new Research Room called Admira Live Test using https://www.getadmira.com/?r=0. "
    "Have Alpha tell me what Admira does, how it could help Nexus Marketing and Creative, and give it a preliminary score. "
    "Do not promote it, create a project, or send anything downstream."
)


def test_ray_live_admira_prompt_resolves_to_research_room():
    semantic = resolve_owner_request(RAY_LIVE_PROMPT)
    assert semantic["intent"] == "RESEARCH_ROOM_REQUEST"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_create_research_room"
    assert semantic["execution_mode"] == "RESEARCH_ROOM_MODE"
    assert semantic["confidence"] >= 0.95
    assert semantic["intent_object"]["primary_mode"] == "RESEARCH_ROOM_MODE"


def test_ray_live_admira_prompt_executes_cleanly_through_worker(monkeypatch):
    delivered = []

    def mock_deliver(update_id, chat_id, response, mission_id=None):
        delivered.append({
            "update_id": update_id,
            "chat_id": chat_id,
            "response": response,
            "mission_id": mission_id,
        })
        return {"state": "DELIVERED", "message_ids": [10002]}

    monkeypatch.setattr(worker, "_deliver_response", mock_deliver)
    monkeypatch.setattr(worker, "is_authorized", lambda *args, **kwargs: True)

    handled = worker._process_message_inner(
        update={},
        message={},
        chat={"id": 1288928049},
        user={"id": 1288928049},
        chat_id=1288928049,
        user_id=1288928049,
        username="ray",
        text=RAY_LIVE_PROMPT,
        update_id=500003,
    )

    assert handled is True
    assert len(delivered) == 1
    reply = delivered[0]["response"]

    assert "RESEARCH_ROOM_CREATED=YES" in reply
    assert "ROOM_ID=room_" in reply
    assert "https://www.getadmira.com/?r=0" in reply
    assert "SOURCE_RETRIEVED=YES" in reply
    assert "ALPHA_INVOKED=YES" in reply
    assert "ALPHA_RESULT_RETURNED=YES" in reply
    assert "PRELIMINARY_SCORE_RETURNED=YES" in reply
    assert "LEGACY_RESEARCH_JOB_CREATED=NO" in reply
    assert "PROMOTED=NO" in reply
    assert "PROJECT_CREATED=NO" in reply
    assert "SPEND=0" in reply
    assert "PUBLISH=NO" in reply
