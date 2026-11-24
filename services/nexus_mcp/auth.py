"""MCP interface policy: all first-phase tools are read-only."""

from __future__ import annotations


def authorize_read(tool_name: str) -> None:
    if (not tool_name.startswith("nexus_get_")
            and tool_name not in {
                "nexus_systems_health", "nexus_systems_status", "nexus_systems_incidents",
                "nexus_systems_incident", "nexus_systems_version_status",
                "nexus_systems_environment_status", "nexus_systems_technology_status",
                "nexus_systems_service_status", "nexus_systems_release_status",
                "nexus_systems_receipt", "nexus_systems_workload_placement",
                "nexus_research_status", "nexus_research_result",
                "nexus_research_search_library", "nexus_list_research_rooms",
                "nexus_engine_list", "nexus_engine_health", "nexus_engine_status",
                "nexus_engine_capabilities", "nexus_engine_result", "nexus_engine_receipt",
            }
            and tool_name != "nexus_delegate_specialist"
            and tool_name not in {
                "gmail_search", "gmail_read_message", "gmail_read_thread",
                "calendar_search_events", "calendar_read_event", "calendar_get_availability",
                "drive_search", "drive_read_file", "nexus_read_workspace_file",
                "google_get_authority", "nexus_get_research_case_state",
                "systems_oracle_release_inspect", "systems_oracle_nova_snapshot_validate", "systems_oracle_nova_poller_status", "systems_oracle_nova_verify", "systems_oracle_receipt_read",
                "systems_status", "systems_job_status", "systems_job_result",
                "systems_upgrade_review", "systems_cleanup_scan", "systems_credential_status", "systems_kaggle_status",
                "systems_ai_usage_summary",
                "nexus_systems_approval_status", "nexus_systems_approval_validate",
                "opportunities_health", "opportunities_status", "opportunities_list",
                "opportunities_get", "opportunities_search", "opportunities_top",
                "opportunities_latest", "opportunities_scorecard", "opportunities_evidence",
                "opportunities_needs_research", "opportunities_history",
                "github_remote_health", "github_remote_status", "github_remote_repo_info",
                "github_remote_read_readme", "github_remote_read_file", "github_remote_list_files",
                "github_remote_releases", "github_remote_current_commit", "github_remote_list_sources",
                "github_remote_monitor_status", "github_remote_get_changes", "github_remote_snapshot_info",
                "github_remote_classify",
            }):
            raise PermissionError("only read-only Nexus MCP tools are exposed")


def authorize_action(tool_name: str) -> None:
    """Authorize the tiny set of bounded internal Nova control actions.

    The MCP bearer boundary authenticates the caller.  This second gate keeps
    the tool surface explicit: no generic writes, shell, publication, spend,
    or arbitrary record mutation are exposed here.
    """
    if tool_name not in {"nexus_assign_research", "nexus_continue_research", "nexus_continue_research_case", "nexus_record_research_synthesis", "nexus_record_research_recommendation", "nexus_research_controller_continue", "nexus_research_controller_advisor_request", "nexus_assign_codex", "nexus_resume_research", "nexus_assign_department_query", "nexus_create_department_directive", "nexus_create_research_room", "nexus_add_room_source", "nexus_ask_alpha_research_room", "nexus_score_research_room", "nexus_promote_research_room", "nexus_assign_notebooklm_runtime_canary", "nexus_assign_creative_asset", "nexus_assign_bounded_coding_task", "nexus_write_workspace_artifact", "nexus_update_workspace_artifact", "nexus_delete_workspace_artifact", "gmail_create_draft", "gmail_modify_message", "calendar_create_private_event", "calendar_update_event", "drive_create_nexus_file", "nexus_systems_restart_safe", "nexus_systems_rollback", "nexus_systems_technology_handoff", "nexus_research_start", "nexus_research_continue", "nexus_research_cancel", "nexus_research_completion_events", "nexus_engine_start", "nexus_engine_continue", "nexus_engine_cancel", "nexus_engine_restart_safe", "systems_oracle_release_stage", "systems_oracle_nova_snapshot", "systems_oracle_nova_activate", "systems_oracle_nova_rollback", "nexus_engine_rollback", "systems_job_create", "opportunities_submit", "opportunities_evaluate", "opportunities_score", "opportunities_update_state", "opportunities_attach_evidence", "opportunities_request_research", "opportunities_accept_research_handoff", "nexus_systems_approval_request", "nexus_systems_approval_decide", "github_remote_register_source", "github_remote_check_source", "github_remote_fetch_snapshot", "github_remote_cleanup_snapshot", "github_remote_route_change"}:
        raise PermissionError("only bounded internal Nexus actions are exposed")
