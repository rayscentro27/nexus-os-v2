"""Unit, contract, and governance tests for the Universal Credential Resolver (Section 31B.2)."""
import io
import json
import os
import sys
from pathlib import Path
import pytest

from nexus_agent_platform.credential_control_plane import (
    CredentialStatus,
    CredentialHandle,
    CredentialResolutionResult,
    CredentialAlreadyExistsError,
    resolve_credential,
    assert_discovery_before_creation,
    get_venture_capabilities,
    list_all_integrations,
    catalog,
    write_reports,
    format_status_report,
    resolve,
)


def test_1_runtime_env_credential_discovered():
    """1. Credential in runtime.env is discovered."""
    res = resolve_credential(capability="telegram.hermes")
    assert res.status == CredentialStatus.AVAILABLE
    assert "CANONICAL_RUNTIME_ENV" in (res.secret_source or "")
    assert res.credential_id == "credential.telegram.hermes.prod.v1"
    assert res.raw_values_included is False


def test_2_macos_keychain_credential_discovered():
    """2. Credential in macOS Keychain is discovered."""
    res = resolve_credential(capability="model.gemini")
    assert res.status == CredentialStatus.AVAILABLE
    assert "MACOS_KEYCHAIN" in (res.secret_source or "")
    assert res.credential_id == "credential.google.gemini.prod.v1"


def test_3_wrangler_oauth_discovered():
    """3. Wrangler OAuth is discovered."""
    res = resolve_credential(capability="cloudflare.pages.write")
    assert res.status == CredentialStatus.AVAILABLE
    assert res.secret_source == "WRANGLER_OAUTH"
    assert res.credential_id == "credential.cloudflare.pages.prod.v1"
    # Never leaks OAuth token
    assert res.raw_values_included is False
    assert "oauth_token" not in (res.secret_ref or "")


def test_4_google_oauth_reference_discovered():
    """4. Google OAuth reference is discovered."""
    res = resolve_credential(capability="gmail.read")
    assert res.status == CredentialStatus.AVAILABLE
    assert res.provider == "google"
    assert res.credential_id == "credential.google.workspace.prod.v1"


def test_5_provider_specific_auth_referenced_without_exposing_secret():
    """5. Provider-specific auth can be referenced without exposing secret."""
    res = resolve_credential(capability="modal.video.generate")
    assert res.status == CredentialStatus.AVAILABLE
    assert res.provider == "modal"
    assert res.handle is not None
    repr_str = repr(res.handle)
    assert "(protected)" in repr_str
    # Verify to_dict contains no secret keys or values
    d = res.to_dict()
    assert d["raw_values_included"] is False
    d_json = json.dumps(d)
    assert "token_secret" not in d_json


def test_6_missing_env_var_does_not_override_valid_credential_elsewhere():
    """6. Missing env var does not override an existing valid credential elsewhere."""
    # When process environment is completely empty, resolve() still locates the credential in CANONICAL_RUNTIME_ENV
    rec = resolve("credential.brave.web_search.prod.v1", environ={})
    assert rec["result"] == "AVAILABLE"
    assert "CANONICAL_RUNTIME_ENV" in rec["source_found"]


def test_7_printify_existing_credential_discovered():
    """7. Printify existing credential is discovered if present."""
    res = resolve_credential(capability="printify.products.read")
    assert res.credential_id == "credential.printify.prod.v1"
    assert res.provider == "printify"
    # Exists in Keychain and validated against live Printify API -> status is AVAILABLE
    assert res.status == CredentialStatus.AVAILABLE
    assert res.secret_source == "MACOS_KEYCHAIN"


def test_8_social_credential_references_discovered():
    """8. Social credential references are discovered if present."""
    # Active Meta token for GoClear exists and is valid
    res_goclear = resolve_credential(capability="facebook.publish", venture_id="vnt_goclear_credit_2026")
    assert res_goclear.status == CredentialStatus.AVAILABLE
    assert res_goclear.provider == "meta"

    # Holiday Commerce has its own live-verified Page token (owner OAuth 2026-11-12)
    res_holiday = resolve_credential(capability="facebook.publish", venture_id="vnt_holiday_commerce_pilot_2026")
    assert res_holiday.status == CredentialStatus.AVAILABLE
    assert res_holiday.credential_id == "credential.meta.social.holiday.prod.v1"


def test_9_cross_venture_credential_isolation_enforced():
    """9. Cross-venture credential isolation enforced."""
    res = resolve_credential(capability="facebook.publish", venture_id="vnt_holiday_commerce_pilot_2026")
    # Must not silently use GoClear's credentials for Holiday
    assert res.credential_id != "credential.meta.social.goclear.prod.v1"
    assert res.credential_id == "credential.meta.social.holiday.prod.v1"
    assert res.status == CredentialStatus.AVAILABLE


def test_10_no_secret_printed_to_stdout(capsys):
    """10. No secret printed to stdout."""
    output = format_status_report()
    # Check that output does not contain raw API keys or passwords
    assert "Bearer " not in output
    assert "sk-" not in output
    assert "ghp_" not in output
    assert "key-" not in output
    assert "================================================================================" in output


def test_11_no_secret_written_to_reports():
    """11. No secret written to reports."""
    rep = write_reports()
    assert rep["raw_values_included"] is False
    catalog_path = Path("reports/runtime/nexus_credential_catalog_latest.json")
    content = catalog_path.read_text(encoding="utf-8")
    assert '"raw_values_included": false' in content
    assert "Bearer " not in content


def test_12_new_departments_can_resolve_credentials_without_knowing_physical_secret_location():
    """12. New departments can resolve credentials without knowing physical secret location."""
    # A generic worker in "PRODUCT" or "FINANCE" requests YouTube metadata
    res = resolve_credential(capability="youtube.metadata")
    assert res.status == CredentialStatus.AVAILABLE
    assert res.handle is not None
    # Calling inject_env injects the alias in-process without caller knowing where it came from
    mock_env = {}
    res.handle.inject_env(target=mock_env)
    assert "NEXUS_GOOGLE_YOUTUBE_API_KEY" in mock_env


def test_13_invalid_expired_credential_returns_correct_state(monkeypatch):
    """13. Invalid/expired credential returns correct state."""
    with monkeypatch.context() as m:
        m.setattr(
            "nexus_agent_platform.credential_control_plane._load",
            lambda: [{
                "credential_id": "credential.test.expired.v1",
                "provider": "test_provider",
                "environment": "prod",
                "capabilities": ["test.expired.read"],
                "status": "EXPIRED",
                "preferred_secret_source": "MACOS_KEYCHAIN",
            }],
        )
        res_expired = resolve_credential(capability="test.expired.read")
        assert res_expired.status == CredentialStatus.EXPIRED

    res_yt_upload = resolve_credential(capability="youtube.upload")
    assert res_yt_upload.status in (CredentialStatus.INSUFFICIENT_SCOPE, CredentialStatus.AUTH_REQUIRED)


def test_14_credential_creation_blocked_until_discovery_completes():
    """14. Credential creation is blocked until discovery completes."""
    # Capability is already available -> attempting to create raises CredentialAlreadyExistsError
    with pytest.raises(CredentialAlreadyExistsError):
        assert_discovery_before_creation(capability="telegram.hermes")

    # Capability is unconfigured (e.g. tiktok) -> discovery passes and returns AUTH_REQUIRED
    res = assert_discovery_before_creation(capability="tiktok.publish")
    assert res.status == CredentialStatus.AUTH_REQUIRED
