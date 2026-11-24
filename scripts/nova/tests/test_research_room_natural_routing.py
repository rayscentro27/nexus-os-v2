from __future__ import annotations

from nova.research_intent import route_research_intent
from nova.semantic_orchestration import resolve_owner_request


BUSINESS_REQUEST = ("Nova, find me an online business opportunity Nexus could realistically start "
    "making money from, figure out how Nexus could automate most of it, and tell me what we "
    "would need to build and do first.")


def test_natural_business_request_routes_to_business_mode():
    result = resolve_owner_request(BUSINESS_REQUEST)
    assert result["intent"] == "RESEARCH_ROOM_REQUEST"
    assert result["execution_mode"] == "BUSINESS_OPPORTUNITY_MODE"
    assert result["executor"] == "research_room_shadow_intake"
    assert result["intent_object"]["research_required"] is True
    assert result["intent_object"]["downstream_actions_before_strategy"] is False


def test_natural_trading_request_routes_to_trading_mode():
    assert route_research_intent("Research this trading strategy and make a paper-trading plan") ["primary_mode"] == "TRADING_STRATEGY_MODE"


def test_natural_nexus_tool_request_routes_to_enhancement_mode():
    assert route_research_intent("Can this tool help Nexus and improve Nova?")["primary_mode"] == "NEXUS_ENHANCEMENT_MODE"


OPENCODE_REVIEW_REQUEST = ("Nova, review OpenCode and tell me whether there is anything Nexus should actually adopt from it. "
    "I do not want a generic software review. I want you to figure out what capabilities or patterns could make Nexus better, "
    "what we already have, what would be duplicate functionality, what we should copy or adapt, what we should ignore, "
    "what risks or costs are involved, and the smallest safe way to test anything worth keeping. "
    "Also tell me what should be added to the Nexus library and what Systems should do next.")


def test_natural_nexus_tool_review_routes_to_enhancement_mode():
    result = resolve_owner_request(OPENCODE_REVIEW_REQUEST)
    assert result["intent"] == "RESEARCH_ROOM_REQUEST"
    assert result["execution_mode"] == "NEXUS_ENHANCEMENT_MODE"
    assert result["executor"] == "research_room_shadow_intake"
    assert result["intent_object"]["research_required"] is True


def test_opencode_style_request_does_not_use_generic_bounded_task_path():
    result = resolve_owner_request(OPENCODE_REVIEW_REQUEST)
    assert result["intent"] != "BOUNDED_CODING_REQUEST"
    assert result["executor"] != "nexus_assign_bounded_coding_task"


def test_enhancement_research_accepted_before_mcp_execution():
    result = resolve_owner_request(OPENCODE_REVIEW_REQUEST)
    assert result["intent_object"]["dispatch_path"] == "NOVA_TO_RESEARCH_ROOM"
    assert result["intent_object"]["downstream_actions_before_strategy"] is False
    assert result["executor"] == "research_room_shadow_intake"


def test_mcp_container_failure_cannot_block_enhancement_research():
    # The Nova worker's Research Room branch is selected before any MCP executor.
    result = resolve_owner_request(OPENCODE_REVIEW_REQUEST)
    assert result["intent"] == "RESEARCH_ROOM_REQUEST"
    assert result["executor"] == "research_room_shadow_intake"


def test_enhancement_result_contract_requires_execution_fields():
    from nexus_agent_platform.research_room.execution_modes import build_execution_strategy
    strategy = build_execution_strategy({"original_request": OPENCODE_REVIEW_REQUEST,
        "metadata": {"execution_mode": "NEXUS_ENHANCEMENT_MODE"}})
    assert strategy["decision"] in {"ADOPT", "ADAPT", "TEST", "IGNORE"}
    assert strategy["library_additions"]
    assert strategy["next_action"]


def test_enhancement_renderer_shows_adopt_adapt_test_ignore():
    from nova.research_room_dispatch import render_nova_research_response
    strategy = {"execution_mode": "NEXUS_ENHANCEMENT_MODE", "decision": "ADAPT",
        "what_is_useful": "Governed coding workflow", "what_nexus_already_has": "Existing agent paths",
        "what_is_duplicate": "Task queue", "what_to_copy_or_adapt": "Least privilege",
        "what_not_to_adopt": "Unattended shell", "risks": ["Repository access"],
        "cost": "Existing capacity", "complexity": "Low", "smallest_safe_test": "Docs-only disposable branch",
        "implementation_plan": ["Review diff"], "library_additions": [{"name": "Reviewable agent workflow"}],
        "next_action": "Systems documents a disposable trial"}
    result = render_nova_research_response({"status": "COMPLETE", "case": {
        "case_id": "case-test", "status": "COMPLETE", "execution_strategy": strategy,
        "handoff": {"kind": "PROPOSED_HANDOFF", "target_department": "SYSTEMS"}}})
    for value in ("Decision", "ADAPT", "What is useful", "What Nexus already has", "What to copy/adapt",
                  "What to ignore", "Risks", "Smallest safe test", "Library additions", "SYSTEMS (shadow only",
                  "Systems next action"):
        assert value.casefold() in result.casefold()


