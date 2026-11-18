import json

import pytest

from nova.nexus_mcp_status import (
    assign_department_task,
    assign_department_tasks,
    build_assignment_linkage,
    call_exact_job_status,
    render_assignment_ack,
    render_assignment_batch,
    render_assignment_failure,
)
from nova.semantic_orchestration import resolve_owner_request
from nova.nova_telegram_worker import dispatch_objective_assignment, find_linked_objective_assignment


LIVE_STOREBUILD_SHAPED = (
    "Nova, run a real Nexus Research mission through the normal governed production path. "
    "Research livestorebuild.com and determine whether Nexus should treat it as a vendor, "
    "affiliate opportunity, ecommerce launch shortcut, business opportunity, or something Nexus "
    "should avoid. Do not use Codex. Do not simulate Research. Do not create duplicate jobs. "
    "Do not enable proactive search. Do not start V6. Use the existing governed Research workflow, "
    "including Alpha Research Director, NotebookLM, adaptive follow-up, deterministic economics "
    "where applicable, Needle readiness, and the compact Research handoff. Immediately after dispatch, "
    "return the real objective and Research job fields. Then allow the existing job to continue normally."
)

TRADINGVIEW_RESEARCH_PROMPT = """Nova, have Nexus research and review this TradingView strategy with the goal
of preparing it for Nexus Trading to paper trade:

https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/

I want Nexus Research to understand what the strategy is, verify the important
claims and rules, identify the questions Trading needs answered, perform any
reasonable bounded research or preliminary testing available, and produce an
actionable handoff to the Trading department.

A poor or negative result does not stop the research. Preserve it as a finding
and still provide Trading with the strategy rules, weaknesses, unanswered
questions, useful indicators or filters to test, and recommended next
experiments.

Do not require me to specify internal Research tools, NotebookLM, Alpha, Needle,
or workflow categories.

The goal is complete when the Research findings and recommended actions have
been handed to Trading for the next step toward paper trading.

Paper trading only. No live-money trading."""


def _queued(_tool, args):
    department = str(args.get("department") or "RESEARCH").upper()
    return ({"status": "queued", "durable_job_id": f"job-{department.lower()}-real",
             "durable_job_state": "READY", "job_id": f"job-{department.lower()}-real",
             "job_state": "READY", "department": department,
             "job_type": "RESEARCH_INTAKE" if args.get("requested_intent") == "RESEARCH_MISSION" else None}, 1)


def test_single_research_mission_creates_one_governed_assignment_and_returns_real_id(monkeypatch):
    from nova import nexus_mcp_status

    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    semantic = resolve_owner_request(LIVE_STOREBUILD_SHAPED)
    assert semantic["intent"] == "RESEARCH_MISSION"
    assert semantic["department"] == "RESEARCH"

    mission = {"mission_id": "nova-test-1", "nova_objective_id": "root-test-objective",
               "root_objective_id": "root-test-objective", "parent_request_id": "root-test-objective"}
    assignment, link, count, reply = dispatch_objective_assignment(mission, LIVE_STOREBUILD_SHAPED, "RESEARCH", requested_intent=semantic["intent"])
    assert count == 1
    assert len(calls) == 1
    assert calls[0][0] == "nexus_assign_research"
    assert calls[0][1]["parent_request_id"] == "root-test-objective"
    assert calls[0][1]["requested_intent"] == "RESEARCH_MISSION"
    assert link["job_id"] == "job-research-real"
    assert mission["objective_assignments"] == [link]
    assert "RESEARCH_JOB_ID=job-research-real" in reply
    assert "JOB_STATUS=READY" in reply
    assert "REQUESTED_INTENT=RESEARCH_MISSION" in reply
    assert "ROUTED_INTENT=RESEARCH_MISSION" in reply
    assert "EXECUTION_PATH=nexus_assign_research" in reply
    assert {call[0] for call in calls} == {"nexus_assign_research"}
    assert "public_web_search" not in {call[0] for call in calls}


def test_exact_tradingview_prompt_is_one_research_intake_assignment(monkeypatch):
    from nova import nexus_mcp_status
    from nexus_agent_platform.research_assignment_intent import assignment_job_type
    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    semantic = resolve_owner_request(TRADINGVIEW_RESEARCH_PROMPT)
    assert semantic["intent"] == "RESEARCH_MISSION"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_assign_research"
    assert semantic["likely_destination"] == "TRADING"
    mission = {"mission_id": "nova-tradingview", "nova_objective_id": "root-tradingview",
               "root_objective_id": "root-tradingview", "parent_request_id": "root-tradingview"}
    assignment, link, _, _ = dispatch_objective_assignment(
        mission, TRADINGVIEW_RESEARCH_PROMPT, "RESEARCH", requested_intent=semantic["intent"],
        followup_department=semantic["likely_destination"])
    assert [name for name, _ in calls] == ["nexus_assign_research"]
    assert calls[0][1]["requested_intent"] == "RESEARCH_MISSION"
    assert calls[0][1]["followup_department"] == "TRADING"
    assert assignment_job_type(calls[0][1]["requested_intent"]) == "RESEARCH_INTAKE"
    assert link["department"] == "RESEARCH"


