from __future__ import annotations

import json
import sqlite3

import pytest

from scripts.opportunities import engine


@pytest.fixture(autouse=True)
def isolate_default_database(monkeypatch, tmp_path):
    # Also isolate engine calls whose database path is supplied as a keyword;
    # candidate payloads are never allowed to select an arbitrary DB path.
    monkeypatch.setattr(engine, "DB_PATH", tmp_path / "opportunities.sqlite3")


def test_schema_contains_authoritative_opportunity_tables(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    engine.initialize(path)
    with sqlite3.connect(path) as con:
        names = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = con.execute("PRAGMA user_version").fetchone()[0]
    assert {"opportunities", "opportunity_sources", "opportunity_evidence",
            "opportunity_scores", "opportunity_risks", "opportunity_history"} <= names
    assert version == engine.SCHEMA_VERSION


def test_mobile_partner_fulfilled_service_is_accepted_and_preserves_delivery_fields(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    result = engine.submit({
        "title": "Mobile DNA testing business", "opportunity_type": "SERVICE",
        "subcategory": "LOCAL_PROFESSIONAL_SERVICE", "summary": "Mobile DNA collection with partner laboratory processing.",
        "delivery_model": "MOBILE_SERVICE", "online_offline_mix": "HYBRID",
        "geographic_scope": "Phoenix metro", "physical_presence_required": True,
        "partner_fulfilled": True, "licensed_partner_required": True,
        "facility_required": False, "local_marketing_dependency": "HIGH",
        "referral_partner_dependency": "HIGH", "source_type": "RAY_MANUAL",
        "verification_state": "UNVERIFIED", "database_path": path,
    })
    assert result["status"] in {"DISCOVERED", "NORMALIZED"}
    row = engine.get(result["opportunity_id"], database_path=path, include_internal_ids=True)
    assert row["delivery_model"] == "MOBILE_SERVICE"
    assert row["partner_fulfilled"] == 1
    assert row["facility_required"] == 0


def test_dedupe_uses_identity_and_source_not_title_only(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    base = {"title": "Scheduling service", "opportunity_type": "SAAS", "summary": "Scheduling for small teams.",
            "source_type": "NOVA_MANUAL", "verification_state": "UNVERIFIED", "database_path": path}
    first = engine.submit({**base, "candidate_name": "Shiftly", "website": "https://shiftly.example"})
    duplicate = engine.submit({**base, "title": "Shiftly team scheduling", "candidate_name": "Shiftly",
                               "website": "https://shiftly.example"})
    distinct = engine.submit({**base, "candidate_name": "Shiftly Pro", "website": "https://different.example"})
    assert first["opportunity_id"] == duplicate["opportunity_id"]
    assert duplicate["duplicate"] is True
    assert distinct["opportunity_id"] != first["opportunity_id"]


def test_evaluation_missing_evidence_keeps_research_more_and_unknown_revenue(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Mobile DNA testing business", "opportunity_type": "SERVICE",
        "subcategory": "LOCAL_PROFESSIONAL_SERVICE", "summary": "Partner-fulfilled mobile service.",
        "delivery_model": "MOBILE_SERVICE", "partner_fulfilled": True,
        "licensed_partner_required": True, "source_type": "RAY_MANUAL", "database_path": path})
    result = engine.evaluate(created["opportunity_id"], database_path=path)
    assert result["status"] == "NEEDS_RESEARCH"
    assert result["recommendation"] == "RESEARCH_MORE"
    assert result["assessment"]["30_days"]["revenue_range"] == "UNKNOWN"
    assert result["assessment"]["60_days"]["revenue_range"] == "UNKNOWN"
    assert result["assessment"]["90_days"]["revenue_range"] == "UNKNOWN"
    assert result["missing_evidence"]


def test_scoring_is_capped_and_every_score_run_is_retained(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Example referral software", "opportunity_type": "AFFILIATE",
        "summary": "Referral opportunity.", "source_type": "OPENAFFILIATE", "database_path": path})
    values = {"revenue_potential_score": 10, "monetization_probability_score": 10,
        "time_to_revenue_score": 10, "capability_fit_score": 10, "audience_fit_score": 10,
        "startup_cost_efficiency_score": 10, "automation_potential_score": 10,
        "competitive_barrier_score": 10, "evidence_quality_score": 10,
        "asset_light_bonus": 20}
    one = engine.score(created["opportunity_id"], values, database_path=path)
    two = engine.score(created["opportunity_id"], values, database_path=path)
    assert one["overall_score"] == 100
    assert two["overall_score"] <= 100
    assert engine.score_history_count(created["opportunity_id"], database_path=path) == 2


def test_scoring_requires_some_evaluable_dimensions(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Unscored idea", "opportunity_type": "OTHER", "summary": "Idea.",
        "source_type": "RAY_MANUAL", "database_path": path})
    result = engine.score(created["opportunity_id"], {}, database_path=path)
    assert result["status"] == "REJECTED"


