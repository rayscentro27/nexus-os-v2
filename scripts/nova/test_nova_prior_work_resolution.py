from nova.semantic_orchestration import resolve_owner_request
from nova.nexus_mcp_status import render_prior_department_result
from nexus_agent_platform.department_router import classify_intent
from nova.nova_telegram_worker import current_lineage_followup_kind, current_lineage_reference
from nova.operator_v1 import actionable
from unittest.mock import patch


def test_prior_department_questions_are_reads_not_assignments():
    cases = {
        "What did Alpha think about the business Research found?": "ALPHA",
        "What was the last thing Research found?": "RESEARCH",
        "What did Systems say about Nexus health?": "SYSTEMS",
        "What was the result of the thing I asked Alpha to review?": "ALPHA",
    }
    for text, department in cases.items():
        route = resolve_owner_request(text)
        assert route["intent"] == "PRIOR_WORK_QUERY"
        assert route["department"] == department
        assert classify_intent(text) == "PRIOR_WORK_QUERY"


def test_rea_result_query_precedes_generic_research_intent():
    route = resolve_owner_request("What did Alpha find from the REA research?")
    assert route["intent"] == "PRIOR_WORK_QUERY"
    assert route["department"] == "ALPHA"
    assert route["capability"] == "nexus.prior_work.read"
    assert route["executor"] is None
    assert classify_intent("What did Alpha find from the REA research?") == "PRIOR_WORK_QUERY"


def test_alpha_recommendation_question_is_a_prior_result_read():
    route = resolve_owner_request("What did Alpha recommend?")
    assert route["intent"] == "PRIOR_WORK_QUERY"
    assert route["department"] == "ALPHA"
    assert route["executor"] is None


def test_existing_research_licensing_followup_binds_current_lineage():
    text = "Tell Alpha to also check licensing on that existing research."
    lineage = {"job_id": "job-existing", "objective_id": "objective-existing"}
    assert current_lineage_followup_kind(text, lineage) == "CONTINUE"
    assert current_lineage_reference(text, lineage) is True
    route = resolve_owner_request(text, context=lineage)
    assert route["intent"] == "CONTINUE_EXISTING_WORK"
    assert route["job_id"] == "job-existing"


def test_generic_prior_result_uses_active_context_but_new_video_stays_assignment():
    context = {"department": "ALPHA", "job_id": "job-existing", "topic": "REA research"}
    route = resolve_owner_request("What were the results?", context=context)
    assert route["intent"] == "PRIOR_WORK_QUERY"
    assert route["department"] == "ALPHA"
    new_video = resolve_owner_request("Research this new video: https://example.com/new-video")
    assert new_video["executor"] == "nexus_assign_research"
    assert new_video["intent"] not in {"PRIOR_WORK_QUERY", "OBJECTIVE_STATUS_QUERY", "CONTINUE_EXISTING_WORK"}


def test_status_query_uses_read_path_and_does_not_assign():
    route = resolve_owner_request("What's the status of that research?")
    assert route["intent"] == "OBJECTIVE_STATUS_QUERY"
    assert route["executor"] == "nexus_get_durable_jobs"
    assert resolve_owner_request("Did Alpha finish?")["intent"] == "OBJECTIVE_STATUS_QUERY"


def test_research_add_on_is_bound_to_existing_job_not_assignment():
    text = "Tell Alpha to also check licensing on that existing research."
    context = {"department": "ALPHA", "job_id": "job-existing", "topic": "REA research"}
    route = resolve_owner_request(text, context=context)
    assert route["intent"] == "CONTINUE_EXISTING_WORK"
    assert route["job_id"] == "job-existing"
    assert route["executor"] is None


def test_result_formatter_prefers_persisted_alpha_summary():
    response = render_prior_department_result({
        "status": "ok", "department": "ALPHA", "job_id": "job-private",
        "summary": "The strongest opportunity is to inspect a Nexus-owned interaction before Coding rebuilds it.",
        "recommendation": "Run one controlled test.",
    })
    assert response.startswith("Alpha finished the Research.")
    assert "one controlled test" in response
    assert "job-private" not in response


