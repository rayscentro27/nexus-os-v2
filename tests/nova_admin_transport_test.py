import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import nova.nova_admin_server as server  # noqa: E402


class FakeHermesResult:
    status = "SUCCEEDED"
    response = "A strategic response."
    provider = "openrouter"
    model = "configured-test-model"
    runtime_host = "ORACLE"
    profile = "nova_nexus"
    toolset = "nexus_mcp_remote"
    latency_ms = 12.0
    hermes_session_id = "20260918_000000_ab12cd"
    error = None


def test_browser_adapter_uses_canonical_hermes_and_declares_no_authority(monkeypatch):
    calls = []
    def fake_hermes(message, session_id, **kwargs):
        calls.append((message, session_id, kwargs))
        return FakeHermesResult()
    monkeypatch.setattr(server, "run_oracle_hermes", fake_hermes)
    payload = server.invoke_nova("Challenge this plan.")
    assert len(calls) == 1
    assert calls[0][1] == "admin-browser"
    assert payload["provider"] == "openrouter"
    assert payload["model"] == "configured-test-model"
    assert payload["execution_authority"] == "NONE"
    assert payload["memory_scope"] == "nova_admin_channel"
    assert payload["hermes_session_id"] == "20260918_000000_ab12cd"


def test_browser_adapter_rejects_client_sensitive_input(monkeypatch):
    monkeypatch.setattr(server, "run_oracle_hermes", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Hermes must not run")))
    try:
        server.invoke_nova("Review the credit report for person@example.com")
    except ValueError as exc:
        assert str(exc) == "client-sensitive-input-not-available-in-nova-browser"
    else:
        raise AssertionError("sensitive input was accepted")


def test_browser_adapter_rejects_legacy_direct_runtime(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_NOVA_RUNTIME", "direct")
    try:
        server.invoke_nova("Hello Nova", "admin-thread-123")
    except RuntimeError as exc:
        assert str(exc) == "legacy_direct_nova_disabled"
    else:
        raise AssertionError("legacy direct runtime was accepted")


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
