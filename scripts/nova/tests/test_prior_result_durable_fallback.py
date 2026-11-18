"""Focused prior-result contracts; uses the active-lineage successor on PYTHONPATH."""
from unittest.mock import patch

from nova.nexus_mcp_status import call_prior_department_result
from nova.semantic_orchestration import resolve_owner_request


JOB_ID = "job_41eac08db91447ae9bcfa4c47d165943"
RECEIPT = "receipt_36db2ccf843949d19a6178779f088889"
QUERY = "What did Alpha find from the REA research?"
ANSWER = "The persisted REA finding recommends one controlled Nexus-owned test."


def _durable_response(*, state="COMPLETED", job_id=JOB_ID, result_summary=None,
                      receipt_ref=RECEIPT):
    row = {"job_id": job_id, "state": state, "department": "RESEARCH", "receipt_ref": receipt_ref,
           "result_summary": result_summary if result_summary is not None else {"answer": ANSWER}}
    return {"status": "ok", "data": {"status": "success", "data": row}}


def test_completion_event_remains_available_when_no_durable_match_exists():
    event = {"status": "ok", "department": "ALPHA", "summary": "Event result"}
    def read(tool, _arguments):
        if tool == "nexus_get_prior_department_result":
            return event, 49
        return {"status": "ok", "data": {"jobs": []}}, 49
    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read) as call:
        result, count = call_prior_department_result(QUERY, "ALPHA", job_id=JOB_ID)
    assert result["summary"] == "Event result"
    assert count == 49
    assert call.call_args_list[-1].args[0] == "nexus_get_prior_department_result"


def test_exact_completed_lineage_result_is_read_before_completion_events():
    def read(tool, arguments):
        assert tool == "nexus_get_durable_jobs"
        assert arguments == {"job_id": JOB_ID, "limit": 1}
        return _durable_response(), 49

    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read) as call:
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=JOB_ID)
    assert result["status"] == "ok"
    assert result["summary"] == ANSWER
    assert result["source"] == "nexus_durable_jobs.result_summary"
    assert call.call_count == 1
    assert call.call_args.args[0] == "nexus_get_durable_jobs"


def test_durable_fallback_preserves_exact_job_and_receipt():
    def read(tool, arguments):
        return (({"status": "unavailable", "error": "durable_completion_events_unavailable"}, 49)
                if tool == "nexus_get_prior_department_result" else (_durable_response(), 49))

    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read):
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=JOB_ID)
    assert result["job_id"] == JOB_ID
    assert result["source_research_job_id"] == JOB_ID
    assert result["receipt_id"] == RECEIPT
    assert result["result_summary"]["answer"] == ANSWER


def test_no_matching_durable_job_returns_no_fake_result():
    def read(tool, arguments):
        if tool == "nexus_get_prior_department_result":
            return {"status": "unavailable", "error": "durable_completion_events_unavailable"}, 49
        if arguments.get("job_id"):
            return {"status": "ok", "data": {"data": {"job_id": "job-unrelated", "state": "COMPLETED",
                    "receipt_ref": RECEIPT, "result_summary": {"answer": "wrong result"}}}}, 49
        return {"status": "ok", "data": {"jobs": [{"job_id": "job-unrelated", "state": "COMPLETED",
                "department": "RESEARCH", "receipt_ref": RECEIPT,
                "result_summary": {"answer": "wrong result"}}]}}, 49

    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read):
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=JOB_ID)
    assert result["status"] == "unavailable"
    assert "summary" not in result


def test_noncompleted_durable_job_is_not_reported_as_findings():
    def read(tool, arguments):
        if tool == "nexus_get_prior_department_result":
            return {"status": "unavailable", "error": "durable_completion_events_unavailable"}, 49
        if arguments.get("job_id"):
            return _durable_response(state="RUNNING"), 49
        return {"status": "ok", "data": {"jobs": []}}, 49

    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read):
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=JOB_ID)
    assert result["status"] == "unavailable"
    assert result["status"] == "unavailable"
    assert "summary" not in result


def test_rea_findings_question_remains_a_prior_result_read():
    route = resolve_owner_request(QUERY, context={"department": "ALPHA", "job_id": JOB_ID,
                                                   "topic": "REA research"})
    assert route["intent"] == "PRIOR_WORK_QUERY"
    assert route["job_id"] == JOB_ID
    def read(tool, _arguments):
        if tool == "nexus_get_prior_department_result":
            return {"status": "unavailable", "error": "durable_completion_events_unavailable"}, 49
        return _durable_response(), 49

    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read) as call:
        result, _ = call_prior_department_result(QUERY, "ALPHA", job_id=route["job_id"])
    assert result["status"] == "ok"
    assert result["job_id"] == JOB_ID
    assert all(args[0] != "nexus_assign_research" for args in call.call_args_list)


def test_recommendation_question_uses_prior_result_and_never_assigns():
    route = resolve_owner_request("What did Alpha recommend?", context={"department": "ALPHA", "job_id": JOB_ID})
    assert route["intent"] == "PRIOR_WORK_QUERY"
    def read(tool, _arguments):
        if tool == "nexus_get_prior_department_result":
            return {"status": "ok", "department": "ALPHA", "summary": "Run a controlled test."}, 49
        return {"status": "ok", "data": {"jobs": []}}, 49
    with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=read) as call:
        result, _ = call_prior_department_result("What did Alpha recommend?", "ALPHA", job_id=JOB_ID)
    assert result["summary"] == "Run a controlled test."
    assert call.call_args_list[-1].args[0] == "nexus_get_prior_department_result"


def test_status_question_remains_status_read_not_assignment():
    route = resolve_owner_request("What's the status of that research?", context={"job_id": JOB_ID})
    assert route["intent"] == "OBJECTIVE_STATUS_QUERY"
    assert route["executor"] == "nexus_get_durable_jobs"
