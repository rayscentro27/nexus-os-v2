"""Hermes-facing exclusion for legacy Research surfaces on Nexus MCP.

The implementations remain registered in ``server.py`` for rollback/reference,
but Research R10 is exposed to agents only through the native ``research`` MCP.
"""

HERMES_DUPLICATE_RESEARCH_TOOLS = frozenset({
    # Legacy Research Room, case, and controller surfaces.
    "nexus_get_research_state",
    "nexus_get_research_queue",
    "nexus_get_research_execution_trace",
    "nexus_assign_research",
    "nexus_continue_research",
    "nexus_get_research_case",
    "nexus_record_research_synthesis",
    "nexus_record_research_recommendation",
    "nexus_continue_research_case",
    "nexus_get_research_controller_status",
    "nexus_get_research_controller_open_questions",
    "nexus_get_research_controller_results",
    "nexus_research_controller_continue",
    "nexus_research_controller_advisor_request",
    "nexus_resume_research",
    # Direct Research R10 wrappers, superseded by provider=research.
    "nexus_research_start",
    "nexus_research_status",
    "nexus_research_result",
    "nexus_research_continue",
    "nexus_research_cancel",
    "nexus_research_search_library",
    "nexus_research_completion_events",
})


def hide_duplicate_research_tools(mcp) -> int:
    """Remove only the fixed legacy Research names from MCP tool discovery.

    This changes the Hermes-visible MCP surface only. The tool implementations,
    authorization functions, and internal engine handoffs remain intact.
    """
    manager = mcp._tool_manager
    before = {tool.name for tool in manager.list_tools()}
    missing = HERMES_DUPLICATE_RESEARCH_TOOLS - before
    if missing:
        raise RuntimeError("EXPECTED_RESEARCH_TOOL_REGISTRATION_MISSING")
    for name in sorted(HERMES_DUPLICATE_RESEARCH_TOOLS):
        manager.remove_tool(name)
    after = {tool.name for tool in manager.list_tools()}
    if before - after != HERMES_DUPLICATE_RESEARCH_TOOLS:
        raise RuntimeError("UNEXPECTED_MCP_TOOL_EXPOSURE_CHANGE")
    return len(before) - len(after)