def test_evidence_risk_and_lifecycle_are_persisted(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Local service", "opportunity_type": "SERVICE", "summary": "Local service.",
        "source_type": "RAY_MANUAL", "database_path": path,
        "risks": [{"risk_type": "PARTNER_DEPENDENCY", "severity": "MEDIUM", "description": "Partner availability requires verification."}]})
    attached = engine.attach_evidence(created["opportunity_id"], {"claim_type": "LOCAL_DEMAND",
        "claim": "Local demand exists", "evidence_value": "Not yet verified", "evidence_quality": "LOW",
        "verification_state": "UNVERIFIED"}, database_path=path)
    assert attached["status"] == "ATTACHED"
    state = engine.update_state(created["opportunity_id"], "NEEDS_RESEARCH", "Evidence remains incomplete.", database_path=path)
    assert state["status"] == "NEEDS_RESEARCH"
    details = engine.get(created["opportunity_id"], database_path=path, include_internal_ids=True)
    assert details["risks"][0]["risk_type"] == "PARTNER_DEPENDENCY"
    assert any(item["event_type"] == "STATE_CHANGED" for item in details["history"])


def test_research_request_uses_existing_idempotent_interface(monkeypatch, tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "DNA collection service", "opportunity_type": "SERVICE",
        "summary": "Mobile DNA collection via licensed lab partner.", "source_type": "RAY_MANUAL", "database_path": path})
    calls = []
    def fake_request(objective, question):
        calls.append({"objective": objective, "question": question})
        return {"status": "queued", "objective_id": "internal-objective", "work_id": "internal-work",
                "durable_job_id": "internal-job", "durable_job_state": "READY"}
    monkeypatch.setattr(engine, "_request_research", fake_request)
    first = engine.request_research(created["opportunity_id"], ["LOCAL_DEMAND", "REGULATORY_REQUIREMENT"], database_path=path)
    second = engine.request_research(created["opportunity_id"], ["LOCAL_DEMAND", "REGULATORY_REQUIREMENT"], database_path=path)
    assert first["status"] == "RESEARCH_PENDING"
    assert second["status"] == "RESEARCH_PENDING"
    assert len(calls) == 1
    assert "NEXUS_RESEARCH_DELIVERABLE_V1" in calls[0]["question"]
    assert "AFFILIATE_RESELLER_WHITE_LABEL_OPTIONS" in calls[0]["question"]
    assert "OPEN_SOURCE_GITHUB_API_OPTIONS" in calls[0]["question"]
    assert "same-assignment continuation" in calls[0]["question"]
    assert len(calls[0]["question"]) <= 1600
    assert engine.get(created["opportunity_id"], database_path=path)["status"] == "RESEARCH_PENDING"


