import json
from pathlib import Path

import pytest

from nexus_agent_platform.loops.kernel import LoopDefinition, run_loop
from nexus_agent_platform.loops.skill_resolver import resolve_skill


ROOT = Path(__file__).resolve().parents[2]


def definition():
    return LoopDefinition(
        loop_id="TEST_WP4_LOOP",
        name="bounded test loop",
        purpose="test",
        trigger_types=("synthetic",),
        default_skill="system-operations",
        allowed_skills=("system-operations",),
        default_worker="NEXUS_OPERATIONS_WORKER",
        allowed_workers=("NEXUS_OPERATIONS_WORKER",),
        default_profile="nexusworker",
        model_policy="LOCAL_PRIVATE",
        allowed_executors=("daily_system_operations",),
    )


def test_skill_resolution_is_explicit_and_bounded():
    result = resolve_skill(
        "system-operations",
        authority_class="internal_read_only",
        worker_id="NEXUS_OPERATIONS_WORKER",
        available_workers={"NEXUS_OPERATIONS_WORKER"},
        available_executors={"daily_system_operations"},
    )
    assert result.skill_id == "system-operations"
    assert result.executor_policy == ("daily_system_operations",)


def test_skill_resolution_fails_closed():
    with pytest.raises(ValueError, match="NO_SKILL_MATCH"):
        resolve_skill("missing-skill", authority_class="internal_read_only", worker_id="NEXUS_OPERATIONS_WORKER", available_workers={"NEXUS_OPERATIONS_WORKER"}, available_executors=set())
    with pytest.raises(ValueError, match="SKILL_BLOCKED_AUTHORITY"):
        resolve_skill("client-lifecycle", authority_class="internal_read_only", worker_id="NEXUS_OPERATIONS_WORKER", available_workers={"NEXUS_OPERATIONS_WORKER"}, available_executors=set())


def test_loop_kernel_emits_verified_receipt(tmp_path):
    result = run_loop(
        definition(),
        {"input_source": "synthetic", "status": "healthy"},
        trigger="synthetic",
        executor=lambda _: {"status": "PASS", "entrypoint": "fixed-test", "artifact": "synthetic.json", "side_effect": {"external": False}},
        reviewer=lambda _: {"status": "PASS", "summary": "bounded review"},
        receipt_dir=tmp_path,
    )
    assert result.final_state == "SUCCEEDED_VERIFIED"
    receipt = json.loads((tmp_path / f"{result.receipt_id}.json").read_text())
    assert receipt["schema_version"] == "nexus.loop-receipt.v2"
    assert receipt["final_state"] == "SUCCEEDED_VERIFIED"


def test_loop_kernel_fails_closed_on_executor_error(tmp_path):
    result = run_loop(definition(), {"input_source": "synthetic"}, trigger="synthetic", executor=lambda _: {"status": "FAIL"}, receipt_dir=tmp_path)
    assert result.final_state == "FAILED"
    receipt = json.loads((tmp_path / f"{result.receipt_id}.json").read_text())
    assert receipt["exit_status"] == "FAIL_CLOSED"
    assert receipt["validation_result"]["status"] == "NOT_PROVEN"
