from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.nexus_mcp import server


def test_tool_surface_is_explicit_and_complete():
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert set(server.TOOL_NAMES).issubset(names)
    assert set(server.SYSTEMS_HOST_CONTROL_TOOL_NAMES).issubset(names)
    assert set(server.SYSTEMS_OPERATOR_TOOL_NAMES).issubset(names)
    assert all(name.startswith("nexus_get_") or name in {"nexus_delegate_specialist", "nexus_assign_research", "nexus_continue_research", "nexus_continue_research_case", "nexus_research_controller_continue", "nexus_research_controller_advisor_request", "nexus_read_workspace_file", "nexus_write_workspace_artifact", "nexus_update_workspace_artifact", "nexus_delete_workspace_artifact", "nexus_record_research_synthesis", "nexus_record_research_recommendation", "nexus_assign_codex", "nexus_resume_research", "nexus_assign_department_query", "nexus_assign_notebooklm_runtime_canary", "nexus_assign_creative_asset", "nexus_assign_bounded_coding_task", "calendar_create_private_event", "calendar_update_event", "calendar_get_availability", "calendar_read_event", "calendar_search_events", "drive_create_nexus_file", "drive_read_file", "drive_search", "gmail_create_draft", "gmail_modify_message", "gmail_read_message", "gmail_read_thread", "gmail_search", "google_get_authority", *server.SYSTEMS_HOST_CONTROL_TOOL_NAMES, *server.SYSTEMS_OPERATOR_TOOL_NAMES, *server.OPPORTUNITIES_TOOL_NAMES, *server.GITHUB_REMOTE_TOOL_NAMES, *server.MARKETING_TOOL_NAMES, *server.CREATIVE_TOOL_NAMES, *server.FUNNEL_TOOL_NAMES} for name in names)
    update = next(tool for tool in server.mcp._tool_manager.list_tools()
                  if tool.name == "nexus_update_workspace_artifact")
    assert {"relative_path", "content", "expected_sha256", "note_id", "file_id"} <= set(update.parameters["properties"])
    delete = next(tool for tool in server.mcp._tool_manager.list_tools()
                  if tool.name == "nexus_delete_workspace_artifact")
    assert {"relative_path", "expected_sha256", "note_id", "file_id"} <= set(delete.parameters["properties"])


def test_systems_host_control_tools_have_fixed_typed_schemas_and_approval_boundaries():
    tools = {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}
    expected = set(server.SYSTEMS_HOST_CONTROL_TOOL_NAMES)
    assert set(server._SYSTEMS_HOST_CONTROL_TOOLS) == expected
    assert len(expected) == 9
    assert tools["systems_oracle_nova_poller_status"].parameters["properties"] == {}
    assert set(tools["systems_oracle_release_inspect"].parameters["properties"]) == {"release_name", "expected_hash"}
    assert set(tools["systems_oracle_release_stage"].parameters["properties"]) == {
        "artifact_id", "release_name", "expected_release_hash", "expected_manifest_hash", "approval_id"}
    assert set(tools["systems_oracle_nova_activate"].parameters["properties"]) == {
        "deployment_id", "target_release_name", "target_release_hash", "shared_release_hash",
        "dependency_lock_hash", "current_snapshot_hash", "target_dropin_hash",
        "expected_effective_dropin_count", "automatic_rollback_on_failure", "approval_id"}
    assert set(tools["systems_oracle_nova_rollback"].parameters["properties"]) == {
        "snapshot_id", "snapshot_hash", "approval_id"}
    from services.nexus_mcp.auth import authorize_action, authorize_read
    for name in ("systems_oracle_release_stage", "systems_oracle_nova_snapshot",
                 "systems_oracle_nova_activate", "systems_oracle_nova_rollback"):
        authorize_action(name)
    for name in expected - {"systems_oracle_release_stage", "systems_oracle_nova_snapshot",
                            "systems_oracle_nova_activate", "systems_oracle_nova_rollback"}:
        authorize_read(name)


