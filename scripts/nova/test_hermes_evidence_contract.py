from hermes_evidence_contract import claim_feedback, evidence_state, turn_requirements


def test_explicit_multi_resource_request_is_scoped_to_current_turn():
    contract = turn_requirements("Using Nexus and current outside information, decide what to test.")
    assert contract["required_resources"] == ["NEXUS", "PUBLIC_WEB"]


def test_tool_execution_is_distinguished_from_prior_context():
    state = evidence_state("Using Nexus and current outside information, decide what to test.", [])
    assert state["missing_resources"] == ["NEXUS", "PUBLIC_WEB"]


def test_page_content_does_not_prove_affiliate_status_without_terms():
    prompt = "Find current affiliate programs and recommend one."
    messages = [{
        "name": "public_web_retrieval_shadow",
        "payload": {"url": "https://example.com/product", "content_length": 20, "content": "A financial product page."},
    }]
    state = evidence_state(prompt, messages)
    state["page_payloads"] = [messages[0]["payload"]]
    feedback = claim_feedback(prompt, "This is a verified affiliate program.", state)
    assert feedback["valid"] is False
    assert "affiliate_program_status" in feedback["unsupported_claims"]


def test_simple_conversation_has_no_resource_obligation():
    assert turn_requirements("What color is the sky?")["required_resources"] == []


def test_advice_urgency_does_not_force_web_research():
    contract = turn_requirements("What should I focus on to make money right now?")
    assert contract["required_resources"] == []
    assert contract["reasoning_first"] is True


def test_named_volatile_subject_requires_current_web_evidence():
    contract = turn_requirements("What is Tesla doing right now, and what do you think?")
    assert contract["required_resources"] == ["PUBLIC_WEB"]
    assert contract["fresh_execution_required"] is True


def test_unsupported_growth_language_is_not_current_evidence():
    prompt = "Check Nexus and current outside information and choose a business opportunity."
    state = evidence_state(prompt, [])
    feedback = claim_feedback(prompt, "Current trends show growing demand and significant interest.", state)
    assert feedback["valid"] is False
    assert "currentness_not_proven" in feedback["unsupported_claims"]


def test_no_tool_business_claim_requires_judgment_framing():
    state = evidence_state("What should I focus on to make money right now?", [])
    feedback = claim_feedback("What should I focus on to make money right now?", "This can create a reliable revenue stream.", state)
    assert feedback["valid"] is False
    assert "no_tool_evidence_attribution" in feedback["unsupported_claims"]


def test_qualified_no_tool_business_judgment_is_allowed():
    state = evidence_state("What should I focus on to make money right now?", [])
    feedback = claim_feedback("What should I focus on to make money right now?", "I think this could become a useful revenue stream, but that is my judgment.", state)
    assert feedback["valid"] is True


def test_completed_retrieval_rejects_stale_planning_language():
    prompt = "Check current outside information and choose a business opportunity."
    messages = [{
        "name": "public_web_retrieval_shadow",
        "payload": {"status": "ok", "currentness": "RECENT_BUT_NOT_CURRENT", "content": "Evidence."},
    }]
    state = evidence_state(prompt, messages)
    state["page_payloads"] = [messages[0]["payload"]]
    feedback = claim_feedback(prompt, "The URLs still need to be retrieved before I can assess this.", state)
    assert feedback["valid"] is False
    assert "retrieval_state_mismatch" in feedback["unsupported_claims"]


def test_brand_name_is_not_a_currentness_claim():
    prompt = "Check Nexus and current outside information and choose a business opportunity."
    state = evidence_state(prompt, [{
        "name": "public_web_retrieval_shadow",
        "payload": {"status": "ok", "currentness": "RECENT_BUT_NOT_CURRENT", "content_length": 40},
    }])
    state["page_payloads"] = [{"currentness": "RECENT_BUT_NOT_CURRENT"}]
    feedback = claim_feedback(prompt, "I would consider a partnership with Current, but the evidence is limited.", state)
    assert feedback["valid"] is True


def test_turn_objective_is_preserved_and_multi_resource_needs_synthesis():
    prompt = "Using Nexus and current outside information, choose a plan."
    contract = turn_requirements(prompt)
    state = evidence_state(prompt, [
        {"name": "nexus_read_shadow", "payload": {"status": "success"}},
        {"name": "public_web_search_shadow", "payload": {"results": [{"title": "source", "url": "https://example.com"}]}},
    ])
    assert contract["turn_objective"] == prompt
    assert state["synthesis_required"] is True


def test_prior_receipts_are_exposed_as_reused_evidence():
    prior = [{
        "source_turn_id": "turn-1", "resource": "NEXUS", "capability": "nexus_read_shadow",
        "request_id": "req-1", "result_id": "result-1", "artifact_id": None,
        "retrieved_at": "2026-08-31T00:00:00+00:00", "currentness": "live",
        "relevance": "prior_turn_followup", "valid_for_current_turn": True,
    }]
    state = evidence_state("Why do you prefer that?", [], prior)
    assert state["reused_evidence"][0]["result_id"] == "result-1"


def test_unrelated_turn_does_not_inherit_prior_nexus_referent():
    prior = [{"resource": "NEXUS", "capability": "nexus_get_system_health"}]
    assert turn_requirements("good morning", prior)["referent_capability"] == ""
    assert turn_requirements("my favorite is hazelnut", prior)["referent_capability"] == ""


def test_anaphoric_turn_preserves_prior_nexus_referent():
    prior = [{"resource": "NEXUS", "capability": "nexus_get_opportunities"}]
    contract = turn_requirements("Which of those are still active?", prior)
    assert contract["referent_capability"] == "nexus_get_opportunities"