def test_normal_presentation_suppresses_internal_ids():
    from services.nexus_mcp.opportunities_operator import _public
    payload = {"opportunity_id": "opp_" + "a" * 32, "source_id": "source-secret",
        "research_job_id": "job_123456789", "title": "Service",
        "score_id": "score_" + "b" * 32,
        "history": [{"metadata": {"research_source_id": "src_" + "c" * 32,
                                    "research_objective_id": "nova_research_1234567890abcdef"}}],
        "identity": {"external_id": "upstream-slug", "partner_program_id": "partner-slug"},
        "candidate_identity": "private-normalized-dedupe-key",
        "summary": "Research ref job_123456789 is pending."}
    shown = json.dumps(_public(payload))
    for hidden in ("opp_", "source-secret", "research_job_id", "job_123456789", "score_", "research_source_id",
                   "src_", "research_objective_id", "nova_research_1234567890abcdef"):
        assert hidden not in shown


def test_get_decodes_and_suppresses_nested_research_ids(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Metadata sanitizer case", "opportunity_type": "OTHER",
        "summary": "A sanitizer contract fixture.", "source_type": "RAY_MANUAL"}, database_path=path)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO opportunity_history VALUES (?,?,?,?,?,?,?,?,?)", (
            "evt_" + "d" * 32, created["opportunity_id"], "TEST_METADATA", None, None,
            "TEST", "Sanitizer fixture.", json.dumps({"research_source_id": "src_" + "e" * 32}), engine.now()))
    result = json.dumps(engine.get(created["opportunity_id"], database_path=path))
    assert "metadata_json" not in result
    assert "research_source_id" not in result
    assert "src_" not in result
    assert "identity" not in result
    assert "candidate_identity" not in result


def test_read_and_action_tool_allowlists_include_opportunities():
    from services.nexus_mcp.auth import authorize_action, authorize_read
    for name in ("opportunities_health", "opportunities_status", "opportunities_search"):
        authorize_read(name)
    for name in ("opportunities_submit", "opportunities_request_research", "opportunities_score"):
        authorize_action(name)


def test_github_opportunity_cannot_be_marked_verified_before_research(tmp_path):
    result = engine.submit({"title": "Unverified GitHub lead", "opportunity_type": "SAAS",
        "summary": "A claim from a public list.", "source_type": "GITHUB",
        "verification_state": "VERIFIED", "database_path": tmp_path / "opportunities.sqlite3"})
    assert result["status"] == "REJECTED"
    assert "RESEARCH_VERIFICATION" in result["reason"]


def test_repeated_evaluation_does_not_duplicate_the_same_risk(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Mobile partner service", "opportunity_type": "SERVICE",
        "summary": "A local service fulfilled by a partner.", "delivery_model": "MOBILE_SERVICE",
        "partner_fulfilled": True, "source_type": "RAY_MANUAL", "database_path": path})
    engine.evaluate(created["opportunity_id"], database_path=path)
    engine.evaluate(created["opportunity_id"], database_path=path)
    detail = engine.get(created["opportunity_id"], database_path=path, include_internal_ids=True)
    kinds = [risk["risk_type"] for risk in detail["risks"]]
    assert kinds.count("PARTNER_DEPENDENCY") == 1
    assert kinds.count("REGULATORY") == 1


def test_openaffiliate_adapter_normalizes_public_query_fields(monkeypatch):
    from scripts.opportunities.source_adapters import openaffiliate
    monkeypatch.setattr(openaffiliate, "_get", lambda *args, **kwargs: {
        "total": 1,
        "programs": [{
            "slug": "example-saas", "name": "Example SaaS", "category": "Business Operations",
            "verified": True, "commission": {"type": "recurring", "rate": "20%"},
            "cookieDays": 30, "approval": "manual approval",
            "restrictions": ["No paid brand bidding"], "url": "https://example.test/affiliates",
        }],
    })
    result = openaffiliate.search(keyword="small business software", category="Business Operations", limit=4)
    item = result["programs"][0]
    assert item["source_external_id"] == "example-saas"
    assert item["verification_state"] == "VERIFIED"
    assert item["metadata"]["commission"]["rate"] == "20%"
    assert item["metadata"]["cookie_duration_days"] == 30
    assert item["metadata"]["approval_requirements"] == "manual approval"
    assert item["metadata"]["restrictions"] == ["No paid brand bidding"]


