from nova.nexus_mcp_status import (
    assign_department_task,
    assign_department_tasks,
    render_assignment_batch,
)
from nova.semantic_orchestration import resolve_owner_request


def _queued(tool, arguments):
    department = arguments.get("department") or "RESEARCH"
    return ({"status": "queued", "job_id": f"job-{department.lower()}-real",
             "durable_job_id": f"job-{department.lower()}-real",
             "job_state": "IN_PROGRESS", "durable_job_state": "IN_PROGRESS",
             "objective_id": "objective-parent-real", "department": department}, 1)


def test_conversational_systems_request_uses_governed_assignment(monkeypatch):
    from nova import nexus_mcp_status

    seen = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", lambda tool, args: (seen.append((tool, args)) or _queued(tool, args)))
    request = "Nova, have Systems inspect the current Nexus runtime and report issues."
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "DEPARTMENT_ASSIGNMENT"
    assert semantic["department"] == "SYSTEMS"
    result, _ = assign_department_task(request, "SYSTEMS", "objective-parent-real")
    assert result["job_id"] == "job-systems-real"
    assert seen[0][0] == "nexus_assign_department_query"
    assert seen[0][1]["department"] == "SYSTEMS"
    assert "system operations" in seen[0][1]["question"].lower()


def test_conversational_research_request_uses_governed_assignment(monkeypatch):
    from nova import nexus_mcp_status

    seen = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", lambda tool, args: (seen.append((tool, args)) or _queued(tool, args)))
    request = "Nova, ask Research to inspect the runtime logs and identify the cause."
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "RESEARCH_REQUEST"
    assert semantic["department"] == "RESEARCH"
    result, _ = assign_department_task(request, "RESEARCH", "objective-parent-real")
    assert result["durable_job_id"] == "job-research-real"
    assert seen[0][0] == "nexus_assign_research"
    assert seen[0][1]["parent_request_id"] == "objective-parent-real"


def test_conversational_alpha_supported_scope_uses_governed_assignment(monkeypatch):
    from nova import nexus_mcp_status

    seen = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", lambda tool, args: (seen.append((tool, args)) or _queued(tool, args)))
    request = "Nova, ask Alpha to review the Microsoft Project business example Research found."
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "DEPARTMENT_ASSIGNMENT"
    assert semantic["department"] == "ALPHA"
    result, _ = assign_department_task(request, "ALPHA", "objective-parent-real")
    assert result["job_id"] == "job-alpha-real"
    assert seen[0][0] == "nexus_assign_department_query"
    assert seen[0][1]["department"] == "ALPHA"


def test_alpha_scope_mismatch_surfaces_actual_blocker_without_wrong_assignment(monkeypatch):
    from nova import nexus_mcp_status

    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", lambda tool, args: (calls.append((tool, args)) or _queued(tool, args)))
    request = "Nova, ask Alpha to review the runtime inspection findings."
    batch = assign_department_tasks(request, ["ALPHA"], "objective-parent-real")
    assert batch["blocked_count"] == 1
    assert "ALPHA_GOVERNED_ACTION_SCOPE_UNSUPPORTED" in batch["assignments"][0]["error"]
    assert calls == []


def test_rejected_alpha_mcp_action_preserves_the_actual_blocker(monkeypatch):
    from nova import nexus_mcp_status

    def rejected(_tool, _args):
        return ({"status": "rejected", "error": "completed_matching_research_evidence_not_found"}, 1)

    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", rejected)
    request = "Nova, ask Alpha to review the Microsoft Project business example Research found."
    batch = assign_department_tasks(request, ["ALPHA"], "objective-parent-real")
    assert batch["blocked_count"] == 1
    assert "completed_matching_research_evidence_not_found" in batch["assignments"][0]["error"]


def test_multi_department_assignment_uses_existing_actions_under_one_parent(monkeypatch):
    from nova import nexus_mcp_status

    calls = []
    def fake_call(tool, args):
        calls.append((tool, dict(args)))
        return _queued(tool, args)

    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", fake_call)
    request = ("Nova, delegate runtime inspection to Systems and Research, then ask Alpha to review the Microsoft Project finding. "
               "Use NotebookLM only through Research.")
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "MULTI_DEPARTMENT_ASSIGNMENT"
    assert semantic["departments"] == ["RESEARCH", "SYSTEMS", "ALPHA"]
    batch = assign_department_tasks(request, semantic["departments"], "objective-parent-real")
    assert batch["accepted_count"] == 3
    assert len(calls) == 3
    assert all(args["parent_request_id"] == "objective-parent-real" for _, args in calls)
    assert {tool for tool, _ in calls} == {"nexus_assign_research", "nexus_assign_department_query"}
    assert all(args.get("department") != "NOTEBOOKLM" for _, args in calls)


def test_running_assignment_keeps_real_in_progress_state():
    batch = {"assignments": [{"department": "SYSTEMS", "job_id": "job-systems-1", "status": "IN_PROGRESS"}]}
    response = render_assignment_batch(batch, "objective-1")
    assert "SYSTEMS_JOB_ID=job-systems-1" in response
    assert "JOB_STATUS=IN_PROGRESS" in response
    assert "not completion claims" in response


def test_actionable_notebooklm_request_is_not_capability_description_fallback():
    request = ("Nova, have Research use NotebookLM to inspect the runtime, have Systems check the queue, "
               "and ask Alpha to review the findings.")
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "MULTI_DEPARTMENT_ASSIGNMENT"
    assert semantic["intent"] != "CAPABILITY_QUERY"
    assert "NOTEBOOKLM" not in semantic["departments"]


def test_pure_notebooklm_capability_question_stays_a_capability_query():
    assert resolve_owner_request("Can you use NotebookLM?")["intent"] == "CAPABILITY_QUERY"
