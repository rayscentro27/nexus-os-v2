from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nexus_agent_platform.proactive_objectives import (
    FAMILIES,
    choose_next_objective,
    hacker_news_default_guard,
    repetition_regression_guard,
)


def test_all_customer_first_families_have_structured_policy_and_no_hn_default():
    required = {"CUSTOMER_NEEDS", "CUSTOMER_COMPLAINTS", "BUSINESS_OPPORTUNITIES",
                "AFFILIATE_OPPORTUNITIES", "FUNDING_GRANTS", "SEO_MARKET_DEMAND",
                "TECHNOLOGY_FOR_NEXUS", "TRADING_INTELLIGENCE", "VIRAL_COMMERCIAL_TRENDS",
                "COMPETITOR_GAPS"}
    assert required <= {row["family"] for row in FAMILIES}
    assert all(row.get("business_reason") and row.get("target") and row.get("question")
               and row.get("queries") and row.get("source_class") and row.get("useful") for row in FAMILIES)
    assert hacker_news_default_guard()


def test_zero_finding_family_saturates_and_rotation_selects_another_family():
    at = datetime.now(timezone.utc)
    first = choose_next_objective(history=[], at=at)
    history = [{"objective_family": first["objective_family"], "query": first["query"],
                "source_class": first["source_class"], "qualified_findings": 0,
                "saturation_state": "SATURATED_RECENTLY", "follow_up_created": False,
                "last_run_at": at.isoformat()}]
    second = choose_next_objective(history=history, at=at + timedelta(minutes=1))
    assert second["objective_family"] != first["objective_family"]
    assert second["source_class"] != "HACKER_NEWS"


def test_repetition_guard_rejects_repeated_empty_same_family_runs():
    at = datetime.now(timezone.utc).isoformat()
    rows = [{"objective_family": "CUSTOMER_NEEDS", "query": "small business funding unmet demand",
             "source_class": "WEB_SEARCH", "qualified_findings": 0, "last_run_at": at}
            for _ in range(4)]
    assert repetition_regression_guard(rows, n=4) is False


def test_historical_hn_evidence_does_not_fail_default_guard():
    assert hacker_news_default_guard()
