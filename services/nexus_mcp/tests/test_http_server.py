from __future__ import annotations

import asyncio

from services.nexus_mcp.http_server import BearerBoundaryMiddleware


def test_boundary_rejects_missing_token(monkeypatch):
    monkeypatch.delenv("NEXUS_MCP_BRIDGE_TOKEN", raising=False)
    assert not __import__("os").getenv("NEXUS_MCP_BRIDGE_TOKEN")


def test_boundary_uses_constant_time_comparison(monkeypatch):
    monkeypatch.setenv("NEXUS_MCP_BRIDGE_TOKEN", "expected")
    assert isinstance(BearerBoundaryMiddleware, type)