def test_existing_nexus_mcp_registers_all_opportunities_tools():
    from services.nexus_mcp import server
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    expected = {
        "opportunities_health", "opportunities_status", "opportunities_list", "opportunities_get",
        "opportunities_search", "opportunities_top", "opportunities_latest", "opportunities_scorecard",
        "opportunities_evidence", "opportunities_needs_research", "opportunities_history",
        "opportunities_submit", "opportunities_evaluate", "opportunities_score",
        "opportunities_update_state", "opportunities_attach_evidence", "opportunities_request_research",
    }
    assert expected <= names


def _complete_research_package():
    from research.notebook_completion_contracts import BUSINESS_OPPORTUNITY_DELIVERABLES
    return {
        "from_engine": "RESEARCH", "to_engine": "BUSINESS_OPPORTUNITIES",
        "case_id": "existing-dna-assignment", "summary_version": "research-handoff-v1",
        "executive_summary": "Evidence-backed public research package.",
        "deliverables": {key: {"status": "COMPLETE", "summary": f"Finding for {key}.",
            "sources": ["https://example.gov/source"]} for key in BUSINESS_OPPORTUNITY_DELIVERABLES},
        "evidence_count": 25, "generated_at": "2026-11-06T00:00:00Z",
    }


def test_research_receiver_rejects_exact_missing_deliverables_and_is_idempotent(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Mobile DNA testing business", "opportunity_type": "SERVICE",
        "summary": "Mobile collection using a qualified external lab.", "source_type": "RAY_MANUAL",
        "database_path": path})
    handoff = _complete_research_package()
    del handoff["deliverables"]["MARKET_DEMAND"]
    first = engine.accept_research_handoff(created["opportunity_id"], handoff,
        research_work_id="existing-dna-work", database_path=path)
    second = engine.accept_research_handoff(created["opportunity_id"], handoff,
        research_work_id="existing-dna-work", database_path=path)
    assert first["status"] == "REJECTED"
    assert first["missing_requirements"] == ["MARKET_DEMAND"]
    assert second["already_recorded"] is True
    assert engine.get(created["opportunity_id"], database_path=path)["status"] == created["status"]


