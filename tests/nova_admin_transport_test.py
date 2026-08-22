import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import nova.nova_admin_server as server  # noqa: E402
from nexus_agent_platform.adapters.state_adapter import AgentState  # noqa: E402


class FakeGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        state.assistant_response = "A strategic response."
        state.metadata = {**state.metadata, "model_provider": "openrouter", "model_used": "configured-test-model"}
        return state


def test_browser_adapter_reuses_canonical_graph_and_declares_no_authority(monkeypatch):
    graph = FakeGraph()
    monkeypatch.setattr(server, "get_nova_graph", lambda: graph)
    payload = server.invoke_nova("Challenge this plan.")
    assert len(graph.calls) == 1
    assert graph.calls[0].agent_id == "hermes_nova"
    metadata = graph.calls[0].metadata if hasattr(graph.calls[0], "metadata") else graph.calls[0]["metadata"]
    assert metadata["channel"] == "admin_browser"
    assert payload["provider"] == "openrouter"
    assert payload["model"] == "configured-test-model"
    assert payload["execution_authority"] == "NONE"
    assert payload["memory_scope"] == "nova_admin_channel"


def test_browser_adapter_rejects_client_sensitive_input(monkeypatch):
    monkeypatch.setattr(server, "get_nova_graph", lambda: (_ for _ in ()).throw(AssertionError("graph must not run")))
    try:
        server.invoke_nova("Review the credit report for person@example.com")
    except ValueError as exc:
        assert str(exc) == "client-sensitive-input-not-available-in-nova-browser"
    else:
        raise AssertionError("sensitive input was accepted")


def test_local_handler_requires_exact_origin_and_is_bounded():
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.NovaAdminHandler)
    httpd.limiter = server.NovaAdminLimiter()
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(f"http://127.0.0.1:{httpd.server_port}/v1/nova/chat", method="OPTIONS", headers={"Origin": "https://not-goclear.example"})
        try:
            urlopen(request)
        except HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("unapproved origin was accepted")
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
