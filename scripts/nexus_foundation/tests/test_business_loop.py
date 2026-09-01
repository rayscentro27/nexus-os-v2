import json
import os
import subprocess
import sys

from nexus_agent_platform.governed import persistence
from nexus_foundation.business_loop import run_mobile_detailing_loop
from nexus_foundation.contracts import load_organization, RESOURCE_PERMISSIONS, dependency_state


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


def test_business_loop_process_boundary_and_dependency_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    result = run_mobile_detailing_loop()
    env = dict(os.environ, PYTHONPATH="scripts", NEXUS_GOVERNED_DATA_DIR=str(tmp_path))
    check = subprocess.run([sys.executable, "-c", "from nexus_agent_platform.governed import persistence; r=persistence.get_record('loop_state', '%s', 'loop_id'); assert r['state']=='WAITING_REVIEW'; print('RELOADED')" % result["loop"]["loop_id"]], env=env, capture_output=True, text=True, check=True)
    assert check.stdout.strip() == "RELOADED"
    unavailable = dependency_state("approved_research", "DISCONNECTED", attempt=1, last_error="bounded_test_outage")
    waiting = {"status": "WAITING_DEPENDENCY", "dependency": unavailable["dependency"], "fabricated_result": False}
    restored = dependency_state("approved_research", "CONNECTED", attempt=2)
    assert waiting["status"] == "WAITING_DEPENDENCY" and waiting["fabricated_result"] is False
    assert restored["state"] == "CONNECTED" and restored["secret_present"] is False
