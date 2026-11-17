from __future__ import annotations

import json

import pytest

from scripts.nexus_agent_platform.durable_jobs import DurableJobStore
from scripts.nexus_agent_platform.workflow_fabric import (
    WorkflowController, WorkflowStateStore, context_packet, continue_workflow, new_workflow,
)


def _workflow():
    return new_workflow(objective="Prepare a draft GoClear campaign", owner="RAY", created_by="RAY")


def test_worker_cannot_terminate_workflow_and_partial_is_preserved():
    workflow = _workflow()
    step = workflow["steps"][0]
    result = continue_workflow(workflow, step, {"status": "FAILED_TERMINAL_SYSTEM", "partial_output": {"draft": 1}})
    assert result["workflow_status"] != "FAILED_TERMINAL_SYSTEM"
    result = continue_workflow(workflow, step, {"status": "PARTIAL", "partial_output": {"draft": 1}})
    assert result["preserve_partial"] is True


def test_retry_policy_uses_same_worker_then_model_fallback():
    workflow = _workflow()
    step = workflow["steps"][0] | {"attempt_count": 0, "max_retries": 2, "fallback_model_profile": "ROUTING_LIGHT"}
    assert continue_workflow(workflow, step, {"status": "RETRY"})["decision"] == "RETRY_SAME_WORKER"
    step["attempt_count"] = 2
    assert continue_workflow(workflow, step, {"status": "RETRY"}, available_models={"ROUTING_LIGHT"})["decision"] == "RETRY_ALTERNATE_MODEL_PROFILE"


def test_approval_wait_and_budget_continuation():
    workflow = _workflow()
    step = {"approval_required": True, "attempt_count": 0, "max_retries": 1}
    assert continue_workflow(workflow, step, {"status": "COMPLETE"})["workflow_status"] == "WAITING_APPROVAL"
    assert continue_workflow(workflow, step, {"status": "RESOURCE_BUDGET_EXCEEDED"})["workflow_status"] == "PARTIAL"


def test_approval_gate_does_not_certify_step_complete():
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")))
    workflow = _workflow()
    step = workflow["steps"][-1] | {"approval_required": True}
    result = controller.record_result(workflow, step, {"status": "COMPLETE"})
    assert result["step_status"] == "WAITING_APPROVAL"
    assert workflow["last_certified_step"] is None


def test_asset_persistence_requires_canonical_r2_and_metadata_receipts():
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")))
    workflow = _workflow()
    step = next(s for s in workflow["steps"] if s["bot_id"] == "ASSET_PERSISTENCE")
    result = controller.record_result(workflow, step, {"status": "COMPLETE", "asset_id": "temporary-only"})
    assert result["step_status"] == "PARTIAL"
    assert step["result"]["error_code"] == "CANONICAL_ASSET_PERSISTENCE_INCOMPLETE"


def test_durable_restart_restores_checkpoint(tmp_path):
    store = WorkflowStateStore(DurableJobStore(tmp_path / "jobs.sqlite3"))
    controller = WorkflowController(store)
    workflow = controller.create(objective="Test objective", owner="RAY", created_by="RAY")
    step = workflow["steps"][0]
    controller.record_result(workflow, step, {"status": "COMPLETE", "output": "intake"})
    controller.persist(workflow)
    reloaded = store.load(workflow["durable_job_id"])
    assert reloaded["last_certified_step"] == "OBJECTIVE_INTAKE"
    assert reloaded["steps"][0]["result"]["output"] == "intake"


def test_dispatch_persists_failure_as_dependency_without_invoking_worker(tmp_path):
    store = WorkflowStateStore(DurableJobStore(tmp_path / "jobs.sqlite3"))
    called = []
    controller = WorkflowController(store, handlers={"CAMPAIGN_CREATION": lambda packet: called.append(packet)})
    workflow = controller.create(objective="Test objective", owner="RAY", created_by="RAY")
    step = next(s for s in workflow["steps"] if s["step_id"] == "CAMPAIGN_CREATION")
    step["depends_on"] = []
    result = controller.dispatch(workflow, step["step_id"])
    stored = store.load(workflow["durable_job_id"])
    assert result["workflow_status"] == "WAITING_DEPENDENCY"
    assert called == []
    assert stored["status"] == "WAITING_DEPENDENCY"


