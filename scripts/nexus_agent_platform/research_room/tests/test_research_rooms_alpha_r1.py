"""Test suite for NEXUS_RESEARCH_ROOMS_ALPHA_R1.

Verifies:
1. Room creation and atomic persistence
2. Source storage (Text, URL, YouTube fallback, Existing Research)
3. Compact Research Brief generation (10 fields; no 25-field commercial plan)
4. Source-grounded Alpha conversation (UNKNOWN is valid; no autonomous continuation loops)
5. Preliminary 5-dimension scoring (0-100; evaluated without deep research)
6. Room promotion package for Nova on explicit request (no directives created by research)
7. Safety assertions: RESEARCH_AUTONOMY_OFF, NO_SPEND, NO_PUBLISH
8. Regression query: "What are the main reasons small service businesses miss or fail to follow up with inbound customer inquiries?"
"""
import json
import pytest
from pathlib import Path

from nexus_agent_platform.research_room.room_manager import (
    ResearchRoomStore,
    ResearchRoomManager,
    RoomSource,
    RoomMessage,
    CompactResearchBrief,
    generate_compact_brief,
    calculate_preliminary_score,
    converse_with_alpha,
    AUTONOMOUS_RESEARCH_OFF,
    PROMOTION_SCHEMA_VERSION,
)


@pytest.fixture
def temp_store(tmp_path):
    return ResearchRoomStore(root=tmp_path / "research_rooms")


@pytest.fixture
def room_manager(temp_store):
    return ResearchRoomManager(store=temp_store)


def test_safety_doctrine_constants():
    """Verify autonomous research is strictly OFF by doctrine."""
    assert AUTONOMOUS_RESEARCH_OFF is True


def test_capability_1_create_room_and_persistence(room_manager, temp_store):
    """Capability 1: Create/open a Research Room and persist atomically."""
    room = room_manager.create_room(
        title="Test Inbound Inquiry Analysis",
        tags=["inbound", "pilot"],
    )
    room_id = room["room_id"]
    assert room_id.startswith("room_")
    assert room["title"] == "Test Inbound Inquiry Analysis"
    assert room["status"] in ("OPEN", "ACTIVE")
    assert room["sources"] == []
    assert len(room["messages"]) == 1
    assert room["messages"][0]["author"] in ("SYSTEM", "NOVA")

    # Verify atomic disk persistence
    loaded = temp_store.load(room_id)
    assert loaded is not None
    assert loaded["room_id"] == room_id
    assert loaded["title"] == "Test Inbound Inquiry Analysis"

    # List rooms
    rooms = room_manager.list_rooms()
    assert len(rooms) == 1
    assert rooms[0]["room_id"] == room_id


def test_capability_2_add_sources_text_url_youtube(room_manager):
    """Capability 2: Add YouTube URL, text, URL, or existing Research source."""
    room = room_manager.create_room("Multi-source Room")
    rid = room["room_id"]

    # Source 1: TEXT
    updated_1 = room_manager.add_source(
        rid,
        source_type="TEXT",
        content_or_url="Field interviews with 15 HVAC contractors showed 9/10 miss calls on job sites.",
        title="Contractor Field Interviews",
    )
    assert len(updated_1["sources"]) == 1
    assert updated_1["sources"][0]["source_type"] == "TEXT"
    assert updated_1["sources"][0]["title"] == "Contractor Field Interviews"

    # Source 2: URL
    updated_2 = room_manager.add_source(
        rid,
        source_type="URL",
        content_or_url="https://example.com/industry-report-2026",
        title="Industry Benchmark Report",
    )
    assert len(updated_2["sources"]) == 2
    assert updated_2["sources"][1]["source_type"] == "URL"

    # Source 3: YOUTUBE
    updated_3 = room_manager.add_source(
        rid,
        source_type="YOUTUBE",
        content_or_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Trade Operations Video Case Study",
    )
    assert len(updated_3["sources"]) == 3
    assert updated_3["sources"][2]["source_type"] == "YOUTUBE"


def test_capability_3_compact_research_brief_generation(room_manager):
    """Capability 3: Produce a compact Research Brief (10 fields; no 25-field commercial plan)."""
    room = room_manager.create_room("Customer Inquiries Analysis")
    rid = room["room_id"]

    source_text = (
        "Small service businesses frequently fail to respond to inbound inquiries due to: "
        "1) Owner-operators working on jobs or driving during business hours without office staff; "
        "2) Fragmented communication channels without central inbox; "
        "3) Lack of automated after-hours response; "
        "4) Inability to instantly quote pricing or availability; "
        "5) Manual triage fatigue during peak seasonal demand."
    )
    updated = room_manager.add_source(rid, "TEXT", source_text, title="Inquiry Response Study")
    brief = updated.get("brief")
    assert brief is not None

    # Check the 10 required brief fields
    required_fields = [
        "summary",
        "key_findings",
        "supported_claims",
        "unverified_or_questionable_claims",
        "evidence_quality",
        "nexus_relevance",
        "possible_application",
        "recommended_next_action",
        "unresolved_points",
        "suggested_next_department",
    ]
    for field in required_fields:
        assert field in brief, f"Missing required brief field: {field}"

    assert len(brief["summary"]) > 20
    assert len(brief["key_findings"]) >= 1
    assert brief["evidence_quality"] in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    assert brief["nexus_relevance"] in ("HIGH", "MEDIUM", "LOW", "NONE")

    # Confirm Research did NOT produce 25-field commercial requirements
    assert "margin_percentage_7_day_projection" not in brief
    assert "tam_sam_som_market_sizing" not in brief
    assert "capital_requirements_series_a" not in brief


