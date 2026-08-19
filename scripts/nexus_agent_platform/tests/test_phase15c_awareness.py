"""Phase 15C shared-awareness and live-operator acceptance tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


QUESTIONS = {
    "Nexus, who are you?": None,
    "Nexus, give me a plan for today.": "DAILY_BRIEF",
    "Nexus, what is the current Nexus OS status?": "SYSTEM_HEALTH",
    "Nexus, what should I focus on to make money today?": "DAILY_BRIEF",
    "Nexus, what is the production client count?": "CLIENT_COUNT",
    "Nexus, what opportunities are currently ACCEPT or WATCH?": "BUSINESS_OPPORTUNITIES",
    "Nexus, what research ran most recently?": "RESEARCH_HISTORY",
    "Nexus, what did Alpha find most recently?": "ALPHA_LATEST",
    "Nexus, when did the Revenue Opportunity loop last run?": "BUSINESS_LOOP_STATUS",
    "Nexus, what is AI operations cost today?": "AI_COST_SUMMARY",
    "Nexus, what is the current payment gate?": "PAYMENT_GATE",
    "Nexus, what is the current client journey gate?": "CLIENT_JOURNEY_GATE",
    "Nexus, what are the current blockers?": "BLOCKERS",
    "Nexus, what approvals are pending?": "APPROVAL_QUEUE",
    "Nexus, what is the status of my business loops?": "BUSINESS_LOOP_STATUS",
    "Nexus, do you have governed access to Nexus OS data?": "get_runtime_capabilities",
    "Nexus, can you read Supabase-backed Nexus data through certified capabilities?": "get_runtime_capabilities",
    "Nexus, can you run arbitrary SQL?": None,
    "Nexus, can you make arbitrary Supabase modifications?": None,
    "Nexus, is Codex currently available?": "WORKFORCE_STATUS",
    "Nexus, is OpenCode currently available?": "WORKFORCE_STATUS",
    "Nexus, which coding workers are available?": "WORKFORCE_STATUS",
    "Nexus, explain the governed coding work-order flow.": None,
    "Nexus, what is the highest-value next action from current Nexus data?": "DAILY_BRIEF",
    "Nexus, show me the evidence you used for that recommendation.": "EVIDENCE_LOOKUP",
}


def test_hermes_exact_telegram_questions_use_deterministic_contracts():
    from nexus_agent_platform.agents.front_brain import classify_message, _deterministic_operational_intent

    for question, expected in QUESTIONS.items():
        if expected is None:
            # Identity, governance refusal, and work-order explanation stay in
            # conversational/governed handling; they must not be misrouted to
            # a stale operational object.
            # Avoid invoking the model for non-read questions in this routing
            # test; the deterministic guard must leave them for their normal
            # identity/governance/conversation handlers.
            assert _deterministic_operational_intent(question) is None
        else:
            decision = classify_message(question)
            assert decision["mode"] == "operational_read"
            assert decision["capability"] == expected


def test_nova_exact_telegram_questions_use_same_contracts():
    from nexus_agent_platform.agents.nova import _semantic_capability_gate

    for question, expected in QUESTIONS.items():
        result = _semantic_capability_gate(question)
        if expected is None:
            if question.endswith("who are you?"):
                assert result is not None and result[0] == "get_agent_details"
            else:
                assert result is None
        else:
            assert result is not None
            assert result[0] == expected


def test_canonical_envelopes_have_authority_and_freshness_metadata():
    from nexus_agent_platform.capabilities.operational_reads import read_operational_capability

    for capability in {
        expected for expected in QUESTIONS.values() if expected and expected != "get_runtime_capabilities"
    }:
        result = read_operational_capability(capability, {"query": "current operator question"})
        assert result["status"] in {"OK", "UNAVAILABLE"}
        assert "source_type" in result and "source_path" in result
        assert "freshness" in result and "provenance" in result
        assert "authority_rank" in result["provenance"]
        if result["status"] == "OK":
            assert result["data"] is not None


def test_nova_denies_arbitrary_sql_and_supabase_writes_without_reporting_worker_failure():
    from nexus_agent_platform.agents.nova import _nova_search_supabase
    from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_WRITES

    assert NOVA_ALLOWED_WRITES == frozenset()
    for request in (
        "Run arbitrary SQL against Supabase",
        "Modify arbitrary Supabase rows",
        "Insert a new client into Supabase",
    ):
        result = _nova_search_supabase(request)
        assert result["status"] == "denied"
        assert "read-only" in result["message"].lower()


def test_nova_live_operator_variants_use_canonical_awareness_before_planner():
    from nexus_agent_platform.agents.nova import _canonical_awareness_capability, _capability_gate
    from nexus_agent_platform.adapters.state_adapter import AgentState

    variants = {
        "Nova, what is the current status of Nexus OS?": "SYSTEM_HEALTH",
        "Nova, how many production clients do I currently have?": "CLIENT_COUNT",
        "Nova, what opportunities are currently ACCEPT or WATCH?": "BUSINESS_OPPORTUNITIES",
        "Nova, what research ran most recently?": "RESEARCH_HISTORY",
        "Nova, what did Alpha find most recently?": "ALPHA_LATEST",
        "Nova, when did the Revenue Opportunity loop last run?": "BUSINESS_LOOP_STATUS",
        "Nova, how much have my AI operations cost today?": "AI_COST_SUMMARY",
        "Nova, what coding workers are available?": "WORKFORCE_STATUS",
        "Nova, what is my highest-value next action based on current Nexus data?": "DAILY_BRIEF",
    }
    for question, expected in variants.items():
        assert _canonical_awareness_capability(question) == expected

    state = AgentState(agent_id="hermes_nova", user_message=next(iter(variants)), metadata={"chat_id": 0})
    with patch("nexus_agent_platform.agents.nova.plan_query", side_effect=AssertionError("planner must not run")), \
         patch("nexus_agent_platform.capabilities.shared.execute_shared_capability", return_value={
             "status": "OK", "data": {"verified": True}, "provenance": {"source_type": "current_runtime_ledger"},
         }):
        result = _capability_gate(state)
    assert result.metadata["capability_gate"]["decision"] == "canonical_awareness"
    assert result.metadata["capability_gate"]["capability"] == "SYSTEM_HEALTH"


def test_workforce_and_loop_taxonomies_are_canonical_not_legacy_counts():
    from nexus_agent_platform.capabilities.operational_reads import read_operational_capability

    workers = read_operational_capability("WORKFORCE_STATUS")
    assert workers["status"] == "OK"
    worker_ids = {row["worker_id"] for row in workers["data"]["worker_pool"]}
    assert {"codex", "opencode", "local_python", "mimo", "kilo"}.issubset(worker_ids)
    loops = read_operational_capability("BUSINESS_LOOP_STATUS")
    assert loops["data"]["active_count"] == len(loops["data"]["loops"]) == 4
    assert not any("process" in key for key in loops["data"]["loops"])


def test_nova_default_presentation_is_concise_and_removes_report_scaffolding():
    from nexus_agent_platform.agents.nova import _present_response
    from nexus_agent_platform.adapters.state_adapter import AgentState

    state = AgentState(agent_id="hermes_nova", user_message="What do you think about the Tesla Model 3?", metadata={})
    answer = _present_response(state, """Pros:\n- quick and efficient\nCons:\n- minimalist controls\nConclusion: it is worth considering.\nFeel free to ask if you need more details.""")
    assert len(answer.split()) < 70
    assert not any(label in answer for label in ("Pros:", "Cons:", "Conclusion:", "Feel free to ask"))


def test_simple_canonical_answers_are_selected_not_dumped():
    from nexus_agent_platform.agents.nova import _present_response
    from nexus_agent_platform.adapters.state_adapter import AgentState

    cases = [
        ("How many production clients do I have?", "CLIENT_COUNT", {"production_total": 14, "active": 14, "onboarding": 0, "tester_or_certification": 24}, "14 production clients"),
        ("What opportunities are ACCEPT or WATCH?", "BUSINESS_OPPORTUNITIES", {"by_decision": {"ACCEPT": 27, "WATCH": 30}}, "27 ACCEPT and 30 WATCH"),
        ("What coding workers are available?", "WORKFORCE_STATUS", {"worker_pool": [{"worker_id": "codex", "status": "AVAILABLE"}, {"worker_id": "opencode", "status": "AVAILABLE"}, {"worker_id": "local_python", "status": "AVAILABLE"}, {"worker_id": "kilo", "status": "INSTALLED_UNPROVEN"}, {"worker_id": "mimo", "status": "INSTALLED_UNPROVEN"}]}, "Codex, OpenCode, and Local Python are available"),
    ]
    for question, capability, data, expected in cases:
        state = AgentState(agent_id="hermes_nova", user_message=question, metadata={"capability_result": {"query_type": capability, "status": "OK", "data": data}})
        answer = _present_response(state, '{"huge": "raw report"}')
        assert expected in answer
        assert "raw report" not in answer


def test_recommendation_is_prerequisite_aware_and_evidence_is_preserved():
    from nexus_agent_platform.agents.nova import _present_response
    from nexus_agent_platform.adapters.state_adapter import AgentState

    daily = {
        "query_type": "DAILY_BRIEF", "status": "OK",
        "data": {"highest_value_next_action": "Approve and complete the $97 checkout", "blockers": [{"blocker": "Stripe Checkout completion", "cause": "runtime keys must be reconciled"}]},
    }
    state = AgentState(agent_id="hermes_nova", user_message="What is my highest-value next action based on current Nexus data?", metadata={"capability_result": daily})
    answer = _present_response(state, "ignored model report")
    assert "reconcile the Stripe runtime to TEST keys" in answer
    assert "$97 test checkout comes after" in answer

    evidence_state = AgentState(agent_id="hermes_nova", user_message="Show me the evidence you used.", metadata={"capability_result": {"query_type": "provenance_followup", "status": "success", "data": {"stored_provenance": {"source_refs": ["reports/hermes_modernization/daily_brief.json", "reports/hermes_modernization/stripe_test_mode_proof.json"], "recommendation_rationale": "Stripe test-key reconciliation is first because the payment gate is BLOCKED_UNTIL_TEST_KEYS_RECONCILED."}}}})
    evidence = _present_response(evidence_state, "I don't have specific evidence.")
    assert "daily_brief.json" in evidence and "stripe_test_mode_proof.json" in evidence
    assert "I don't have specific evidence" not in evidence


def test_explicit_deep_dive_bypasses_default_compression():
    from nexus_agent_platform.agents.nova import _present_response
    from nexus_agent_platform.adapters.state_adapter import AgentState

    state = AgentState(agent_id="hermes_nova", user_message="Give me a detailed analysis of starting a trucking company including startup costs, risks, financing, business models, and market entry.", metadata={})
    detailed = "Pros:\nStartup costs\nRisks\nFinancing\nBusiness models\nMarket entry\nConclusion"
    assert _present_response(state, detailed) == detailed


def test_business_opportunity_result_excludes_process_actions_and_supports_empty_shape():
    from nexus_agent_platform.capabilities.operational_reads import _business_opportunities

    result = _business_opportunities()
    assert result["status"] == "OK"
    assert result["data"]["taxonomy"].startswith("BUSINESS_OPPORTUNITIES")
    assert all("system_health.run" not in str(item) for item in result["data"]["items"])
    assert all("repo_intelligence.scan" not in str(item) for item in result["data"]["items"])
    assert isinstance(result["data"]["by_decision"], dict)


def test_canonical_reads_have_real_current_sources_and_taxonomy():
    from nexus_agent_platform.capabilities.operational_reads import read_operational_capability

    loops = read_operational_capability("BUSINESS_LOOP_STATUS")
    assert loops["status"] == "OK"
    assert loops["data"]["active_count"] == 4
    assert set(loops["data"]["loops"]) == {
        "open_source_scout_loop", "seo_opportunity_loop",
        "revenue_opportunity_loop", "research_intake_loop",
    }

    opportunities = read_operational_capability("BUSINESS_OPPORTUNITIES")
    assert opportunities["status"] == "OK"
    assert opportunities["data"]["taxonomy"].startswith("BUSINESS_OPPORTUNITIES")

    alpha = read_operational_capability("ALPHA_LATEST")
    assert alpha["status"] == "OK"
    assert alpha["data"]["not_study_snapshot"] is True


def test_payment_gate_does_not_claim_test_mode_when_live_keys_are_reported():
    from nexus_agent_platform.capabilities.operational_reads import read_operational_capability

    result = read_operational_capability("PAYMENT_GATE")
    assert result["status"] == "OK"
    assert result["data"]["gate"] == "BLOCKED_UNTIL_TEST_KEYS_RECONCILED"
    assert result["data"]["stripe_mode"] == "NOT_CONFIRMED_TEST"
    assert result["data"]["no_live_revenue_recorded"] is True
    assert result["warnings"]


def test_supabase_session_table_contract_is_not_requests_session():
    from nexus_agent_platform.capabilities.supabase_read_client import GovernedSupabaseReadClient

    transport = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = [{"id": "r1"}]
    transport.get.return_value = response
    client = GovernedSupabaseReadClient("https://example.supabase.co", "test-key", transport)
    result = client.table("nexus_research_runs").select("id").order("created_at", desc=True).limit(1).execute()
    assert result.ok is True
    assert result.data == [{"id": "r1"}]
    assert transport.get.call_args.kwargs["params"]["select"] == "id"


def test_shared_read_layer_rejects_unapproved_table():
    from nexus_agent_platform.capabilities.supabase_read_client import GovernedSupabaseReadClient

    client = GovernedSupabaseReadClient("https://example.supabase.co", "test-key", MagicMock())
    try:
        client.table("arbitrary_table")
    except ValueError as exc:
        assert "not approved" in str(exc)
    else:
        raise AssertionError("unapproved table was accepted")
