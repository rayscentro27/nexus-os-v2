"""MCP interface policy: all first-phase tools are read-only."""

from __future__ import annotations


def authorize_read(tool_name: str) -> None:
    if (not tool_name.startswith("nexus_get_")
            and tool_name != "nexus_delegate_specialist"
            and tool_name not in {
                "gmail_search", "gmail_read_message", "gmail_read_thread",
                "calendar_search_events", "calendar_read_event", "calendar_get_availability",
                "drive_search", "drive_read_file",
            }):
            raise PermissionError("only read-only Nexus MCP tools are exposed")


def authorize_action(tool_name: str) -> None:
    """Authorize the tiny set of bounded internal Nova control actions.

    The MCP bearer boundary authenticates the caller.  This second gate keeps
    the tool surface explicit: no generic writes, shell, publication, spend,
    or arbitrary record mutation are exposed here.
    """
    if tool_name not in {"nexus_assign_research", "nexus_assign_codex", "nexus_resume_research"}:
        raise PermissionError("only bounded internal Nexus actions are exposed")