def test_systems_operator_surface_is_bounded_and_typed():
    tools = {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}
    expected = set(server.SYSTEMS_OPERATOR_TOOL_NAMES)
    assert len(expected) == 8
    assert expected <= set(tools)
    assert {"objective", "component", "requested_action", "environment", "preferred_execution_worker"} <= set(
        tools["systems_job_create"].parameters["properties"])
    assert tools["systems_job_create"].parameters["properties"]["requested_action"]["enum"] == [
        "UPGRADE_REVIEW", "UPGRADE", "INSTALL_TECHNOLOGY", "CLEANUP",
        "CREDENTIAL_ROTATION", "KAGGLE_JOB", "REPAIR", "VALIDATION", "MAINTENANCE"]
    from services.nexus_mcp.auth import authorize_action, authorize_read
    authorize_action("systems_job_create")
    for name in expected - {"systems_job_create"}:
        authorize_read(name)


def test_systems_host_control_mcp_call_preserves_correlation_and_host_approval(monkeypatch):
    from nexus_agent_platform import systems_consumer
    seen = []
    monkeypatch.setattr(systems_consumer, "invoke_oracle_host_control",
        lambda capability, arguments, correlation_id: seen.append((capability, arguments, correlation_id)) or {
            "status": "success", "capability": capability, "correlation_id": correlation_id,
            "result": {"ok": True, "result": {"main_pid": "347244", "poller_count": 1}},
            "response_sha256": "a" * 64})
    monkeypatch.setattr(server, "RECEIPT_DIR", Path("/tmp") / f"nexus-mcp-hc-test-{__import__('uuid').uuid4().hex}")
    result = server._systems_host_control_call("systems_oracle_nova_poller_status", {})
    assert result["status"] == "success"
    assert result["correlation_id"] == result["request_id"]
    assert seen[0][0] == "systems.oracle.nova.poller_status"
    assert seen[0][2] == result["request_id"]
    assert result["host_result"]["result"]["poller_count"] == 1
    assert result["receipt"]
    import shutil
    shutil.rmtree(server.RECEIPT_DIR, ignore_errors=True)


def test_research_execution_trace_is_exact_job_bounded_and_read_only(tmp_path, monkeypatch):
    ledger = tmp_path / "data/runtime/research_execution_jobs.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '{"execution_id":"job_exact12345678","status":"RUNNING","worker_id":"research_operator_worker"}\n'
        '{"execution_id":"job_exact12345678","status":"FAILED_RETRYABLE","error":"JOB_BUDGET_LIMIT",'
        '"failure_class":"CANONICAL_INGESTION_NOT_VERIFIED","ingestion_status":null,"supabase_source_id":null}\n'
        '{"execution_id":"job_other12345678","status":"FAILED_RETRYABLE","error":"unrelated"}\n',
        encoding="utf-8")
    monkeypatch.setattr(server, "ROOT", tmp_path)
    result = server._get_research_execution_trace("job_exact12345678")
    assert result["status"] == "ok"
    assert result["read_only"] is True
    assert result["event_count"] == 2
    assert all(row["evidence_id"].startswith("research_execution_event:job_exact12345678:")
               for row in result["events"])
    assert result["events"][1]["failure_class"] == "CANONICAL_INGESTION_NOT_VERIFIED"
    assert "job_other12345678" not in str(result)


def test_research_execution_trace_rejects_non_exact_id():
    result = server._get_research_execution_trace("../research_execution_jobs.jsonl")
    assert result["status"] == "rejected"
    assert result["error"] == "EXACT_DURABLE_JOB_ID_REQUIRED"


