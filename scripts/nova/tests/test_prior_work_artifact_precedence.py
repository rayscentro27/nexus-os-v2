"""Prior-result artifact selection must outrank incomplete Research cases."""
from unittest.mock import patch

from nova.nexus_mcp_status import call_prior_department_result, render_prior_department_result
from nova.nova_telegram_worker import _prior_result_preempts_case_resolution
from nova.operator_shadow import decide_research_case_resolution
from nova.semantic_orchestration import resolve_owner_request


REA_JOB = "job_41eac08db91447ae9bcfa4c47d165943"
STALE_JOB = "job_f6b9d236db3d4393a82af581c50522dd"
CASE_ID = "rcase_f6c19e2c0afe9c44ea"
RECEIPT = "receipt_36db2ccf843949d19a6178779f088889"
QUERY = "What did Alpha find from the REA research?"
SUMMARY = (
    "REA is promising as an inspection layer. DeepSeek Harness and REA official projects were identified; "
    "licensing appears workable. The 90% cheaper claim is unsupported and identical reconstruction was not verified. "
    "The strongest Nexus fit is Coding and Systems. Run a controlled test; recommendation: RESEARCH_MORE."
)


def _job(job_id, *, state="COMPLETED", answer=SUMMARY, department="RESEARCH", receipt=RECEIPT):
    return {"job_id": job_id, "state": state, "department": department,
            "payload_ref": "nova_research_work_3f07f6ff61e266d5b74f",
            "receipt_ref": receipt,
            "result_summary": {"answer": answer, "completed_at": "2026-10-20T00:00:00Z"} if answer else None}


def test_result_queries_carry_completed_result_preference_and_preempt_case_resolution():
    queries = [QUERY, "What did Alpha recommend?", "What were the results of that research?"]
    for text in queries:
        route = resolve_owner_request(text, context={"job_id": STALE_JOB, "case_id": CASE_ID})
        assert route["intent"] == "PRIOR_WORK_QUERY"
        assert route["artifact_preference"] == "COMPLETED_RESULT"
        assert _prior_result_preempts_case_resolution(route) is True


def test_topic_match_selects_completed_rea_result_over_stale_job_and_case():
    def read(tool, arguments):
        assert tool == "nexus_get_durable_jobs"
        if arguments.get("job_id"):
            return {"status": "ok", "data": {"job_id": STALE_JOB, "state": "READY"}}, 49
        return {"status": "ok", "data": {"jobs": [
            _job("job-unrelated", answer="A completed unrelated research result."),
            _job(REA_JOB),
        ]}}, 49

    context = {"job_id": STALE_JOB, "case_id": CASE_ID, "topic": "ongoing Research case"}
    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read) as calls:
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=STALE_JOB, context=context)
    assert result["artifact_type"] == "DURABLE_RESEARCH_JOB"
    assert result["job_id"] == REA_JOB
    assert result["status"] == "ok"
    assert result["receipt_id"] == RECEIPT
    assert [call.args[0] for call in calls.call_args_list] == [
        "nexus_get_durable_jobs", "nexus_get_durable_jobs"]


def test_incomplete_or_unreceipted_jobs_are_not_result_candidates():
    incomplete = _job("job-incomplete", state="RUNNING")
    missing_receipt = _job("job-no-receipt", receipt="")
    def read(_tool, arguments):
        if arguments.get("job_id"):
            return {"status": "ok", "data": {"job_id": STALE_JOB, "state": "READY"}}, 49
        if arguments.get("state") == "COMPLETED":
            return {"status": "ok", "data": {"jobs": [incomplete, missing_receipt]}}, 49
        return {"status": "unavailable", "error": "durable_completion_events_unavailable"}, 49
    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read):
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=STALE_JOB)
    assert result["status"] == "unavailable"
    assert result.get("artifact_type") is None
    assert "summary" not in result


def test_case_questions_keep_case_resolution_and_continuation():
    lineage = {"case_id": CASE_ID, "research_case_id": CASE_ID}
    for text in ("What questions are still open on the REA case?",
                 "What is the status of the REA case?"):
        route = resolve_owner_request(text, context=lineage)
        assert _prior_result_preempts_case_resolution(route) is False
        decision = decide_research_case_resolution(text, lineage=lineage)
        assert decision["DECISION"] == "READ_CASE"
        assert decision["TARGET_ENTITY_ID"] == CASE_ID
    continuation = resolve_owner_request("Continue researching the licensing issue.", context=lineage)
    assert continuation["intent"] == "CONTINUE_EXISTING_WORK"
    assert _prior_result_preempts_case_resolution(continuation) is False


def test_new_research_request_remains_new_assignment():
    route = resolve_owner_request("Research this new video: https://example.com/new")
    assert route["intent"] == "RESEARCH_ONLY_REQUEST"
    assert route["executor"] == "nexus_assign_research"
    assert _prior_result_preempts_case_resolution(route) is False


def test_conversational_formatter_uses_alpha_result_without_backend_ids():
    result = {"status": "ok", "department": "ALPHA", "job_id": REA_JOB,
              "receipt_id": RECEIPT, "summary": SUMMARY, "artifact_type": "DURABLE_RESEARCH_JOB"}
    rendered = render_prior_department_result(result)
    for phrase in ("DeepSeek Harness", "licensing appears workable", "90% cheaper claim is unsupported",
                   "identical reconstruction was not verified", "Coding and Systems", "RESEARCH_MORE"):
        assert phrase in rendered
    assert REA_JOB not in rendered
    assert RECEIPT not in rendered


def test_conversational_formatter_parses_persisted_structured_answer():
    structured = repr({
        "finding": "The video presents DeepSeek Harness and REA as an inspection tool.",
        "business_judgment": "Licensing appears workable, but savings and identical reconstruction are not verified.",
        "additional_findings": ["Coding and Systems are the strongest Nexus fit."],
        "recommendation": "Run a controlled test and gather usage receipts before adoption.",
        "actions_taken": "No installation or production changes were made.",
    })
    result = {"status": "ok", "department": "ALPHA", "job_id": REA_JOB,
              "receipt_id": RECEIPT, "summary": structured,
              "result_summary": {"answer": structured}}
    rendered = render_prior_department_result(result)
    assert rendered.startswith("Alpha finished the REA research.")
    assert "{'finding':" not in rendered
    assert "DeepSeek Harness" in rendered
    assert "Licensing appears workable" in rendered
    assert "Coding and Systems" in rendered
    assert "controlled test" in rendered
    assert REA_JOB not in rendered and RECEIPT not in rendered
