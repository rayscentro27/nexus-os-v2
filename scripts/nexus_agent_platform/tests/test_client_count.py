"""Tests for the Supabase-backed client count capability.

Verifies that _get_client_count queries client_profiles, applies production
tenant filtering, excludes demo/certification/tester records, and never
reads the process registry.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.agents.hermes import (
    _get_client_count, _PRODUCTION_TENANT, _NON_PRODUCTION_TENANT_PREFIXES,
    _TESTER_SOURCES,
)


class TestClientCountNeverUsesRegistry:
    """The process registry must never be consulted for client counts."""

    def test_no_json_load_in_client_count(self):
        """_get_client_count must not open nexus_process_registry.json."""
        import ast
        source_path = os.path.join(
            os.path.dirname(__file__), "..", "agents", "hermes.py"
        )
        with open(source_path) as f:
            tree = ast.parse(f.read())
        # Find the _get_client_count function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_get_client_count":
                func_source = ast.get_source_segment(
                    open(source_path).read(), node
                )
                assert "nexus_process_registry" not in func_source, (
                    "_get_client_count must not reference the process registry"
                )
                assert "json.load" not in func_source, (
                    "_get_client_count must not use json.load"
                )
                break
        else:
            pytest.fail("_get_client_count function not found")


class TestClientCountProductionFilter:
    """Production tenant filtering must work correctly."""

    def _mock_response(self, rows, status_code=200):
        mock = MagicMock()
        mock.ok = status_code == 200
        mock.status_code = status_code
        mock.json.return_value = rows
        return mock

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_production_tenant_only(self, mock_client):
        """Only goclear tenant with non-tester source counts as production."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "onboarding", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "tenant_demo_goclear", "status": "active", "client_visible": False, "source": "static_import"},
            {"tenant_id": "tenant-cert-persona-a", "status": "active", "client_visible": True, "source": "synthetic_certification"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 2
        assert result["active"] == 1
        assert result["onboarding"] == 1
        assert result["tester_or_certification"] == 2

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_demo_tenant_excluded(self, mock_client):
        """tenant_demo_* records are excluded from production count."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "tenant_demo_goclear", "status": "active", "client_visible": False, "source": "static_import"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 0
        assert result["tester_or_certification"] == 1

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_certification_tenants_excluded(self, mock_client):
        """tenant-cert-* records are excluded from production count."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "tenant-cert-persona-a", "status": "active", "client_visible": True, "source": "synthetic_certification"},
            {"tenant_id": "tenant-cert-persona-b", "status": "active", "client_visible": True, "source": "synthetic_certification"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 0
        assert result["tester_or_certification"] == 2

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_tester_invitation_excluded(self, mock_client):
        """tester_invitation source in production tenant is excluded."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "onboarding", "client_visible": True, "source": "tester_invitation"},
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 1
        assert result["tester_or_certification"] == 1


class TestClientCountStatusGrouping:
    """Status grouping must categorize profiles correctly."""

    def _mock_response(self, rows, status_code=200):
        mock = MagicMock()
        mock.ok = status_code == 200
        mock.status_code = status_code
        mock.json.return_value = rows
        return mock

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_active_vs_onboarding(self, mock_client):
        """Active and onboarding statuses are grouped separately."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "onboarding", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 3
        assert result["active"] == 2
        assert result["onboarding"] == 1

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_unknown_status_goes_to_inactive(self, mock_client):
        """Unrecognized status values count as inactive."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "paused", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": None, "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "", "client_visible": True, "source": "goclear_signup"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 3
        assert result["inactive"] == 3

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_hidden_profiles_counted(self, mock_client):
        """Hidden profiles (client_visible=false) are counted separately."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "active", "client_visible": False, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 2
        assert result["hidden"] == 1


class TestClientCountErrorHandling:
    """Error conditions must be handled gracefully."""

    def test_missing_credentials(self):
        """Missing Supabase credentials returns error dict."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SUPABASE_URL", None)
            os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            result = _get_client_count()
            assert result["error"] is not None
            assert result["production_total"] == 0

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_supabase_failure(self, mock_client):
        """Supabase HTTP error returns error dict."""
        session = MagicMock()
        mock_client.return_value = session
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        session.get.return_value = mock_response
        result = _get_client_count()
        assert result["error"] is not None
        assert "401" in result["error"]

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_network_error(self, mock_client):
        """Network error returns error dict."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.side_effect = ConnectionError("timeout")
        result = _get_client_count()
        assert result["error"] is not None
        assert "timeout" in result["error"]


class TestClientCountNoPII:
    """Output must never contain client PII."""

    def _mock_response(self, rows, status_code=200):
        mock = MagicMock()
        mock.ok = status_code == 200
        mock.status_code = status_code
        mock.json.return_value = rows
        return mock

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_no_names_in_output(self, mock_client):
        """Result dict must not contain client names or labels."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
        ])
        result = _get_client_count()
        result_str = json.dumps(result)
        assert "Julius" not in result_str
        assert "client_label" not in result_str
        assert "legal_name" not in result_str
        assert "phone" not in result_str
        assert "email" not in result_str

    @patch("nexus_agent_platform.agents.hermes._supabase_client")
    def test_no_hardcoded_count(self, mock_client):
        """Result must reflect actual query, not a hard-coded number."""
        session = MagicMock()
        mock_client.return_value = session
        session.get.return_value = self._mock_response([
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "goclear_signup"},
        ])
        result = _get_client_count()
        assert result["production_total"] == 3
        assert result["all_profiles"] == 3


class TestClientCountVsAcquisition:
    """Client count must not trigger acquisition advice."""

    def test_count_intent_metadata(self):
        """client_count intent uses get_client_count capability."""
        from nexus_agent_platform.agents.hermes import _classify_intent
        assert _classify_intent("how many clients do we have?") == "client_count"
        assert _classify_intent("client count") == "client_count"
        assert _classify_intent("number of clients") == "client_count"

    def test_acquisition_not_count(self):
        """client_acquisition intent must not be client_count."""
        from nexus_agent_platform.agents.hermes import _classify_intent
        assert _classify_intent("how can we get more clients?") == "client_acquisition"
        assert _classify_intent("find new clients") == "client_acquisition"
