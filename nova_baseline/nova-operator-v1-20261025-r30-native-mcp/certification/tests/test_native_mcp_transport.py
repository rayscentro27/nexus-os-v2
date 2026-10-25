from __future__ import annotations

import ast
import asyncio
import inspect
import os
import sys
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


COMPONENT = Path(__file__).resolve().parents[2]
RUNTIME = COMPONENT / "runtime"
sys.path.insert(0, str(RUNTIME / "scripts"))

from nova import nexus_mcp_status as status  # noqa: E402
from nova.research_intent import route_research_only_request  # noqa: E402
from nova.semantic_orchestration import resolve_owner_request  # noqa: E402


class _AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *args):
        return False


class _FakeHTTPX:
    def __init__(self):
        self.client = None

    def AsyncClient(self, *, headers, timeout):
        self.client = SimpleNamespace(headers=headers, timeout=timeout)
        return _AsyncContext(self.client)


class _FakeSession:
    def __init__(self, read, write):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def initialize(self):
        self.calls.append(("initialize",))

    async def list_tools(self):
        self.calls.append(("tools/list",))
        return SimpleNamespace(tools=[SimpleNamespace(name="nexus_assign_research", description="assign", inputSchema={}),
                                      SimpleNamespace(name="nexus_get_durable_jobs", description="status", input_schema={}),
                                      SimpleNamespace(name="nexus_get_system_health", description="health", inputSchema={})])

    async def call_tool(self, name, arguments):
        self.calls.append(("tools/call", name, arguments))
        return SimpleNamespace(isError=False, structuredContent={"status": "ok"}, content=[])


def _fake_streamable(_endpoint, *, http_client):
    return _AsyncContext((object(), object()))


