"""Test suite for Research Room MCP Tools (services/nexus_mcp).

Tests the 7 exposed Research Room tools:
1. nexus_list_research_rooms
2. nexus_get_research_room
3. nexus_create_research_room
4. nexus_add_room_source
5. nexus_ask_alpha_research_room
6. nexus_score_research_room
7. nexus_promote_research_room
"""
import pytest
from services.nexus_mcp.server import (
    _list_research_rooms,
    _get_research_room,
    _create_research_room,
    _add_room_source,
    _ask_alpha_research_room,
    _score_research_room,
    _promote_research_room,
)


def test_mcp_create_and_get_room():
    create_res = _create_research_room(
        title="MCP Test Room Inbound Analysis",
        source_content="Contractor call triage field study.",
        source_type="TEXT",
        source_title="Field Study",
    )
    assert create_res["status"] == "CREATED"
    room_id = create_res["room_id"]
    assert room_id.startswith("room_")

    # Get room
    get_res = _get_research_room(room_id)
    assert get_res["status"] == "OK"
    room = get_res["room"]
    assert room["title"] == "MCP Test Room Inbound Analysis"
    assert len(room["sources"]) == 1


def test_mcp_list_rooms():
    list_res = _list_research_rooms(limit=10)
    assert list_res["status"] in ("OK", "EMPTY")
    assert isinstance(list_res["rooms"], list)
    assert list_res["metadata"]["read_only"] is True


def test_mcp_add_source_and_score():
    create_res = _create_research_room(title="MCP Add Source Room")
    rid = create_res["room_id"]

    add_res = _add_room_source(
        room_id=rid,
        source_type="URL",
        content_or_url="https://example.com/industry-inbound-study",
        title="Inbound Study",
    )
    assert add_res["status"] == "OK"
    assert len(add_res["room"]["sources"]) == 1

    score_res = _score_research_room(room_id=rid)
    assert score_res["status"] == "OK"
    assert score_res["preliminary_score"] is not None
    assert 0 <= score_res["preliminary_score"] <= 100


def test_mcp_ask_alpha_and_promote():
    create_res = _create_research_room(
        title="MCP Alpha Grounded Q&A Room",
        source_content="HVAC contractors miss 60% of incoming inquiries while in crawlspaces.",
        source_type="TEXT",
        source_title="HVAC Inquiries Study",
    )
    rid = create_res["room_id"]

    # Ask Alpha
    ask_res = _ask_alpha_research_room(
        room_id=rid,
        question="What percentage of inquiries do HVAC contractors miss?",
    )
    assert ask_res["status"] == "OK"
    assert "alpha_message" in ask_res
    assert "60%" in ask_res["alpha_message"]["content"] or "HVAC" in ask_res["alpha_message"]["content"]

    # Promote to Nova
    promote_res = _promote_research_room(
        room_id=rid,
        requested_objective="Prepare a bounded pilot for contractor inbound call intake.",
    )
    assert promote_res["status"] == "PROMOTED"
    pkg = promote_res["promotion_package"]
    assert pkg["room_id"] == rid
    assert pkg["promoted_by"] == "RAY"
    assert pkg["promoted_project_id"].startswith("proj_research_")
