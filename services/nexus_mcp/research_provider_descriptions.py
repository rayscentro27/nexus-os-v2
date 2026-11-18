"""Clarify ownership for generic Nexus diagnostic tools in Hermes discovery."""

NEXUS_CROSS_ENGINE_TOOL_DESCRIPTIONS = {
    "nexus_get_durable_jobs": (
        "Inspect durable jobs across Nexus for cross-engine operational diagnostics, "
        "queue investigation, or exact job lookup. For ordinary Research-engine "
        "status, use the dedicated Research provider."
    ),
    "nexus_get_prior_department_result": (
        "Retrieve prior department results for cross-department or Nexus-wide "
        "investigation. For ordinary Research results, use the dedicated Research provider."
    ),
    "nexus_engine_status": (
        "Inspect a named engine as part of Nexus-wide systems or engine diagnostics. "
        "Use a dedicated engine provider for ordinary domain interaction when available."
    ),
    "nexus_engine_result": (
        "Retrieve an exact engine result for Nexus-wide operational diagnostics. "
        "Use the dedicated engine provider for ordinary domain-specific result requests "
        "when available."
    ),
}


def clarify_cross_engine_tool_descriptions(mcp) -> int:
    """Update descriptions only; preserve registered names and callables."""
    manager = mcp._tool_manager
    registered = {tool.name for tool in manager.list_tools()}
    missing = set(NEXUS_CROSS_ENGINE_TOOL_DESCRIPTIONS) - registered
    if missing:
        raise RuntimeError("EXPECTED_CROSS_ENGINE_TOOL_REGISTRATION_MISSING")

    for name, description in NEXUS_CROSS_ENGINE_TOOL_DESCRIPTIONS.items():
        manager.get_tool(name).description = description

    if any(
        manager.get_tool(name).description != description
        for name, description in NEXUS_CROSS_ENGINE_TOOL_DESCRIPTIONS.items()
    ):
        raise RuntimeError("CROSS_ENGINE_TOOL_DESCRIPTION_UPDATE_FAILED")
    return len(NEXUS_CROSS_ENGINE_TOOL_DESCRIPTIONS)
