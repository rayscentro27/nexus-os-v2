from scripts.nexus_agent_platform.finance.foundation import financial_event, proposal_economics


def test_financial_event_preserves_truth_class_and_direction():
    event = financial_event(event_type="model_usage", value_class="ESTIMATED", direction="EXPENSE", source="receipt")
    assert event["value_class"] == "ESTIMATED"
    assert event["direction"] == "EXPENSE"
    assert event["verified"] is False


def test_zero_cost_proposal_has_no_purchase_authority():
    proposal = proposal_economics(proposal_id="x", owner="Systems", purpose="test", one_time_cost=0, recurring_cost=0, estimated_usage_cost=0)
    assert proposal["economic_status"] == "ZERO_COST"
    assert proposal["purchase_authorized"] is False


def test_unknown_costs_are_not_coerced_to_zero():
    proposal = proposal_economics(proposal_id="x", owner="Systems", purpose="test")
    assert proposal["economic_status"] == "INSUFFICIENT_EVIDENCE"