def test_prior_result_handler_uses_read_tool_only():
    from nova.nexus_mcp_status import call_prior_department_result
    response = {"status": "ok", "department": "ALPHA", "summary": "verified finding"}
    with patch("nova.nexus_mcp_status.call_mcp_tool", return_value=(response, 49)) as call:
        result, count = call_prior_department_result(
            "What did Alpha find from the REA research?", "ALPHA")
    assert result["summary"] == "verified finding"
    assert count == 49
    assert [item.args[0] for item in call.call_args_list] == [
        "nexus_get_durable_jobs", "nexus_get_prior_department_result"]
    assert all(item.args[0] != "nexus_assign_research" for item in call.call_args_list)


def test_prior_result_handler_precedes_generic_assignment_branch():
    from pathlib import Path
    worker = Path("scripts/nova/nova_telegram_worker.py").read_text()
    assert worker.index('if semantic.get("intent") == "PRIOR_WORK_QUERY"') < worker.index(
        'if selected_department in {"RESEARCH", "SYSTEMS", "ALPHA"}')


def test_goclear_email_followup_remains_google_read():
    route = resolve_owner_request("What did you find in my last GoClear email?")
    assert route["intent"] == "GOOGLE_ACTION"


def test_new_alpha_assignment_remains_an_assignment():
    route = resolve_owner_request("Have Alpha review that business.")
    assert route["intent"] == "DEPARTMENT_ASSIGNMENT"
    assert route["department"] == "ALPHA"


def test_alpha_prior_result_summary_is_evidence_bounded():
    response = render_prior_department_result({
        "status": "ok",
        "department": "ALPHA",
        "alpha_evaluation": {
            "decision": "RESEARCH_MORE",
            "evidence_strength": "weak",
            "strengths": ["Relevant product categories", "Free online Office", "Microsoft resources"],
            "weaknesses": ["No prices", "Search snippets", "General account pages"],
            "strongest_assumption": "A dedicated plan page has pricing.",
            "weakest_assumption": "Snippets preserve context.",
            "one_improvement": "Read the official plans page.",
            "why_interesting": "Pricing informs market adoption.",
        },
    })
    assert "recommended more research" in response
    assert "No prices" in response
    assert "exact prices were not verified" in response


def test_cross_turn_research_case_reference_recognizes_opened_case():
    lineage = {"objective_id": "obj-exact", "project_id": "project-exact",
               "job_id": "job-exact", "case_id": "case-exact"}
    assert current_lineage_followup_kind(
        "Nova, continue the Research case you just opened through the normal workflow.", lineage) == "CONTINUE"


def test_cross_turn_referential_phrases_bind_current_entity_without_ids():
    lineage = {"case_id": "case-exact"}
    cases = {
        "continue that case": "CONTINUE",
        "what happened with that job?": "READ",
        "delete it": "None",
        "show me the result": "READ",
        "keep going with that": "CONTINUE",
    }
    for text, expected in cases.items():
        result = current_lineage_followup_kind(text, lineage)
        assert (str(result) if result is not None else "None") == expected


def test_generic_research_status_is_not_misclassified_as_current_case():
    assert current_lineage_followup_kind("What is the current status of Research?", {"case_id": "case-exact"}) is None
    assert current_lineage_followup_kind("continue that case", None) is None
    assert current_lineage_reference("delete it", {"note_id": "note-exact"}) is True
    assert current_lineage_reference("delete it", None) is False
    assert current_lineage_reference("show me the result", {"case_id": "case-exact"}) is True


def test_same_research_case_work_request_is_actionable_and_resolves_exact_case():
    text = ("Nova, keep working on that same Research case. Answer the two remaining questions, "
            "use other sources or Outside Advisor if needed, and continue through synthesis. "
            "Don't come back just because one source fails.")
    lineage = {"objective_id": "obj-exact", "project_id": "project-exact",
               "job_id": "job-exact", "case_id": "case-exact"}
    semantic = resolve_owner_request(text)
    assert semantic["intent"] == "CONTINUE_EXISTING_WORK"
    assert actionable(text, semantic["intent"]) is True
    assert current_lineage_reference(text, lineage) is True
    assert current_lineage_followup_kind(text, lineage) == "CONTINUE"

