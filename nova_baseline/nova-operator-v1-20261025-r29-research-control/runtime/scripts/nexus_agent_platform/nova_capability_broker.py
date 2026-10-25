"""Compact capability catalog and model-led information plan for Nova."""
from __future__ import annotations

from typing import Any, Dict, List

from nexus_agent_platform.nova_intelligence_model import (
    ACTION_BOUNDARIES,
    REASONING_ABILITIES,
    knowledge_resource_catalog,
)

CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "GENERAL_REASONING": {"health": "local", "cost_class": "included", "read_or_write": "read", "privacy_scope": "conversation", "authority_scope": "none", "fallbacks": []},
    "PUBLIC_WEB_SEARCH": {"health": "provider-dependent", "cost_class": "free-first", "read_or_write": "read", "privacy_scope": "public-only", "authority_scope": "none", "fallbacks": ["Alpha", "general reasoning"]},
    "PUBLIC_WEB_RETRIEVAL": {"health": "Alpha/provider-dependent", "cost_class": "free-first", "read_or_write": "read", "privacy_scope": "public-only", "authority_scope": "none", "fallbacks": ["search snippets with limits"]},
    "ALPHA_RESEARCH": {"health": "bounded/partial", "cost_class": "free-first", "read_or_write": "delegated", "privacy_scope": "public-or-approved-internal", "authority_scope": "governed intake", "fallbacks": ["public web"]},
    "COMPANY_DATA": {"health": "source-dependent", "cost_class": "included", "read_or_write": "read", "privacy_scope": "approved company data", "authority_scope": "read allowlist", "fallbacks": ["verified artifact"]},
    "NEXUS_LIVE_TRUTH": {"health": "runtime-dependent", "cost_class": "included", "read_or_write": "read", "privacy_scope": "Nexus state", "authority_scope": "TruthKernel", "fallbacks": ["explicit UNKNOWN"]},
    "NEXUS_CAPABILITY_MAP": {"health": "live-read", "cost_class": "included", "read_or_write": "read", "privacy_scope": "Nexus capability metadata", "authority_scope": "approved read allowlist", "fallbacks": ["explicit UNKNOWN"]},
    "NEXUS_OPERATION_REQUEST": {"health": "governed intake", "cost_class": "included", "read_or_write": "submit-only", "privacy_scope": "approved request", "authority_scope": "Nexus validates", "fallbacks": ["explain blocked"]},
    "CAPABILITY_STATUS": {"health": "live-read", "cost_class": "included", "read_or_write": "read", "privacy_scope": "capability metadata", "authority_scope": "read allowlist", "fallbacks": []},
    "REPORT_ARTIFACT_READ": {"health": "provenance-dependent", "cost_class": "included", "read_or_write": "read", "privacy_scope": "approved artifacts", "authority_scope": "truth validation", "fallbacks": ["historical-only"]},
}


def capability_catalog() -> Dict[str, Any]:
    return {
        "capabilities": CAPABILITIES,
        "knowledge_resources": knowledge_resource_catalog(),
        "reasoning_abilities": list(REASONING_ABILITIES),
        "action_boundaries": ACTION_BOUNDARIES,
        "broker_role": "describe_only",
        "execution_authority": "shared_capability_boundary",
    }


MODEL_CAPABILITY_MARKER = "nova_capability_request"


def validate_model_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a model-selected request without choosing a resource for it."""
    name = str(request.get("capability", "")).upper()
    aliases = {"PUBLIC_WEB_SEARCH": "public_web_search", "PUBLIC_WEB_RETRIEVAL": "public_web_retrieval", "ALPHA_RESEARCH": "submit_alpha_request", "CAPABILITY_STATUS": "get_live_capability_status", "NEXUS_READ": "get_capability_registry", "NEXUS_CAPABILITY_MAP": "get_capability_registry"}
    if name not in aliases:
        return {"status": "rejected", "error": "capability-not-allowlisted", "capability": name}
    arguments = request.get("arguments") if isinstance(request.get("arguments"), dict) else {}
    # Contextual handoffs may omit a repeated objective. A prior referent is
    # sufficient to form a bounded research request; no source or question
    # owner is inferred here.
    if name == "ALPHA_RESEARCH" and not str(arguments.get("objective", "")).strip():
        referent = str(arguments.get("referent", "")).strip()
        if referent:
            arguments = {**arguments, "objective": referent}
    return {"status": "validated", "capability": aliases[name], "requested_capability": name, "arguments": arguments, "cost_class": CAPABILITIES.get(name, {}).get("cost_class", "unknown"), "read_only": name != "ALPHA_RESEARCH"}


def build_information_plan(question: str, domains: List[str]) -> Dict[str, Any]:
    public = {"PUBLIC_BUSINESS_RESEARCH", "PUBLIC_COMPANY_RESEARCH", "PUBLIC_CURRENT_INFORMATION", "WEBSITE_ANALYSIS"}
    internal = {"NEXUS_OPERATIONS", "CLIENT_DATA", "INTERNAL_COMPANY_BUSINESS", "INTERNAL_RESEARCH_ALPHA"}
    resources: List[str] = ["GENERAL_REASONING"]
    if public & set(domains):
        resources += ["PUBLIC_WEB_SEARCH", "PUBLIC_WEB_RETRIEVAL"]
    if "INTERNAL_RESEARCH_ALPHA" in domains:
        resources.append("ALPHA_RESEARCH")
    if internal & set(domains):
        resources += ["COMPANY_DATA", "NEXUS_LIVE_TRUTH"]
    return {"question": question[:500], "domains": domains, "initial_view_before_retrieval": True, "information_needed": resources, "tool_selection": "MODEL_LED_AFTER_UNDERSTANDING", "broker": "DESCRIPTIVE_ONLY"}
