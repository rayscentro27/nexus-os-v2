"""Small, dependency-free schemas used by the Nexus MCP server."""

from __future__ import annotations

from typing import Any


TOOL_NAMES = (
    "nexus_get_reviews",
    "nexus_get_work_items",
    "nexus_get_blockers",
    "nexus_get_opportunities",
    "nexus_get_business_state",
    "nexus_get_system_health",
    "nexus_get_research_state",
    "nexus_get_research_queue",
    "nexus_continue_research_case",
    "nexus_get_research_controller_status",
    "nexus_get_research_controller_open_questions",
    "nexus_get_research_controller_results",
    "nexus_research_controller_continue",
    "nexus_research_controller_advisor_request",
    "nexus_get_alpha_review",
    "nexus_get_prior_department_result",
    "nexus_get_durable_jobs",
    "nexus_get_research_execution_trace",
    "nexus_delegate_specialist",
    "nexus_assign_research",
    "nexus_assign_codex",
    "nexus_resume_research",
    "nexus_assign_department_query",
    "nexus_assign_notebooklm_runtime_canary",
    "nexus_get_codex_assignment",
)

# Operational reads are volatile by capability.  This metadata describes the
# freshness contract; it is not a cache policy and never makes persisted data
# current on its own.
CAPABILITY_FRESHNESS = {name: "VOLATILE" for name in TOOL_NAMES}


def unavailable(capability: str, error: str) -> dict[str, Any]:
    return {
        "status": "NOT_AVAILABLE",
        "as_of": None,
        "source": "nexus_canonical_read_layer",
        "capability": capability,
        "items": [],
        "metadata": {"read_only": True, "canonical": True},
        "error": error,
    }
