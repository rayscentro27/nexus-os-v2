import json

from nexus_agent_platform.department_router import classify_intent, execute, resolve


def test_conversation_and_state_queries_do_not_require_execution_routes():
    for text in ("Hello Nexus", "How are you today?", "Good morning", "What can you do?"):
        assert classify_intent(text) == "CONVERSATION"
        response, metadata = execute(text)
        assert metadata["lane"] == "CONVERSATIONAL_LANE"
        assert "loop" not in metadata
        assert "loop" not in response.lower()
    for text in ("What is the current status of Nexus?", "What's working right now?", "What is blocked?", "What needs my attention?"):
        assert classify_intent(text) == "STATE_QUERY"
        response, metadata = execute(text)
        assert metadata["lane"] == "READ_ONLY_STATE_LANE"
        assert "What is true now?" in response
    for text in ("Show current jobs.", "Show me current durable jobs."):
        assert classify_intent(text) == "LIST_JOBS"
        response, metadata = execute(text)
        assert metadata["lane"] == "READ_ONLY_STATE_LANE"
        assert "Nexus objective accepted" not in response
    assert classify_intent("What is Research doing?") == "STATE_QUERY"
    assert classify_intent("Find one current online business with publicly visible pricing and cite the public pricing page.") == "RESEARCH"


def test_status_queries_do_not_build_company_objective_steps():
    from nexus_agent_platform.company_objective_router import route_company_objective
    for text in ("Show current jobs.", "Show me current durable jobs.", "What is Research doing?"):
        result = route_company_objective(text, conversation_message_id="read-query-test")
        assert result["intent_class"] in {"STATE_QUERY", "LIST_JOBS"}
        assert len(result["steps"]) == 1
        assert result["routing_basis"]["read_only"] is True


def test_department_intents_resolve_through_canonical_registries():
    expected = {
        "Run the system operations check": ("SYSTEM_OPERATIONS", "OPERATIONS", "NEXUS_DAILY_SYSTEM_OPERATIONS"),
        "Check the repo": ("REPO_INTELLIGENCE", "SYSTEM_ENGINEERING", "NEXUS_REPO_INTELLIGENCE"),
        "What's blocking funding readiness?": ("FUNDING_READINESS", "CREDIT_BUSINESS_FUNDING", "NEXUS_CREDIT_BUSINESS_FUNDING"),
    }
    for text, (intent, department, loop) in expected.items():
        result = resolve(text)
        assert result["intent_class"] == intent
        assert result["department"] == department
        assert result["loop"] == loop
        assert result["status"] == "RESOLVED"
    research = resolve("Research this company")
    assert research["intent_class"] == "ASSIGN_DEPARTMENT_TASK"
    assert research["status"] == "GOVERNED_MCP_ASSIGNMENT_REQUIRED"
    assert "loop" not in research


def test_unknown_is_safe_and_approval_is_not_routed_as_operator_work():
    assert classify_intent("do something surprising") == "UNKNOWN"
    assert resolve("do something surprising")["status"] == "UNKNOWN_INTENT"
    assert classify_intent("APPROVE HG-WP5-HERMES-TELEGRAM-DEPARTMENT-ROUTING-20260829-01") == "UNKNOWN"


def test_execution_lane_still_requires_registry_route():
    response, metadata = execute("do something")
    assert metadata["outcome"] == "BLOCKED"
    assert "No work was executed" in response


def test_result_rendering_answers_the_question_without_receipt_path():
    checks = (
        ("Run the daily system operations check.", ("Nexus operations check", "KEY FINDINGS")),
        ("Research OpenAI.", ("Research:", "KEY FINDINGS")),
        ("Check the Nexus repository.", ("Repository intelligence:", "WORKTREE")),
    )
    for text, markers in checks:
        response, metadata = execute(text)
        assert metadata["outcome"] == "ANSWERED"
        assert all(marker.lower() in response.lower() for marker in markers)
        assert "receipt_path" not in response.lower()