def test_exact_case_inspection_is_lineage_bound_and_read_only(monkeypatch):
    case = {"case_id": "case-exact", "primary_question": "Continue project project-exact",
            "sources": [], "findings": [], "syntheses": [], "status": "SYNTHESIZING"}
    job = {"correlation_id": "objective-exact", "department": "RESEARCH",
           "job_type": "RESEARCH_INTAKE"}
    monkeypatch.setattr(server, "_exact_research_case", lambda *_: (case, job, None))
    value = server._get_research_case("case-exact", "objective-exact", "project-exact", "job-exact")
    assert value["status"] == "ok"
    assert value["read_only"] is True
    assert value["no_mutation"] is True
    assert value["case_id"] == "case-exact"
    assert value["case_state"]["status"] == "SYNTHESIZING"


def test_research_room_controller_tools_are_registered_with_exact_lineage_schemas():
    tools = {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}
    lineage = {"case_id", "objective_id", "project_id", "durable_job_id"}
    for name in ("nexus_get_research_controller_status", "nexus_get_research_controller_open_questions",
                 "nexus_get_research_controller_results"):
        assert name in tools
        assert set(tools[name].parameters["properties"]) == lineage
    assert set(tools["nexus_research_controller_continue"].parameters["properties"]) == lineage | {"instruction"}
    assert set(tools["nexus_research_controller_advisor_request"].parameters["properties"]) == lineage | {"question", "review_role"}
    from services.nexus_mcp.auth import authorize_action, authorize_read
    authorize_action("nexus_research_controller_continue")
    authorize_action("nexus_research_controller_advisor_request")
    authorize_read("nexus_get_research_controller_status")


def test_research_controller_read_and_write_wrappers_require_exact_case_binding(monkeypatch):
    case = {"case_id": "case-exact", "primary_question": "project-exact", "sources": [],
            "findings": [], "syntheses": [], "status": "PROMISING"}
    job = {"correlation_id": "objective-exact", "department": "RESEARCH", "job_type": "RESEARCH_INTAKE"}
    monkeypatch.setattr(server, "_exact_research_case", lambda *args: (case, job, None))
    from nexus_agent_platform.research_room import production_controller
    monkeypatch.setattr(production_controller, "status", lambda *args: {"status": "ok", "read_only": True, "no_mutation": True})
    status = server._research_controller_read("status", "case-exact", "objective-exact", "project-exact", "job-exact")
    assert status["read_only"] and status["no_mutation"]
    calls = []
    monkeypatch.setattr(production_controller, "continue_case", lambda *args: calls.append(args) or {"status": "advanced"})
    continued = server._research_controller_continue("case-exact", "objective-exact", "project-exact", "job-exact", "continue same case")
    assert continued["status"] == "advanced"
    assert calls == [("case-exact", "objective-exact", "project-exact", "job-exact", "continue same case")]
    monkeypatch.setattr(server, "_exact_research_case", lambda *args: (None, None, {"status": "rejected", "error": "LINEAGE"}))
    rejected = server._research_controller_continue("case-other", "objective-exact", "project-exact", "job-exact", "continue same case")
    assert rejected["error"] == "LINEAGE"
    assert calls[-1][0] == "case-exact"


def test_research_synthesis_requires_attached_evidence_and_is_governed(monkeypatch):
    case = {"case_id": "case-exact", "sources": [{"source_id": "source-exact"}], "syntheses": []}
    monkeypatch.setattr(server, "_exact_research_case", lambda *_: (case, {}, None))
    invalid = server._record_research_synthesis("case-exact", "objective-exact", "project-exact", "job-exact",
        [{"claim": "claim", "evidence_ids": ["source-other"]}], [], [], [], ["source-exact"])
    assert invalid["status"] == "rejected"
    assert invalid["error"] == "SYNTHESIS_CLAIM_EVIDENCE_MISMATCH"
    from services.nexus_mcp.auth import authorize_action
    authorize_action("nexus_record_research_synthesis")