class NativeMCPTransportTests(unittest.TestCase):
    def test_01_default_endpoint_is_native_mcp_path(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(status._native_endpoint(), "http://127.0.0.1:18765/mcp")

    def test_02_base_endpoint_adds_mcp_path(self):
        with patch.dict(os.environ, {"NEXUS_MCP_URL": "http://127.0.0.1:18765/"}, clear=True):
            self.assertEqual(status._native_endpoint(), "http://127.0.0.1:18765/mcp")

    def test_03_configured_mcp_path_is_preserved(self):
        with patch.dict(os.environ, {"NEXUS_MCP_URL": "https://nexus.example/mcp"}, clear=True):
            self.assertEqual(status._native_endpoint(), "https://nexus.example/mcp")

    def test_04_invalid_endpoint_fails_closed(self):
        with patch.dict(os.environ, {"NEXUS_MCP_URL": "file:///tmp/mcp"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "MCP_ENDPOINT_INVALID"):
                status._native_endpoint()

    def test_05_keychain_credential_is_read_without_logging(self):
        fake = SimpleNamespace(returncode=0, stdout="secret-test-value\n", stderr="")
        with patch.object(status.subprocess, "run", return_value=fake) as run:
            self.assertEqual(status._load_bridge_token(), "secret-test-value")
        self.assertEqual(run.call_args.args[0][:3], ["/usr/bin/security", "find-generic-password", "-s"])
        self.assertNotIn("secret-test-value", repr(run.call_args))

    def test_06_missing_keychain_credential_fails_closed(self):
        with patch.object(status.subprocess, "run", return_value=SimpleNamespace(returncode=44, stdout="", stderr="")):
            with self.assertRaisesRegex(RuntimeError, "MCP_AUTH_FAILED"):
                status._load_bridge_token()

    def test_07_native_session_initializes_and_lists_tools(self):
        fake_httpx = _FakeHTTPX()
        async def invoke():
            return await status._perform_native_request(
                {"operation": "list_tools"}, "http://127.0.0.1:18765/mcp", "test-token",
                httpx_module=fake_httpx, streamable_factory=_fake_streamable,
                session_class=_FakeSession)

        response = asyncio.run(invoke())
        self.assertEqual(response["tool_count"], 3)
        self.assertIn("nexus_assign_research", {tool["name"] for tool in response["tools"]})
        self.assertEqual(fake_httpx.client.headers["Authorization"], "Bearer test-token")

    def test_08_authenticated_native_protocol_headers_and_call(self):
        fake_httpx = _FakeHTTPX()
        fake_session = _FakeSession
        captured = {}

        def session_factory(read, write):
            captured["session"] = fake_session(read, write)
            return captured["session"]

        async def invoke():
            return await status._perform_native_request(
                {"tool": "nexus_get_system_health", "arguments": {}},
                "http://127.0.0.1:18765/mcp", "test-token", httpx_module=fake_httpx,
                streamable_factory=_fake_streamable, session_class=session_factory)

        response = asyncio.run(invoke())
        self.assertEqual(fake_httpx.client.headers["Authorization"], "Bearer test-token")
        self.assertEqual(fake_httpx.client.timeout, 60)
        self.assertEqual(response["tool_count"], 3)
        self.assertEqual(response["result"], {"status": "ok"})
        self.assertEqual(captured["session"].calls[0], ("initialize",))
        self.assertEqual(captured["session"].calls[1], ("tools/list",))

    def test_09_missing_token_does_not_fallback(self):
        with patch.object(status, "_load_bridge_token", side_effect=RuntimeError("MCP_AUTH_FAILED")):
            with self.assertRaisesRegex(RuntimeError, "MCP_AUTH_FAILED"):
                status._native_mcp_request({"operation": "list_tools"})

    def test_10_invalid_token_is_bounded_auth_error(self):
        with patch.object(status, "_load_bridge_token", return_value="invalid"):
            with patch.object(status, "_perform_native_request", new=AsyncMock(side_effect=RuntimeError("HTTP 401 Unauthorized"))):
                with self.assertRaisesRegex(RuntimeError, "MCP_AUTH_FAILED"):
                    status._native_mcp_request({"operation": "list_tools"})

    def test_11_unavailable_endpoint_is_bounded_transport_error(self):
        with patch.object(status, "_load_bridge_token", return_value="test-token"):
            with patch.object(status, "_perform_native_request", new=AsyncMock(side_effect=RuntimeError("connection refused"))):
                with self.assertRaisesRegex(RuntimeError, "MCP_TRANSPORT_UNREACHABLE"):
                    status._native_mcp_request({"operation": "list_tools"})

    def test_12_assignment_and_exact_status_use_native_request(self):
        assignment = {"status": "queued", "durable_job_id": "job_x"}
        with patch.object(status, "_native_mcp_request", return_value={"result": {"data": assignment}, "tool_count": 49}) as call:
            status.assign_research_only(objective="A sufficiently long objective", question="A specific question",
                                        correlation_id="nova-research-only-test")
        request = call.call_args.args[0]
        self.assertEqual(request["tool"], "nexus_assign_research")
        self.assertEqual(request["arguments"]["requested_intent"], "RESEARCH_ONLY")
        self.assertEqual(request["arguments"]["parent_request_id"], "nova-research-only-test")
        with patch.object(status, "_native_mcp_request", return_value={"result": {"data": {"jobs": [{"job_id": "job_x"}]}}, "tool_count": 49}) as call:
            status.call_exact_job_status("job_x")
        self.assertEqual(call.call_args.args[0], {"tool": "nexus_get_durable_jobs", "arguments": {"job_id": "job_x", "limit": 1}})

    def test_13_no_docker_or_direct_database_fallback(self):
        source = inspect.getsource(status)
        self.assertNotIn("podman", source.casefold())
        self.assertNotIn("docker exec", source.casefold())
        self.assertNotIn("nexus-hermes-0206", source)
        self.assertNotIn("supabase.create_client", source.casefold())
        self.assertNotIn("postgrest", source.casefold())

    def test_14_conversational_research_control_is_unchanged(self):
        message = "Research this for me: check the official docs for a behavior."
        self.assertEqual(resolve_owner_request(message)["intent"], "RESEARCH_ONLY_REQUEST")
        self.assertEqual(route_research_only_request(message)["research_intent"], "RESEARCH_ONLY")


if __name__ == "__main__":
    unittest.main()
