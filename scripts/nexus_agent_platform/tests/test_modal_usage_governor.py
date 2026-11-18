import pytest

from scripts.nexus_agent_platform.modal_usage_governor import (
    evaluate_monthly_budget, parse_billing_summary, preflight_modal_job,
)


def test_modal_budget_bands_and_reservations():
    assert evaluate_monthly_budget(proposed_job_usd=0.1, confirmed_usage_usd=10).band == "NORMAL"
    assert evaluate_monthly_budget(proposed_job_usd=0.1, confirmed_usage_usd=21).band == "WARNING"
    assert evaluate_monthly_budget(proposed_job_usd=0.1, confirmed_usage_usd=27).band == "CONSERVE"
    assert evaluate_monthly_budget(proposed_job_usd=0.1, confirmed_usage_usd=30).status == "WAITING_APPROVAL"
    assert evaluate_monthly_budget(proposed_job_usd=0.1, confirmed_usage_usd=20,
                                   estimated_usage_usd=2, reserved_usage_usd=1).band == "WARNING"


def test_unknown_cost_or_provider_usage_is_not_zero():
    assert preflight_modal_job(proposed_job_usd=None, confirmed_usage_usd=0)["status"] == "WAITING_APPROVAL"
    assert preflight_modal_job(proposed_job_usd=0.1, confirmed_usage_usd=None)["status"] == "WAITING_APPROVAL"


def test_job_ceiling_requires_approval():
    result = evaluate_monthly_budget(proposed_job_usd=5.01, confirmed_usage_usd=0)
    assert result.status == "WAITING_APPROVAL"
    assert result.band == "JOB_CEILING"


def test_billing_parser_uses_metered_not_net_billed_amount():
    assert parse_billing_summary({"metered_cost": 1.66, "billed_cost": 0}) == 1.66
    with pytest.raises(ValueError, match="USAGE_UNKNOWN"):
        parse_billing_summary({"billed_cost": 0})
