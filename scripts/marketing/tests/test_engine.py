from __future__ import annotations

import pytest

from scripts.marketing import engine


def _handoff(opportunity_id="opp_test0000000000000000000000000000", *, ready=False):
    """A condensed, BO-shaped handoff. Hermetic: tests never touch the live DB."""
    return {
        "OPPORTUNITY_ID": opportunity_id,
        "WHAT_WE_ARE_MONETIZING": "Test monetization case",
        "WHY_NOW": "UNKNOWN",
        "TARGET_CUSTOMER": "SMB owners",
        "CUSTOMER_NEED": "Needs a reliable solution",
        "VALUE_PROPOSITION": "Fast, affordable outcome",
        "RECOMMENDED_MONETIZATION_MODEL": "AFFILIATE referral model",
        "ALTERNATIVE_MONETIZATION_MODELS": ["SERVICE"],
        "PRODUCT_SERVICE_PRICE": 100.0,
        "30_DAY_REVENUE_SCENARIO": {"REVENUE_RANGE": [500, 1500]},
        "60_DAY_REVENUE_SCENARIO": {"REVENUE_RANGE": [1000, 3000]},
        "90_DAY_REVENUE_SCENARIO": {"REVENUE_RANGE": [1500, 4500]},
        "ESTIMATED_TIME_TO_FIRST_REVENUE": {"ESTIMATED_RANGE_DAYS": [20, 45]},
        "PRIMARY_CHANNEL_OPPORTUNITIES": ["SEO_SEARCH_CONSOLE", "YOUTUBE"],
        "LOW_CAPITAL_TEST": {"TEST_DURATION": "14-30 days", "TRAFFIC_TARGET": 1000, "CONVERSION_TARGET": 20},
        "PAID_TEST_LIMIT": 100,
        "MARKETING_REQUIREMENTS": ["Landing page", "Tracking"],
        "CREATIVE_REQUIREMENTS": ["Hook video", "Offer page copy"],
        "PRIMARY_RISKS": ["PLATFORM_DEPENDENCY"],
        "EXTERNAL_BOUNDARIES": ["Affiliate account approval"],
        "MISSING_INPUTS": [] if ready else ["EXPECTED_CONVERSION (needs Research)"],
        "COMMERCIAL_RECOMMENDATION": "TEST" if ready else "RESEARCH_MORE",
        "HANDOFF_READY": ready,
    }