def test_research_recommendation_requires_attached_evidence_and_is_governed(monkeypatch):
    case = {"case_id": "case-exact", "sources": [{"source_id": "source-exact"}], "recommendations": []}
    monkeypatch.setattr(server, "_exact_research_case", lambda *_: (case, {}, None))
    monkeypatch.setattr("research.research_case_engine.recommendation", lambda *a, **k: {
        "ok": True, "recommendation": {"recommendation": k["kind"], "supporting_evidence": k["supporting_evidence"]}})
    value = server._record_research_recommendation("case-exact", "objective-exact", "project-exact", "job-exact",
        "PARK", "Historical evidence boundary", ["source-exact"], [], ["traceback unavailable"], [], 0.9, "Retain result")
    assert value["status"] == "recorded"
    assert value["recommendation"]["recommendation"] == "PARK"
    rejected = server._record_research_recommendation("case-exact", "objective-exact", "project-exact", "job-exact",
        "PARK", "Historical evidence boundary", ["source-other"], [], [], [], 0.9, "Retain result")
    assert rejected["error"] == "RECOMMENDATION_SOURCE_NOT_ATTACHED_TO_CASE"
    from services.nexus_mcp.auth import authorize_action
    authorize_action("nexus_record_research_recommendation")
    authorize_action("nexus_update_workspace_artifact")
    authorize_action("nexus_delete_workspace_artifact")


@pytest.mark.parametrize("text", [
    "Create a logo for Nexus Test. Do not publish it.",
    "Create a disposable logo without posting publicly.",
    "Make an internal logo; no publishing or customer distribution.",
    "Create a small temporary test. Do not modify production files, commit, push, or deploy.",
])
def test_bounded_control_action_allows_negated_external_action_constraints(text):
    assert server._requests_external_or_production_action(text) is False


@pytest.mark.parametrize("text", [
    "Create a logo and publish it publicly.",
    "Deploy this coding change to production.",
    "Purchase the asset and send it to customers.",
    "Do not modify production files; deploy this coding change to production.",
])
def test_bounded_control_action_still_rejects_requested_external_actions(text):
    assert server._requests_external_or_production_action(text) is True


def test_public_result_preserves_canonical_state_and_metadata():
    value = server._public_result(
        "nexus_get_blockers",
        {
            "status": "success",
            "source": "governed_state",
            "source_type": "live_governed_state",
            "freshness": "live",
            "data": {"blockers": [{"id": "b-1", "status": "BLOCKED"}]},
            "provenance": {"source_timestamp": "2026-08-31T00:00:00+00:00"},
        },
    )
    assert value["status"] == "ok"
    assert value["items"] == [{"id": "b-1", "status": "BLOCKED"}]
    assert value["metadata"] == {
        "read_only": True,
        "canonical": True,
        "freshness": "live",
        "item_count": 1,
        "source_commit": None,
        "currentness": "CURRENT",
        "volatility": "VOLATILE",
        "live_response_eligible": True,
        "filtered_historical_count": 0,
        "filtered_synthetic_count": 0,
        "filtered_other_noncurrent_count": 0,
    }


def test_public_result_marks_partial_business_state_and_live_health():
    business = server._public_result(
        "nexus_get_business_state",
        {"status": "partial", "freshness": "live", "data": {}, "provenance": {}},
    )
    health = server._public_result(
        "nexus_get_system_health",
        {"status": "partial", "freshness": "live", "data": {}, "provenance": {}},
    )
    assert business["metadata"]["currentness"] == "PARTIAL"
    assert health["metadata"]["currentness"] == "CURRENT"