@pytest.mark.parametrize("prompt", [
    "Nova, have Nexus research these three online business opportunities and give me a detailed report so I can decide whether any are worth keeping in the Nexus library for deeper research.",
    "Nova, have Nexus research this business funding strategy and tell me whether it is worth keeping in our funding knowledge library.",
    "Research this video and have Alpha help determine the important questions.",
])
def test_research_activity_and_internal_advisor_mentions_stay_one_research_mission(prompt):
    semantic = resolve_owner_request(prompt)
    assert semantic["intent"] == "RESEARCH_MISSION"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_assign_research"


def test_explicit_independent_department_action_remains_multi_department():
    semantic = resolve_owner_request(
        "Have Research investigate this company and have Systems independently audit our integration with it.")
    assert semantic["intent"] == "MULTI_DEPARTMENT_ASSIGNMENT"
    assert semantic["departments"] == ["RESEARCH", "SYSTEMS"]


def test_runtime_inspection_requires_explicit_research_runtime_target():
    semantic = resolve_owner_request("Nova, inspect why the Research dispatcher is not claiming jobs.")
    assert semantic["intent"] == "RESEARCH_RUNTIME_INSPECTION"
    assert semantic["executor"] == "nexus_assign_research"
    assert resolve_owner_request("Research this and Systems inspect runtime.")["intent"] == "MULTI_DEPARTMENT_ASSIGNMENT"


def test_successful_coordination_reply_requires_a_real_assignment_id():
    from pathlib import Path

    with pytest.raises(ValueError, match="assignment_id_required"):
        render_assignment_ack({"nova_objective_id": "root-1", "department": "RESEARCH", "current_status": "READY"})
    worker_source = Path(__file__).resolve().parents[1].joinpath("nova_telegram_worker.py").read_text()
    assert '"RESEARCH_MISSION"' in worker_source
    assert "Nexus objective accepted." not in worker_source


def test_mcp_assignment_failure_returns_actual_blocker_without_accepted_claim(monkeypatch):
    from nova import nexus_mcp_status

    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", lambda *_: ({
        "status": "rejected", "error": "research_governor_not_ready",
    }, 1))
    with pytest.raises(RuntimeError, match="research_governor_not_ready"):
        assign_department_task(LIVE_STOREBUILD_SHAPED, "RESEARCH", "root-1")
    reply = render_assignment_failure("root-1", "research_governor_not_ready")
    assert "OBJECTIVE_ACCEPTED=NO" in reply
    assert "DISPATCH_STATUS=FAILED" in reply
    assert "BLOCKER=research_governor_not_ready" in reply
    assert "Nexus objective accepted" not in reply


def test_multi_department_assignments_keep_parent_and_real_ids_and_blockers(monkeypatch):
    from nova import nexus_mcp_status

    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    batch = assign_department_tasks(
        "Delegate this objective to Research and Systems.", ["RESEARCH", "SYSTEMS"], "root-parent-2")
    links = [build_assignment_linkage("root-parent-2", "root-parent-2", row["department"],
                                     {"job_id": row["job_id"], "job_state": row["status"]})
             for row in batch["assignments"]]
    reply = render_assignment_batch(batch, "root-parent-2")
    assert len(calls) == 2
    assert all(args[1]["parent_request_id"] == "root-parent-2" for args in calls)
    assert {link["job_id"] for link in links} == {"job-research-real", "job-systems-real"}
    assert all(link["parent_request_id"] == "root-parent-2" for link in links)
    assert "OBJECTIVE_ACCEPTED=YES" in reply
    assert "RESEARCH_JOB_ID=job-research-real" in reply
    assert "SYSTEMS_JOB_ID=job-systems-real" in reply