def test_natural_claim_request_routes_to_claim_mode():
    assert route_research_intent("Is this claim true, can $7 really become $500?")["primary_mode"] == "CLAIM_VERIFICATION_MODE"


def test_deep_mode_requires_explicit_depth_request():
    assert route_research_intent("Do deep research on the architecture tradeoffs")["primary_mode"] == "DEEP_RESEARCH_MODE"
    assert route_research_intent("What online business should Nexus start?")["primary_mode"] == "BUSINESS_OPPORTUNITY_MODE"


def test_not_an_alpha_assignment_cannot_block_research():
    result = resolve_owner_request(BUSINESS_REQUEST)
    assert result["intent"] == "RESEARCH_ROOM_REQUEST"
    assert result["intent_object"]["alpha_assignment_required"] is False


def test_missing_downstream_action_cannot_block_research():
    result = route_research_intent(BUSINESS_REQUEST)
    assert result is not None
    assert result["primary_mode"] == "BUSINESS_OPPORTUNITY_MODE"
    assert result["possible_downstream_departments"] == []


def test_missing_governed_mcp_action_cannot_block_research():
    result = resolve_owner_request(BUSINESS_REQUEST)
    assert result["executor"] == "research_room_shadow_intake"
    assert result["intent_object"]["downstream_actions_before_strategy"] is False


def test_research_objective_accepted_before_handoff_capability_check():
    result = resolve_owner_request(BUSINESS_REQUEST)
    assert result["intent_object"]["research_required"] is True
    assert result["intent_object"]["dispatch_path"] == "NOVA_TO_RESEARCH_ROOM"


def test_business_mode_final_strategy_and_nova_plan_contract():
    from nexus_agent_platform.research_room.execution_modes import build_execution_strategy
    strategy = build_execution_strategy({"original_request": BUSINESS_REQUEST,
        "metadata": {"execution_mode": "BUSINESS_OPPORTUNITY_MODE"}})
    assert strategy["execution_mode"] == "BUSINESS_OPPORTUNITY_MODE"
    assert strategy["top_businesses"]
    assert strategy["how_nova_runs_it"]
    assert strategy["library_additions"]
    assert strategy["next_action"]


def test_no_department_or_alpha_assignment_is_created_for_business_research():
    result = resolve_owner_request(BUSINESS_REQUEST)
    assert result["departments"] == ["RESEARCH"]
    assert result["executor"] == "research_room_shadow_intake"


def test_ingress_room_dispatch_uses_existing_room_and_creates_proposed_case(monkeypatch, tmp_path):
    from nova import research_room_dispatch

    calls = []
    strategy = {"execution_mode": "BUSINESS_OPPORTUNITY_MODE", "winner": "Test offer",
        "top_businesses": [{"business": "Test offer"}], "how_nova_runs_it": {"finds_customers": "researches"},
        "library_additions": [{"name": "Reusable offer"}], "next_action": "Ray reviews ICP"}
    case = {"case_id": "case-room", "status": "COMPLETE", "execution_strategy": strategy,
        "handoff": {"kind": "PROPOSED_HANDOFF", "target_department": None, "action_owner": "RAY/NOVA"}}

    def run(**kwargs):
        calls.append(kwargs)
        return {"status": "COMPLETE", "case": case, "artifacts": {}}

    monkeypatch.setattr("nexus_agent_platform.research_room.business_opportunity_proof.run_business_opportunity_proof", run)
    result = research_room_dispatch.execute_research_room_request(BUSINESS_REQUEST,
        objective_id="nova-objective-test", repository_root=tmp_path)
    assert result["objective_accepted"] is True
    assert result["case"]["status"] == "COMPLETE"
    assert result["case"]["execution_strategy"]["next_action"]
    assert calls[0]["objective"] == BUSINESS_REQUEST
    assert calls[0]["intent_object"]["primary_mode"] == "BUSINESS_OPPORTUNITY_MODE"


def test_room_one_turn_contract_runs_without_optional_langgraph(monkeypatch):
    from nexus_agent_platform.research_room.models import new_case
    from nexus_agent_platform.research_room.room_graph import RoomGraph
    from nexus_agent_platform.research_room.source_tools import SourceTools

    graph = RoomGraph(source_tools=SourceTools(), advisor_router=None)
    def missing_langgraph():
        raise ModuleNotFoundError("No module named 'langgraph'", name="langgraph")
    monkeypatch.setattr(graph, "_graph", missing_langgraph)
    result = graph.turn(new_case("nova-room-fallback", BUSINESS_REQUEST).to_dict())
    assert result["turn_count"] == 1
    assert result["next_participant"] == "SOURCE_ANALYST"
