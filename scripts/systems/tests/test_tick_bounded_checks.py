"""Maintenance tick: a slow probe hits its own budget (TIMEOUT) without hanging
the tick, and the stdlib MCP streamable-HTTP client speaks the same protocol
(JSON and SSE replies, session header, bounded tool calls)."""
from __future__ import annotations

import importlib
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
tick = importlib.import_module("maintenance_tick")


def test_slow_probe_times_out_others_complete(monkeypatch):
    budgets = {k: 2 for k in tick.CHECK_BUDGETS}
    monkeypatch.setattr(tick, "CHECK_BUDGETS", budgets)
    monkeypatch.setattr(tick, "_sqlite_check", lambda p: {"status": "PASS"})
    fast = lambda *a, **k: {"status": "PASS"}
    for name in ("_s1_health", "_http_health", "_workflow_snapshot", "_launchd", "_pending_systems_work",
                 "_manifest_drift", "_node_probe", "_oracle_bridges", "_durable_dispatch", "_postiz_governed",
                 "_postiz_oauth_bounce"):
        monkeypatch.setattr(tick, name, fast)

    async def research_ok():
        return {"status": "PASS"}

    async def nexus_hangs():
        import asyncio
        await asyncio.sleep(30)   # far beyond its 2s budget

    monkeypatch.setattr(tick, "_research_mcp_snapshot", research_ok)
    monkeypatch.setattr(tick, "_mcp_snapshot", nexus_hangs)
    monkeypatch.setattr(tick, "MCP_SNAPSHOT_DEADLINE_SECONDS", 60)
    t0 = time.monotonic()
    checks, durations = tick._run_checks()
    assert time.monotonic() - t0 < 6, "tick must not wait for the hung probe"
    assert checks["nexus_mcp"]["status"] == "TIMEOUT" and checks["nexus_mcp"]["budget_seconds"] == 2
    assert checks["research_mcp"]["status"] == "PASS"
    assert all(checks[k]["status"] == "PASS" for k in checks if k != "nexus_mcp")


class _FakeMcp(BaseHTTPRequestHandler):
    log_message = lambda *a: None
    calls: list = []

    def do_POST(self):
        msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _FakeMcp.calls.append((msg.get("method"), self.headers.get("Authorization"), self.headers.get("Mcp-Session-Id")))
        if "id" not in msg:
            self.send_response(202); self.end_headers(); return
        m = msg["method"]
        if m == "tools/call" and msg["params"]["name"] == "slow_tool":
            time.sleep(3)
        if m == "tools/call" and msg["params"]["name"] == "broken":
            body = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32000, "message": "x"}}
        else:
            result = {"initialize": {"protocolVersion": "2025-03-26", "capabilities": {}},
                      "tools/list": {"tools": [{"name": "research_health"}, {"name": "research_status"}]},
                      "tools/call": {"content": [{"type": "text", "text": json.dumps({"data": {"status": "ok"}})}]}}[m]
            body = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
        sse = m == "tools/call"
        raw = (f"event: message\ndata: {json.dumps(body)}\n\n" if sse else json.dumps(body)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
        self.send_header("Mcp-Session-Id", "sess-1")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def do_DELETE(self):
        _FakeMcp.calls.append(("DELETE", None, self.headers.get("Mcp-Session-Id")))
        self.send_response(200); self.end_headers()


@pytest.fixture()
def server():
    _FakeMcp.calls = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _FakeMcp)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/mcp"
    srv.shutdown()


def test_stdlib_client_protocol(server):
    with tick._McpHttpSession(server, "TOKEN_never_print") as s:
        names = s.tool_names()
        payload = tick._tool_payload(s.call_tool("research_health", {}))
    assert names == {"research_health", "research_status"}
    assert payload == {"data": {"status": "ok"}}
    methods = [c[0] for c in _FakeMcp.calls]
    assert methods == ["initialize", "notifications/initialized", "tools/list", "tools/call", "DELETE"]
    assert all(c[1] == "Bearer TOKEN_never_print" for c in _FakeMcp.calls if c[0] != "DELETE")
    assert _FakeMcp.calls[0][2] is None and all(c[2] == "sess-1" for c in _FakeMcp.calls[1:])


def test_stdlib_client_bounded_and_errors(server):
    with tick._McpHttpSession(server, "t") as s:
        t0 = time.monotonic()
        with pytest.raises((TimeoutError, OSError)):
            s.call_tool("slow_tool", {}, timeout=1)
        assert time.monotonic() - t0 < 2.5
    with tick._McpHttpSession(server, "t") as s:
        with pytest.raises(RuntimeError):
            s.call_tool("broken", {})
