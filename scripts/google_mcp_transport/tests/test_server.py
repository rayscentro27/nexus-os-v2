from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from scripts.google_mcp_transport import server


def test_imports_exact_pinned_google_server_and_exposes_its_tool_set():
    assert Path(server.google_server.__file__).resolve() == server.GOOGLE_SOURCE_MODULE.resolve()
    names = {row.name for row in server.mcp._tool_manager.list_tools()}
    gs = server.google_server
    assert len(names) == 27  # 14 (r1.1.1) + 13 read-only r1.2 tools
    assert names - set(gs.CORE_READ_TOOL_NAMES) == {
        "google_get_authority",
        "gmail_search", "gmail_read_message", "gmail_read_thread",
        "calendar_search_events", "calendar_read_event", "calendar_get_availability",
        "drive_search", "drive_read_file",
        "gmail_create_draft", "gmail_modify_message",
        "calendar_create_private_event", "calendar_update_event", "drive_create_nexus_file",
    }


def test_http_boundary_rejects_missing_and_wrong_transport_tokens(monkeypatch):
    monkeypatch.setenv(server.TRANSPORT_TOKEN_ENV, "test-google-transport-secret")
    with TestClient(server.app) as client:
        assert client.get("/mcp").status_code == 401
        assert client.get("/mcp", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/mcp", headers={"Authorization": "Bearer test-google-transport-secret"}).status_code != 401


def test_transport_endpoint_is_fixed_loopback_and_not_nexus_port():
    assert server.TRANSPORT_HOST == "127.0.0.1"
    assert server.TRANSPORT_PORT == 18767
    assert server.TRANSPORT_PORT != 18765


def test_keychain_credential_reference_is_separate_from_google_oauth(monkeypatch):
    monkeypatch.delenv(server.TRANSPORT_TOKEN_ENV, raising=False)
    monkeypatch.setattr(server.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "opaque-test-token\n", "returncode": 0})())
    assert server._transport_token() == "opaque-test-token"
    assert server.KEYCHAIN_SERVICE == "nexus/credential.nexus.google.mcp.transport.v1"
    assert server.KEYCHAIN_SERVICE != server.google_server.CREDENTIAL_ID