def test_schema_and_connection_registry_seeded(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    engine.initialize(path)
    conns = engine.connections(database_path=path)
    assert conns["count"] == len(engine._CONNECTION_SEED)
    # every connection names a revenue/market-intelligence workflow
    assert all(c["business_purpose"] for c in conns["connections"])
    # paid channels are approval-gated
    paid = [c for c in conns["connections"] if c["platform"].endswith("_ADS")]
    assert paid and all(c["approval_required"] == 1 for c in paid)


def test_intake_consumes_handoff_and_builds_full_plan(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    res = engine.intake("opp_test0000000000000000000000000000", handoff=_handoff(), database_path=path)
    assert res["status"] == "OK"
    c = res["campaign"]
    for f in ("audience", "positioning", "offer", "funnel", "landing_page_requirements", "cta",
              "organic_strategy", "paid_test", "attribution_plan", "measurement_plan",
              "creative_request", "forecast"):
        assert c[f], f
    assert c["primary_channel"] == "SEO_SEARCH_CONSOLE"
    assert c["alternative_channels"] == ["YOUTUBE"]
    assert c["recommended_next_action"] == "CONTINUE"  # no actuals yet


def test_organic_first_and_paid_approval_gate(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    res = engine.intake("opp_test0000000000000000000000000000", handoff=_handoff(), database_path=path)
    c = res["campaign"]
    assert c["organic_strategy"]["POLICY"].startswith("ORGANIC_FIRST")
    assert c["organic_strategy"]["CASH_REQUIRED"] == 0
    assert c["paid_test"]["APPROVAL_REQUIRED"] is True
    assert c["paid_test"]["MAXIMUM_SPEND"] == 100
    assert c["approval_required"] == 1


def test_creative_request_contract_complete(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    engine.intake("opp_test0000000000000000000000000000", handoff=_handoff(), database_path=path)
    cr = engine.creative_request(opportunity_id="opp_test0000000000000000000000000000",
                                 database_path=path)["creative_request"]["CREATIVE_REQUEST"]
    for f in ("AUDIENCE", "CUSTOMER_PROBLEM", "EMOTIONAL_DRIVER", "POSITIONING", "OFFER", "CHANNEL",
              "CONTENT_FORMAT", "HOOK", "MESSAGE", "CTA", "ASSET_REQUIREMENTS",
              "LANDING_PAGE_REQUIREMENTS", "CAMPAIGN_OBJECTIVE", "SUCCESS_METRIC"):
        assert f in cr, f
    assert cr["HARD_RULE"].startswith("CREATIVE CREATES")


def test_attribution_and_measurement_plans(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    c = engine.intake("opp_test0000000000000000000000000000", handoff=_handoff(), database_path=path)["campaign"]
    assert "OPPORTUNITY_ID" in c["attribution_plan"]["KEYS"]
    assert "UTM parameters" in c["attribution_plan"]["MECHANISMS"]
    assert "ROAS" in c["measurement_plan"]["TRACKED_METRICS"]
    assert c["measurement_plan"]["FORECAST_VS_ACTUAL_WINDOWS"] == ["30_DAY", "60_DAY", "90_DAY"]


def test_forecast_vs_actual_unknown_without_data(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    engine.intake("opp_test0000000000000000000000000000", handoff=_handoff(), database_path=path)
    perf = engine.performance("opp_test0000000000000000000000000000", database_path=path)
    assert perf["ACTUAL"]["RECORDS"] == 0
    assert perf["FORECAST_VS_ACTUAL"]["EXPECTED_30_DAY_REVENUE"] == [500, 1500]
    assert perf["FORECAST_VS_ACTUAL"]["ACTUAL_30_DAY_REVENUE"] == "UNKNOWN"


def test_recommendation_transitions_from_recorded_actuals(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    engine.intake(oid, handoff=_handoff(), database_path=path)
    # organic converting, no spend -> CONTINUE
    r1 = engine.record_performance(oid, "30_DAY", {"impressions": 1000, "clicks": 50, "conversions": 3,
                                                   "gross_revenue": 300, "ad_spend": 0}, database_path=path)
    assert r1["recommended_next_action"] == "CONTINUE"
    # strong paid ROAS -> SCALE
    r2 = engine.record_performance(oid, "30_DAY", {"clicks": 120, "conversions": 10, "gross_revenue": 1000,
                                                   "ad_spend": 200, "roas": 5.0}, database_path=path)
    assert r2["recommended_next_action"] == "SCALE"
    perf = engine.performance(oid, database_path=path)
    assert perf["LEDGER_ROWS"] == 2
    assert perf["FORECAST_VS_ACTUAL"]["ACTUAL_30_DAY_REVENUE"] == 1300.0


def test_recommendation_modify_and_hold(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    engine.intake(oid, handoff=_handoff(), database_path=path)
    # clicks but no conversions -> MODIFY
    r = engine.record_performance(oid, "LIVE", {"impressions": 500, "clicks": 40, "conversions": 0},
                                  database_path=path)
    assert r["recommended_next_action"] == "MODIFY"


def test_record_performance_never_fabricates(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    engine.intake(oid, handoff=_handoff(), database_path=path)
    engine.record_performance(oid, "LIVE", {"clicks": 10}, database_path=path)
    perf = engine.performance(oid, database_path=path)
    # only clicks supplied; revenue/spend stay UNKNOWN
    assert perf["ACTUAL"]["TOTAL_CLICKS"] == 10
    assert perf["ACTUAL"]["TOTAL_GROSS_REVENUE"] == "UNKNOWN"


def test_market_feedback_roundtrip(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    engine.intake(oid, handoff=_handoff(), database_path=path)
    engine.record_feedback("CUSTOMER_OBJECTION", "Too expensive vs incumbent", opportunity_id=oid, database_path=path)
    fb = engine.market_feedback(opportunity_id=oid, database_path=path)
    assert fb["count"] == 1
    assert fb["items"][0]["intel_type"] == "CUSTOMER_OBJECTION"


def test_nova_summary_and_approval_items(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    engine.intake(oid, handoff=_handoff(), database_path=path)
    ns = engine.nova_summary(opportunity_id=oid, database_path=path)["nova_summary"]
    for f in ("WHAT_WE_ARE_MONETIZING", "STATUS", "PRIMARY_CHANNEL", "APPROVAL_REQUIRED", "APPROVAL_ITEMS",
              "CREATIVE_REQUEST_READY", "ATTRIBUTION_PLAN_READY", "MEASUREMENT_PLAN_READY",
              "RECOMMENDED_NEXT_ACTION"):
        assert f in ns, f
    assert ns["APPROVAL_ITEMS"]  # publishing + paid test both gated
    assert "OPPORTUNITY_ID" not in ns  # suppressed by default


def test_internal_ids_suppressed_by_default(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    engine.intake(oid, handoff=_handoff(), database_path=path)
    plain = engine.get_campaign(opportunity_id=oid, database_path=path)["campaign"]
    assert "opportunity_id" not in plain and "campaign_id" not in plain
    diag = engine.get_campaign(opportunity_id=oid, database_path=path, include_internal_ids=True)["campaign"]
    assert diag["opportunity_id"] == oid


def test_intake_is_idempotent_per_opportunity(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    oid = "opp_test0000000000000000000000000000"
    a = engine.intake(oid, handoff=_handoff(), database_path=path)["campaign"]
    b = engine.intake(oid, handoff=_handoff(), database_path=path)["campaign"]
    # same opportunity -> same campaign record refreshed, not duplicated
    assert a["campaign_id"] == b["campaign_id"]
    lst = engine.list_campaigns(database_path=path)
    assert lst["count"] == 1


def test_health_and_data_authority(tmp_path):
    path = tmp_path / "marketing.sqlite3"
    engine.initialize(path)
    h = engine.health(database_path=path)
    assert h["status"] == "PASS"
    assert h["authority"]["LOCAL_SQLITE_IS_AUTHORITATIVE"] == "YES"
    assert h["authority"]["SUPABASE_IS_RAW_DATA_WAREHOUSE"] == "NO"