def test_prior_alpha_result_requires_completed_job_receipt_lineage(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from nexus_agent_platform import durable_jobs

    root = tmp_path
    runtime = root / "data/runtime"
    runtime.mkdir(parents=True)
    event = {
        "event_type": "ALPHA_RESULT", "alpha_job_id": "alpha-job-1",
        "source_research_job_id": "research-job-1", "source": "alpha-receipt-1",
        "created_at": "2026-10-11T10:00:00Z", "summary": "Alpha review summary",
    }
    (runtime / "nova_material_events.jsonl").write_text(json.dumps(event) + "\n")
    job = SimpleNamespace(job_id="alpha-job-1", department="ALPHA", state="COMPLETED", receipt_ref="alpha-receipt-1")
    monkeypatch.setattr(server, "ROOT", root)
    monkeypatch.setattr(server, "RECEIPT_DIR", root / "receipts")
    monkeypatch.setattr(durable_jobs, "default_store", lambda: SimpleNamespace(get=lambda _job_id: job))
    monkeypatch.setattr(server, "_call", lambda *_args, **_kwargs: {
        "status": "partial", "request_id": "mcp-alpha-read-1",
        "data": {"evaluation": {"decision": "RESEARCH_MORE", "strengths": ["evidence"]}},
    })

    result = server._get_prior_department_result("ALPHA", "What did Alpha think?")
    assert result["status"] == "ok"
    assert result["job_id"] == "alpha-job-1"
    assert result["receipt_id"] == "alpha-receipt-1"
    assert result["source_research_job_id"] == "research-job-1"
    assert result["alpha_evaluation"]["decision"] == "RESEARCH_MORE"
    assert result["request_id"].startswith("nexus-prior-work-")
    assert len(list((root / "receipts").glob("*.json"))) == 1


def test_prior_result_rejects_mismatched_or_noncompleted_receipt(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from nexus_agent_platform import durable_jobs

    runtime = tmp_path / "data/runtime"
    runtime.mkdir(parents=True)
    event = {"event_type": "SYSTEMS_RESULT", "systems_job_id": "systems-job-1",
             "source": "wrong-receipt", "summary": "stale", "created_at": "2026-10-11T10:00:00Z"}
    (runtime / "nova_material_events.jsonl").write_text(json.dumps(event) + "\n")
    job = SimpleNamespace(job_id="systems-job-1", department="SYSTEMS", state="BLOCKED", receipt_ref="actual-receipt")
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(durable_jobs, "default_store", lambda: SimpleNamespace(get=lambda _job_id: job))
    result = server._get_prior_department_result("SYSTEMS", "what did Systems say")
    assert result["status"] == "not_found"


def test_business_state_tool_description_is_operationally_scoped():
    source = Path(server.__file__).read_text(encoding="utf-8")
    description = next(
        line for line in source.splitlines()
        if 'name="nexus_get_business_state"' in line
    )
    assert "Nexus operational-state" in description
    assert "not general business advice" in description
    assert "hypothetical idea evaluation" in description


def test_canonical_read_failure_is_explicit_and_not_fabricated(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    monkeypatch.setattr(server, "read_canonical", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    value = server._call("nexus_get_reviews")
    assert value["status"] == "NOT_AVAILABLE"
    assert value["items"] == []
    receipts = list(tmp_path.glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["result_status"] == "NOT_AVAILABLE"
    assert receipt["read_only"] is True
    assert receipt["authority_owner"] == "Nexus"


def test_successful_reads_are_deduplicated_only_within_turn(monkeypatch, tmp_path: Path):
    server._TURN_RESULTS.clear()
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    calls = []

    def read_once(*args, **kwargs):
        calls.append((args, kwargs))
        return {"status": "empty", "freshness": "live", "data": {}, "provenance": {}}

    monkeypatch.setattr(server, "read_canonical", read_once)
    monkeypatch.setenv("NEXUS_MCP_TURN_ID", "turn-test-1")
    first = server._call("nexus_get_reviews")
    second = server._call("nexus_get_reviews")
    assert len(calls) == 1
    assert first["metadata"].get("deduplicated") is None
    assert second["metadata"]["deduplicated"] is True
    receipts = [json.loads(path.read_text()) for path in sorted(tmp_path.glob("*.json"))]
    assert len(receipts) == 2
    deduplicated = [receipt for receipt in receipts if receipt["deduplicated"]]
    assert len(deduplicated) == 1
    assert deduplicated[0]["turn_id"] == "turn-test-1"


@pytest.mark.parametrize("name", server.TOOL_NAMES)
def test_each_tool_has_expected_input_schema(name):
    if name in {"nexus_delegate_specialist", "nexus_assign_research", "nexus_continue_research_case", "nexus_research_controller_continue", "nexus_research_controller_advisor_request", "nexus_get_research_controller_status", "nexus_get_research_controller_open_questions", "nexus_get_research_controller_results", "nexus_assign_codex", "nexus_resume_research", "nexus_assign_department_query", "nexus_assign_notebooklm_runtime_canary"}:
        return
    tool = next(tool for tool in server.mcp._tool_manager.list_tools() if tool.name == name)
    if name in {"nexus_get_research_state", "nexus_get_alpha_review"}:
        assert "objective_id" in tool.parameters.get("properties", {})
    elif name == "nexus_get_prior_department_result":
        assert {"department", "question"} <= set(tool.parameters.get("properties", {}))
    elif name == "nexus_get_durable_jobs":
        assert {"state", "limit", "job_id"} <= set(tool.parameters.get("properties", {}))
    elif name == "nexus_get_research_execution_trace":
        assert "job_id" in tool.parameters.get("properties", {})
    else:
        assert tool.parameters == {} or tool.parameters.get("properties", {}) == {}


def test_specialist_request_rejects_unknown_specialist():
    result = server._delegate_specialist("UNKNOWN", "inspect current state")
    assert result["status"] == "rejected"


def test_nova_research_assignment_is_idempotent_and_bounded(monkeypatch, tmp_path: Path):
    queue_path = tmp_path / "research_work_queue.json"
    from nexus_agent_platform import research_work_queue
    real_queue = research_work_queue.ResearchWorkQueue
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue", lambda: real_queue(queue_path))
    first = server._assign_research(
        "Investigate current small-business funding readiness pain",
        "What evidence shows a current customer need and what remains uncertain?",
    )
    second = server._assign_research(
        "Investigate current small-business funding readiness pain",
        "What evidence shows a current customer need and what remains uncertain?",
    )
    assert first["status"] == "queued"
    assert second["status"] == "idempotent_existing"
    assert first["work_id"] == second["work_id"]
    assert json.loads(queue_path.read_text())["items"][0]["requested_by"] == "hermes_nova"


def test_research_intake_job_correlation_uses_returned_objective_id(monkeypatch, tmp_path: Path):
    from types import SimpleNamespace
    from nexus_agent_platform import durable_jobs, research_work_queue
    real_queue = research_work_queue.ResearchWorkQueue
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue",
        lambda: real_queue(tmp_path / "intake_queue.json"))
    captured = {}
    class Store:
        def enqueue(self, department, job_type, **kwargs):
            captured.update(department=department, job_type=job_type, **kwargs)
            return SimpleNamespace(job_id="job-intake-contract", state="READY")
    monkeypatch.setattr(durable_jobs, "default_store", lambda: Store())
    result = server._assign_research("r45 certification objective correlation contract",
        "Use only supplied facts to compare two ordinary options.",
        requested_intent="RESEARCH_MISSION")
    assert result["status"] == "queued"
    assert captured["correlation_id"] == result["objective_id"]
    assert captured["governance_context"]["objective_id"] == result["objective_id"]


def test_specialist_request_is_allowlisted_and_read_only(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "_call",
        lambda name: {"status": "ok", "request_id": "read-1", "metadata": {"currentness": "CURRENT"}},
    )
    result = server._delegate_specialist("SYSTEM", "check current health")
    assert result["status"] == "delegated"
    assert result["specialist"] == "SYSTEM"
    assert result["result"]["status"] == "ok"
    assert json.loads(next(tmp_path.glob("nexus-delegation-*.json")).read_text())["read_only"] is True


def test_department_receipt_contract_is_correlated_and_bounded(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "_call",
        lambda name: {
            "status": "ok",
            "request_id": "read-2",
            "source": "live-system-health",
            "currentness": "CURRENT",
            "metadata": {"freshness": "live", "started_at": "2026-09-18T00:00:00+00:00", "completed_at": "2026-09-18T00:00:01+00:00"},
            "data": {"overall_status": "HEALTHY"},
        },
    )
    result = server._delegate_specialist("SYSTEM", "check current health", conversation_id="conv-123")
    receipt = result["delegation_receipt"]
    assert receipt["department"] == "SYSTEMS_ENGINEERING"
    assert receipt["conversation_id"] == "conv-123"
    assert receipt["execution_type"] == "FRESH_EXECUTION"
    assert receipt["source_type"] == "LIVE_RUNTIME"
    assert receipt["freshness"] == "FRESH"
    assert receipt["status"] == "COMPLETED"
    assert receipt["underlying_request_id"] == "read-2"


def test_exact_research_case_continuation_uses_governed_job_context(monkeypatch):
    import os
    from nexus_agent_platform import durable_jobs
    from research import research_case_engine

    expected = {"case_id": "case-exact", "objective_id": "objective-exact",
        "project_id": "project-exact", "durable_job_id": "job-exact"}
    monkeypatch.setattr(durable_jobs, "default_store", lambda: type("Store", (), {
        "get": lambda self, job_id: {"job_id": job_id, "correlation_id": "objective-exact",
            "department": "RESEARCH", "job_type": "RESEARCH_INTAKE"}
    })())
    monkeypatch.setattr(research_case_engine, "get_case", lambda case_id: {
        "case_id": case_id, "project_id": "project-exact", "objective_id": "objective-exact",
        "primary_question": "Use the supplied fixture to compare two options.",
        "status": "MORE_RESEARCH_REQUIRED"})
    observed = {}
    def continue_once(case_id):
        observed.update({"case_id": case_id, "job_id": os.environ.get("NEXUS_DURABLE_JOB_ID"),
            "correlation_id": os.environ.get("NEXUS_CORRELATION_ID"),
            "department": os.environ.get("NEXUS_DEPARTMENT"),
            "job_type": os.environ.get("NEXUS_JOB_TYPE")})
        return {"status": "CONTINUED", "case_id": case_id, "sources_opened": 1}
    monkeypatch.setattr(research_case_engine, "continue_case_once", continue_once)
    result = server._continue_research_case(**expected)
    assert result["case_id"] == "case-exact"
    assert result["execution"]["sources_opened"] == 1
    assert observed == {"case_id": "case-exact", "job_id": "job-exact",
        "correlation_id": "objective-exact", "department": "RESEARCH",
        "job_type": "RESEARCH_INTAKE"}


def test_exact_research_case_continuation_rejects_project_mismatch(monkeypatch):
    from nexus_agent_platform import durable_jobs
    from research import research_case_engine

    monkeypatch.setattr(research_case_engine, "get_case", lambda case_id: {
        "case_id": case_id, "project_id": "project-exact", "objective_id": "objective-exact",
        "primary_question": "Use the supplied fixture to compare two options."})
    monkeypatch.setattr(durable_jobs, "default_store", lambda: type("Store", (), {
        "get": lambda self, job_id: {"job_id": job_id, "correlation_id": "objective-exact",
            "department": "RESEARCH", "job_type": "RESEARCH_INTAKE"}
    })())
    result = server._continue_research_case("case-exact", "objective-exact", "other-project", "job-exact")
    assert result["error"] == "RESEARCH_CASE_PROJECT_MISMATCH"


def test_opportunities_research_receiver_gate_is_bounded_and_authorized():
    tools = {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}
    tool = tools["opportunities_accept_research_handoff"]
    assert set(tool.parameters["properties"]) == {"opportunity_id", "handoff_json", "research_work_id"}
    from services.nexus_mcp.auth import authorize_action
    authorize_action("opportunities_accept_research_handoff")