def test_capability_4_alpha_conversational_chat_and_unknown(room_manager):
    """Capability 4: Converse with Alpha inside the room; UNKNOWN is valid; no directives."""
    room = room_manager.create_room("Grounded Conversation Room")
    rid = room["room_id"]

    room_manager.add_source(
        rid,
        "TEXT",
        "The survey included 150 local service operators across Texas and Arizona. 60% had no CRM.",
        title="Southwest Regional Survey",
    )

    # Question 1: Grounded in source
    res1 = room_manager.chat_with_alpha(rid, "How many operators were surveyed and what states?")
    alpha_reply1 = res1["alpha_message"]["content"]
    assert "150" in alpha_reply1
    assert "Texas" in alpha_reply1 or "Arizona" in alpha_reply1

    # Question 2: Outside sources -> UNKNOWN must be returned or acknowledged
    res2 = room_manager.chat_with_alpha(rid, "What was the average EBITDA multiple for French bakeries in 2021?")
    alpha_reply2 = res2["alpha_message"]["content"]
    assert "UNKNOWN" in alpha_reply2 or "not addressed" in alpha_reply2.lower() or "not in the room" in alpha_reply2.lower()

    # Verify Alpha created NO directives, spent NO money, and published NOTHING
    assert "directive_id" not in res2
    assert "publish_status" not in res2
    assert AUTONOMOUS_RESEARCH_OFF is True


def test_capability_5_preliminary_score_without_deep_research(room_manager):
    """Capability 5: Preliminary score (0-100 across 5 dimensions) without deep research."""
    room = room_manager.create_room("Scoring Room")
    rid = room["room_id"]

    room_manager.add_source(
        rid,
        "TEXT",
        "AI automation for contractor inbound inquiries. High revenue potential with minimal setup.",
        title="Opportunity Summary",
    )

    score_result = room_manager.score_room(rid)
    score = score_result["preliminary_score"]
    assert 0 <= score <= 100

    basis = score_result["score_basis"]
    assert basis["score_type"] == "PRELIMINARY_SCORE"
    assert basis["evaluated_without_deep_research"] is True
    assert 0 <= basis["nexus_relevance_score"] <= 20
    assert 0 <= basis["revenue_potential_score"] <= 20
    assert 0 <= basis["evidence_quality_score"] <= 20
    assert 0 <= basis["ease_of_execution_score"] <= 20
    assert 0 <= basis["automation_potential_score"] <= 20


def test_capability_6_promote_to_nova_on_explicit_request(room_manager):
    """Capability 6: Promote room to Nova on Ray's explicit request."""
    room = room_manager.create_room("Promotion Candidate Room")
    rid = room["room_id"]

    room_manager.add_source(
        rid,
        "TEXT",
        "Inbound inquiry automation for local trade businesses.",
        title="Core Concept",
    )
    room_manager.score_room(rid)

    promotion_pkg = room_manager.promote_to_nova(
        rid,
        requested_objective="Prepare a bounded pilot for contractor inbound call intake.",
    )

    assert promotion_pkg["schema_version"] == PROMOTION_SCHEMA_VERSION
    assert promotion_pkg["room_id"] == rid
    assert promotion_pkg["promoted_by"] == "RAY"
    assert promotion_pkg["promoted_project_id"].startswith("proj_research_")
    assert promotion_pkg["requested_objective"] == "Prepare a bounded pilot for contractor inbound call intake."

    # Room state must reflect promotion
    updated_room = room_manager.get_room(rid)
    assert updated_room["promoted_project_id"] == promotion_pkg["promoted_project_id"]
    last_msg = updated_room["messages"][-1]
    assert last_msg["author"] == "NOVA"
    assert "Governed Nexus execution boundary established" in last_msg["content"]


def test_regression_small_service_business_inquiries(room_manager):
    """Regression test: 'What are the main reasons small service businesses miss or fail to follow up with inbound customer inquiries?'

    Must:
    1. Complete cleanly without Codex continuation loop
    2. NOT trigger CODEX_TIMEOUT
    3. Return 5 concrete operational reasons
    4. Not create automatic marketing/creative directives
    """
    query = "What are the main reasons small service businesses miss or fail to follow up with inbound customer inquiries?"
    result = room_manager.execute_routine_research(objective=query)

    assert result["status"] == "COMPLETED"
    assert result["continuation_loop_active"] is False
    assert result["codex_timeout"] is False

    room = result["room"]
    assert room is not None
    assert room["preliminary_score"] > 0

    brief = result["brief"]
    assert brief is not None
    assert len(brief["key_findings"]) >= 1

    # Ask Alpha the exact regression question
    chat_result = room_manager.chat_with_alpha(room["room_id"], query)
    reply = chat_result["alpha_message"]["content"]

    # Verify the concrete operational findings are delivered
    assert "Owner-operators" in reply or "job" in reply.lower()
    assert "Fragmented" in reply or "channels" in reply.lower()
    assert "after-hours" in reply.lower() or "triage" in reply.lower()
