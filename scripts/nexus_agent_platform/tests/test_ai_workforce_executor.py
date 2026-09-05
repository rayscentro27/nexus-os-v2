import json

from nexus_agent_platform import ai_workforce_executor as worker
from nexus_agent_platform import nexus_command_acknowledgement as control


def test_model_plan_is_consumed_by_allowlisted_executor_and_review(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "RECEIPT_DIR", tmp_path)
    calls = []

    def fake_call(agent_id, messages, max_tokens=300):
        calls.append(agent_id)
        if agent_id.endswith("planner"):
            return {"model": "test-model", "usage": {"total_tokens": 10}, "content": json.dumps({
                "objective_id": "portal.admin_control_center",
                "next_action": "internal.capability_verify",
                "rationale": "verify the existing bounded local path",
                "completion_check": "verification artifact exists",
                "needs_human": False,
            })}
        return {"model": "test-model", "usage": {"total_tokens": 8}, "content": json.dumps({
            "result_quality": "PASS", "verified": True,
            "remaining_work": "continue missing criteria", "pushback": "none",
        })}

    monkeypatch.setattr(worker, "_call", fake_call)
    result = worker.run_ai_planned_verification(
        {"parent_goal": "portal.admin_control_center", "department": "Portal/Product", "question": "q", "summary": "s"},
        lambda finding: {"status": "PASS", "artifact_path": "reports/runtime/proof.json"},
    )
    assert result["status"] == "PASS"
    assert result["ai_model_invoked"] is True
    assert calls == ["nexus_ai_workforce_planner", "nexus_ai_workforce_reviewer"]
    assert (tmp_path / result["receipt_path"].split("/")[-1]).exists()


def test_nova_safe_assignment_is_allowlisted_and_durable(monkeypatch, tmp_path):
    monkeypatch.setattr(control, "SAFE_CONTROL_REQUESTS", tmp_path / "requests.jsonl")
    result = control.assign_safe_internal_work(
        goal_id="portal.admin_control_center",
        department="Portal/Product",
        summary="Queue bounded internal admin capability verification",
    )
    assert result["status"] == "QUEUED"
    assert result["assigned_worker_or_queue"] == "active_operator"
    record = json.loads((tmp_path / "requests.jsonl").read_text().splitlines()[0])
    assert record["action"] == "ai.plan_and_verify"
    assert record["external_side_effects"] is False
