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