def test_research_receiver_accepts_complete_package_without_duplicate_receipt(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    created = engine.submit({"title": "Mobile DNA testing business", "opportunity_type": "SERVICE",
        "summary": "Mobile collection using a qualified external lab.", "source_type": "RAY_MANUAL",
        "database_path": path})
    handoff = _complete_research_package()
    result = engine.accept_research_handoff(created["opportunity_id"], handoff,
        research_work_id="existing-dna-work", database_path=path)
    assert result["status"] == "ACCEPTED"
    assert result["current_stage"] == "BUSINESS_OPPORTUNITIES"
    assert engine.get(created["opportunity_id"], database_path=path)["status"] == "UNDER_REVIEW"
    assert engine.accept_research_handoff(created["opportunity_id"], handoff,
        research_work_id="existing-dna-work", database_path=path)["already_recorded"] is True


# ---------------------------------------------------------------------------
# Commercial synthesis layer (additive capabilities).
# ---------------------------------------------------------------------------

def _supported_commercial_opportunity(path):
    details = {
        "selling_price": 100.0, "variable_cost_per_unit": 40.0,
        "customer_acquisition_cost": 10.0, "ongoing_fixed_cost": 200.0,
        "conversion_rate": 0.02,
        "scenarios": {
            "downside": {"traffic": 500, "conversion_rate": 0.01, "average_revenue": 100,
                         "variable_cost": 40, "marketing_cost": 50},
            "base": {"traffic": 1000, "conversion_rate": 0.02, "average_revenue": 100,
                     "variable_cost": 40, "marketing_cost": 100},
            "upside": {"traffic": 2000, "conversion_rate": 0.03, "average_revenue": 100,
                       "variable_cost": 40, "marketing_cost": 150},
        },
        "time_to_launch_days": {"min": 14, "max": 30},
        "nexus_launch_days": {"min": 7, "max": 14},
        "external_wait_days": {"min": 7, "max": 21},
        "launch_requirements": ["Offer page", "Payment setup"],
        "time_to_first_revenue_days": {"min": 20, "max": 45},
        "required_traffic": 1000, "channels": ["SEO", "Referral"],
        "low_capital_test": {"paid_test_limit": 100},
    }
    return engine.submit({
        "title": "Commercial Synthesis Svc", "opportunity_type": "SERVICE",
        "summary": "temp", "delivery_model": "REMOTE_SERVICE", "target_customer": "SMB owners",
        "revenue_model": "Flat service fee", "startup_cost_estimate": 500.0,
        "time_to_first_revenue_days": 30, "revenue_details": details,
        "source_type": "RAY_MANUAL", "verification_state": "UNVERIFIED",
    }, database_path=path)["opportunity_id"]


def test_unit_economics_derives_only_supported_numbers(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    ue = engine.unit_economics(oid, database_path=path)
    assert ue["GROSS_PROFIT_PER_UNIT_OR_CONVERSION"] == 60.0
    assert ue["GROSS_MARGIN_PERCENT"] == 60.0
    assert ue["CONTRIBUTION_MARGIN"] == 50.0
    assert ue["FIXED_STARTUP_COST"] == 500.0
    assert ue["MISSING_INPUTS"] == []


def test_unit_economics_never_fabricates_and_names_missing_inputs(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = engine.submit({"title": "Bare Svc", "opportunity_type": "SERVICE", "summary": "x",
        "delivery_model": "REMOTE_SERVICE", "source_type": "RAY_MANUAL",
        "verification_state": "UNVERIFIED"}, database_path=path)["opportunity_id"]
    ue = engine.unit_economics(oid, database_path=path)
    assert ue["SELLING_PRICE_OR_REVENUE_PER_CONVERSION"] == "UNKNOWN"
    assert ue["GROSS_PROFIT_PER_UNIT_OR_CONVERSION"] == "UNKNOWN"
    assert any("SELLING_PRICE" in m for m in ue["MISSING_INPUTS"])


def test_break_even_and_scenarios(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    be = engine.break_even(oid, database_path=path)
    assert be["BREAK_EVEN_UNITS_OR_CONVERSIONS"] == 14
    assert be["BREAK_EVEN_REVENUE"] == 1400.0
    assert be["BREAK_EVEN_TRAFFIC_OR_LEADS"] == 700
    assert be["BASE_SCENARIO"]["ESTIMATED_NET_RESULT"] == 1100.0
    assert be["DOWNSIDE_SCENARIO"]["ESTIMATED_NET_RESULT"] != "UNKNOWN"
    assert be["UPSIDE_SCENARIO"]["ESTIMATED_NET_RESULT"] != "UNKNOWN"


def test_break_even_scenarios_unknown_without_inputs(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = engine.submit({"title": "Bare Svc 2", "opportunity_type": "SERVICE", "summary": "x",
        "delivery_model": "REMOTE_SERVICE", "source_type": "RAY_MANUAL",
        "verification_state": "UNVERIFIED"}, database_path=path)["opportunity_id"]
    be = engine.break_even(oid, database_path=path)
    assert be["BREAK_EVEN_UNITS_OR_CONVERSIONS"] == "UNKNOWN"
    assert be["BASE_SCENARIO"]["STATUS"] == "UNKNOWN"


def test_revenue_30_60_90_scenarios(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    rs = engine.revenue_scenarios(oid, database_path=path)
    for key in ("30_DAY_REVENUE_SCENARIO", "60_DAY_REVENUE_SCENARIO", "90_DAY_REVENUE_SCENARIO"):
        assert key in rs
        assert rs[key]["REVENUE_RANGE"] != "UNKNOWN"
    assert rs["90_DAY_REVENUE_SCENARIO"]["EXPECTED_NET_RESULT"] != "UNKNOWN"


def test_time_to_launch_splits_nexus_and_external(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    ttl = engine.time_to_launch(oid, database_path=path)
    est = ttl["ESTIMATED_TIME_TO_LAUNCH"]
    assert est["ESTIMATED_RANGE_DAYS"] == [14, 30]
    assert est["NEXUS_CONTROLLED_WORK_DAYS"] == [7, 14]
    assert est["EXTERNAL_WAITING_DAYS"] == [7, 21]


def test_time_to_first_revenue_estimate(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    ttfr = engine.time_to_first_revenue(oid, database_path=path)
    assert ttfr["ESTIMATED_TIME_TO_FIRST_REVENUE"]["ESTIMATED_RANGE_DAYS"] == [20, 45]
    assert ttfr["REQUIRED_TRAFFIC_OR_LEAD_EVENT"] == 1000.0


def test_low_capital_test_preserves_organic_first(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    lct = engine.low_capital_test(oid, database_path=path)
    assert lct["CASH_REQUIRED"] == 0
    assert lct["PHILOSOPHY"].startswith("ORGANIC_FIRST")
    assert lct["NEXT_ACTION_IF_SUCCESS"].startswith("SMALL_PAID_TEST_IF_JUSTIFIED")
    assert lct["PAID_TEST_LIMIT"] == 100


def test_marketing_handoff_is_complete_and_supabase_safe(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    mh = engine.marketing_handoff(oid, database_path=path)
    for field in ("OPPORTUNITY_ID", "WHAT_WE_ARE_MONETIZING", "RECOMMENDED_MONETIZATION_MODEL",
                  "UNIT_ECONOMICS", "BREAK_EVEN_MODEL", "DOWNSIDE_BASE_UPSIDE_SCENARIOS",
                  "30_DAY_REVENUE_SCENARIO", "60_DAY_REVENUE_SCENARIO", "90_DAY_REVENUE_SCENARIO",
                  "ESTIMATED_TIME_TO_LAUNCH", "ESTIMATED_TIME_TO_FIRST_REVENUE", "LOW_CAPITAL_TEST",
                  "PAID_TEST_LIMIT", "MARKETING_REQUIREMENTS", "CREATIVE_REQUIREMENTS",
                  "PRIMARY_RISKS", "EXTERNAL_BOUNDARIES", "MISSING_INPUTS", "COMMERCIAL_RECOMMENDATION"):
        assert field in mh, field
    assert mh["LOCAL_SQLITE_IS_AUTHORITATIVE"] == "YES"
    assert mh["SUPABASE_IS_COORDINATION_LAYER"] == "YES"
    assert mh["RAW_RESEARCH_SENT_TO_SUPABASE"] == "NO"
    assert mh["HANDOFF_READY"] is True


def test_marketing_handoff_suppresses_internal_id_by_default(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = _supported_commercial_opportunity(path)
    assert "OPPORTUNITY_ID" not in engine.marketing_handoff(oid, database_path=path, include_internal_ids=False)
    assert engine.marketing_handoff(oid, database_path=path, include_internal_ids=True)["OPPORTUNITY_ID"] == oid


def test_commercial_synthesis_is_read_only_for_missing_data(tmp_path):
    path = tmp_path / "opportunities.sqlite3"
    oid = engine.submit({"title": "RO Svc", "opportunity_type": "SERVICE", "summary": "x",
        "delivery_model": "REMOTE_SERVICE", "source_type": "RAY_MANUAL",
        "verification_state": "UNVERIFIED"}, database_path=path)["opportunity_id"]
    before = engine.get(oid, database_path=path)["status"]
    engine.unit_economics(oid, database_path=path)
    engine.break_even(oid, database_path=path)
    engine.marketing_handoff(oid, database_path=path)
    assert engine.get(oid, database_path=path)["status"] == before
