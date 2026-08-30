import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.nova_company_context import build_company_context, context_for_prompt
from nexus_agent_platform.agents.nova import _canonical_awareness_capability, _present_response
from nexus_agent_platform.adapters.state_adapter import AgentState
from nexus_agent_platform.nexus_command_acknowledgement import acknowledge_command, submit_nexus_request


def test_company_context_prompt_is_bounded_and_non_authoritative():
    rendered = context_for_prompt({
        "current_status": {"program_state": "ACTIVE"},
        "operations": {"status": "UNKNOWN"},
        "research": {}, "ray_attention": {}, "business": {"top_priority": {}},
        "blockers": [], "unknown": ["freshness unavailable"],
        "authority": "CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES",
    })
    assert "CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES" in rendered
    assert "ACTIVE" in rendered


def test_command_acknowledgement_does_not_overclaim_completion():
    ack = acknowledge_command(
        "req-1", authority_status="AUTHORIZED_READ_ONLY",
        current_state="QUEUED", status="QUEUED",
        work_order_id="wo-1", assigned_department="OPERATIONS",
    )
    assert ack["command_received"] is True
    assert ack["status"] == "QUEUED"
    assert ack["current_state"] != "COMPLETED"
    assert ack["authority"] == "NEXUS_TRUTHKERNEL"


def test_acknowledgement_rejects_unknown_state():
    try:
        acknowledge_command("req-1", authority_status="UNKNOWN", current_state="UNKNOWN", status="MAGIC")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown acknowledgement state accepted")


def test_compound_salutation_does_not_swallow_company_question():
    state = AgentState(agent_id="hermes_nova", user_message="Good morning. What happened overnight?")
    state.metadata["capability_result"] = {"query_type": "get_operational_summary", "status": "success", "data": {}}
    rendered = _present_response(state, "The overnight operating summary is available.")
    assert "overnight operating summary" in rendered.lower()
    assert "what's on your mind" not in rendered.lower()


def test_semantic_company_domains_choose_canonical_reads():
    assert _canonical_awareness_capability("Did Research find anything interesting lately?") == "get_recent_research"
    assert _canonical_awareness_capability("Anything waiting on me today?") == "get_pending_approvals"
    assert _canonical_awareness_capability("How is Nexus doing right now?") == "get_system_health"


def test_delegation_language_is_bounded_to_prior_context():
    from nexus_agent_platform.agents.nova import _capability_gate
    state = AgentState(agent_id="hermes_nova", user_message="Okay, send that over to Nexus", metadata={"chat_id": 0})
    # No prior context means the ambiguous referent cannot create a request.
    result = _capability_gate(state)
    assert result.metadata.get("capability_gate", {}).get("decision") != "bounded_delegation"


def test_nova_can_submit_intake_without_executing(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    ack = submit_nexus_request(summary="Review the safe internal recommendation", referent="Prior recommendation")
    assert ack["status"] == "RECEIVED"
    assert ack["authority_status"] == "PENDING_NEXUS_VALIDATION"
    assert ack["current_state"] == "RECEIVED"
    assert ack["receipt"]


def test_company_context_does_not_promote_stale_brief_recommendations():
    context = build_company_context()
    if not context["data_quality"]["daily_brief_current"]:
        assert context["recommended_priorities"] == []
        assert context["business"]["top_priority"] == {}