def test_dependency_requires_verified_resolution_before_resume(tmp_path):
    store = WorkflowStateStore(DurableJobStore(tmp_path / "jobs.sqlite3"))
    controller = WorkflowController(store)
    workflow = controller.create(objective="Test objective", owner="RAY", created_by="RAY")
    controller.park_for_dependency(workflow, dependency="CAPABILITY", reason="not available")
    with pytest.raises(ValueError, match="NOT_RESUMABLE|DEPENDENCIES_UNRESOLVED"):
        controller.resume(workflow)
    controller.resolve_dependency(workflow, "CAPABILITY", verification_ref="health-receipt-1")
    controller.resume(workflow)
    assert workflow["status"] == "RUNNING"


def test_context_packet_is_bounded_and_has_no_transcript_field():
    workflow = _workflow()
    packet = context_packet(workflow, workflow["steps"][0], relevant_facts=["x" * 20000])
    assert "transcript" not in packet
    assert packet.get("context_truncated") is True
    assert packet["workflow_id"] == workflow["workflow_id"]


def test_cron_idle_makes_zero_model_calls():
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")))
    result = controller.run_cronbot("UNFINISHED_WORK_CRON", [])
    assert result == {"cronbot_id": "UNFINISHED_WORK_CRON", "examined": 0, "dispatched": 0, "model_calls": 0}


def test_terminal_system_failure_is_controller_gated():
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")))
    workflow = _workflow()
    with pytest.raises(ValueError, match="NO_SAFE_CONTINUATION"):
        controller.fail_terminal_system(workflow, reason="temporary", safe_continuation_exists=True)


def test_no_completion_without_receipt():
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")))
    workflow = _workflow()
    with pytest.raises(ValueError, match="WORKFLOW_STEPS_INCOMPLETE"):
        controller.certify_completion(workflow, {"result": "done"})


def test_business_workflow_contract_fails_closed_on_unverified_connector():
    controller = WorkflowController(WorkflowStateStore(DurableJobStore(":memory:")),
                                    runtime_health={"MAC_MINI": "HEALTHY"})
    workflow = _workflow()
    step = next(s for s in workflow["steps"] if s["step_id"] == "CAMPAIGN_CREATION")
    with pytest.raises(Exception):
        controller.authorize_step(workflow, step)


def test_workflow_definition_and_contracts_are_bounded():
    definition = json.loads((__import__("pathlib").Path(__file__).resolve().parents[3] /
                             "configs/workflows/nexus_business_to_campaign_r1.json").read_text())
    assert len(definition["steps"]) == 15
    assert definition["ai_worker_can_terminate_workflow"] is False
    assert definition["governance"]["publication_allowed"] is False


def test_all_workflow_step_permissions_match_control_plane():
    from scripts.nexus_agent_platform.agent_control_plane import public_registry_snapshot
    definition = json.loads((__import__("pathlib").Path(__file__).resolve().parents[3] /
                             "configs/workflows/nexus_business_to_campaign_r1.json").read_text())
    registry = public_registry_snapshot()
    identities = {x.get("agent_id") or x.get("bot_id"): x for x in registry["agents"]}
    for step in definition["steps"]:
        bot = identities[step["bot_id"]]
        assert step["owner"] == bot.get("domain", step["owner"])
        assert step.get("skill_id") is None or step["skill_id"] in bot.get("allowed_skills", [])
        assert step["model_profile"] in bot.get("allowed_model_profiles", [])
        assert step["environment_id"] in bot.get("allowed_execution_environments", [])
        assert set(step.get("connector_ids", [])) <= set(bot.get("allowed_connectors", []))
