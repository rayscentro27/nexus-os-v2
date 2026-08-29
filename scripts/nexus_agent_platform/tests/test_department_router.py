import json

from nexus_agent_platform.department_router import classify_intent, resolve


def test_department_intents_resolve_through_canonical_registries():
    expected = {
        "How is Nexus doing?": ("STATUS", "OPERATIONS", "NEXUS_DAILY_SYSTEM_OPERATIONS"),
        "Run the system operations check": ("SYSTEM_OPERATIONS", "OPERATIONS", "NEXUS_DAILY_SYSTEM_OPERATIONS"),
        "Research this company": ("RESEARCH", "RESEARCH_ALPHA", "NEXUS_RESEARCH_INTELLIGENCE"),
        "Check the repo": ("REPO_INTELLIGENCE", "SYSTEM_ENGINEERING", "NEXUS_REPO_INTELLIGENCE"),
        "What's blocking funding readiness?": ("FUNDING_READINESS", "CREDIT_BUSINESS_FUNDING", "NEXUS_CREDIT_BUSINESS_FUNDING"),
        "What needs my attention?": ("RAY_REVIEW", "GOVERNANCE_REVIEW", "NEXUS_RAY_REVIEW"),
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


def test_department_registry_has_real_departments_and_shared_skill_mapping():
    registry = json.load(open("data/runtime/nexus_department_registry.json"))
    ids = {item["department_id"] for item in registry["departments"]}
    assert {"OPERATIONS", "RESEARCH_ALPHA", "CREDIT_BUSINESS_FUNDING", "CLIENT_LIFECYCLE", "MARKETING_CREATIVE", "GOVERNANCE_REVIEW", "SYSTEM_ENGINEERING"} <= ids
    skills = json.load(open("data/runtime/nexus_skill_registry.json"))
    assert len(skills["department_mappings"]["work-order-management"]["secondary_departments"]) >= 3
    assert len(skills["department_mappings"]["failure-recovery"]["other_allowed_loops"]) >= 1
