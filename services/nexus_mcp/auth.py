"""MCP interface policy: all first-phase tools are read-only."""

from __future__ import annotations


def authorize_read(tool_name: str) -> None:
    if not tool_name.startswith("nexus_get_") and tool_name != "nexus_delegate_specialist":
        raise PermissionError("only read-only Nexus MCP tools are exposed")
