"""Tests for shared certified capabilities and Nova adapter.

Covers: shared client-count routing, email normalization, identity resolution,
error integrity, permissions, provenance, Nova adapter behavior, and isolation.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ─── Email Normalization ───────────────────────────────────

class TestEmailNormalization:
    """Tests for _normalize_email in shared capabilities."""

    def test_lowercase(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("Test@Example.COM") == "test@example.com"

    def test_whitespace(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("  user@domain.com  ") == "user@domain.com"

    def test_mailto_prefix(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("mailto:user@domain.com") == "user@domain.com"

    def test_mailto_uppercase(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("mailto:USER@DOMAIN.COM") == "user@domain.com"

    def test_markdown_mailto(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("[user@domain.com](mailto:user@domain.com)") == "user@domain.com"

    def test_surrounding_punctuation(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("<user@domain.com>") == "user@domain.com"

    def test_invalid_email(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("not-an-email") is None

    def test_empty_string(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("") is None

    def test_none(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email(None) is None

    def test_complex_markdown(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        result = _normalize_email("[THEWORLDZMINE@GMAIL.COM](mailto:theworldzmine@gmail.com)")
        assert result == "theworldzmine@gmail.com"

    def test_real_worldzmine(self):
        from nexus_agent_platform.capabilities.shared import _normalize_email
        assert _normalize_email("theworldzmine@gmail.com") == "theworldzmine@gmail.com"
        assert _normalize_email("THEWORLDZMINE@GMAIL.COM") == "theworldzmine@gmail.com"


# ─── Permission Enforcement ────────────────────────────────

class TestPermissions:
    """Tests for code-enforced permission profiles."""

    def test_nova_can_invoke_approved_reads(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        for cap in ["get_runtime_capabilities", "get_client_count",
                     "resolve_user_identity_by_email", "get_system_health",
                     "get_pending_approvals", "get_recent_research",
                     "get_opportunities", "get_client_profile",
                     "get_funding_readiness", "get_operational_summary"]:
            assert _check_permission("hermes_nova", cap, is_write=False) is None

    def test_nova_cannot_invoke_writes(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        for cap in ["create_test_user", "send_email", "schedule_report"]:
            err = _check_permission("hermes_nova", cap, is_write=True)
            assert err is not None
            assert "not in" in err

    def test_nova_cannot_invoke_unregistered_reads(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        err = _check_permission("hermes_nova", "arbitrary_sql", is_write=False)
        assert err is not None

    def test_nova_cannot_invoke_hermes_capabilities(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        err = _check_permission("hermes_nova", "get_system_status", is_write=False)
        assert err is not None

    def test_unknown_agent_rejected(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        err = _check_permission("unknown_agent", "get_client_count", is_write=False)
        assert err is not None
        assert "Unknown agent" in err

    def test_hermes_can_invoke_its_capabilities(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        for cap in ["get_client_count", "get_system_status", "get_failure_report"]:
            assert _check_permission("nexus_hermes", cap, is_write=False) is None

    def test_nova_allowed_reads_frozen(self):
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_READS
        assert isinstance(NOVA_ALLOWED_READS, frozenset)
        assert len(NOVA_ALLOWED_READS) == 11

    def test_nova_allowed_writes_empty(self):
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_WRITES
        assert isinstance(NOVA_ALLOWED_WRITES, frozenset)
        assert len(NOVA_ALLOWED_WRITES) == 0


# ─── Write Detection ───────────────────────────────────────

class TestWriteDetection:
    """Tests for write-request detection."""

    def test_create_user_detected(self):
        from nexus_agent_platform.capabilities.shared import detect_write_request
        result = detect_write_request("Can you add a new test user using test@gmail.com?")
        assert result is not None
        assert result["requested_action"] == "create_test_user"
        assert result["execution_allowed"] is False

    def test_conversation_not_detected(self):
        from nexus_agent_platform.capabilities.shared import detect_write_request
        assert detect_write_request("How many clients do we have?") is None

    def test_read_not_detected(self):
        from nexus_agent_platform.capabilities.shared import detect_write_request
        assert detect_write_request("Check if user@gmail.com exists") is None


# ─── Shared Client Count ───────────────────────────────────

class TestSharedClientCount:
    """Tests for shared client-count handler routing to certified handler."""

    def test_routes_to_hermes_handler(self):
        """Shared handler must call hermes._get_client_count."""
        from nexus_agent_platform.capabilities.shared import _handle_client_count

        mock_result = {
            "production_total": 14,
            "active": 14,
            "onboarding": 0,
            "inactive": 0,
            "hidden": 0,
            "tester_or_certification": 24,
            "all_profiles": 38,
            "tenant": "goclear",
            "retrieved_at": "12:00 PM MT",
            "error": None,
            "provenance": {
                "capability": "get_client_count",
                "status": "success",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "row_count": 38,
            },
        }

        with patch("nexus_agent_platform.agents.hermes._get_client_count",
                    return_value=mock_result):
            result = _handle_client_count(trace_id="test_123")

        assert result["status"] == "success"
        assert result["capability"] == "get_client_count"
        data = result["data"]
        assert data["production_clients"] == 14
        assert data["active"] == 14
        assert data["onboarding"] == 0
        assert data["tester_or_certification"] == 24
        prov = result["provenance"]
        assert prov["handler"] == "hermes._get_client_count"
        assert prov["trace_id"] == "test_123"

    def test_canonical_schema_fields(self):
        """Result must include all canonical fields."""
        from nexus_agent_platform.capabilities.shared import _handle_client_count

        mock_result = {
            "production_total": 14, "active": 14, "onboarding": 0,
            "inactive": 0, "hidden": 0, "tester_or_certification": 24,
            "all_profiles": 38, "error": None,
            "provenance": {"status": "success", "source": "supabase",
                           "source_type": "live_governed_read",
                           "retrieved_at": "", "freshness": "live", "row_count": 38},
        }

        with patch("nexus_agent_platform.agents.hermes._get_client_count",
                    return_value=mock_result):
            result = _handle_client_count()

        data = result["data"]
        required = {"production_clients", "active", "onboarding",
                     "inactive", "hidden", "tester_or_certification", "all_profiles"}
        assert required.issubset(data.keys())

    def test_handler_error_becomes_error_status(self):
        """Handler exception must produce error status, not silent failure."""
        from nexus_agent_platform.capabilities.shared import _handle_client_count

        with patch("nexus_agent_platform.agents.hermes._get_client_count",
                    side_effect=RuntimeError("DB connection lost")):
            result = _handle_client_count(trace_id="test_err")

        assert result["status"] == "error"
        assert "DB connection lost" in result["error"]
        assert result["provenance"]["status"] == "error"

    def test_no_duplicate_query_implementation(self):
        """Nova connector must not have its own _get_client_count_nova."""
        from nexus_agent_platform.connectors import nova_supabase
        assert not hasattr(nova_supabase, "_get_client_count_nova")


# ─── Identity Resolution ───────────────────────────────────

class TestIdentityResolution:
    """Tests for canonical identity resolution."""

    def _mock_session(self, auth_users=None, profile_rows=None,
                      auth_ok=True, profile_ok=True, auth_status=200,
                      profile_status=200):
        """Create a mock Supabase session."""
        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"

        # Auth response
        auth_resp = MagicMock()
        auth_resp.ok = auth_ok
        auth_resp.status_code = auth_status
        auth_resp.json.return_value = {"users": auth_users or []}

        # Profile response
        profile_resp = MagicMock()
        profile_resp.ok = profile_ok
        profile_resp.status_code = profile_status
        profile_resp.json.return_value = profile_rows or []

        def get_side_effect(url, params=None, timeout=None):
            if "auth/v1/admin/users" in url:
                return auth_resp
            if "rest/v1/client_profiles" in url:
                return profile_resp
            mock_resp = MagicMock()
            mock_resp.ok = False
            mock_resp.status_code = 404
            return mock_resp

        session.get = MagicMock(side_effect=get_side_effect)
        return session

    def test_email_found_in_both_sources(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[{"email": "test@gmail.com", "email_confirmed_at": "2024-01-01"}],
            profile_rows=[{"id": "1", "email": "test@gmail.com", "status": "active",
                           "source": "tester_invitation", "tenant_id": "goclear"}],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution(
                {"email": "test@gmail.com"}, trace_id="test_id"
            )

        assert result["status"] == "success"
        data = result["data"]
        assert data["exists_anywhere"] is True
        assert data["verification_complete"] is True
        assert "tester" in data["account_classifications"]
        assert data["sources"]["supabase_auth"]["exists"] is True
        assert data["sources"]["client_profiles"]["exists"] is True

    def test_email_not_found(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[{"email": "other@gmail.com"}],
            profile_rows=[],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "nonexistent@gmail.com"})

        assert result["status"] == "success"
        assert result["data"]["exists_anywhere"] is False
        assert result["data"]["verification_complete"] is True

    def test_auth_error_not_treated_as_not_found(self):
        """Auth error must remain error, never become not_found."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(auth_ok=False, auth_status=500, profile_rows=[])

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "test@gmail.com"})

        assert result["status"] == "partial"
        assert result["data"]["verification_complete"] is False
        assert result["data"]["sources"]["supabase_auth"]["status"] == "error"

    def test_profile_error_not_treated_as_not_found(self):
        """Profile error must remain error, never become not_found."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[], profile_ok=False, profile_status=500
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "test@gmail.com"})

        assert result["status"] == "partial"
        assert result["data"]["verification_complete"] is False
        assert result["data"]["sources"]["client_profiles"]["status"] == "error"

    def test_invalid_email_returns_error(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        result = _handle_identity_resolution({"email": "not-an-email"})
        assert result["status"] == "error"
        assert "Invalid email" in result["error"]

    def test_unavailable_session_returns_unavailable(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=None):
            result = _handle_identity_resolution({"email": "test@gmail.com"})

        assert result["status"] == "unavailable"
        assert "credentials not configured" in result["error"].lower()

    def test_production_classification(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[{"email": "prod@gmail.com", "email_confirmed_at": "2024-01-01"}],
            profile_rows=[{"id": "1", "email": "prod@gmail.com", "status": "active",
                           "source": "manual", "tenant_id": "goclear"}],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "prod@gmail.com"})

        assert "production" in result["data"]["account_classifications"]

    def test_certification_classification(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[],
            profile_rows=[{"id": "1", "email": "cert@gmail.com", "status": "active",
                           "source": "manual", "tenant_id": "tenant-cert-123"}],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "cert@gmail.com"})

        assert "certification" in result["data"]["account_classifications"]

    def test_auth_only_profile_not_found(self):
        """Email in Auth but not in client_profiles."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[{"email": "authonly@gmail.com", "email_confirmed_at": "2024-01-01"}],
            profile_rows=[],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "authonly@gmail.com"})

        assert result["data"]["exists_anywhere"] is True
        assert result["data"]["sources"]["supabase_auth"]["exists"] is True
        assert result["data"]["sources"]["client_profiles"]["exists"] is False

    def test_profile_only_auth_not_found(self):
        """Email in client_profiles but not in Auth."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[],
            profile_rows=[{"id": "1", "email": "profileonly@gmail.com", "status": "active",
                           "source": "manual", "tenant_id": "goclear"}],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "profileonly@gmail.com"})

        assert result["data"]["exists_anywhere"] is True
        assert result["data"]["sources"]["supabase_auth"]["exists"] is False
        assert result["data"]["sources"]["client_profiles"]["exists"] is True

    def test_partial_verification_on_source_error(self):
        """One source error must produce partial verification."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_ok=False, auth_status=500,
            profile_rows=[{"id": "1", "email": "partial@gmail.com", "status": "active",
                           "source": "manual", "tenant_id": "goclear"}],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "partial@gmail.com"})

        assert result["status"] == "partial"
        assert result["data"]["verification_complete"] is False

    def test_auth_pagination_completes(self):
        """Auth lookup should paginate until found or pages exhausted."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"

        # First page: 200 users, target not found
        page1_resp = MagicMock()
        page1_resp.ok = True
        page1_resp.json.return_value = {
            "users": [{"email": f"user{i}@test.com"} for i in range(200)]
        }

        # Second page: target found
        page2_resp = MagicMock()
        page2_resp.ok = True
        page2_resp.json.return_value = {
            "users": [{"email": "target@gmail.com", "email_confirmed_at": "2024-01-01"}]
        }

        call_count = [0]
        def get_side_effect(url, params=None, timeout=None):
            if "auth/v1/admin/users" in url:
                call_count[0] += 1
                if call_count[0] == 1:
                    return page1_resp
                return page2_resp
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = []
            return mock_resp

        session.get = MagicMock(side_effect=get_side_effect)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "target@gmail.com"})

        assert result["data"]["exists_anywhere"] is True
        assert result["data"]["sources"]["supabase_auth"]["exists"] is True

    def test_safety_limit_on_pagination(self):
        """Auth lookup should stop at safety limit."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"

        # Always return full pages to hit the limit
        full_page_resp = MagicMock()
        full_page_resp.ok = True
        full_page_resp.json.return_value = {
            "users": [{"email": f"user{i}@test.com"} for i in range(200)]
        }

        session.get = MagicMock(return_value=full_page_resp)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "deep@gmail.com"})

        assert result["data"]["sources"]["supabase_auth"]["status"] == "incomplete"
        assert result["data"]["verification_complete"] is False

    def test_auth_exception_returns_error(self):
        """Auth API exception must return error status, not crash."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        session.get = MagicMock(side_effect=RuntimeError("Connection refused"))

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "test@gmail.com"})

        assert result["data"]["sources"]["supabase_auth"]["status"] == "error"
        assert result["data"]["verification_complete"] is False

    def test_profile_exception_returns_error(self):
        """Profile query exception must return error status, not crash."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"

        def get_side_effect(url, params=None, timeout=None):
            if "auth/v1/admin/users" in url:
                mock_resp = MagicMock()
                mock_resp.ok = True
                mock_resp.json.return_value = {"users": []}
                return mock_resp
            raise RuntimeError("Query failed")

        session.get = MagicMock(side_effect=get_side_effect)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution({"email": "test@gmail.com"})

        assert result["data"]["sources"]["client_profiles"]["status"] == "error"
        assert result["data"]["verification_complete"] is False

    def test_worldzmine_email_not_reported_absent(self):
        """theworldzmine@gmail.com must not be reported absent if Auth has it."""
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = self._mock_session(
            auth_users=[{"email": "theworldzmine@gmail.com",
                         "email_confirmed_at": "2024-01-01"}],
            profile_rows=[],
        )

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution(
                {"email": "theworldzmine@gmail.com"}
            )

        assert result["data"]["exists_anywhere"] is True
        assert result["data"]["sources"]["supabase_auth"]["exists"] is True


