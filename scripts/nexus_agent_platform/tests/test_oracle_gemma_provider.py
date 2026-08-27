from nexus_agent_platform.oracle_cost_guard import evaluate
from nexus_agent_platform.oracle_gemma_provider import validate_review

def test_valid_bounded_review_preserves_deterministic_status():
    result = validate_review({"status":"NO_VALID_SETUP","risk":"LOW","recommendation":"Continue scanning.","evidence_refs":[]}, expected_status="NO_VALID_SETUP")
    assert result["valid"] is True

def test_made_up_status_is_rejected():
    assert validate_review({"status":"ALL_CLEAR_AND_TRADE","risk":"LOW","recommendation":"x","evidence_refs":[]})["valid"] is False

def test_authority_request_is_rejected():
    assert validate_review({"status":"NO_VALID_SETUP","risk":"LOW","recommendation":"Place an order now.","evidence_refs":[]})["valid"] is False

def test_cost_guard_never_grants_dollar_budget():
    assert evaluate(0.0)["status"] == "ORACLE_COST_HEALTHY"
    assert evaluate(0.01)["positive_cost_blocks_expansion"] is True
    assert evaluate(None, fresh=False)["status"] == "ORACLE_COST_UNKNOWN"
