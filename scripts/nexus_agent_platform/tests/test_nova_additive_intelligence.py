from nexus_agent_platform.nova_capability_broker import capability_catalog
from nexus_agent_platform.nova_intelligence_model import (
    action_boundary,
    additive_capability_invariant,
    knowledge_resource_catalog,
    register_resource,
)


def test_reference_source_a_and_b_are_generic_and_comparable():
    catalog = knowledge_resource_catalog([
        {"resource_id": "REFERENCE_SOURCE_A", "resource_type": "reference", "content": "Source A says the process has three steps."},
        {"resource_id": "REFERENCE_SOURCE_B", "resource_type": "reference", "content": "Source B says the process has four steps and adds a review."},
    ])
    assert catalog["REFERENCE_SOURCE_A"]["content"].startswith("Source A")
    assert catalog["REFERENCE_SOURCE_B"]["content"].startswith("Source B")
    assert "REFERENCE_SOURCE_A" in catalog and "REFERENCE_SOURCE_B" in catalog


def test_adding_source_does_not_reduce_existing_resources():
    before = knowledge_resource_catalog()
    after = register_resource(before, {"resource_id": "REFERENCE_SOURCE_C", "resource_type": "reference"})
    assert additive_capability_invariant(before, after)
    assert set(before).issubset(set(after))


def test_catalog_exposes_resources_and_reasoning_without_selecting_one():
    catalog = capability_catalog()
    assert catalog["broker_role"] == "describe_only"
    assert "PUBLIC_WEB" in catalog["knowledge_resources"]
    assert "NEXUS_OS" in catalog["knowledge_resources"]
    assert "COMPARE" in catalog["reasoning_abilities"]
    assert "ECONOMIC_ANALYSIS" in catalog["reasoning_abilities"]


def test_google_capabilities_remain_granular_and_actions_are_governed():
    resources = knowledge_resource_catalog()
    assert resources["GOOGLE_WORKSPACE_READ"]["read_capability"] == "google_workspace_read"
    send = action_boundary("SEND_EMAIL")
    assert send["authority_required"] is True
    assert send["approval_required"] is True
    assert action_boundary("SUBMIT_NEXUS_WORK")["executor"] == "Nexus"


def test_reasoning_and_risk_do_not_require_action_authority():
    catalog = capability_catalog()
    assert "RISK_ANALYSIS" in catalog["reasoning_abilities"]
    assert "RECOMMEND" in catalog["reasoning_abilities"]
    # Thinking about an action is distinct from crossing its action boundary.
    assert action_boundary("SPEND_FUNDS")["approval_required"] is True
