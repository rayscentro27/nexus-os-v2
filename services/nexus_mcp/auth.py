"""MCP interface policy: all first-phase tools are read-only."""

from __future__ import annotations


def authorize_read(tool_name: str) -> None:
    if not tool_name.startswith("nexus_get_"):
        raise PermissionError("only read-only Nexus MCP tools are exposed")

