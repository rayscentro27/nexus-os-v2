from nexus_agent_platform.nova_capability_certification import (
    CapabilityResult, build_report, check_state_consistency,
)


def test_completed_child_queued_work_without_parent_action_fails_consistency():
    result = check_state_consistency({
        "root_objective_state": "PARTIAL", "durable_job_state": "COMPLETED",
        "work_item_state": "QUEUED", "parent_workflow_state": "IN_PROGRESS",
        "continuation_state": "NONE", "result_state": "PERSISTED",
        "delivery_state": "NOT_TESTED",
    })
    assert result["state_consistency"] == "FAIL"
    assert "DURABLE_COMPLETED_WORK_STILL_QUEUED" in result["violations"]


def test_active_continuation_is_consistent_for_in_progress_root():
    result = check_state_consistency({
        "root_objective_state": "IN_PROGRESS", "durable_job_state": "COMPLETED",
        "work_item_state": "IN_PROGRESS", "parent_workflow_state": "IN_PROGRESS",
        "continuation_state": "READY", "result_state": "PERSISTED",
    })
    assert result["state_consistency"] == "PASS"


def test_parent_projection_does_not_masquerade_as_active_child():
    result = check_state_consistency({
        "root_objective_state": "IN_PROGRESS", "durable_job_state": "COMPLETED",
        "work_item_state": "IN_PROGRESS", "parent_workflow_state": "IN_PROGRESS",
        "continuation_state": "COMPLETED", "result_state": "PERSISTED",
    })
    assert result["state_consistency"] == "FAIL"
    assert "INCOMPLETE_ROOT_WITHOUT_ACTIVE_CONTINUATION" in result["violations"]


def test_harness_report_validates_status_vocabulary():
    result = CapabilityResult(capability="test", overall_status="PASS", failure_layer="UNKNOWN")
    report = build_report(results=[result])
    assert report["mode"] == "OBSERVER_ONLY_SAFE"
    assert report["control_plane_status"] == "PASS"