def test_repository_result_has_operator_level_status_contract():
    response, metadata = execute("Check the Nexus repository.")
    assert metadata["outcome"] == "ANSWERED"
    for marker in ("CURRENT CHECKPOINT", "HEAD:", "Origin:", "ahead", "behind", "WORKTREE", "Changed paths", "Expected campaign changes", "VERIFICATION", "WHAT THIS MEANS", "NEXT ACTION"):
        assert marker.lower() in response.lower()
    assert "receipt_path" not in response.lower()


def test_research_result_has_synthesis_contract():
    response, metadata = execute("Research OpenAI.")
    assert metadata["outcome"] == "ANSWERED"
    for marker in ("EXECUTIVE SUMMARY", "KEY FINDINGS", "WHAT CHANGED", "WHY IT MATTERS", "UNCERTAINTIES", "SOURCES USED"):
        assert marker.lower() in response.lower()
    assert "receipt_path" not in response.lower()


def test_review_state_query_reads_actual_queue_without_creating_work():
    response, metadata = execute("What items currently need my review?")
    assert classify_intent("What items currently need my review?") == "RAY_REVIEW"
    assert metadata["lane"] == "EXECUTION_LANE"
    assert "do not currently have any required review items" in response.lower()
    assert "WHAT TO REVIEW FIRST" not in response
    assert "Verified Nexus receipt recorded" in response


def test_review_request_variants_use_governed_review_route():
    for text in ("Which items currently require my review?", "What approvals need my review?", "Prioritize the items that need my review"):
        result = resolve(text)
        assert result["intent_class"] == "RAY_REVIEW"
        assert result["department"] == "GOVERNANCE_REVIEW"
        assert result["loop"] == "NEXUS_RAY_REVIEW"


def test_operations_and_health_are_distinct_lanes():
    assert classify_intent("Run the daily system operations check") == "SYSTEM_OPERATIONS"
    assert classify_intent("Check for degraded services and recovery needs") == "SYSTEM_HEALTH"


def test_explicit_telegram_systems_health_command_becomes_health_assignment():
    assert classify_intent("Nova, run a real Nexus Systems health check now.\nUse the actual Systems department.") == "SYSTEM_HEALTH"


def test_systems_worker_prefix_does_not_shadow_natural_healthy_request():
    text = "Run a bounded read-only Systems system operations check: Nova, have Systems check whether Nexus is healthy."
    result = resolve(text)
    assert result["intent_class"] == "SYSTEM_HEALTH"
    assert result["loop"] == "NEXUS_SYSTEM_HEALTH_RECOVERY"


def test_notebooklm_resource_alarm_routes_to_systems_governor_diagnostic():
    text="Systems: diagnose the NotebookLM research_discovery resource circuit, retries and cache reuse."
    result=resolve(text)
    assert result["intent_class"]=="RESOURCE_GOVERNANCE_DIAGNOSIS"
    assert result["department"]=="OPERATIONS"
    assert result["loop"]=="NEXUS_RESOURCE_GOVERNANCE_DIAGNOSIS"
    assert result["status"]=="RESOLVED"


