"""Phase 15C shared-awareness and live-operator acceptance tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


QUESTIONS = {
    "Nexus, what opportunities are currently ACCEPT or WATCH?": "BUSINESS_OPPORTUNITIES",
    "Nexus, what research ran most recently?": "RESEARCH_HISTORY",
    "Nexus, when did the Revenue Opportunity loop last run?": "BUSINESS_LOOP_STATUS",
    "Nexus, show me the evidence you used for that answer.": "EVIDENCE_LOOKUP",
    "Nexus, what is the current payment gate?": "PAYMENT_GATE",
    "Nexus, what is the current client journey gate?": "CLIENT_JOURNEY_GATE",
    "Nexus, is Codex currently available?": "WORKFORCE_STATUS",
    "Nexus, what is the status of my business loops?": "BUSINESS_LOOP_STATUS",
    "Nexus, do you have governed access to Nexus OS data?": "get_runtime_capabilities",
    "Nexus, what is the highest-value next action?": "DAILY_BRIEF",
}


def test_hermes_exact_telegram_questions_use_deterministic_contracts():
    from nexus_agent_platform.agents.front_brain import classify_message

    for question, expected in QUESTIONS.items():
        decision = classify_message(question)
        assert decision["mode"] == "operational_read"
        assert decision["capability"] == expected


def test_nova_exact_telegram_questions_use_same_contracts():
    from nexus_agent_platform.agents.nova import _semantic_capability_gate

    for question, expected in QUESTIONS.items():
        result = _semantic_capability_gate(question)
        assert result is not None
        assert result[0] == expected


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
