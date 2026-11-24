"""Tests for credential health validation, revalidation triggers, and safe refresh."""
import json
import ssl
import urllib.error
import pytest
from unittest.mock import MagicMock

from nexus_agent_platform import credential_control_plane as cp
from nexus_agent_platform.credential_control_plane import (
    CredentialStatus,
    HealthCheckStatus,
    LiveValidationResult,
    refresh_credential_health,
    resolve_credential,
    validate_credential_live,
    update_registry_credential,
    registry_entry,
)

PRINTIFY_ID = "credential.printify.prod.v1"


def test_1_stale_expired_state_can_be_refreshed_to_available_after_secret_replacement(monkeypatch):
    """1. Stale EXPIRED state can be refreshed to AVAILABLE after secret replacement."""
    # Simulate a credential previously marked EXPIRED
    update_registry_credential(PRINTIFY_ID, {"status": "EXPIRED", "secret_mdat": "old_timestamp"})
    assert registry_entry(PRINTIFY_ID)["status"] == "EXPIRED"

    # Simulate updated Keychain secret metadata
    monkeypatch.setattr(cp, "_get_secret_metadata_timestamp", lambda entry: "new_timestamp_20261111")
    # Mock live validator returning PASS (e.g. HTTP 200)
    monkeypatch.setattr(
        cp,
        "validate_credential_live",
        lambda cid: LiveValidationResult(
            credential_id=cid,
            status=HealthCheckStatus.PASS,
            http_status=200,
            message="HTTP 200 OK",
        ),
    )

    res = refresh_credential_health(PRINTIFY_ID)
    assert res["old_status"] == "EXPIRED"
    assert res["new_status"] == "AVAILABLE"
    assert res["live_status"] == "PASS"
    assert registry_entry(PRINTIFY_ID)["status"] == "AVAILABLE"


def test_2_http_200_maps_to_available(monkeypatch):
    """2. HTTP 200 maps to AVAILABLE."""
    monkeypatch.setattr(cp, "_keychain_value", lambda cid, comp: "valid_token_test")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    monkeypatch.setattr(cp.urllib.request, "urlopen", lambda req, **kw: mock_cm)

    live_res = validate_credential_live(PRINTIFY_ID)
    assert live_res.status == HealthCheckStatus.PASS
    assert live_res.http_status == 200

    refresh_res = refresh_credential_health(PRINTIFY_ID)
    assert refresh_res["new_status"] == "AVAILABLE"


def test_3_http_401_maps_to_expired_or_revoked(monkeypatch):
    """3. HTTP 401 maps to EXPIRED_OR_REVOKED."""
    monkeypatch.setattr(cp, "_keychain_value", lambda cid, comp: "expired_token_test")

    def mock_urlopen(req, **kw):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(cp.urllib.request, "urlopen", mock_urlopen)

    live_res = validate_credential_live(PRINTIFY_ID)
    assert live_res.status == HealthCheckStatus.EXPIRED_OR_REVOKED
    assert live_res.http_status == 401

    refresh_res = refresh_credential_health(PRINTIFY_ID)
    assert refresh_res["new_status"] == "EXPIRED"
    assert refresh_res["live_status"] == "EXPIRED_OR_REVOKED"


def test_4_ssl_network_errors_do_not_map_to_expired(monkeypatch):
    """4. SSL/network errors do not map to EXPIRED."""
    # Ensure credential starts AVAILABLE
    update_registry_credential(PRINTIFY_ID, {"status": "AVAILABLE"})

    # Test Network Error
    def mock_network_err(req, **kw):
        raise urllib.error.URLError("Connection refused [Errno 61]")

    monkeypatch.setattr(cp.urllib.request, "urlopen", mock_network_err)
    live_res = validate_credential_live(PRINTIFY_ID)
    assert live_res.status == HealthCheckStatus.NETWORK_ERROR

    refresh_res = refresh_credential_health(PRINTIFY_ID)
    # Status must NOT be marked EXPIRED on network failure
    assert refresh_res["new_status"] == "AVAILABLE"
    assert registry_entry(PRINTIFY_ID)["status"] == "AVAILABLE"

    # Test SSL Error
    def mock_ssl_err(req, **kw):
        raise urllib.error.URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")

    monkeypatch.setattr(cp.urllib.request, "urlopen", mock_ssl_err)
    live_ssl = validate_credential_live(PRINTIFY_ID)
    assert live_ssl.status == HealthCheckStatus.SSL_ERROR

    refresh_ssl = refresh_credential_health(PRINTIFY_ID)
    assert refresh_ssl["new_status"] == "AVAILABLE"
    assert registry_entry(PRINTIFY_ID)["status"] == "AVAILABLE"


def test_5_resolver_uses_refreshed_state(monkeypatch):
    """5. Universal capability resolver immediately returns AVAILABLE once refreshed."""
    update_registry_credential(PRINTIFY_ID, {"status": "AVAILABLE"})
    monkeypatch.setattr(cp, "_keychain_value", lambda cid, comp: "live_valid_fixture")

    for cap in (
        "printify.shops.read",
        "printify.products.read",
        "printify.products.write",
        "printify.orders.read",
        "printify.orders.write",
    ):
        res = resolve_credential(capability=cap)
        assert res.status == CredentialStatus.AVAILABLE
        assert res.credential_id == PRINTIFY_ID
        assert res.handle is not None


def test_6_no_secret_values_exposed():
    """6. Validation results and refresh responses never contain raw secret values."""
    res = refresh_credential_health(PRINTIFY_ID)
    res_str = json.dumps(res)
    assert res["values_included"] is False
    assert "Bearer " not in res_str
    assert "sk-" not in res_str
    assert "ghp_" not in res_str


def test_7_no_duplicate_credential_created():
    """7. Revalidation operates strictly in-place; no duplicate credential entries created."""
    credentials = cp._load()
    printify_entries = [c for c in credentials if c.get("provider") == "printify"]
    assert len(printify_entries) == 1
    assert printify_entries[0]["credential_id"] == PRINTIFY_ID
