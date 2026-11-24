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
    "nexus_get_project",
    "nexus_get_projects",
    "nexus_get_project_approvals",
    "nexus_create_department_directive",
    "nexus_get_department_directive",
    "nexus_get_directive_events",
    "nexus_list_research_rooms",
    "nexus_get_research_room",
    "nexus_create_research_room",
    "nexus_add_room_source",
    "nexus_ask_alpha_research_room",
    "nexus_score_research_room",
    "nexus_promote_research_room",
)

# Operational Systems tools are registered separately from Nova's conversational
# read list. They are selected only for an explicit Systems operation.
SYSTEMS_HOST_CONTROL_TOOL_NAMES = (
    "systems_oracle_release_inspect",
    "systems_oracle_release_stage",
    "systems_oracle_nova_snapshot",
    "systems_oracle_nova_snapshot_validate",
    "systems_oracle_nova_poller_status",
    "systems_oracle_nova_activate",
    "systems_oracle_nova_verify",
    "systems_oracle_nova_rollback",
    "systems_oracle_receipt_read",
)

SYSTEMS_OPERATOR_TOOL_NAMES = (
    "systems_status", "systems_job_create", "systems_job_status", "systems_job_result",
    "systems_upgrade_review", "systems_cleanup_scan", "systems_credential_status",
    "systems_kaggle_status",
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
