"""Additive knowledge, reasoning, and action contracts for Nova.

Resources describe what Nova may consult; they do not select a source or own a
question. Reasoning abilities are intellectual operations, not permission gates.
Actions are the only contracts that carry consequence/authority metadata.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping


KNOWLEDGE_RESOURCES: Dict[str, Dict[str, Any]] = {
    "MODEL_GENERAL_KNOWLEDGE": {
        "resource_id": "MODEL_GENERAL_KNOWLEDGE", "resource_type": "model",
        "description": "General model knowledge and reasoning", "domains": ["general"],
        "read_capability": "general_reasoning", "current_availability": "local",
        "freshness": "model-dependent", "provenance_class": "model_knowledge",
        "cost_class": "included", "privacy_scope": "conversation",
        "retrieval_method": "model_context", "searchable": False, "comparable": True,
        "authority_required": False,
    },
    "PUBLIC_WEB": {
        "resource_id": "PUBLIC_WEB", "resource_type": "web_search",
        "description": "Approved public search and source discovery", "domains": ["public"],
        "read_capability": "public_web_search", "current_availability": "provider-dependent",
        "freshness": "live-on-retrieval", "provenance_class": "external_public",
        "cost_class": "free-first", "privacy_scope": "public-only",
        "retrieval_method": "approved_search_provider", "searchable": True, "comparable": True,
        "authority_required": False,
    },
    "PUBLIC_WEBSITE": {
        "resource_id": "PUBLIC_WEBSITE", "resource_type": "web_retrieval",
        "description": "Read-only retrieval of a public page", "domains": ["public", "website"],
        "read_capability": "public_web_retrieval", "current_availability": "provider-dependent",
        "freshness": "live-on-retrieval", "provenance_class": "external_public",
        "cost_class": "free-first", "privacy_scope": "public-only",
        "retrieval_method": "approved_http_or_browser_reader", "searchable": False, "comparable": True,
        "authority_required": False,
    },
    "COMPANY_DATABASE": {
        "resource_id": "COMPANY_DATABASE", "resource_type": "live_database",
        "description": "Authorized company and business data", "domains": ["company", "business"],
        "read_capability": "company_data", "current_availability": "source-dependent",
        "freshness": "query-time", "provenance_class": "live_database",
        "cost_class": "included", "privacy_scope": "approved-company-data",
        "retrieval_method": "authorized_read_adapter", "searchable": True, "comparable": True,
        "authority_required": True,
    },
    "NEXUS_OS": {
        "resource_id": "NEXUS_OS", "resource_type": "operational_platform",
        "description": "Nexus capability knowledge and authorized company operations", "domains": ["nexus", "company"],
        "read_capability": "nexus_read", "current_availability": "runtime-dependent",
        "freshness": "query-time", "provenance_class": "nexus-governed",
        "cost_class": "included", "privacy_scope": "approved-nexus-data",
        "retrieval_method": "shared_capability_boundary", "searchable": True, "comparable": True,
        "authority_required": True,
    },
    "NEXUS_LIVE_TRUTH": {
        "resource_id": "NEXUS_LIVE_TRUTH", "resource_type": "live_truth",
        "description": "Current Nexus operational evidence, receipts, and governed state", "domains": ["nexus_operations"],
        "read_capability": "nexus_live_truth", "current_availability": "runtime-dependent",
        "freshness": "query-time", "provenance_class": "live_receipt_or_runtime",
        "cost_class": "included", "privacy_scope": "approved-nexus-data",
        "retrieval_method": "truth_view", "searchable": False, "comparable": True,
        "authority_required": True,
    },
    "ALPHA_RESEARCH": {
        "resource_id": "ALPHA_RESEARCH", "resource_type": "specialist", 
        "description": "Deep research, verification, economics, and challenge", "domains": ["research", "economics"],
        "read_capability": "alpha_research", "current_availability": "bounded/partial",
        "freshness": "artifact-dependent", "provenance_class": "research_artifact",
        "cost_class": "free-first", "privacy_scope": "public-or-approved-internal",
        "retrieval_method": "governed_research_handoff", "searchable": True, "comparable": True,
        "authority_required": True,
    },
    "GOOGLE_WORKSPACE_READ": {
        "resource_id": "GOOGLE_WORKSPACE_READ", "resource_type": "integration",
        "description": "Granular Gmail, Calendar, and Drive read capabilities", "domains": ["company", "communication"],
        "read_capability": "google_workspace_read", "current_availability": "capability-specific",
        "freshness": "query-time", "provenance_class": "integration_status",
        "cost_class": "included", "privacy_scope": "approved-google-data",
        "retrieval_method": "governed_google_adapter", "searchable": False, "comparable": False,
        "authority_required": True,
    },
    "REPORT_ARCHIVE": {
        "resource_id": "REPORT_ARCHIVE", "resource_type": "artifact_archive",
        "description": "Historical and current reports, subject to provenance filtering", "domains": ["reference", "company", "research"],
        "read_capability": "report_artifact_read", "current_availability": "provenance-dependent",
        "freshness": "artifact-timestamp", "provenance_class": "artifact",
        "cost_class": "included", "privacy_scope": "approved-artifacts",
        "retrieval_method": "artifact_index", "searchable": True, "comparable": True,
        "authority_required": True,
    },
}

REASONING_ABILITIES = tuple(
    "UNDERSTAND EXPLAIN COMPARE CHALLENGE SYNTHESIZE ECONOMIC_ANALYSIS "
    "RISK_ANALYSIS RECOMMEND PLAN PRIORITIZE".split()
)

ACTION_BOUNDARIES: Dict[str, Dict[str, Any]] = {
    "SEND_EMAIL": {"side_effect": "external communication", "authority_required": True, "approval_required": True, "cost": "policy-dependent", "reversible": False, "executor": "approved_email_path"},
    "CREATE_CALENDAR_EVENT": {"side_effect": "external calendar mutation", "authority_required": True, "approval_required": True, "cost": "included", "reversible": True, "executor": "approved_calendar_path"},
    "SUBMIT_NEXUS_WORK": {"side_effect": "governed operational request", "authority_required": True, "approval_required": "Nexus-determined", "cost": "included", "reversible": False, "executor": "Nexus"},
    "SPEND_FUNDS": {"side_effect": "monetary spend", "authority_required": True, "approval_required": True, "cost": "actual spend", "reversible": False, "executor": "approved finance path"},
    "WRITE_CLIENT_DATA": {"side_effect": "production data mutation", "authority_required": True, "approval_required": True, "cost": "included", "reversible": "policy-dependent", "executor": "Nexus"},
}


def knowledge_resource_catalog(extra: Iterable[Mapping[str, Any]] = ()) -> Dict[str, Dict[str, Any]]:
    """Return a copy of resources, optionally extended without replacing defaults."""
    result = deepcopy(KNOWLEDGE_RESOURCES)
    for resource in extra:
        item = dict(resource)
        resource_id = str(item.get("resource_id", "")).strip()
        if not resource_id:
            raise ValueError("resource_id is required")
        result[resource_id] = item
    return result


def register_resource(catalog: Mapping[str, Mapping[str, Any]], resource: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Add a resource descriptor without changing existing resources."""
    result = deepcopy(dict(catalog))
    item = dict(resource)
    resource_id = str(item.get("resource_id", "")).strip()
    if not resource_id:
        raise ValueError("resource_id is required")
    result[resource_id] = item
    return result


def action_boundary(action: str) -> Dict[str, Any]:
    """Return consequence metadata; this does not authorize or execute an action."""
    key = str(action).upper().strip()
    if key not in ACTION_BOUNDARIES:
        raise KeyError(key)
    result = deepcopy(ACTION_BOUNDARIES[key])
    result["action"] = key
    return result


def additive_capability_invariant(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """Resources/abilities added later cannot remove baseline entries."""
    return set(before).issubset(set(after))
