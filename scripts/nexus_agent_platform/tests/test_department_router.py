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


def test_department_intents_resolve_through_canonical_registries():
    expected = {
        "Run the system operations check": ("SYSTEM_OPERATIONS", "OPERATIONS", "NEXUS_DAILY_SYSTEM_OPERATIONS"),
        "Research this company": ("RESEARCH", "RESEARCH_ALPHA", "NEXUS_RESEARCH_INTELLIGENCE"),
        "Check the repo": ("REPO_INTELLIGENCE", "SYSTEM_ENGINEERING", "NEXUS_REPO_INTELLIGENCE"),
        "What's blocking funding readiness?": ("FUNDING_READINESS", "CREDIT_BUSINESS_FUNDING", "NEXUS_CREDIT_BUSINESS_FUNDING"),
    }
    for text, (intent, department, loop) in expected.items():
        result = resolve(text)
        assert result["intent_class"] == intent
        assert result["department"] == department
        assert result["loop"] == loop
        assert result["status"] == "RESOLVED"


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
    assert metadata["lane"] == "READ_ONLY_STATE_LANE"
    assert "Verified Nexus review state was checked" in response


def test_department_registry_has_real_departments_and_shared_skill_mapping():
    registry = json.load(open("data/runtime/nexus_department_registry.json"))
    ids = {item["department_id"] for item in registry["departments"]}
    assert {"OPERATIONS", "RESEARCH_ALPHA", "CREDIT_BUSINESS_FUNDING", "CLIENT_LIFECYCLE", "MARKETING_CREATIVE", "GOVERNANCE_REVIEW", "SYSTEM_ENGINEERING"} <= ids
    skills = json.load(open("data/runtime/nexus_skill_registry.json"))
    assert len(skills["department_mappings"]["work-order-management"]["secondary_departments"]) >= 3
    assert len(skills["department_mappings"]["failure-recovery"]["other_allowed_loops"]) >= 1