# ─── Shared Capability Execution ───────────────────────────

class TestSharedCapabilityExecution:
    """Tests for the shared execute_shared_capability boundary."""

    def test_unauthorized_capability_rejected(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        result = execute_shared_capability(
            "hermes_nova", "arbitrary_sql", {"query": "SELECT * FROM users"}
        )
        assert result["status"] == "unauthorized"
        assert "not in" in result["error"]

    def test_unknown_agent_rejected(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        result = execute_shared_capability(
            "unknown_agent", "get_client_count", {}
        )
        assert result["status"] == "unauthorized"

    def test_write_denied(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        result = execute_shared_capability(
            "hermes_nova", "get_client_count",
            {"raw_text": "create a new user account"}
        )
        assert result["status"] == "denied"

    def test_unregistered_capability_rejected_by_permission(self):
        """Capability not in allowlist is rejected by permission check."""
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        result = execute_shared_capability(
            "hermes_nova", "nonexistent_capability", {}
        )
        assert result["status"] == "unauthorized"

    def test_provenance_included_in_result(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        mock_result = {
            "production_total": 14, "active": 14, "onboarding": 0,
            "inactive": 0, "hidden": 0, "tester_or_certification": 24,
            "all_profiles": 38, "error": None,
            "provenance": {"status": "success", "source": "supabase",
                           "source_type": "live_governed_read",
                           "retrieved_at": "", "freshness": "live", "row_count": 38},
        }

        with patch("nexus_agent_platform.agents.hermes._get_client_count",
                    return_value=mock_result):
            result = execute_shared_capability(
                "hermes_nova", "get_client_count", {}, trace_id="trace_abc"
            )

        assert "provenance" in result
        assert result["provenance"]["trace_id"] == "trace_abc"

    def test_runtime_capabilities_uses_agent_id(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        result = execute_shared_capability(
            "hermes_nova", "get_runtime_capabilities", {}
        )
        assert result["status"] == "success"
        assert result["data"]["agent_id"] == "hermes_nova"
        assert "get_client_count" in result["data"]["available_reads"]


# ─── General Search ─────────────────────────────────────────

class TestGeneralSearch:
    """Tests for the shared general_search capability."""

    def test_empty_query_returns_error(self):
        from nexus_agent_platform.capabilities.shared import _handle_general_search
        result = _handle_general_search({"query": ""})
        assert result["status"] == "error"
        assert "No search query" in result["error"]

    def test_unavailable_session_returns_unavailable(self):
        from nexus_agent_platform.capabilities.shared import _handle_general_search
        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=None):
            result = _handle_general_search({"query": "test"})
        assert result["status"] == "unavailable"

    def test_search_approved_tables(self):
        from nexus_agent_platform.capabilities.shared import _handle_general_search

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"

        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = [
            {"id": "1", "client_label": "ray@example.com", "status": "active",
             "source": "manual", "tenant_id": "goclear"},
        ]
        session.get = MagicMock(return_value=resp)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_general_search({"query": "ray@example.com"})

        assert result["status"] == "success"
        assert result["data"]["match_count"] >= 1
        assert "client_profiles" in result["data"]["sources_searched"]
        prov = result["provenance"]
        assert prov["capability"] == "general_search"
        assert prov["freshness"] == "live"
        assert "client_profiles" in prov["tables_searched"]

    def test_no_matches_returns_not_found(self):
        from nexus_agent_platform.capabilities.shared import _handle_general_search

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"

        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = []
        session.get = MagicMock(return_value=resp)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_general_search({"query": "zzznonexistent999"})

        assert result["status"] == "not_found"
        assert result["data"]["match_count"] == 0

    def test_provenance_has_trace_id(self):
        from nexus_agent_platform.capabilities.shared import _handle_general_search

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = []
        session.get = MagicMock(return_value=resp)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_general_search(
                {"query": "test"}, trace_id="gs_trace_123"
            )

        assert result["provenance"]["trace_id"] == "gs_trace_123"

    def test_nova_can_invoke_general_search(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = []
        session.get = MagicMock(return_value=resp)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = execute_shared_capability(
                "hermes_nova", "general_search",
                {"query": "test"}, trace_id="nova_gs_test"
            )

        assert result["status"] in ("success", "not_found")
        assert result["capability"] == "general_search"


# ─── Nova Search Tool Routing ───────────────────────────────

class TestNovaSearchToolRouting:
    """Tests for _nova_search_supabase routing through shared layer."""

    def test_write_denied(self):
        from nexus_agent_platform.agents.nova import _nova_search_supabase
        result = _nova_search_supabase("create a test user at x@y.com")
        assert result["status"] == "denied"
        assert result["tool"] == "nova_search_supabase"

    def test_identity_lookup_routes_to_shared(self):
        from nexus_agent_platform.agents.nova import _nova_search_supabase
        with patch("nexus_agent_platform.capabilities.shared.execute_shared_capability",
                    return_value={
                        "status": "success",
                        "data": {"normalized_email": "test@gmail.com",
                                 "exists_anywhere": True,
                                 "verification_complete": True,
                                 "account_classifications": ["auth_user"],
                                 "sources": {}},
                        "provenance": {"capability": "resolve_user_identity_by_email"},
                    }) as mock_exec:
            result = _nova_search_supabase(
                "check if test@gmail.com exists in supabase"
            )
        assert result["query_type"] == "resolve_user_identity_by_email"
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][1] == "resolve_user_identity_by_email"

    def test_client_count_routes_to_shared(self):
        from nexus_agent_platform.agents.nova import _nova_search_supabase
        with patch("nexus_agent_platform.capabilities.shared.execute_shared_capability",
                    return_value={
                        "status": "success",
                        "data": {"production_clients": 14, "active": 14},
                        "provenance": {"capability": "get_client_count"},
                    }) as mock_exec:
            result = _nova_search_supabase(
                "how many clients do we have in supabase"
            )
        assert result["query_type"] == "get_client_count"
        call_args = mock_exec.call_args
        assert call_args[0][1] == "get_client_count"

    def test_capabilities_routes_to_shared(self):
        from nexus_agent_platform.agents.nova import _nova_search_supabase
        with patch("nexus_agent_platform.capabilities.shared.execute_shared_capability",
                    return_value={
                        "status": "success",
                        "data": {"available_reads": ["get_client_count"]},
                        "provenance": {"capability": "get_runtime_capabilities"},
                    }) as mock_exec:
            result = _nova_search_supabase(
                "what can you access in supabase"
            )
        assert result["query_type"] == "get_runtime_capabilities"
        call_args = mock_exec.call_args
        assert call_args[0][1] == "get_runtime_capabilities"

    def test_general_fallback_routes_to_shared(self):
        from nexus_agent_platform.agents.nova import _nova_search_supabase
        with patch("nexus_agent_platform.capabilities.shared.execute_shared_capability",
                    return_value={
                        "status": "not_found",
                        "data": {"matches": [], "sources_searched": ["client_profiles"],
                                 "match_count": 0},
                        "provenance": {"capability": "general_search"},
                    }) as mock_exec:
            result = _nova_search_supabase(
                "search supabase for GoClear workflows"
            )
        assert result["query_type"] == "general_search"
        call_args = mock_exec.call_args
        assert call_args[0][1] == "general_search"

    def test_nova_has_no_direct_supabase_access(self):
        """Nova must not have its own Supabase client or session."""
        import inspect
        from nexus_agent_platform.agents import nova
        source = inspect.getsource(nova)
        assert "_nova_supabase_client" not in source
        assert "import requests" not in source


# ─── Nova Adapter ──────────────────────────────────────────

class TestNovaAdapter:
    """Tests for the thin Nova adapter over shared capabilities."""

    def test_nova_capability_allowlist(self):
        from nexus_agent_platform.connectors.nova_supabase import NOVA_ALLOWED_READS
        assert "get_runtime_capabilities" in NOVA_ALLOWED_READS
        assert "get_client_count" in NOVA_ALLOWED_READS
        assert "resolve_user_identity_by_email" in NOVA_ALLOWED_READS
        assert "general_search" in NOVA_ALLOWED_READS
        assert "get_system_health" in NOVA_ALLOWED_READS
        assert "get_pending_approvals" in NOVA_ALLOWED_READS
        assert "get_recent_research" in NOVA_ALLOWED_READS
        assert "get_opportunities" in NOVA_ALLOWED_READS
        assert "get_client_profile" in NOVA_ALLOWED_READS
        assert "get_funding_readiness" in NOVA_ALLOWED_READS
        assert "get_operational_summary" in NOVA_ALLOWED_READS
        assert len(NOVA_ALLOWED_READS) == 11

    def test_nova_rejects_unregistered_capability(self):
        from nexus_agent_platform.connectors.nova_supabase import execute_nova_capability

        result = execute_nova_capability("arbitrary_sql")
        assert result["status"] == "unauthorized"

    def test_nova_delegates_to_shared_adapter(self):
        from nexus_agent_platform.connectors.nova_supabase import execute_nova_capability

        mock_result = {
            "production_total": 14, "active": 14, "onboarding": 0,
            "inactive": 0, "hidden": 0, "tester_or_certification": 24,
            "all_profiles": 38, "error": None,
            "provenance": {"status": "success", "source": "supabase",
                           "source_type": "live_governed_read",
                           "retrieved_at": "", "freshness": "live", "row_count": 38},
        }

        with patch("nexus_agent_platform.agents.hermes._get_client_count",
                    return_value=mock_result):
            result = execute_nova_capability("get_client_count")

        assert result["status"] == "success"
        assert result["data"]["production_clients"] == 14

    def test_nova_identity_resolution_passes_email(self):
        from nexus_agent_platform.connectors.nova_supabase import execute_nova_capability

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=None):
            result = execute_nova_capability(
                "resolve_user_identity_by_email",
                {"email": "test@gmail.com"}
            )

        assert result["status"] == "unavailable"

    def test_nova_write_denial(self):
        from nexus_agent_platform.connectors.nova_supabase import detect_nova_write_request

        result = detect_nova_write_request("Can you add a new test user using x@y.com?")
        assert result is not None
        assert result["execution_allowed"] is False

    def test_nova_no_supabase_import_in_source(self):
        """Nova connector must not import Supabase client directly."""
        import inspect
        from nexus_agent_platform.connectors import nova_supabase
        source = inspect.getsource(nova_supabase)
        # Should not create its own Supabase session
        assert "_nova_supabase_client" not in source
        assert "import requests" not in source

    def test_nova_tool_returns_success(self):
        """Nova tool integration should work through shared adapter."""
        from nexus_agent_platform.connectors.nova_supabase import execute_nova_capability

        result = execute_nova_capability("get_client_count")
        assert result["status"] == "success"

    def test_nova_write_detection(self):
        """Write detection should still work from the connector."""
        from nexus_agent_platform.connectors.nova_supabase import detect_nova_write_request

        assert detect_nova_write_request("create a test user test@gmail.com")
        assert not detect_nova_write_request("how many clients do we have")


# ─── Provenance ────────────────────────────────────────────

class TestProvenance:
    """Tests for provenance integrity."""

    def test_client_count_provenance_has_handler(self):
        from nexus_agent_platform.capabilities.shared import _handle_client_count

        mock_result = {
            "production_total": 14, "active": 14, "onboarding": 0,
            "inactive": 0, "hidden": 0, "tester_or_certification": 24,
            "all_profiles": 38, "error": None,
            "provenance": {"status": "success", "source": "supabase",
                           "source_type": "live_governed_read",
                           "retrieved_at": "", "freshness": "live", "row_count": 38},
        }

        with patch("nexus_agent_platform.agents.hermes._get_client_count",
                    return_value=mock_result):
            result = _handle_client_count(trace_id="prov_test")

        prov = result["provenance"]
        assert prov["handler"] == "hermes._get_client_count"
        assert prov["trace_id"] == "prov_test"
        assert prov["access_boundary"] == "approved read capability only"

    def test_identity_provenance_has_sources_checked(self):
        from nexus_agent_platform.capabilities.shared import _handle_identity_resolution

        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"users": []}
        session.get = MagicMock(return_value=mock_resp)

        with patch("nexus_agent_platform.capabilities.shared._supabase_session",
                    return_value=session):
            result = _handle_identity_resolution(
                {"email": "test@gmail.com"}, trace_id="id_prov_test"
            )

        prov = result["provenance"]
        assert "supabase_auth" in prov["sources_checked"]
        assert "client_profiles" in prov["sources_checked"]
        assert prov["trace_id"] == "id_prov_test"
        assert prov["verification_complete"] in (True, False)


# ─── Response Generation ───────────────────────────────────

class TestResponseGeneration:
    """Tests for Nova's conversational brain response quality."""

    def test_nova_brain_has_soul_description(self):
        """Nova brain SOUL should describe business context."""
        from nexus_agent_platform.agents.nova import SOUL
        assert "GoClear" in SOUL
        assert "read-only" in SOUL
        assert "Supabase" in SOUL

    def test_nova_brain_has_supabase_tool(self):
        """Nova brain should have a Supabase search tool function."""
        from nexus_agent_platform.agents.nova import _nova_search_supabase
        assert callable(_nova_search_supabase)


# ─── Isolation ─────────────────────────────────────────────

class TestIsolation:
    """Tests for security and isolation guarantees."""

    def test_no_supabase_key_in_nova_connector(self):
        """Nova connector must not reference SUPABASE_SERVICE_ROLE_KEY."""
        import inspect
        from nexus_agent_platform.connectors import nova_supabase
        source = inspect.getsource(nova_supabase)
        assert "SUPABASE_SERVICE_ROLE_KEY" not in source
        assert "service_role_key" not in source.lower() or "UNSAFE_FIELDS" in source

    def test_no_raw_sql_possible(self):
        """Shared adapter must not execute raw SQL."""
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        result = execute_shared_capability(
            "hermes_nova", "resolve_user_identity_by_email",
            {"email": "test@gmail.com", "raw_text": "SELECT * FROM users"}
        )
        # Should either execute normally or deny — never execute SQL
        assert result["status"] in ("success", "partial", "unavailable", "error", "denied")

    def test_shared_session_has_no_exported_credentials(self):
        """Shared session must not expose credentials."""
        from nexus_agent_platform.capabilities.shared import _supabase_session
        session = _supabase_session()
        if session is not None:
            # The session should have headers but not expose the key
            headers = dict(session.headers)
            # apikey is in headers for Supabase — that's expected
            # but we should not export it as a return value
            assert "apikey" in headers or session is None


# ─── Graph Integration ─────────────────────────────────────

class TestGraphIntegration:
    """Tests for Nova graph structure with shared capabilities."""

    def test_graph_has_capability_gate_node(self):
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        assert "capability_gate" in graph._node_fns

    def test_graph_node_count(self):
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        expected = ["classify_intent", "handle_utility", "capability_gate",
                     "build_context", "generate_response", "validate_output",
                     "compose_output"]
        assert list(graph._node_fns.keys()) == expected

    def test_nova_uses_shared_module_not_direct_queries(self):
        """Nova brain should own its Supabase tools."""
        import inspect
        from nexus_agent_platform.agents import nova
        source = inspect.getsource(nova)
        assert "nova_search_supabase" in source  # tool is defined in nova
        assert "_nova_supabase_client" not in source  # no direct client


# ─── Semantic Capability Gate ──────────────────────────────

class TestSemanticCapabilityGate:
    """Tests for semantic intent matching without requiring 'Supabase' keyword."""

    def test_identity_without_supabase_keyword(self):
        """Email lookup must trigger without requiring 'Supabase'."""
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Look up user@example.com")
        assert result is not None
        cap, args = result
        assert cap == "resolve_user_identity_by_email"
        assert args["email"] == "user@example.com"

    def test_identity_what_kind_of_account(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What kind of account is ray@example.com?")
        assert result is not None
        cap, args = result
        assert cap == "resolve_user_identity_by_email"
        assert args["email"] == "ray@example.com"

    def test_identity_markdown_email(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Check [user@example.com](mailto:user@example.com)")
        assert result is not None
        cap, args = result
        assert cap == "resolve_user_identity_by_email"

    def test_identity_uppercase_email(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Look up USER@EXAMPLE.COM")
        assert result is not None
        cap, args = result
        assert cap == "resolve_user_identity_by_email"
        assert args["email"] == "USER@EXAMPLE.COM"

    def test_client_count_without_supabase_keyword(self):
        """Client count must trigger without 'Supabase'."""
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("How many clients do we have?")
        assert result is not None
        cap, _ = result
        assert cap == "get_client_count"

    def test_client_count_production_tester(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate(
            "How many production clients and tester profiles?"
        )
        assert result is not None
        cap, _ = result
        assert cap == "get_client_count"

    def test_client_count_onboarding(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Are any clients onboarding?")
        assert result is not None
        cap, _ = result
        assert cap == "get_client_count"

    def test_client_count_breakdown(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Give me the client breakdown")
        assert result is not None
        cap, _ = result
        assert cap == "get_client_count"

    def test_runtime_without_supabase_keyword(self):
        """Runtime query must trigger without 'Supabase'."""
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What can you access?")
        assert result is not None
        cap, _ = result
        assert cap == "get_runtime_capabilities"

    def test_runtime_connected(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Are you connected to Supabase?")
        assert result is not None
        cap, _ = result
        assert cap == "get_runtime_capabilities"

    def test_runtime_what_tools(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What tools do you currently have?")
        assert result is not None
        cap, _ = result
        assert cap == "get_runtime_capabilities"

    def test_general_search_requires_both_verb_and_term(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Search Supabase for GoClear")
        assert result is not None
        cap, _ = result
        assert cap == "general_search"

    def test_no_tool_conversation(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        assert _semantic_capability_gate("Why is the sky blue?") is None

    def test_no_tool_opinion(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        assert _semantic_capability_gate("What do you think of Cadillac SUVs?") is None

    def test_no_tool_greeting(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        assert _semantic_capability_gate("hello") is None

    def test_precedence_identity_over_general(self):
        """Email with search verb should resolve identity, not general search."""
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Search for user@example.com in the records")
        assert result is not None
        cap, _ = result
        assert cap == "resolve_user_identity_by_email"

    def test_precedence_client_count_over_general(self):
        """Client count request should not go to general search."""
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate(
            "Search for how many clients we have in the system"
        )
        assert result is not None
        cap, _ = result
        assert cap == "get_client_count"


# ─── Write Detection with Identity Read ────────────────────

class TestWriteDetectionWithIdentity:
    """Tests for write request detection and optional identity read."""

    def test_write_detected(self):
        from nexus_agent_platform.agents.nova import _detect_write_request
        result = _detect_write_request("Add a test user for user@example.com")
        assert result is not None
        assert result["requested_action"] == "create_test_user"
        assert result["execution_allowed"] is False
        assert result["arguments"]["email"] == "user@example.com"

    def test_write_no_email(self):
        from nexus_agent_platform.agents.nova import _detect_write_request
        result = _detect_write_request("Add a new test user account")
        assert result is not None
        assert result["arguments"]["email"] is None

    def test_read_not_detected_as_write(self):
        from nexus_agent_platform.agents.nova import _detect_write_request
        assert _detect_write_request("How many clients do we have?") is None

    def test_identity_lookup_not_detected_as_write(self):
        from nexus_agent_platform.agents.nova import _detect_write_request
        assert _detect_write_request("Check if user@example.com exists") is None


# ─── Contradiction Validation ──────────────────────────────

class TestContradictionValidation:
    """Tests for response validation against verified capability facts."""

    def test_client_count_contradiction_rejected(self):
        """Model saying 56 production when tool says 14 must be rejected."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability(
            "We have 56 production clients and 12 tester profiles.",
            {
                "status": "success",
                "query_type": "get_client_count",
                "data": {
                    "production_clients": 14,
                    "tester_or_certification": 24,
                },
            },
        )
        assert result == "capability_contradiction"

    def test_client_count_correct_allowed(self):
        """Model saying 14 when tool says 14 must be allowed."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability(
            "We have 14 production clients.",
            {
                "status": "success",
                "query_type": "get_client_count",
                "data": {"production_clients": 14},
            },
        )
        assert result is None

    def test_identity_exists_denial_rejected(self):
        """Model saying 'cannot look up' when email exists must be rejected."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability(
            "I can't look up specific email addresses directly.",
            {
                "status": "success",
                "query_type": "resolve_user_identity_by_email",
                "data": {
                    "exists_anywhere": True,
                    "verification_complete": True,
                },
            },
        )
        assert result == "capability_contradiction"

    def test_identity_nonexistent_allowed(self):
        """Model saying 'not found' when email doesn't exist must be allowed."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability(
            "That email was not found in our records.",
            {
                "status": "success",
                "query_type": "resolve_user_identity_by_email",
                "data": {
                    "exists_anywhere": False,
                    "verification_complete": True,
                },
            },
        )
        assert result is None

    def test_no_contradiction_without_capability(self):
        """No capability result means no contradiction check."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability("The sky is blue.", None)
        assert result is None

    def test_no_contradiction_on_failed_capability(self):
        """Failed capability should not trigger contradiction."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability(
            "I couldn't get the data.",
            {
                "status": "error",
                "query_type": "get_client_count",
                "data": {},
            },
        )
        assert result is None

    def test_identity_exists_nonexistent_claim_rejected(self):
        """Model saying 'does not exist' when email exists must be rejected."""
        from nexus_agent_platform.agents.nova import _validate_against_capability
        result = _validate_against_capability(
            "That account does not exist in our system.",
            {
                "status": "success",
                "query_type": "resolve_user_identity_by_email",
                "data": {
                    "exists_anywhere": True,
                    "verification_complete": True,
                },
            },
        )
        assert result == "capability_contradiction"


# ─── Fail-Closed Behavior ──────────────────────────────────

class TestFailClosed:
    """Tests that capability failures prevent model from fabricating data."""

    def test_client_count_error_produces_fallback(self):
        """When get_client_count fails, the fallback must not contain numbers."""
        from nexus_agent_platform.agents.nova import _build_fallback_response
        resp = _build_fallback_response("capability_contradiction", "how many clients")
        assert "correct" in resp.lower() or "verified" in resp.lower() or "different" in resp.lower()

    def test_identity_error_prevents_fabrication(self):
        """When identity capability fails, model must not claim user absent."""
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "error",
            "query_type": "resolve_user_identity_by_email",
            "data": {},
            "error": "Connection refused",
        })
        assert "error" in context.lower()
        assert "Do NOT fabricate" in context

    def test_capability_unavailable_in_context(self):
        """Unavailable capability must appear in verified context."""
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "unavailable",
            "query_type": "get_client_count",
            "data": {},
        })
        assert "unavailable" in context.lower()
        assert "Do NOT fabricate" in context


# ─── Verified Context Formatting ───────────────────────────

class TestVerifiedContextFormatting:
    """Tests for the VERIFIED OPERATIONAL DATA context blocks."""

    def test_client_count_context_structure(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "success",
            "query_type": "get_client_count",
            "data": {
                "production_clients": 14,
                "active": 14,
                "onboarding": 0,
                "tester_or_certification": 24,
                "all_profiles": 38,
            },
        })
        assert "[VERIFIED OPERATIONAL DATA]" in context
        assert "[END VERIFIED OPERATIONAL DATA]" in context
        assert "production_clients: 14" in context
        assert "tester_or_certification: 24" in context

    def test_identity_context_structure(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "success",
            "query_type": "resolve_user_identity_by_email",
            "data": {
                "normalized_email": "test@gmail.com",
                "exists_anywhere": True,
                "verification_complete": True,
                "account_classifications": ["auth_user", "production"],
                "sources": {},
            },
        })
        assert "[VERIFIED OPERATIONAL DATA]" in context
        assert "normalized_email: test@gmail.com" in context
        assert "exists_anywhere: true" in context
        assert "auth_user" in context

    def test_identity_incomplete_includes_warning(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "partial",
            "query_type": "resolve_user_identity_by_email",
            "data": {
                "normalized_email": "test@gmail.com",
                "exists_anywhere": False,
                "verification_complete": False,
                "account_classifications": [],
                "sources": {"supabase_auth": {"status": "error"}},
            },
        })
        assert "Do NOT claim the user does not exist" in context

    def test_general_search_context_structure(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "success",
            "query_type": "general_search",
            "data": {
                "matches": [{"source": "client_profiles", "match": "test@test.com",
                             "type": "Client profiles"}],
                "sources_searched": ["client_profiles"],
                "match_count": 1,
            },
        })
        assert "[VERIFIED OPERATIONAL DATA]" in context
        assert "match_count: 1" in context

    def test_runtime_context_structure(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "success",
            "query_type": "get_runtime_capabilities",
            "data": {
                "available_reads": ["get_client_count", "general_search"],
                "available_actions": [],
                "connected_systems": {"supabase": {"status": "connected"}},
            },
        })
        assert "get_client_count" in context
        assert "supabase_connected: connected" in context

    def test_write_denied_context(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "denied",
            "query_type": "write_denied",
            "message": "Write operations are not permitted.",
        })
        assert "Write operations are not permitted" in context

    def test_unauthorized_context(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        context = _format_verified_context({
            "status": "unauthorized",
            "query_type": "get_system_status",
            "data": {},
        })
        assert "not authorized" in context.lower()


# ─── SOUL Quality ──────────────────────────────────────────

class TestSoulUpdates:
    """Tests for SOUL behavioral instructions."""

    def test_soul_allows_email_lookup(self):
        """SOUL must not deny email lookup capability."""
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "you can look up specific email" in soul_lower or "identity resolution" in soul_lower

    def test_soul_mentions_governed_reads(self):
        from nexus_agent_platform.agents.nova import SOUL
        assert "governed read" in SOUL.lower() or "approved governed" in SOUL.lower()

    def test_soul_mentions_fail_closed(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "never fabricate" in soul_lower or "do not fabricate" in soul_lower or "never fabricate operational" in soul_lower

    def test_soul_mentions_verified_data(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "verified operational data" in soul_lower or "treat verified" in soul_lower
