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
)


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

