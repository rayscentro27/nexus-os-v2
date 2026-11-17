"""One production-order continuous-kernel wake with all network disabled."""
import json
import os
import socket
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, parse_qs

import pytest

sys.path[:0] = ["scripts", "scripts/social"]


class _Response:
    def __init__(self, body, status=200):
        self.status = status
        self._body = json.dumps(body).encode()

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, *_): return self._body


@pytest.mark.parametrize("scenario,channel_count,market_due,pending_count,recovery_count,feeder_gap_count,resume_count,combined", [
    ("CHANNELS_1", 1, False, 0, 0, 0, 0, False),
    ("EMPTY_QUEUE", 2, False, 0, 0, 0, 0, False),
    ("CHANNELS_3", 3, False, 0, 0, 0, 0, False),
    ("CHANNELS_10", 10, False, 0, 0, 0, 0, False),
    ("MARKET_HEARTBEAT_DUE", 2, True, 0, 0, 0, 0, False),
    ("ONE_PENDING_GAP", 2, False, 1, 0, 0, 0, False),
    ("FIVE_PENDING_GAPS", 2, False, 5, 0, 0, 0, False),
    ("FIFTEEN_PENDING_GAPS", 2, False, 15, 0, 0, 0, False),
    ("RECOVERY_0", 2, False, 0, 0, 0, 0, False),
    ("RECOVERY_1", 2, False, 0, 1, 0, 0, False),
    ("RECOVERY_5", 2, False, 0, 5, 0, 0, False),
    ("RECOVERY_15", 2, False, 0, 15, 0, 0, False),
    ("PENDING_FEEDER_RESEARCH_GAPS", 2, False, 0, 0, 5, 0, False),
    ("FIFTEEN_SOURCE_RESUME", 2, False, 0, 0, 0, 15, False),
    ("CONTENT_INTELLIGENCE_DUE", 2, True, 0, 0, 0, 0, False),
    ("REALISTIC_COMBINED_STARTUP", 2, True, 0, 5, 5, 0, True),
])
def test_complete_kernel_wake_is_mocked_and_research_sources_are_attributed(
        monkeypatch, tmp_path, scenario, channel_count, market_due, pending_count,
        recovery_count, feeder_gap_count, resume_count, combined):
    concurrency_keys = ("NEXUS_RESEARCH_MAX_TOTAL_CONCURRENCY", "NEXUS_RESEARCH_MAX_YOUTUBE_CONCURRENCY",
                        "NEXUS_RESEARCH_MAX_WEB_CONCURRENCY", "NEXUS_RESEARCH_MAX_DISCOVERY_CONCURRENCY")
    initial_concurrency_env = {key: os.environ.get(key) for key in concurrency_keys}
    import _supabase as sb
    import run_continuous_operating_kernel as kernel
    from nexus_agent_platform import feeder_runtime, research_sources_trace as trace
    from nexus_agent_platform import supabase_egress_guard as guard
    from research import notebooklm_research_worker as research_worker, youtube_full_pipeline
    from research import pulse_runtime
    from research import run_market_intelligence_heartbeat as heartbeat
    from nexus_agent_platform import content_intelligence as content
    import youtube_full_pipeline as top_level_youtube
    # The production module applies its weekend mode to the process at import;
    # undo only that import side effect inside this isolated test process.
    for key, value in initial_concurrency_env.items():
        if value is None: os.environ.pop(key, None)
        else: os.environ[key] = value

    # Redirect all diagnostic/runtime writes touched by this one bounded wake.
    monkeypatch.setattr(kernel, "ROOT", tmp_path)
    monkeypatch.setattr(kernel, "PROGRESS_PATH", tmp_path / "progress.json")
    monkeypatch.setattr(kernel, "EXECUTION_JOBS_PATH", tmp_path / "execution.jsonl")
    monkeypatch.setattr(research_worker, "ROOT", tmp_path)
    monkeypatch.setattr(research_worker, "PROACTIVE_STATE_PATH", tmp_path / "proactive-state.json")
    monkeypatch.setattr(trace, "TRACE_PATH", tmp_path / "diagnostics/research_sources_trace.jsonl")
    monkeypatch.setattr(guard, "STATE", tmp_path / "egress.json")
    monkeypatch.setattr(guard, "SAFE_MODE_STATE", tmp_path / "safe-mode.json")
    monkeypatch.setattr(guard, "WAKE_BUDGET_STATE", tmp_path / "research_sources_wake_budget.json")
    monkeypatch.setattr(guard, "SYSTEMS_INCIDENTS", tmp_path / "systems_workflow_runs.jsonl")
    monkeypatch.setattr(sb, "URL", "https://mock.supabase.invalid")
    monkeypatch.setattr(sb, "KEY", "mock-key")
    # Several legacy modules import the shared adapter under the top-level and
    # social package names; redirect each loaded adapter to the same mock host.
    for loaded in list(sys.modules.values()):
        if loaded is not None and hasattr(loaded, "URL") and hasattr(loaded, "KEY") and hasattr(loaded, "rest"):
            monkeypatch.setattr(loaded, "URL", sb.URL)
            monkeypatch.setattr(loaded, "KEY", sb.KEY)
    monkeypatch.setenv("SUPABASE_URL", sb.URL)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", sb.KEY)
    monkeypatch.setenv("NEXUS_RESEARCH_SOURCES_TRACE", "1")

    wake_id = f"wake_mock_{scenario.lower()}"
    calls = []
    feeder_calls = []
    handoff_posts = []
    questionnaire_reads = []
    fifo_dispatches = []
    actual_network_attempts = []
    now = datetime.now(timezone.utc)
    jobs = [
        {"job_id": name, "cadence_seconds": cadence, "enabled": True,
         "next_run_at": (now + timedelta(hours=2)).isoformat(), "last_status": "PASS"}
        for name, cadence in pulse_runtime.PULSE_JOBS.items()
    ]

    def mock_urlopen(request, *args, **kwargs):
        url = request.full_url if isinstance(request, __import__("urllib.request").request.Request) else str(request)
        parts = urlsplit(url)
        if parts.hostname != "mock.supabase.invalid":
            actual_network_attempts.append(parts.hostname or "unknown")
            raise AssertionError("NETWORK_CALL_BLOCKED_BY_KERNEL_WAKE_HARNESS")
        path = parts.path.split("/rest/v1/", 1)[-1]
        table = path.split("?", 1)[0]
        query = parse_qs(parts.query)
        calls.append({"table": table, "query": parts.query, "method": getattr(request, "method", "GET")})
        if table == "research_sources":
            if "registry_kind" in parts.query:
                result = [{"id": f"channel-{i}", "title": f"Mock channel {i}",
                           "url": f"https://youtube.com/channel/UC{i}",
                           "metadata": {"source_id": f"channel-{i}", "name": f"Mock channel {i}",
                               "source_type": "YOUTUBE_CHANNEL", "canonical_url": f"https://youtube.com/channel/UC{i}",
                               "external_channel_id": f"UC{i}", "enabled": True,
                               "monitor_mode": "NEW_CONTENT_ONLY", "triage_mode": "TRIAGE_ONLY",
                               "registry_kind": "DESIGNATED_YOUTUBE_CHANNEL"}}
                          for i in range(channel_count)]
            elif "video_id" in parts.query:
                result = [{"metadata": {"video_id": f"oldvideo{i:07d}"}} for i in range(3)]
            elif "id=eq." in parts.query:
                result = [{"id": "mock-row", "metadata": {}}]
            else:
                result = []
        elif table == "pulse_schedule_registry":
            result = jobs if "enabled=eq.true" in parts.query else [row for row in jobs if f"job_id=eq.{row['job_id']}" in parts.query]
        elif table == "pulse_provider_registry":
            result = [{"provider_name": f"P{i}", "current_status": "PASS", "nexus_tested": True} for i in range(8)]
        elif table == "nexus_feeder_runtime_settings":
            result = [{"settings_id": "NEXUS_FEEDER_RUNTIME", "external_feeders_enabled": True,
                       "ray_nova_intake_enabled": False, "max_sources_per_wake": 4}]
        else:
            result = []
        method = getattr(request, "method", "GET")
        status = 201 if method.upper() == "POST" else 200
        if method.upper() == "POST" and table == "research_sources":
            result = [{"id": f"mock-source-{len(calls)}"}]
        elif method.upper() == "POST" and not result:
            result = [{"id": f"mock-row-{len(calls)}"}]
        return _Response(result, status)

    monkeypatch.setattr(sb.urllib.request, "urlopen", mock_urlopen)
    monkeypatch.setattr(sys, "argv", ["run_continuous_operating_kernel.py", "--daemon", "--max-cycles", "1"])
    monkeypatch.setattr(kernel, "build_source_registry", lambda: [])
    monkeypatch.setattr(kernel, "build_program_registry", lambda **_: [])
    monkeypatch.setattr(kernel, "run_productivity_audit", lambda **_: {"status": "SKIPPED_INTERVAL"})
    monkeypatch.setattr(kernel, "market_wake_due", lambda *_: market_due)
    if hasattr(kernel, "market_last_run"):
        monkeypatch.setattr(kernel, "market_last_run", 0)
    monkeypatch.setattr(kernel, "fifo_queue_wake", lambda item, **_: {"status": "PASS", "work_id": item.get("work_id")})
    monkeypatch.setattr(kernel, "run_due_tradingview_monitor", lambda: {"status": "NOT_DUE"})
    monkeypatch.setattr(kernel, "run_cycle", lambda fn, **kwargs: {"result": fn(), "cycle_id": kwargs.get("cycle_id")})
    monkeypatch.setattr(kernel, "bounded_wake", lambda callback, **kwargs: callback())
    monkeypatch.setattr(kernel, "select_lane", lambda **_: {"no_source_selected": True, "selection_reason": "MOCK_EMPTY_QUEUE"})

    fixture_count = max(feeder_gap_count, resume_count)
    feeder_sources = [{"source_id": f"fixture-source-{i}", "feeder_type": [
        "BUSINESS_OPPORTUNITY_FEEDER", "BUSINESS_FUNDING_FEEDER",
        "BUSINESS_CREATION_BANKABILITY_FEEDER", "FOREX_INDICATOR_STRATEGY_FEEDER",
        "OPTIONS_STRATEGY_FEEDER"][i % 5], "source_type": "YOUTUBE_VIDEO",
        "source_title": f"Completed fixture source {i}", "source_url": f"https://youtube.com/watch?v=fixture{i}",
        "notebook_reference": f"canonical-notebook-{i % 5}", "case_id": f"case-{i}"}
        for i in range(fixture_count)]
    feeder_gap_rows = [{"question_id": f"gap-{i}", "source_id": f"fixture-source-{i if resume_count else 0}",
                        "question": f"Exact verification question {i}", "return_to": "BUSINESS_FUNDING",
                        "research_request_id": (f"gap-{i}" if combined or resume_count else None),
                        "status": ("IN_PROGRESS" if combined or resume_count else "OPEN")}
                       for i in range(max(feeder_gap_count, resume_count))]
    work_items = ([{"work_id": f"gap-{i}", "status": "COMPLETE", "request_type": "FEEDER_GAP_CLOSURE",
                    "last_result": {"gap_state": "COMPLETED", "evidence_state": "CROSS_SUPPORTED"},
                    "artifact_id": f"artifact-{i}", "result_id": f"result-{i}",
                    "evidence_refs": [], "completed_at": now.isoformat()}
                   for i in range(resume_count)] if resume_count else [])
    if pending_count:
        work_items = [{"work_id": f"pending-{i}", "status": "QUEUED", "work_class": "GENERAL_DISCOVERY",
                       "request_type": "FEEDER_GAP_CLOSURE", "source_id": f"fixture-source-{i}",
                       "notebook_reference": f"canonical-notebook-{i % 5}",
                       "recommended_research_method": "NOTEBOOKLM_FAST_RESEARCH"}
                      for i in range(pending_count)]
    if combined:
        # Research is pending but not eligible yet, so it can coexist with the
        # scheduled heartbeat under the kernel's due-work priority rules.
        work_items = [{"work_id": "pending-gap", "status": "WAITING", "work_class": "GENERAL_DISCOVERY",
                       "next_eligible_at": (now + timedelta(hours=2)).isoformat(),
                       "request_type": "FEEDER_GAP_CLOSURE", "source_id": "fixture-source-0",
                       "notebook_reference": "canonical-notebook-0"}]

    class _Queue:
        def __init__(self):
            self.items = list(work_items)
            self.expired = [{"work_id": f"recovery-{i}", "status": "EXPIRED_LEASE",
                             "work_class": "GENERAL_DISCOVERY", "request_type": "FEEDER_GAP_CLOSURE",
                             "source_id": f"fixture-source-{i}",
                             "notebook_reference": f"canonical-notebook-{i % 5}"}
                            for i in range(recovery_count)]
            self.recovery_calls = 0
        def migrate_fifo(self): return None
        def load(self): return {"items": [*self.items, *self.expired]}
        def claim_next(self, **_):
            for row in [*self.items, *self.expired]:
                if row.get("status") == "QUEUED":
                    row["status"] = "IN_PROGRESS"
                    return row
            return None
        def recover_expired_leases(self):
            self.recovery_calls += 1
            recovered = 0
            for row in self.expired:
                if row.get("status") == "EXPIRED_LEASE":
                    row["status"] = "QUEUED"; recovered += 1
            return recovered
        def summary(self): return {"queue_depth": 0, "by_class": {}, "by_status": {}}
        def release(self, *_args, **_kwargs): return None
        def settle(self, work_id, status, **_kwargs):
            row = next((item for item in [*self.items, *self.expired] if item.get("work_id") == work_id), None)
            if row: row["status"] = status
            return row

    queue = _Queue()
    def mock_feeder_request(path, method="GET", body=None, prefer="return=minimal"):
        feeder_calls.append({"path": path, "method": method, "body": body})
        if "questionnaire_runs" in path: questionnaire_reads.append(path)
        if path.startswith("nexus_feeder_runtime_settings"):
            return [{"settings_id": "NEXUS_FEEDER_RUNTIME", "external_feeders_enabled": True,
                     "ray_nova_intake_enabled": False, "max_sources_per_wake": 4}]
        if "nexus_feeder_research_gaps?status=eq.OPEN" in path:
            return [dict(row) for row in feeder_gap_rows if row["status"] == "OPEN"]
        if "nexus_feeder_research_gaps?status=in." in path:
            return [dict(row) for row in feeder_gap_rows]
        if "nexus_feeder_research_gaps?source_id=in." in path and "status=neq.COMPLETED" in path:
            return []
        if "nexus_feeder_sources?source_id=in." in path:
            return feeder_sources
        if "nexus_feeder_sources?source_id=eq." in path:
            return [row for row in feeder_sources if row["source_id"] in path]
        if "nexus_feeder_questionnaire_runs?source_id=in." in path:
            return [{"source_id": row["source_id"], "structured_fields": {"fixture": True},
                     "source_claims": [], "recommended_next_action": "DEPARTMENT_REVIEW",
                     "started_at": now.isoformat()} for row in feeder_sources]
        if "nexus_feeder_questionnaire_runs?source_id=eq." in path:
            return [{"source_id": "fixture", "structured_fields": {"fixture": True},
                     "source_claims": [], "recommended_next_action": "DEPARTMENT_REVIEW"}]
        if "nexus_feeder_sources?ingestion_status=in." in path or "nexus_feeder_templates" in path:
            return []
        if method == "POST":
            if "nexus_feeder_handoffs?on_conflict=handoff_id" in path: handoff_posts.append(body)
            return [{"id": f"feeder-row-{len(feeder_calls)}"}]
        return []
    monkeypatch.setattr(feeder_runtime, "_request", mock_feeder_request)
    monkeypatch.setattr(feeder_runtime, "_enqueue_gap", lambda src, qid, question, route: queue.items.append(
        {"work_id": qid, "status": "QUEUED", "work_class": "GENERAL_DISCOVERY",
         "request_type": "FEEDER_GAP_CLOSURE", "source_id": src.get("source_id"),
         "notebook_reference": src.get("notebook_reference"),
         "recommended_research_method": "NOTEBOOKLM_FAST_RESEARCH"}))
    import nexus_agent_platform.research_work_queue as rwq
    monkeypatch.setattr(rwq, "ResearchWorkQueue", lambda: queue)
    monkeypatch.setattr(kernel, "default_queue", lambda: queue)
    monkeypatch.setattr(research_worker, "default_queue", lambda: queue)
    monkeypatch.setattr(youtube_full_pipeline, "select_channel_videos", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(top_level_youtube, "select_channel_videos", lambda *_args, **_kwargs: [])
    if "youtube_full_pipeline" in sys.modules:
        monkeypatch.setattr(sys.modules["youtube_full_pipeline"], "select_channel_videos", lambda *_args, **_kwargs: [])

    if market_due:
        topics = ["business funding", "online business", "AI consulting"]
        monkeypatch.setattr(heartbeat, "seed_topics", lambda: topics)
        monkeypatch.setattr(heartbeat, "bounded_lane", lambda callback, **_: callback())
        monkeypatch.setattr(heartbeat, "touch_seed_registry", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(heartbeat, "youtube_content", lambda *_args, **_kwargs: {"videos": [], "videos_found": 0, "failures": []})
        monkeypatch.setattr(heartbeat, "run_lane", lambda *_args, **_kwargs: {"status": "COMPLETED", "results_found": 0, "new_sources": 0, "duplicates": 0, "failed_queries": []})
        monkeypatch.setattr(heartbeat, "affiliate_discovery", lambda *_args, **_kwargs: {"status": "COMPLETED", "programs_discovered": 0})
        monkeypatch.setattr(content, "_public_json", lambda *_args, **_kwargs: ["", ["signal-a", "signal-b", "signal-c"]])
        monkeypatch.setattr(content, "youtube_content", lambda *_args, **_kwargs: {"videos": [], "videos_found": 0, "failures": []})
        from research import proactive_research_memory
        monkeypatch.setattr(proactive_research_memory, "close_due_research_cases", lambda **_: {"closed": 0})

    # Feeder process_once runs through the kernel phase with synthetic replies.
    guard.invalidate_cache("settings:feeder_runtime")
    if scenario == "CONTENT_INTELLIGENCE_DUE":
        research_worker.PROACTIVE_STATE_PATH.write_text(json.dumps({
            "last_channel_refresh": now.isoformat(), "last_proactive_search": now.isoformat(),
            "last_gap_scan": now.isoformat()}))

    class _Completed:
        def __init__(self, stdout="{}", returncode=0): self.stdout, self.returncode, self.stderr = stdout, returncode, ""

    def mock_subprocess_run(command, **kwargs):
        if "systems_workflow" in " ".join(map(str, command)):
            return _Completed(json.dumps({"status": "PASS"}))
        if "feeder_runtime.py" in " ".join(map(str, command)):
            result = feeder_runtime.process_once()
            return _Completed(json.dumps(result))
        return _Completed("{}", 0)

    monkeypatch.setattr(kernel.subprocess, "run", mock_subprocess_run)
    # Invoke the actual dispatched worker entry point in-process with its
    # child environment. This prevents a real child process while exercising
    # the production dispatch and feeder-gap hydration path.
    import types
    notebook_expansion = types.ModuleType("notebook_source_expansion")
    notebook_expansion.run_notebook_gap_operator = lambda context: {
        "gap_state": "COMPLETED", "supabase_persistence_pass": True,
        "evidence_state": "CROSS_SUPPORTED", "return_to_feeder": True,
        "research_session_id": "mock-session"}
    monkeypatch.setitem(sys.modules, "notebook_source_expansion", notebook_expansion)
    import run_dispatched_research_job as dispatched
    monkeypatch.setattr(dispatched, "default_queue", lambda: queue)
    monkeypatch.setattr(dispatched, "event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dispatched, "JOBS", tmp_path / "research_execution_jobs.jsonl")
    def mocked_fifo_wake(item, *, execution_id, timeout_seconds):
        fifo_dispatches.append(item.get("work_id"))
        child_env = kernel.child_environment({**os.environ,
            "NEXUS_FIFO_QUEUE": "1", "NEXUS_WORK_ID": str(item.get("work_id", "")),
            "NEXUS_SELECTED_LANE_ID": "FIFO_RESEARCH",
            "NEXUS_SELECTED_WORK_CLASS": str(item.get("work_class", "")),
            "NEXUS_WORK_ITEM_JSON": json.dumps(item, sort_keys=True)})
        prior_argv = sys.argv
        try:
            sys.argv = ["run_dispatched_research_job.py", "--execution-id", execution_id,
                        "--timeout-seconds", str(timeout_seconds)]
            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(os.environ, child_env, clear=False):
                exit_code = dispatched.main()
            return {"status": "PASS" if exit_code == 0 else "DEGRADED", "work_id": item.get("work_id"),
                    "worker_exit_code": exit_code}
        finally:
            sys.argv = prior_argv
    monkeypatch.setattr(kernel, "fifo_queue_wake", mocked_fifo_wake)

    # The imported handoff module is isolated to a no-work result.
    import types
    handoff = types.ModuleType("operations.department_handoff_continuation")
    handoff.process_next_company_case_directive = lambda **_: {"status": "DIRECTIVE_RUNTIME_DEGRADED"}
    monkeypatch.setitem(sys.modules, "operations.department_handoff_continuation", handoff)

    # Any non-mocked raw socket path fails closed even if a helper bypasses urllib.
    def blocked_socket(*args, **kwargs):
        actual_network_attempts.append("raw-socket")
        raise AssertionError("RAW_NETWORK_CALL_BLOCKED_BY_KERNEL_WAKE_HARNESS")
    monkeypatch.setattr(socket, "create_connection", blocked_socket)
    monkeypatch.setattr(socket.socket, "connect", blocked_socket)
    monkeypatch.setenv("NEXUS_WAKE_ID", wake_id)
    assert kernel.main() in (0, 1)
    assert actual_network_attempts == []
    trace_rows = [json.loads(line) for line in trace.TRACE_PATH.read_text().splitlines()] if trace.TRACE_PATH.exists() else []
    wake_ids = {row["wake_id"] for row in trace_rows}
    assert len(wake_ids) <= 1 and (not wake_ids or next(iter(wake_ids)).startswith("wake_"))
    assert all(row["query"].get("selected_fields") != ["*"] for row in trace_rows)
    assert len([call for call in calls if call["table"] == "research_sources"]) == len(trace_rows)
    from nexus_agent_platform import supabase_egress_guard as egress_guard
    assert len(trace_rows) <= egress_guard.MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE
    if scenario == "CONTENT_INTELLIGENCE_DUE":
        assert len(trace_rows) == 9
    elif market_due:
        # Trend signals use one identity batch and one idempotent bulk upsert;
        # interpretation packages retain their bounded writes.
        assert len(trace_rows) == 12
    elif pending_count or feeder_gap_count:
        assert len(trace_rows) == 0
    else:
        assert len(trace_rows) == 3
    expected_calls = (12 if scenario in {"MARKET_HEARTBEAT_DUE", "REALISTIC_COMBINED_STARTUP"} else
                      9 if scenario == "CONTENT_INTELLIGENCE_DUE" else
                      0 if pending_count or feeder_gap_count else 3)
    assert len(trace_rows) == expected_calls
    if scenario.startswith("RECOVERY_") or combined:
        assert queue.recovery_calls >= 1
    if scenario.startswith("RECOVERY_"):
        assert len(trace_rows) == 3
    if pending_count or scenario == "PENDING_FEEDER_RESEARCH_GAPS":
        assert len(fifo_dispatches) == 1
    if combined or resume_count or scenario == "RECOVERY_0":
        assert len(fifo_dispatches) == 0
    if scenario == "PENDING_FEEDER_RESEARCH_GAPS":
        source_batch_reads = [item for item in feeder_calls if item["method"] == "GET"
                              and item["path"].startswith("nexus_feeder_sources?source_id=in.")]
        assert len(source_batch_reads) == 1
        assert len([item for item in feeder_calls if item["method"] == "GET"
                    and "nexus_feeder_sources?source_id=eq." in item["path"]]) == 0
    if resume_count:
        assert len(handoff_posts) == resume_count
        handoff_ids = [row.get("handoff_id") for row in handoff_posts if isinstance(row, dict)]
        assert len(handoff_ids) == resume_count and len(set(handoff_ids)) == resume_count
        assert len(questionnaire_reads) == 1  # one batch read of completed questionnaire records
        assert not any(item["method"] == "POST" and item["path"].startswith("nexus_feeder_sources?")
                       for item in feeder_calls)
    groups = {}
    for row in trace_rows:
        key = (row["caller_module"], row["caller_function"], row["kernel_phase"],
               json.dumps(row["query"], sort_keys=True))
        groups[key] = groups.get(key, 0) + 1
    source_query_calls = [row for row in feeder_calls if row["path"].startswith("nexus_feeder_sources?")]
    endpoint_counts = Counter(call["table"] for call in calls)
    print(json.dumps({"scenario": scenario, "correlation_id": next(iter(wake_ids), None),
                      "research_sources_calls": len(trace_rows),
                      "caller_breakdown": [{"module": key[0], "function": key[1], "phase": key[2],
                                            "query": json.loads(key[3]), "count": count}
                                           for key, count in groups.items()],
                      "supabase_requests": len(calls), "monitored_channels": channel_count,
                      "top_endpoints": endpoint_counts.most_common(5),
                      "fifo_dispatches": len(fifo_dispatches),
                      "feeder_source_queries": len(source_query_calls), "handoffs": len(handoff_posts),
                      "questionnaire_reads": len(questionnaire_reads),
                      "market_heartbeat_due": market_due,
                      "network_calls_allowed": False}, sort_keys=True))
