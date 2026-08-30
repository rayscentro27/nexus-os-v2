import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.nova_company_context import build_company_context, context_for_prompt
from nexus_agent_platform.agents.nova import _canonical_awareness_capability, _present_response, classify_company_question, _capability_gate
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


def test_question_types_separate_fact_advice_research_and_conversation():
    assert classify_company_question("How many clients are onboarding?") == "FACTUAL"
    assert classify_company_question("Do you think there is a better way to improve onboarding?") == "ADVISORY"
    assert classify_company_question("Did Research find anything worth pursuing?") == "RESEARCH"
    assert classify_company_question("What do you think about Tesla?") == "GENERAL_CONVERSATION"


def test_advisory_onboarding_does_not_select_client_count():
    state = AgentState(
        agent_id="hermes_nova",
        user_message="Do you think there is a better way to improve our client onboarding?",
        metadata={"chat_id": 0},
    )
    result = _capability_gate(state)
    gate = result.metadata.get("capability_gate", {})
    assert result.metadata.get("question_type") == "ADVISORY"
    assert gate.get("decision") == "reasoning_first"
    assert gate.get("capability") is None


def test_advisory_focus_today_uses_current_operational_context(monkeypatch):
    calls = []

    def fake_execute(agent_id, capability, arguments=None, **kwargs):
        calls.append(capability)
        return {"status": "success", "data": {}, "provenance": {}}

    monkeypatch.setattr("nexus_agent_platform.capabilities.shared.execute_shared_capability", fake_execute)
    state = AgentState(agent_id="hermes_nova", user_message="What do you think we should focus on today?", metadata={"chat_id": 0})
    result = _capability_gate(state)
    assert result.metadata.get("question_type") == "ADVISORY"
    assert calls == ["get_operational_summary"]


def test_contextual_free_research_uses_approved_search(monkeypatch, tmp_path):
    monkeypatch.setenv("NOVA_MEMORY_DIR", str(tmp_path))
    from nexus_agent_platform.agents import nova
    monkeypatch.setattr(nova, "load_memory", lambda chat_id: [
        {"role": "assistant", "content": "Opportunity A may reduce onboarding friction."},
    ])
    calls = []

    def fake_execute(agent_id, capability, arguments=None, **kwargs):
        calls.append((capability, arguments))
        return {"status": "success", "data": {"results": []}, "provenance": {}}

    monkeypatch.setattr("nexus_agent_platform.capabilities.shared.execute_shared_capability", fake_execute)
    state = AgentState(agent_id="hermes_nova", user_message="Is there a free way to research this further?", metadata={"chat_id": 42})
    result = _capability_gate(state)
    assert result.metadata["capability_gate"]["decision"] == "free_first_research"
    assert calls and calls[0][0] == "general_search"
    assert "Opportunity A" in calls[0][1]["query"]


def test_truth_view_preserves_provenance_and_is_not_a_second_store(monkeypatch):
    from nexus_agent_platform import nova_truth_view
    monkeypatch.setattr(nova_truth_view, "read_operational_capability", None, raising=False)
    # The adapter imports the reader locally; smoke-test its public contract
    # through a controlled module replacement.
    import nexus_agent_platform.capabilities.operational_reads as reads
    monkeypatch.setattr(reads, "read_operational_capability", lambda capability, arguments=None: {
        "status": "OK", "data": {"capability": capability}, "source_path": "current.json",
        "source_type": "current_runtime_ledger", "as_of": "2026-08-30T00:00:00Z", "freshness": "FRESH",
    })
    result = nova_truth_view.read_truth_domains("NEXUS_RUNTIME")
    assert result["authority"] == "NEXUS_TRUTHKERNEL_CANONICAL_READS"
    assert result["independent_truth_store"] is False
    assert result["claims"][0]["source"] == "current.json"


def test_domain_policy_selects_sources_by_subject_not_verification_alone():
    from nexus_agent_platform.domain_source_policy import classify_domain, source_plan
    assert "NEXUS_OPERATIONS" in classify_domain("Is Active Operator running?")
    assert "CLIENT_DATA" in classify_domain("How many real clients do we have?")
    assert "INTERNAL_RESEARCH_ALPHA" in classify_domain("What did Research find last night?")
    public = source_plan("Can an AI automation agency realistically make $10,000 a month?")
    assert "PUBLIC_BUSINESS_RESEARCH" in public["domains"]
    assert public["nexus_relevant"] is False


def test_outside_world_question_does_not_select_nexus_canonical_read(monkeypatch):
    from nexus_agent_platform.agents.nova import _capability_gate
    calls = []
    monkeypatch.setattr("nexus_agent_platform.capabilities.shared.execute_shared_capability", lambda *a, **k: calls.append(a[1]) or {"status": "success", "data": {}, "provenance": {}})
    state = AgentState(agent_id="hermes_nova", user_message="What are the benefits of an LLC?", metadata={"chat_id": 0})
    result = _capability_gate(state)
    assert "NEXUS_OPERATIONS" not in result.metadata["question_domains"]
    assert not calls


def test_legacy_report_is_quarantined_from_current_truth():
    from nexus_agent_platform.report_quarantine import classify_report
    assessment = classify_report("reports/hermes_modernization/daily_brief.json", {"status": "healthy"})
    assert assessment["provenance"] == "LEGACY_UNKNOWN"
    assert assessment["current_truth_eligible"] is False
    assert assessment["historical_reference_allowed"] is True


def test_public_research_selects_public_web_not_nexus(monkeypatch):
    from nexus_agent_platform.agents.nova import _capability_gate
    calls = []
    monkeypatch.setattr("nexus_agent_platform.capabilities.shared.execute_shared_capability", lambda *a, **k: calls.append(a[1]) or {"status": "success", "data": {"results": []}, "provenance": {}})
    state = AgentState(agent_id="hermes_nova", user_message="Research whether an AI automation agency can make $10,000 a month.", metadata={"chat_id": 0})
    result = _capability_gate(state)
    assert result.metadata["question_domains"]
    assert calls == ["public_web_search"]
