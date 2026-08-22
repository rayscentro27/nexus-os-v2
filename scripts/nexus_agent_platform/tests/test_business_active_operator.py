import json

import pytest

import scripts.operations.business_active_operator as business
import scripts.operations.nexus_active_operator_runner as runner
from nexus_agent_platform.governed import action_registry, persistence


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))


def test_business_attention_prioritizes_opportunity_and_preserves_truth(monkeypatch):
    monkeypatch.setattr(business, "opportunity_portfolio", lambda: {"rankings": {"needs_ray": [{"opportunity_id": "opp-1", "title": "Review funding offer", "status": "NEEDS_RAY_REVIEW", "scores": {"overall_score": 82}, "evidence_refs": ["ev-1"]}], "needs_research": []}})
    monkeypatch.setattr(business, "growth_portfolio", lambda: {"counts": {"NEEDS_RAY_REVIEW": 0, "NEEDS_RESEARCH": 0, "MEASUREMENT_PENDING": 0}})
    monkeypatch.setattr(business, "list_growth_experiments", lambda: [])
    result = business.discover_business_attention()
    assert result["findings"][0]["priority"] == "P2"
    assert result["findings"][0]["truth_class"] == "EVIDENCE_BACKED"


def test_unknown_revenue_is_one_grouped_p3_finding(monkeypatch):
    monkeypatch.setattr(business, "opportunity_portfolio", lambda: {"rankings": {"needs_ray": [], "needs_research": []}})
    monkeypatch.setattr(business, "growth_portfolio", lambda: {"counts": {"NEEDS_RAY_REVIEW": 0, "NEEDS_RESEARCH": 0, "MEASUREMENT_PENDING": 0}})
    monkeypatch.setattr(business, "list_growth_experiments", lambda: [])
    monkeypatch.setattr(persistence, "latest_record", lambda collection: {"revenue_truth": "NOT_CONNECTED", "snapshot_id": "snap-1", "freshness": "CURRENT"} if collection == "revenue_snapshots" else None)
    result = business.discover_business_attention()
    rows = [row for row in result["findings"] if row["category"] == "revenue_measurement_connection_gap"]
    assert len(rows) == 1
    assert rows[0]["priority"] == "P3"
    assert "not zero" in rows[0]["reason"]


def test_source_failure_isolated(monkeypatch):
    monkeypatch.setattr(business, "opportunity_portfolio", lambda: (_ for _ in ()).throw(RuntimeError("unavailable")))
    monkeypatch.setattr(business, "growth_portfolio", lambda: {"counts": {"NEEDS_RAY_REVIEW": 0, "NEEDS_RESEARCH": 0, "MEASUREMENT_PENDING": 1}})
    monkeypatch.setattr(business, "list_growth_experiments", lambda: [])
    result = business.discover_business_attention()
    assert any(error.startswith("opportunity_engine:") for error in result["errors"])
    assert any(row["category"] == "growth_measurement_gap" for row in result["findings"])


def test_material_fingerprint_changes_and_brief_is_safe(tmp_path):
    one = business._finding(source_system="growth_operations", source_record_id="g1", category="growth_review", priority="P2", summary="Review", reason="old", truth_class="UNKNOWN", freshness="CURRENT", recommended_action="business_attention.review", action_class="APPROVAL_REQUIRED", approval_required=True, state={"status": "READY_FOR_REVIEW"})
    two = business._finding(source_system="growth_operations", source_record_id="g1", category="growth_review", priority="P2", summary="Review", reason="new", truth_class="UNKNOWN", freshness="CURRENT", recommended_action="business_attention.review", action_class="APPROVAL_REQUIRED", approval_required=True, state={"status": "NEEDS_RAY_REVIEW"})
    assert one["dedupe_key"] == two["dedupe_key"]
    assert one["finding_id"] != two["finding_id"]
    path = tmp_path / "brief.md"
    business.write_business_priority_brief({"generated_at": "now", "findings": [two], "sources": {"revenue_hub": "NOT_CONNECTED"}}, path)
    text = path.read_text()
    assert "external_action_performed=false" in text
    assert "SSN" not in text


def test_priority_policy_and_authority_firewall():
    assert runner.PRIORITY_RANK["P0"] < runner.PRIORITY_RANK["P2"] < runner.PRIORITY_RANK["P4"]
    assert action_registry.action_exists("business_attention.review")
    assert action_registry.is_action_executable("business_attention.review")
    for action in ("charge_customer", "send_customer_email", "send_sms", "post_to_social_media", "shell.arbitrary", "place_trade"):
        assert runner.classify_action(action) == "NOT_AUTHORIZED"


def test_hermes_business_answers_read_operator_outputs():
    heartbeat = {"operator_run_id": "run-1", "business_priorities": [{"priority": "P2", "approval_required": True, "summary": "Review"}]}
    answer = business.answer_business_question("What should I focus on today?", heartbeat=heartbeat)
    assert answer["type"] == "today_priorities"
    assert answer["priorities"][0]["priority"] == "P2"
    away = business.answer_business_question("What did Nexus do while I was away?", heartbeat=heartbeat, latest_receipt={"operator_run_id": "run-1", "business_safe_actions_executed": ["business_attention.generate"], "business_work_orders_created": []})
    assert away["safe_actions"] == ["business_attention.generate"]
    assert away["external_action_performed"] is False
