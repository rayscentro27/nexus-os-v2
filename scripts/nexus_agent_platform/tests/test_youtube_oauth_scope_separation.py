"""Unit and contract tests for YouTube OAuth Scope Separation Remediation."""
import pytest
from nexus_agent_platform.google_workspace import (
    SCOPES as WS_SCOPES,
    validate_scopes as validate_ws_scopes,
    CREDENTIAL_ID as WS_CREDENTIAL_ID,
    reauthorize_existing as ws_reauthorize,
)
from nexus_agent_platform.youtube_upload import (
    YOUTUBE_SCOPES,
    YOUTUBE_SCOPE_NAMES,
    YOUTUBE_UPLOAD_SCOPE,
    WORKSPACE_CREDENTIAL_ID,
    YOUTUBE_CREDENTIAL_ID,
    _validate_youtube_scopes,
    _get_oauth_client,
    generate_youtube_auth_url,
)
from nexus_agent_platform.credential_control_plane import (
    resolve_credential,
    CredentialStatus,
)


def test_1_workspace_oauth_remains_unchanged():
    """1. Workspace OAuth remains unchanged with strictly Gmail/Calendar/Drive scopes."""
    assert validate_ws_scopes(WS_SCOPES)
    assert YOUTUBE_UPLOAD_SCOPE not in WS_SCOPES
    assert "https://www.googleapis.com/auth/drive.file" in WS_SCOPES


def test_2_3_4_youtube_oauth_request_contains_no_workspace_scopes():
    """2-4. YouTube OAuth request contains NO Drive, Gmail, or Calendar scopes."""
    for scope in YOUTUBE_SCOPES:
        s_lower = scope.lower()
        assert "drive" not in s_lower, f"Forbidden Drive scope found: {scope}"
        assert "gmail" not in s_lower, f"Forbidden Gmail scope found: {scope}"
        assert "calendar" not in s_lower, f"Forbidden Calendar scope found: {scope}"
        assert "mail.google.com" not in s_lower

    # Verify scope guard rejects Workspace scopes
    with pytest.raises(ValueError, match="SCOPE_SEPARATION_VIOLATION"):
        _validate_youtube_scopes(YOUTUBE_SCOPES + ["https://www.googleapis.com/auth/drive.file"])
    with pytest.raises(ValueError, match="SCOPE_SEPARATION_VIOLATION"):
        _validate_youtube_scopes(YOUTUBE_SCOPES + ["https://www.googleapis.com/auth/gmail.readonly"])
    with pytest.raises(ValueError, match="SCOPE_SEPARATION_VIOLATION"):
        _validate_youtube_scopes(YOUTUBE_SCOPES + ["https://www.googleapis.com/auth/calendar.events"])


def test_5_existing_oauth_client_reused(monkeypatch):
    """5. Existing OAuth client reused without creating a new client."""
    monkeypatch.setenv("NEXUS_GOOGLE_WORKSPACE_CLIENT_ID", "mock-client-id")
    monkeypatch.setenv("NEXUS_GOOGLE_WORKSPACE_CLIENT_SECRET", "mock-client-secret")
    client = _get_oauth_client()
    assert client["client_id"] == "mock-client-id"
    assert client["client_secret"] == "mock-client-secret"


def test_6_youtube_auth_url_generated_cleanly(monkeypatch):
    """6. YouTube auth URL contains YouTube scopes only, access_type=offline, and prompt=consent."""
    monkeypatch.setenv("NEXUS_GOOGLE_WORKSPACE_CLIENT_ID", "mock-client-id")
    monkeypatch.setenv("NEXUS_GOOGLE_WORKSPACE_CLIENT_SECRET", "mock-client-secret")
    res = generate_youtube_auth_url()
    assert res["status"] == "AUTHORIZATION_URL_CREATED"
    url = res["authorization_url"]
    assert "youtube.upload" in url
    assert "youtube.readonly" in url
    assert "drive" not in url
    assert "gmail" not in url
    assert "calendar" not in url
    assert "include_granted_scopes" not in url  # Must NOT be included
    assert "access_type=offline" in url
    assert "prompt=consent" in url


def test_7_8_credential_resolution_isolation():
    """7-8. Capability youtube.upload resolves youtube credential; drive/gmail/calendar resolve workspace."""
    res_yt = resolve_credential(capability="youtube.upload")
    assert res_yt.credential_id == "credential.google.youtube.upload.prod.v1"
    assert res_yt.credential_id != "credential.google.workspace.prod.v1"

    res_drive = resolve_credential(capability="drive.file")
    assert res_drive.credential_id == "credential.google.workspace.prod.v1"
    assert res_drive.credential_id != "credential.google.youtube.upload.prod.v1"

    res_gmail = resolve_credential(capability="gmail.read")
    assert res_gmail.credential_id == "credential.google.workspace.prod.v1"

    res_cal = resolve_credential(capability="calendar.read")
    assert res_cal.credential_id == "credential.google.workspace.prod.v1"


def test_9_deprecated_combined_flow_fails_safely():
    """9. Deprecated --with-youtube on workspace module fails safely with actionable guidance."""
    with pytest.raises(RuntimeError, match="GOOGLE_SCOPE_CONFLICT"):
        ws_reauthorize(with_youtube=True)


def test_10_no_secrets_in_payloads(monkeypatch):
    """10. Zero raw credentials leaked in generated flow dictionaries."""
    monkeypatch.setenv("NEXUS_GOOGLE_WORKSPACE_CLIENT_ID", "mock-client-id")
    monkeypatch.setenv("NEXUS_GOOGLE_WORKSPACE_CLIENT_SECRET", "super-secret-value")
    res = generate_youtube_auth_url()
    assert "super-secret-value" not in str(res)
    assert res["secret_values_exposed"] is False