def test_status_followup_resolves_and_reads_only_exact_linked_job(monkeypatch, tmp_path):
    from nova import nexus_mcp_status, nova_telegram_worker as worker

    record = {
        "mission_id": "nova-old", "nova_objective_id": "root-livestorebuild",
        "parent_request_id": "root-livestorebuild",
        "original_message": "Research livestorebuild.com and determine the vendor opportunity.",
        "objective_assignments": [{
            "nova_objective_id": "root-livestorebuild", "parent_request_id": "root-livestorebuild",
            "department": "RESEARCH", "assignment_id": "job-linked-existing",
            "job_id": "job-linked-existing", "created_at": "2026-10-13T16:12:00+00:00",
            "current_status": "READY",
        }],
    }
    (tmp_path / "mission.json").write_text(json.dumps(record))
    linked = find_linked_objective_assignment("check status of LiveStoreBuild research", tmp_path)
    assert linked["job_id"] == "job-linked-existing"
    calls = []
    def read(tool, args):
        calls.append((tool, dict(args)))
        return ({"status": "success", "data": {"jobs": [
            {"job_id": "other-job", "department": "RESEARCH", "state": "READY"},
            {"job_id": "job-linked-existing", "department": "RESEARCH", "state": "RUNNING"},
        ]}}, 26)
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", read)
    exact, count = call_exact_job_status(linked["job_id"])
    assert count == 26
    assert exact["job"]["job_id"] == "job-linked-existing"
    assert exact["job"]["state"] == "RUNNING"
    assert calls == [("nexus_get_durable_jobs", {"job_id": "job-linked-existing", "limit": 1})]
    assert resolve_owner_request("check status of the LiveStoreBuild research")["intent"] == "OBJECTIVE_STATUS_QUERY"


def test_exact_existing_job_status_creates_no_objective_or_research_job(monkeypatch):
    from contextlib import nullcontext
    from nova import nova_telegram_worker as worker

    request = ("Nova, inspect the existing Research job: job_example123. "
               "Do not create a new objective. Do not create a new Research job. "
               "Do not retry or restart the mission. Return the exact blocker.")
    monkeypatch.setattr(worker, "_acquire_chat_lock", lambda _chat: True)
    monkeypatch.setattr(worker, "_release_chat_lock", lambda _chat: None)
    monkeypatch.setattr(worker, "is_authorized", lambda *_: True)
    monkeypatch.setattr(worker, "stage_execution", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(worker, "_set_owner_turn_governance_context", lambda _mission, **_kwargs: {})
    monkeypatch.setattr(worker, "_restore_owner_turn_governance_context", lambda _previous: None)
    monkeypatch.setattr(worker, "create_mission", lambda *_: pytest.fail("status query created an objective"))
    calls = []
    monkeypatch.setattr(worker, "_exact_research_status_response", lambda job_id: (
        calls.append(job_id) or ("RESEARCH_JOB_ID=job_example123\nJOB_STATUS=BLOCKED", 26,
                                 {"status": "ok", "job": {"department": "RESEARCH"}})))
    delivered = []
    monkeypatch.setattr(worker, "_deliver_response", lambda *args, **kwargs: (
        delivered.append((args, kwargs)) or {"state": "DELIVERED", "message_ids": [1]}
    ))
    result = worker._process_message_inner({}, {}, {"id": 123}, {"id": 456}, 123, 456,
                                          "ray", request, 999001)
    assert result is True
    assert calls == ["job_example123"]
    assert len(delivered) == 1


def test_exact_job_status_exposes_only_live_fields_and_labels_missing_blocker(monkeypatch):
    from nova import nexus_mcp_status, nova_telegram_worker as worker

    monkeypatch.setattr(nexus_mcp_status, "call_exact_job_status", lambda job_id: ({
        "status": "ok", "job": {
            "job_id": job_id, "department": "RESEARCH", "job_type": "NOTEBOOKLM_RESEARCH",
            "state": "BLOCKED", "attempt_count": 1, "claimed_by": "dispatcher-1",
            "correlation_id": "root-existing", "created_at": "created", "started_at": "started",
            "completed_at": "blocked", "last_error_code": None, "last_error_summary": None,
            "receipt_ref": None,
        },
    }, 26))
    response, count, result = worker._exact_research_status_response("job_example123")
    assert count == 26
    assert result["job"]["job_id"] == "job_example123"
    assert "JOB_STATUS=BLOCKED" in response
    assert "ATTEMPT_COUNT=1" in response
    assert "CLAIMED_BY=dispatcher-1" in response
    assert "BLOCKER_CODE=NONE_RECORDED" in response
    assert "NEW_OBJECTIVE_CREATED=NO" in response
    assert "NEW_RESEARCH_JOB_CREATED=NO" in response


def test_notebooklm_stays_inside_research_assignment_boundary(monkeypatch):
    from nova import nexus_mcp_status

    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    request = "Nova, have Research use NotebookLM to inspect this objective through the governed workflow."
    assignment, _ = assign_department_task(request, "RESEARCH", "root-notebooklm")
    assert assignment["durable_job_id"] == "job-research-real"
    assert calls[0][0] == "nexus_assign_research"
    assert "NOTEBOOKLM" not in str(calls[0][1].get("department", "")).upper()
    assert all("notebooklm" not in name.casefold() for name, _ in calls)


def test_mission_creation_uses_initialized_timestamp_and_persists_objective(tmp_path, monkeypatch):
    from nova import nova_telegram_worker as worker

    monkeypatch.setattr(worker, "NOVA_MISSIONS_DIR", str(tmp_path))
    mission = worker.create_mission(987654321, 12345, 67890, LIVE_STOREBUILD_SHAPED)
    assert mission["created_at"] == mission["timestamps"]["received_at"]
    assert mission["objective_assignments"] == []
    saved = json.loads((tmp_path / f"{mission['mission_id']}.json").read_text())
    assert saved["root_objective_id"] == mission["nova_objective_id"]


def test_internal_research_components_do_not_expand_top_level_assignments(monkeypatch):
    from nova import nexus_mcp_status

    request = (
        "Research livestorebuild.com and determine whether Nexus should treat it as a vendor. "
        "Research owns Alpha Research Director, NotebookLM, adaptive follow-up, Needle, "
        "deterministic economics, systems review, credit funding, marketing creative, and "
        "governance review as internal workflow components."
    )
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "RESEARCH_MISSION"
    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    mission = {"mission_id": "nova-internal-components", "nova_objective_id": "root-internal",
               "root_objective_id": "root-internal", "parent_request_id": "root-internal"}
    _, link, _, reply = dispatch_objective_assignment(
        mission, request, "RESEARCH", requested_intent=semantic["intent"])
    assert link["department"] == "RESEARCH"
    assert [tool for tool, _ in calls] == ["nexus_assign_research"]
    assert "EXECUTION_PATH=nexus_assign_research" in reply


def test_explicit_research_and_systems_request_creates_both_governed_assignments(monkeypatch):
    from nova import nexus_mcp_status

    request = "Research this and Systems inspect runtime."
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "MULTI_DEPARTMENT_ASSIGNMENT"
    assert semantic["departments"] == ["RESEARCH", "SYSTEMS"]
    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    batch = assign_department_tasks(request, semantic["departments"], "root-explicit-multi")
    assert len(calls) == 2
    assert {tool for tool, _ in calls} == {"nexus_assign_research", "nexus_assign_department_query"}
    assert {row["department"] for row in batch["assignments"]} == {"RESEARCH", "SYSTEMS"}
    assert {row["job_id"] for row in batch["assignments"]} == {
        "job-research-real", "job-systems-real",
    }


def test_research_cross_department_required_allows_only_explicit_systems_escalation(monkeypatch):
    from nova import nexus_mcp_status

    request = (
        "Research returned CROSS_DEPARTMENT_REQUIRED for live runtime checks. "
        "Have Systems inspect runtime health."
    )
    semantic = resolve_owner_request(request)
    assert semantic["intent"] == "DEPARTMENT_ASSIGNMENT"
    assert semantic["department"] == "SYSTEMS"
    calls = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool",
                        lambda tool, args: (calls.append((tool, dict(args))) or _queued(tool, args)))
    assignment, _ = assign_department_task(request, "SYSTEMS", "root-escalation")
    assert assignment["job_id"] == "job-systems-real"
    assert len(calls) == 1 and calls[0][0] == "nexus_assign_department_query"


