import pytest

from nexus_agent_platform.workflow_execution import classify_job, classify_step, job_execution_record, nova_execution_plan
from nexus_agent_platform.durable_objective_control import objective_stop_class


@pytest.mark.parametrize("job_type,department,expected", [
    ("NOVA_ALPHA_RESULT_NOTICE", "NOVA", "DETERMINISTIC"),
    ("NEXUS_DEPARTMENT_QUERY", "ALPHA", "STRONG_REASONING"),
    ("NEXUS_DEPARTMENT_QUERY", "SYSTEMS", "DETERMINISTIC"),
    ("NEXUS_DEPARTMENT_QUERY", "FINANCE", "DETERMINISTIC"),
    ("NEXUS_DEPARTMENT_QUERY", "TRADING", "SPECIALIZED_EXECUTOR"),
    ("RESEARCH_GAP_VERIFY", "RESEARCH", "SPECIALIZED_EXECUTOR"),
    ("CREATIVE_ASSET_GENERATE", "CREATIVE", "SPECIALIZED_EXECUTOR"),
])
def test_active_job_classes_are_declared(job_type, department, expected):
    assert classify_job(job_type, department) == expected


def test_explicit_step_class_is_validated_and_recorded():
    record = job_execution_record("NEXUS_DEPARTMENT_QUERY", "SYSTEMS",
                                  {"execution_class": "DETERMINISTIC"})
    assert record["execution_class"] == "DETERMINISTIC"
    assert record["model_call_required"] is False
    with pytest.raises(ValueError, match="INVALID_EXECUTION_CLASS"):
        classify_job("NEXUS_DEPARTMENT_QUERY", "SYSTEMS", {"execution_class": "GEMMA"})


def test_known_workflow_operations_have_explicit_execution_classes():
    deterministic = ("artifact_lookup", "receipt_verification", "job_creation",
        "department_handoff", "resource_state_lookup", "provider_health_lookup",
        "openrouter_quota_lookup", "queue_transition", "job_claim_lease",
        "receipt_persistence", "completion_event_creation", "telegram_acknowledgment",
        "google_calendar_read", "google_gmail_read", "google_drive_read", "known_mcp_action")
    assert all(classify_step(step) == "DETERMINISTIC" for step in deterministic)
    assert classify_step("simple_context_reference") == "LIGHT_REASONING"
    assert classify_step("alpha_evaluation") == "STRONG_REASONING"
    assert classify_step("backtest") == "SPECIALIZED_EXECUTOR"
    with pytest.raises(ValueError, match="UNDECLARED_WORKFLOW_STEP"):
        classify_step("unknown_transition")


def test_workflow_stop_doctrine_continues_on_ordinary_failure():
    assert objective_stop_class() == "CONTINUE"
    assert objective_stop_class(technical_impossibility_confirmed=True) == "CONTINUE"
    assert objective_stop_class(technical_impossibility_confirmed=True,
                                repair_retry_reroute_exhausted=True) == "TRUE_TECHNICAL_BLOCKER"
    assert objective_stop_class(new_incremental_cash_required=True) == "NEW_INCREMENTAL_CASH_REQUIRED"
    assert objective_stop_class(ray_action_required=True) == "RAY_ACTION_REQUIRED"


def test_nova_known_read_and_known_command_do_not_need_model_routing():
    for intent in ("LIST_JOBS", "LIVE_STATE_QUERY", "PRIOR_WORK_QUERY", "CAPABILITY_QUERY", "GOOGLE_ACTION"):
        plan = nova_execution_plan({"intent": intent})
        assert plan["execution_class"] == "DETERMINISTIC"
        assert plan["model_call_required"] is False
    command = nova_execution_plan({"intent": "DEPARTMENT_ASSIGNMENT"})
    assert command["model_call_required"] is False


def test_research_assignment_uses_deterministic_plan_and_workflow_handoff():
    from nexus_agent_platform.research_ai_orchestrator import plan_assigned_work, apply_research_handoff_contract
    item = {"work_id": "research-1", "required_tool": "WEB_ACQUISITION",
            "department_target": "ALPHA", "alpha_eligible": True,
            "next_action": "Return verified evidence to Alpha."}
    plan, route = plan_assigned_work(item)
    assert plan["model_calls"] == 0
    assert route["execution_class"] == "DETERMINISTIC"
    interpreted = apply_research_handoff_contract(item, {"next_capability": "MARKETING", "ready_for_alpha": False})
    assert interpreted["next_capability"] == "ALPHA"
    assert interpreted["ready_for_alpha"] is True
    assert interpreted["action_statement"] == "Return verified evidence to Alpha."
    assert interpreted["handoff_source"] == "WORKFLOW_CONTRACT"


def test_assigned_research_planning_call_reduction_is_measured(monkeypatch):
    import nexus_agent_platform.research_ai_orchestrator as research_ai
    calls = []
    monkeypatch.setattr(research_ai, "certified_capabilities", lambda: [])
    monkeypatch.setattr(research_ai, "_persist", lambda kind, payload: "fixture")
    monkeypatch.setattr(research_ai, "_call", lambda prompt, system: (
        calls.append(system) or ({"required_capabilities": ["WEB_ACQUISITION"],
            "preferred_capability": "WEB_ACQUISITION"}, {"model_calls": 1, "model": "fixture"})))
    research_ai.investigate({"work_id": "assigned-work", "question": "Verify assigned evidence"})
    before = len(calls)
    calls.clear()
    research_ai.plan_assigned_work({"work_id": "assigned-work", "required_tool": "WEB_ACQUISITION"})
    after = len(calls)
    assert (before, after) == (1, 0)
