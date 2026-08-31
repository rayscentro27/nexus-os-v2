"""Canonical mapping for the first Nexus MCP read surface."""

from __future__ import annotations

from typing import Any

from nexus_agent_platform.capabilities.shared import execute_shared_capability


CAPABILITY_MAP = {
    # Use live governed readers, not historical dashboard aliases.
    "nexus_get_reviews": "get_pending_approvals",
    "nexus_get_work_items": "get_work_queue",
    "nexus_get_blockers": "BLOCKERS",
    "nexus_get_opportunities": "BUSINESS_OPPORTUNITIES",
    "nexus_get_business_state": "get_operational_summary",
    "nexus_get_system_health": "SYSTEM_HEALTH",
}


def read_canonical(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read only through the shared Nexus permission/canonical boundary."""
    capability = CAPABILITY_MAP[tool_name]
    return execute_shared_capability(
        "hermes_nova",
        capability,
        arguments or {},
        conversation_id="hermes-mcp",
        trace_id=f"mcp:{tool_name}",
    )