def test_research_mission_short_circuits_company_planner_before_decomposition():
    from pathlib import Path

    worker_source = Path(__file__).resolve().parents[1].joinpath("nova_telegram_worker.py").read_text()
    direct_branch = worker_source.index('if selected_department in {"RESEARCH", "SYSTEMS", "ALPHA"}')
    planner_call = worker_source.index("route_company_objective(text, conversation_message_id=update_id)")
    assert direct_branch < planner_call
    assert resolve_owner_request(LIVE_STOREBUILD_SHAPED)["intent"] == "RESEARCH_MISSION"


@pytest.mark.parametrize(("prompt", "destination"), [
    ("Nova, have Nexus research this business opportunity so Marketing can decide how to promote it.", "MARKETING"),
    ("Nova, research this funding strategy so the Funding department can evaluate whether to use it.", "FUNDING"),
    ("Nova, research this app and determine whether Systems should implement the missing capabilities.", "SYSTEMS"),
])
def test_research_destination_is_context_only(prompt, destination):
    semantic = resolve_owner_request(prompt)
    assert semantic["intent"] == "RESEARCH_MISSION"
    assert semantic["department"] == "RESEARCH"
    assert semantic["executor"] == "nexus_assign_research"
    assert semantic["likely_destination"] == destination
    assert semantic.get("departments", ["RESEARCH"]) == ["RESEARCH"]
