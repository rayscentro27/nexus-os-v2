from nova.semantic_orchestration import resolve_owner_request
import pytest


def test_alpha_paraphrases_resolve_to_same_governed_capability():
    requests = [
        "Have Alpha review that.",
        "Ask Alpha whether that business is any good.",
        "What does Alpha think about the business Research found?",
        "Run Research's last idea through Alpha.",
    ]
    results = [resolve_owner_request(value) for value in requests]
    assert all(row["intent"] == "DEPARTMENT_ASSIGNMENT" for row in results)
    assert all(row["department"] == "ALPHA" for row in results)
    assert all(row["executor"] == "nexus_assign_department_query" for row in results)


def test_systems_health_paraphrases_resolve_to_same_capability():
    requests = [
        "Check the system.",
        "Have Systems make sure everything is healthy.",
        "Run a Nexus health check.",
    ]
    results = [resolve_owner_request(value) for value in requests]
    assert all(row["intent"] == "DEPARTMENT_ASSIGNMENT" for row in results)
    assert all(row["department"] == "SYSTEMS" for row in results)


def test_implicit_business_discovery_selects_research():
    result = resolve_owner_request("Find me a business worth looking at.")
    assert result["intent"] == "RESEARCH_ROOM_REQUEST"
    assert result["department"] == "RESEARCH"
    assert result["execution_mode"] == "BUSINESS_OPPORTUNITY_MODE"
    assert result["executor"] == "research_room_shadow_intake"


@pytest.mark.parametrize("message", [
    "Nova, research livestorebuild.com and tell me whether Nexus should use it, partner with it, copy the model, or avoid it.",
    "Nova, research the latest five videos from this YouTube channel and tell me whether anything in them can improve Nexus Trading.",
])
def test_natural_research_commands_are_research_missions_not_prior_result_queries(message):
    result = resolve_owner_request(message)
    assert result["intent"] == "RESEARCH_MISSION"
    assert result["department"] == "RESEARCH"
    assert result["executor"] == "nexus_assign_research"


def test_alpha_research_gap_request_stays_one_cross_department_continuation():
    result = resolve_owner_request(
        "Nova, since Alpha says the evidence is weak, have Research fix the biggest evidence gap and then send the improved result back through Alpha."
    )
    assert result["intent"] == "CROSS_DEPARTMENT_CONTINUATION"
    assert result["department"] == "RESEARCH"
    assert result["capabilities"] == ["RESEARCH", "ALPHA"]


def test_capability_questions_and_unsupported_department_work_stay_truthful():
    assert resolve_owner_request("What tools can you use right now?")["intent"] == "CAPABILITY_QUERY"
    unsupported = resolve_owner_request("Prepare a full marketing launch campaign.")
    assert unsupported["intent"] == "MARKETING_REQUEST"
    assert unsupported["executor"] is None


@pytest.mark.parametrize("message", [
    "How many Nexus MCP tools are available?",
    "Nova, use Nexus MCP only and tell me how many tools are currently available. "
    "Do not use model memory. If the MCP call fails, return the actual blocker.",
    "Nova, what do you have access to?",
])
def test_standalone_live_capability_questions_precede_stale_conversation_context(message):
    result = resolve_owner_request(message)
    assert result["intent"] == "CAPABILITY_QUERY"
    assert result["executor"] == "nexus_mcp_tool_discovery"
    assert result["capability"] == "nexus.mcp.tool_discovery"
    assert result["job_id"] is None


def test_unambiguous_named_research_followup_can_resolve_existing_objective():
    result = resolve_owner_request("What's happening with that LiveStoreBuild research?")
    assert result["intent"] == "OBJECTIVE_STATUS_QUERY"
    assert result["executor"] == "nexus_get_durable_jobs"


def test_capability_request_after_status_request_starts_new_semantic_route():
    status = resolve_owner_request("why is job_example123 blocked?")
    capability = resolve_owner_request("How many Nexus MCP tools are available?")
    assert status["intent"] == "RESEARCH_STATUS_QUERY"
    assert capability["intent"] == "CAPABILITY_QUERY"
    assert capability["job_id"] is None


def test_explicit_existing_research_job_inspection_precedes_mission_routing():
    request = ("Nova, inspect the existing Research job: "
               "job_e1e940074e6440439a852f2432cd5462. Do not create a new objective. "
               "Do not create a new Research job. Do not retry or restart the mission. "
               "The current state is BLOCKED. Return the exact blocker for this existing job.")
    result = resolve_owner_request(request)
    assert result["intent"] == "RESEARCH_STATUS_QUERY"
    assert result["executor"] == "nexus_get_durable_jobs"
    assert result["job_id"] == "job_e1e940074e6440439a852f2432cd5462"
    assert result["intent"] != "RESEARCH_MISSION"


@pytest.mark.parametrize("message", [
    "check status of job_example123",
    "why is job_example123 blocked",
    "retrieve the result for job_example123",
    "what was the result of job_example123",
    "is job_example123 complete",
    "inspect job_example123 and determine whether Research should continue",
])
def test_existing_job_status_and_result_phrasings_are_read_only(message):
    result = resolve_owner_request(message)
    assert result["intent"] == "RESEARCH_STATUS_QUERY"
    assert result["executor"] == "nexus_get_durable_jobs"


def test_retry_word_alone_does_not_route_to_research_assignment():
    result = resolve_owner_request("retry job_example123")
    assert result["intent"] not in {"RESEARCH_MISSION", "RESEARCH_REQUEST"}


def test_google_and_multicapability_requests_keep_their_semantic_targets():
    assert resolve_owner_request("What's my next calendar appointment?")["intent"] == "GOOGLE_ACTION"
    assert resolve_owner_request("Find the latest GoClear email and summarize it.")["intent"] == "GOOGLE_ACTION"
    result = resolve_owner_request("Look at our landing page and tell me what should improve.")
    assert result["intent"] == "MULTI_CAPABILITY_ORCHESTRATION"
    assert result["capabilities"] == ["BROWSER", "MARKETING"]


def test_natural_creative_asset_request_selects_governed_creative_executor():
    result = resolve_owner_request("Nova, have Creative make a simple test logo for Nexus Test.")
    assert result["intent"] == "CREATIVE_ASSET_REQUEST"
    assert result["executor"] == "nexus_assign_creative_asset"


def test_natural_opencode_request_selects_bounded_coding_executor():
    result = resolve_owner_request("Nova, have OpenCode create and run a small Python test in a temporary workspace.")
    assert result["intent"] == "BOUNDED_CODING_REQUEST"
    assert result["executor"] == "nexus_assign_bounded_coding_task"