def test_v5_parallel_public_research_uses_its_approved_oracle_policy(monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform.loops import governed_loops as loops
    captured={}
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job-public-research")
    monkeypatch.setenv("NEXUS_JOB_ATTEMPT_COUNT","4")
    monkeypatch.setattr("nexus_agent_platform.provider_enforcement.execute",
        lambda provider,service,action,estimate,operation,**context:
            captured.update(provider=provider,service=service,job_type=context.get("job_type"),purpose=context.get("purpose")) or operation())
    monkeypatch.setattr(loops.subprocess,"run",lambda *args,**kwargs:
        SimpleNamespace(returncode=0,stderr="",stdout=json.dumps({"query":"public business models",
            "results":[{"title":"Source","url":"https://example.test/source","content":"Public evidence."}]})))
    result=loops._research({"question":"Research public business models",
        "live_private_searxng":True,"v5_owner_campaign":True})
    assert result["status"]=="PASS"
    assert captured=={"provider":"ORACLE","service":"private_research_search",
        "job_type":"NEXUS_DEPARTMENT_QUERY_V5_6FB82FD9:PRIVATE_RESEARCH_SEARCH",
        "purpose":"READ_ONLY_REMOTE_SEARCH:job-public-research:4"}


def test_online_business_pricing_request_builds_relevant_provider_query(monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform.loops import governed_loops as loops
    captured={}
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job-runtime-research")
    monkeypatch.setenv("NEXUS_JOB_ATTEMPT_COUNT","1")
    monkeypatch.setattr("nexus_agent_platform.provider_enforcement.execute",
        lambda provider,service,action,estimate,operation,**context: operation())
    def fake_run(command,*args,**kwargs):
        captured["command"]=" ".join(command)
        return SimpleNamespace(returncode=0,stderr="",stdout='{"query":"online business public pricing page pricing plans","results":[]}')
    monkeypatch.setattr(loops.subprocess,"run",fake_run)
    loops._research({"question":"Find one current online business with publicly visible pricing and cite the public pricing page.",
        "live_private_searxng":True,"v5_owner_campaign":True})
    assert "find%20one" not in captured["command"].lower()
    assert "project%20management%20software%20pricing%20plans%20per%20user%20per%20month%20official%20pricing%20page" in captured["command"].lower()


def test_targeted_pricing_query_keeps_entity_and_drops_reporting_tail(monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform.loops import governed_loops as loops
    captured={}
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job-targeted-pricing")
    monkeypatch.setenv("NEXUS_JOB_ATTEMPT_COUNT","1")
    monkeypatch.setattr("nexus_agent_platform.provider_enforcement.execute",
        lambda provider,service,action,estimate,operation,**context: operation())
    def fake_run(command,*args,**kwargs):
        captured["command"]=" ".join(command)
        return SimpleNamespace(returncode=0,stderr="",stdout='{"query":"Calendly pricing page","results":[]}')
    monkeypatch.setattr(loops.subprocess,"run",fake_run)
    loops._research({"question":"Research the current official Calendly pricing page and its listed plan prices.",
        "live_private_searxng":True,"v5_owner_campaign":True})
    assert "Calendly%20pricing%20page" in captured["command"]
    assert "current" not in captured["command"].split("&format")[0]


def test_current_operator_and_named_service_evidence_are_rendered():
    response, metadata = execute("Run the daily system operations check")
    assert metadata["outcome"] == "ANSWERED"
    for service in ("Hermes", "Ollama", "SearXNG", "TruthKernel", "Active Operator", "Mac/Oracle bridge"):
        assert service in response
    assert "Verify Supabase via browser DevTools" not in response


def test_repo_analysis_has_operational_consequence_language():
    response, metadata = execute("Inspect the current nexus-os-v2 repository and identify recent changes affecting Active Operator stability")
    assert metadata["outcome"] == "ANSWERED"
    assert "WHY IT MATTERS" in response
    assert "This change is in the Active Operator/runtime evidence path." not in response


def test_department_registry_has_real_departments_and_shared_skill_mapping():
    registry = json.load(open("data/runtime/nexus_department_registry.json"))
    ids = {item["department_id"] for item in registry["departments"]}
    assert {"OPERATIONS", "RESEARCH_ALPHA", "CREDIT_BUSINESS_FUNDING", "CLIENT_LIFECYCLE", "MARKETING_CREATIVE", "GOVERNANCE_REVIEW", "SYSTEM_ENGINEERING"} <= ids
    skills = json.load(open("data/runtime/nexus_skill_registry.json"))
    assert len(skills["department_mappings"]["work-order-management"]["secondary_departments"]) >= 3
    assert len(skills["department_mappings"]["failure-recovery"]["other_allowed_loops"]) >= 1
