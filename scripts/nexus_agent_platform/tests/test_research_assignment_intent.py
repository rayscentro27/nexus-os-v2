from __future__ import annotations

import sys
from types import ModuleType

from nexus_agent_platform.research_assignment_intent import classify_research_assignment


LIVESTOREBUILD_PROMPT = """Research livestorebuild.com and determine whether Nexus should treat it as
a vendor, affiliate opportunity, ecommerce launch shortcut, business
opportunity, or something to avoid. Use the normal governed Research path.
Research should continue through Alpha Research Director, NotebookLM,
adaptive follow-up, economics where applicable, Needle, and compact handoff.
Do not create duplicate jobs."""


def test_livestorebuild_mission_with_internal_notebooklm_is_research_mission():
    assert classify_research_assignment(LIVESTOREBUILD_PROMPT) == "RESEARCH_MISSION"


def test_internal_research_components_do_not_select_notebook_operation():
    prompt = "Research this opportunity using Alpha Research Director, NotebookLM, adaptive follow-up, and Needle."
    assert classify_research_assignment(prompt) == "RESEARCH_MISSION"


def test_negative_duplicate_job_constraint_does_not_trigger_notebook_operation():
    prompt = "Research this business opportunity with NotebookLM inside Research. Do not create duplicate jobs."
    assert classify_research_assignment(prompt) == "RESEARCH_MISSION"


def test_research_workflow_may_create_or_reuse_its_notebook():
    prompt = "Run the governed Research workflow and create or reuse the correct NotebookLM notebook."
    assert classify_research_assignment(prompt) == "RESEARCH_MISSION"


def test_direct_notebook_query_with_reference_is_notebook_operation():
    assert classify_research_assignment("Ask notebook nb_abc123 this question: what are the key findings?") == "NOTEBOOKLM_OPERATION"
    assert classify_research_assignment("Run NotebookLM against notebook nb_abc123.") == "NOTEBOOKLM_OPERATION"
    assert classify_research_assignment("Summarize notebook nb_abc123.") == "NOTEBOOKLM_OPERATION"


def test_direct_source_add_with_notebook_reference_is_notebook_operation():
    assert classify_research_assignment("Add this source to notebook nb_abc123: https://example.com") == "NOTEBOOKLM_OPERATION"


def test_direct_notebook_operation_still_requires_governed_notebook_reference():
    from nexus_agent_platform.research_assignment_executor import execute_assignment

    result = execute_assignment({
        "requested_intent": "NOTEBOOKLM_OPERATION",
        "objective": "Ask notebook this question",
        "question": "What are the key findings?",
        "notebook_operation": "ASK",
    })
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "NOTEBOOK_ID_REQUIRED_FOR_GOVERNED_NOTEBOOK_OPERATION"


def test_incidental_or_negated_notebooklm_mention_is_not_a_direct_operation():
    assert classify_research_assignment("Research this market; NotebookLM may be part of the internal workflow.") == "RESEARCH_MISSION"
    assert classify_research_assignment("Do not query notebook nb_abc123 directly; research the opportunity instead.") == "RESEARCH_MISSION"


def test_research_mission_executor_opens_case_without_entry_notebook_id(monkeypatch):
    from nexus_agent_platform.research_assignment_executor import execute_assignment

    calls = []
    research_package = ModuleType("research")
    cases = ModuleType("research.research_case_engine")
    cases.open_or_join_case = lambda **kwargs: calls.append(("open", kwargs)) or {
        "case": {"case_id": "case-test", "notebook_workspace": {"notebook_id": "notebook-created-by-case"}}
    }
    cases.get_case = lambda case_id: {"case_id": case_id, "notebook_workspace": {"notebook_id": "notebook-created-by-case"}}
    playbook = ModuleType("research.notebook_playbook_runner")
    playbook.run_case_playbook = lambda *args, **kwargs: calls.append(("playbook", kwargs)) or {
        "ok": True, "notebook_id": "notebook-created-by-case"
    }
    research_package.research_case_engine = cases
    monkeypatch.setitem(sys.modules, "research", research_package)
    monkeypatch.setitem(sys.modules, "research.research_case_engine", cases)
    monkeypatch.setitem(sys.modules, "research.notebook_playbook_runner", playbook)

    result = execute_assignment({
        "requested_intent": "RESEARCH_MISSION",
        "objective": "Research the Livestorebuild business opportunity",
        "question": "Research the Livestorebuild business opportunity",
        "objective_id": "objective-test",
        "work_id": "work-test",
        # Deliberately no notebook_id or notebook_reference.
    })

    assert result["status"] == "CONTINUATION_REQUIRED"
    assert result["requested_intent"] == result["routed_intent"] == "RESEARCH_MISSION"
    assert result["execution_path"] == "RESEARCH_INTAKE"
    assert result["research_intake"]["notebooklm_selected"] is False
    assert result["notebook_id"] is None
    assert result["task_fulfillment"]["task_fulfilled"] is False
    assert result["task_fulfillment"]["routing_blocker"] == "RESEARCH_CONTINUATION_REQUIRED"
    assert calls[0][0] == "open"
    assert calls[0][1]["force_existing"] is False
    assert [kind for kind, _ in calls] == ["open"]


def test_explicit_ray_same_objective_continuation_can_resume_when_case_ceiling_is_full(monkeypatch):
    from nexus_agent_platform.research_assignment_executor import execute_assignment

    calls = []
    research_package = ModuleType("research")
    cases = ModuleType("research.research_case_engine")
    cases.open_or_join_case = lambda **kwargs: calls.append(kwargs) or {
        "case": {"case_id": "case-owner-continuation"}
    }
    cases.get_case = lambda case_id: {"case_id": case_id}
    research_package.research_case_engine = cases
    monkeypatch.setitem(sys.modules, "research", research_package)
    monkeypatch.setitem(sys.modules, "research.research_case_engine", cases)

    result = execute_assignment({
        "requested_intent": "RESEARCH_MISSION",
        "objective": "Continue the current project",
        "question": "Continue the current project",
        "objective_id": "nova_research_exact",
        "followup_of": "nova_research_exact",
        "source_type": "NOVA_OBJECTIVE",
        "requested_by": "hermes_nova",
        "work_id": "work-exact-continuation",
    })

    assert calls[0]["force_existing"] is True
    assert calls[0]["originating_goal_id"] == "nova_research_exact"
    assert result["status"] == "CONTINUATION_REQUIRED"
    assert result["case_id"] == "case-owner-continuation"
