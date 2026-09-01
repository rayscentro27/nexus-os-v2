import json

from nexus_agent_platform.governed import persistence
from nexus_foundation.business_loop import run_mobile_detailing_loop
from nexus_foundation.contracts import load_organization, RESOURCE_PERMISSIONS


def test_mobile_detailing_business_loop_is_durable_and_honest(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    result = run_mobile_detailing_loop()
    assert result["status"] == "PASS"
    assert result["idea"]["status"] == "OPPORTUNITY_ACCEPT_FOR_VALIDATION"
    assert result["decision"]["recommendation"] == "ACCEPT_FOR_VALIDATION"
    assert result["launch"]["status"] == "WAITING_REVIEW"
    assert result["launch"]["not_launched"] is True
    assert result["external_actions"] == {"ad_spend": False, "publishing": False, "outreach": False, "payments": False, "deployment": False}
    assert result["economics"]["scenarios"]["BASE"]["monthly_revenue"] == 10890
    assert result["economics"]["scenarios"]["BASE"]["break_even_jobs_per_month"] == 24
    assert len(result["research"]["sources"]) == 5
    assert result["challenge"]["status"] == "PASS"
    assert all(order["status"] == "COMPLETED" for order in result["work_orders"])
    assert all(order["receipt_refs"] for order in result["work_orders"])
    assert persistence.get_record("business_ideas", result["idea"]["idea_id"], "idea_id")
    assert persistence.get_record("launch_candidates", result["launch"]["launch_candidate_id"], "launch_candidate_id")
    assert persistence.get_record("loop_state", result["loop"]["loop_id"], "loop_id")["state"] == "WAITING_REVIEW"
    assert result["cost"]["research_calls"] == 5
    assert result["cost"]["retries"] == 0


def test_business_loop_reload_and_authority_boundaries(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    result = run_mobile_detailing_loop()
    assert len(persistence.read_records("business_ideas")) == 2  # initial + state update
    assert len(persistence.read_records("business_research")) == 3
    assert len(persistence.read_records("work_orders")) == 4  # immutable assignment/terminal records for the executed chain
    assert json.loads(json.dumps(result["loop"]))["next_step"] == "GOVERNED_VALIDATION"
    assert RESOURCE_PERMISSIONS["ALPHA"]["nexus"] == "read"
    assert "live_trading" not in RESOURCE_PERMISSIONS["TRADING_ENGINE"] or RESOURCE_PERMISSIONS["TRADING_ENGINE"]["live_trading"] == "none"
