from nova.nexus_mcp_status import _mcp_failure_code, render_status_result, status_tool_for


def test_mcp_client_loads_hermes_credentials_without_py_yaml():
    from nova import nexus_mcp_status

    assert "from dotenv import load_dotenv" in nexus_mcp_status._CONTAINER_CALL
    assert "from ruamel.yaml import YAML" in nexus_mcp_status._CONTAINER_CALL
    assert "os.path.expandvars" in nexus_mcp_status._CONTAINER_CALL
    assert "import asyncio,json,sys,yaml,httpx" not in nexus_mcp_status._CONTAINER_CALL


def test_mcp_failures_are_reported_as_safe_specific_categories():
    assert _mcp_failure_code("httpx.ConnectError: All connection attempts failed") == "MCP_TRANSPORT_UNREACHABLE"
    assert _mcp_failure_code("HTTP 401 Unauthorized") == "MCP_AUTH_FAILED"
    assert _mcp_failure_code("ReadTimeout: timed out") == "MCP_SERVER_TIMEOUT"
    assert _mcp_failure_code("server is parked") == "MCP_SERVER_PARKED"
    assert _mcp_failure_code("MCP_TOOL_NOT_REGISTERED") == "MCP_TOOL_NOT_REGISTERED"
    assert _mcp_failure_code("MCP_CONNECTOR_AUTH_FAILED") == "CONNECTOR_AUTH_FAILED"


def test_status_queries_select_read_only_mcp_tools():
    assert status_tool_for("What is the current Nexus status?")[0] == "nexus_get_system_health"
    assert status_tool_for("Show me current durable jobs.") == ("nexus_get_durable_jobs", {"limit": 10})
    assert status_tool_for("What is Research doing?")[0] == "nexus_get_research_state"
    assert status_tool_for("What is Nexus working on right now?")[0] == "nexus_get_work_items"


def test_status_answers_render_actual_tool_result_values():
    message = render_status_result("Show current jobs", "nexus_get_durable_jobs", {
        "status": "ok", "request_id": "mcp-test", "data": {"data": {"jobs": [
            {"job_id": "job-live", "job_type": "REAL_JOB", "state": "READY"}
        ]}},
    })
    assert "job-live" in message and "REAL_JOB" in message and "READY" in message
    assert "live Nexus MCP" in message


def test_current_work_answer_uses_live_work_item_values():
    message = render_status_result("What is Nexus working on right now?", "nexus_get_work_items", {
        "status": "ok", "data": {"items": [
            {"work_id": "work-live", "title": "Current objective", "status": "RUNNING"}
        ]},
    })
    assert "work-live" in message and "Current objective" in message and "RUNNING" in message


def test_exact_job_status_uses_id_filter_and_returns_correlated_work_details(monkeypatch):
    from nova import nexus_mcp_status

    observed = {}
    def fake_call(tool, arguments):
        observed.update(tool=tool, arguments=arguments)
        return ({"status": "ok", "data": {"data": {
            "jobs": [{"job_id": "job_exact123", "department": "RESEARCH", "state": "BLOCKED",
                      "attempt_count": 1, "claimed_by": "worker-1", "last_error_code": "NO_PROVIDER",
                      "last_error_summary": "Provider unavailable", "receipt_ref": "rcpt_internal_test",
                      "result_summary": {"department_receipt_id": "rcpt_department_test"}}],
            "research_work_item": {"work_id": "work-exact", "requested_intent": "RESEARCH_MISSION",
                                    "routed_intent": "RESEARCH_MISSION", "execution_path": "GROUPED_NOTEBOOKLM_RESEARCH",
                                    "status": "BLOCKED_EXTERNAL", "blocker": "PROVIDER_UNAVAILABLE",
                                    "result": "No sources acquired"}}}}, 26)
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", fake_call)
    result, count = nexus_mcp_status.call_exact_job_status("job_exact123")
    message = nexus_mcp_status.render_exact_job_status(result)
    assert observed == {"tool": "nexus_get_durable_jobs", "arguments": {"job_id": "job_exact123", "limit": 1}}
    assert count == 26 and result["status"] == "ok"
    for value in ("ERROR_CODE=NO_PROVIDER", "ERROR_SUMMARY=Provider unavailable", "RESEARCH_WORK_ID=work-exact",
                  "BLOCKER=PROVIDER_UNAVAILABLE", "RESULT=No sources acquired", "READ_ONLY=YES"):
        assert value in message
    assert "rcpt_internal_test" not in message
    assert "rcpt_department_test" not in message
    diagnostic = nexus_mcp_status.render_exact_job_status(result, include_internal_receipts=True)
    assert "RECEIPT_REFERENCE=rcpt_internal_test" in diagnostic
    assert "DEPARTMENT_RECEIPT_ID=rcpt_department_test" in diagnostic


def test_internal_receipts_are_exposed_only_for_explicit_user_requests():
    from nova.nexus_mcp_status import internal_receipt_requested

    assert internal_receipt_requested("Show me the completion receipt")
    assert internal_receipt_requested("What is the internal receipt ID?")
    assert not internal_receipt_requested("What did Research find and recommend?")


def test_exact_job_not_found_is_explicit_and_never_falls_back_to_job_list(monkeypatch):
    from nova import nexus_mcp_status
    seen = []
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", lambda tool, args: (seen.append((tool, args)) or
        ({"status": "ok", "data": {"data": {"jobs": []}}}, 26)))
    result, _ = nexus_mcp_status.call_exact_job_status("job_missing123")
    assert result["status"] == "not_found"
    assert seen == [("nexus_get_durable_jobs", {"job_id": "job_missing123", "limit": 1})]


def test_systems_health_command_uses_bounded_durable_mcp_assignment(monkeypatch):
    from nova import nexus_mcp_status

    seen = {}
    def fake_call(tool, arguments):
        seen.update(tool=tool, arguments=arguments)
        return ({"status": "queued", "job_id": "job-systems-live", "job_state": "READY"}, 25)
    monkeypatch.setattr(nexus_mcp_status, "call_mcp_tool", fake_call)
    command = ("Nova, run a real Nexus Systems health check now.\n\nUse the actual Systems department.\n\n"
               "Give me: SYSTEMS_JOB_ID= JOB_STATUS= EXECUTING_DEPARTMENT=\n"
               "When it completes, proactively send me current host, Supabase, Oracle, durable queue, and resource guard status.")
    result, tool_count = nexus_mcp_status.assign_systems_task(command, "telegram-update-1")
    assert result["job_id"] == "job-systems-live"
    assert tool_count == 25
    assert seen["tool"] == "nexus_assign_department_query"
    assert seen["arguments"]["department"] == "SYSTEMS"
    assert len(seen["arguments"]["question"]) <= 240
