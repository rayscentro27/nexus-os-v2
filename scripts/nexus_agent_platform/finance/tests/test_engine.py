from nexus_agent_platform.finance.engine import budget_check, break_even, campaign_preflight, record_cost


def test_break_even_is_explicit_when_inputs_are_unknown():
    assert break_even(100.0, None)["break_even_quantity"] == "UNKNOWN"
    assert break_even(100.0, 25.0)["break_even_quantity"] == 4


def test_budget_breaker_pauses_optional_consumption():
    result = budget_check({"cash_cost_usd": 11}, {"MAX_CASH_COST_USD": 10})
    assert result["state"] == "PAUSE_OPTIONAL_CONSUMPTION"
    assert result["overages"] == ["MAX_CASH_COST_USD"]


def test_campaign_preflight_preserves_unknown_revenue():
    result = campaign_preflight(campaign_id="campaign-test", upfront_cost=12, continuous_cost=0, max_validation_cost_usd=12, price="UNKNOWN", variable_cost="UNKNOWN")
    assert result["provenance"].startswith("ESTIMATED")
    assert result["scenarios"]["BASE"]["revenue"] == "UNKNOWN"


def test_cost_receipt_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    first = record_cost("receipt-test", department="FINANCE", cash_cost_usd=0)
    second = record_cost("receipt-test", department="FINANCE", cash_cost_usd=0)
    assert first["receipt_id"] == second["receipt_id"]
    assert second["idempotent"] is True
