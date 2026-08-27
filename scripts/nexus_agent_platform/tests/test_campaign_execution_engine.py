from pathlib import Path

from nexus_agent_platform.campaign_execution_engine import campaign_status, run_campaign_cycle


def test_real_campaign_continuation_consumes_failure_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    state = tmp_path / "campaign.json"
    ledger = tmp_path / "ledger.jsonl"
    receipts = tmp_path / "receipts"
    objectives = [
        {"objective_id": "o1", "capability_id": "system.health", "test_only": True},
        {"objective_id": "o2", "capability_id": "system.health", "force_failure": True, "failure_signature": "bounded-timeout", "test_only": True},
        {"objective_id": "o3", "capability_id": "system.health", "test_only": True},
        {"objective_id": "o5", "capability_id": "system.health", "test_only": True},
    ]
    first = run_campaign_cycle(scheduler_instance="com.nexus.continuous-loop.certification", objectives=objectives, state_path=state, ledger_path=ledger, receipt_dir=receipts)
    assert {row["objective_id"] for row in first["objectives"]} == {"o1", "o2", "o3", "o5"}
    assert all(row["receiver_ack"] == "PASS" for row in first["objectives"])
    assert {row["objective_id"] for row in first["objectives"] if row["state"] == "COMPLETED"} == {"o1", "o3", "o5"}
    assert first["generated_work"] and first["campaign_health"] == "RECOVERING"
    second = run_campaign_cycle(scheduler_instance="com.nexus.continuous-loop.certification", state_path=state, ledger_path=ledger, receipt_dir=receipts)
    assert second["objectives"]
    assert second["objectives"][0]["state"] == "COMPLETED"
    assert second["objectives"][0]["verification"] == "PASS"
    assert campaign_status(state)["queued_executable_work"] == 0


def test_campaign_status_protects_false_active_state(tmp_path):
    state = tmp_path / "campaign.json"
    state.write_text('{"campaign_id":"c","status":"ACTIVE","objective_queue":[{"objective_id":"next"}],"active_work_orders":[],"recovering_objectives":[]}', encoding="utf-8")
    status = campaign_status(state)
    assert status["campaign_health"] == "RUNNING"
    assert status["active_executors"] == 0
    assert status["queued_executable_work"] == 1
