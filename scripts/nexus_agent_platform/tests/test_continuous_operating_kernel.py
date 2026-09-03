import json

from nexus_agent_platform import continuous_operating_kernel as kernel


def test_incomplete_objective_has_next_action_and_owner():
    assert kernel.next_research_action(queue_empty=True, incomplete_objectives=1) == "CONTINUE_INCOMPLETE_OBJECTIVE"


def test_empty_queue_selects_discovery_without_stopping():
    assert kernel.next_research_action(queue_empty=True, incomplete_objectives=0) == "RUN_BOUNDED_AUTONOMOUS_DISCOVERY"


def test_alpha_weak_score_requests_targeted_research_then_rejects_branch():
    follow_up = kernel.alpha_feedback_decision(.31, ["independent confirmation"], revision=0)
    rejected = kernel.alpha_feedback_decision(.31, ["independent confirmation"], revision=2)
    assert follow_up["decision"] == "FOLLOW_UP_RESEARCH"
    assert rejected["decision"] == "REJECT_BRANCH_KEEP_PARENT_OPEN"
    assert rejected["parent_objective_remains_open"] is True


def test_resource_pressure_yields_and_auto_resumes():
    result = kernel.resource_decision(pressure=.9, checkpoint={"item": "source-1"})
    assert result["state"] == "YIELDING"
    assert result["research_enabled"] is True
    assert result["resume_without_manual_restart"] is True


def test_watchdog_requires_bounded_recovery_for_stale_enabled_loop():
    result = kernel.watchdog_decision(enabled=True, state="STOPPED", heartbeat_age_seconds=2000)
    assert result["status"] == "RECOVERY_REQUIRED"
    assert result["circuit_breaker"] is True


def test_weak_alpha_evidence_automatically_runs_one_followup():
    result = kernel.run_feedback_cycle(
        lambda: {"score": .3, "missing_evidence": ["independent source"]},
        lambda decision: {"status": "PASS", "used_gap": decision["missing_evidence"]},
    )
    assert result["alpha_decision"]["decision"] == "FOLLOW_UP_RESEARCH"
    assert result["followup"]["status"] == "PASS"
    assert result["objective_terminal"] is False


def test_watchdog_recovery_is_one_bounded_cycle():
    result = kernel.recover_loop(
        enabled=True, state="FAILED", heartbeat_age_seconds=2000,
        restart_fn=lambda: {"result": {"status": "PASS"}, "cycle_id": "recovered"},
    )
    assert result["status"] == "RECOVERED"
    assert result["attempts"] == 1
    assert result["bounded"] is True


def test_cycle_writes_active_heartbeat_and_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, "HEARTBEAT_PATH", tmp_path / "heartbeat.json")
    monkeypatch.setattr(kernel, "RECEIPT_PATH", tmp_path / "receipt.json")
    receipt = kernel.run_cycle(lambda: {"status": "PASS", "real_research": True}, cycle_id="c1", queue_empty=True)
    heartbeat = json.loads((tmp_path / "heartbeat.json").read_text())
    assert receipt["single_final_outcome"] is True
    assert heartbeat["enabled"] is True
    assert heartbeat["heartbeat"] == "ACTIVE"
    assert heartbeat["queue_empty_does_not_stop"] is True
