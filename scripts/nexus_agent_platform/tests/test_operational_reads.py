"""Tests for Hermes Nova operational read expansion.

Covers: system health, pending approvals, recent research, opportunities,
client profile, funding readiness, operational summary, provenance hardening,
provenance follow-up, semantic routing, truth guard, and security.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ─── System Health ──────────────────────────────────────────

class TestSystemHealth:
    """Tests for get_system_health shared handler."""

    def test_healthy_system(self):
        from nexus_agent_platform.capabilities.shared import _handle_system_health
        with patch("nexus_agent_platform.agents.hermes._get_system_status",
                    return_value={"working": "5/5 processes active", "needs_attention": "", "detail": ""}), \
             patch("nexus_agent_platform.agents.hermes._get_failure_report",
                    return_value={"working": "No failures recorded today", "needs_attention": "", "detail": ""}), \
             patch("nexus_agent_platform.agents.hermes._get_process_failures",
                    return_value={"status": "ok", "total": 0, "by_status": {}, "failures": []}):
            result = _handle_system_health(trace_id="test_health_1")
        assert result["status"] == "success"
        assert result["capability"] == "get_system_health"
        data = result["data"]
        assert data["overall_status"] == "healthy"
        assert data["active_services"] == 5
        assert data["failed_services"] == 0
        assert result["provenance"]["trace_id"] == "test_health_1"

    def test_degraded_system(self):
        from nexus_agent_platform.capabilities.shared import _handle_system_health
        with patch("nexus_agent_platform.agents.hermes._get_system_status",
                    return_value={"working": "3/5 processes active", "needs_attention": "", "detail": ""}), \
             patch("nexus_agent_platform.agents.hermes._get_failure_report",
                    return_value={"working": "No failures recorded today", "needs_attention": "", "detail": ""}), \
             patch("nexus_agent_platform.agents.hermes._get_process_failures",
                    return_value={"status": "ok", "total": 2, "by_status": {"FAILED": 2}, "failures": []}):
            result = _handle_system_health(trace_id="test_health_2")
        data = result["data"]
        assert data["overall_status"] == "degraded"
        assert data["failed_services"] == 2

    def test_failure_present(self):
        from nexus_agent_platform.capabilities.shared import _handle_system_health
        with patch("nexus_agent_platform.agents.hermes._get_system_status",
                    return_value={"working": "4/5 processes active", "needs_attention": "Process X down", "detail": "- Process X: failed"}), \
             patch("nexus_agent_platform.agents.hermes._get_failure_report",
                    return_value={"working": "1 failures today", "needs_attention": "API timeout", "detail": ""}), \
             patch("nexus_agent_platform.agents.hermes._get_process_failures",
                    return_value={"status": "ok", "total": 1, "by_status": {"FAILED": 1}, "failures": []}):
            result = _handle_system_health(trace_id="test_health_3")
        data = result["data"]
        assert data["overall_status"] == "degraded"
        assert len(data["recent_failures"]) > 0

    def test_unavailable_source(self):
        from nexus_agent_platform.capabilities.shared import _handle_system_health
        with patch("nexus_agent_platform.agents.hermes._get_system_status",
                    side_effect=Exception("file not found")), \
             patch("nexus_agent_platform.agents.hermes._get_failure_report",
                    side_effect=Exception("file not found")), \
             patch("nexus_agent_platform.agents.hermes._get_process_failures",
                    side_effect=Exception("supabase down")):
            result = _handle_system_health(trace_id="test_health_4")
        data = result["data"]
        assert data["overall_status"] == "unknown"
        assert len(data["important_warnings"]) > 0

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        for q in ["How is Nexus doing today?", "Is the system healthy?", "Anything broken?", "What needs attention?", "Is anything down?"]:
            gate = _semantic_capability_gate(q)
            assert gate is not None, f"Failed for: {q}"
            assert gate[0] == "get_system_health", f"Wrong cap for: {q}"


# ─── Pending Approvals ─────────────────────────────────────

class TestPendingApprovals:
    """Tests for get_pending_approvals shared handler."""

    def test_zero_pending(self):
        from nexus_agent_platform.capabilities.shared import _handle_pending_approvals
        with patch("nexus_agent_platform.agents.hermes._get_pending_approvals",
                    return_value={"status": "ok", "total": 5, "pending_count": 0, "items": []}):
            result = _handle_pending_approvals(trace_id="test_a1")
        assert result["status"] == "success"
        assert result["data"]["count"] == 0
        assert result["data"]["items"] == []

    def test_one_pending(self):
        from nexus_agent_platform.capabilities.shared import _handle_pending_approvals
        items = [{"id": "a1", "type": "email", "title": "Review email draft", "created_at": "2026-01-01"}]
        with patch("nexus_agent_platform.agents.hermes._get_pending_approvals",
                    return_value={"status": "ok", "total": 3, "pending_count": 1, "items": items}):
            result = _handle_pending_approvals(trace_id="test_a2")
        assert result["data"]["count"] == 1
        assert result["data"]["items"][0]["title"] == "Review email draft"

    def test_multiple_pending(self):
        from nexus_agent_platform.capabilities.shared import _handle_pending_approvals
        items = [
            {"id": "a1", "type": "email", "title": "Review email", "created_at": "2026-01-01"},
            {"id": "a2", "type": "report", "title": "Approve report", "created_at": "2026-01-02"},
            {"id": "a3", "type": "work_order", "title": "New work order", "created_at": "2026-01-03"},
        ]
        with patch("nexus_agent_platform.agents.hermes._get_pending_approvals",
                    return_value={"status": "ok", "total": 3, "pending_count": 3, "items": items}):
            result = _handle_pending_approvals(trace_id="test_a3")
        assert result["data"]["count"] == 3

    def test_unavailable(self):
        from nexus_agent_platform.capabilities.shared import _handle_pending_approvals
        with patch("nexus_agent_platform.agents.hermes._get_pending_approvals",
                    return_value={"status": "unavailable", "error": "File not found"}):
            result = _handle_pending_approvals(trace_id="test_a4")
        assert result["status"] == "unavailable"
        assert result["data"]["count"] == 0

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        for q in ["Do I have anything to approve?", "What approvals are waiting on me?", "What needs Ray Review?"]:
            gate = _semantic_capability_gate(q)
            assert gate is not None, f"Failed for: {q}"
            assert gate[0] == "get_pending_approvals", f"Wrong cap for: {q}"


# ─── Recent Research ───────────────────────────────────────

class TestRecentResearch:
    """Tests for get_recent_research shared handler."""

    def test_recent_results(self):
        from nexus_agent_platform.capabilities.shared import _handle_recent_research
        raw = {
            "status": "ok",
            "runs": {"total": 5, "completed": 3, "failed": 1, "items": [
                {"id": "r1", "query": "market analysis", "status": "completed", "category": "business", "created_at": "2026-01-01", "completed_at": "2026-01-01"},
            ]},
            "results": {"total": 10, "items": [
                {"id": "res1", "run_id": "r1", "source": "web", "title": "Market Trends 2026", "url": "http://example.com", "created_at": "2026-01-01"},
            ]},
        }
        with patch("nexus_agent_platform.agents.hermes._get_research_history", return_value=raw):
            result = _handle_recent_research(trace_id="test_r1")
        assert result["status"] == "success"
        assert result["data"]["runs"]["total"] == 5
        assert result["data"]["results"]["total"] == 10

    def test_none(self):
        from nexus_agent_platform.capabilities.shared import _handle_recent_research
        raw = {"status": "ok", "runs": {"total": 0, "completed": 0, "items": []}, "results": {"total": 0, "items": []}}
        with patch("nexus_agent_platform.agents.hermes._get_research_history", return_value=raw):
            result = _handle_recent_research(trace_id="test_r2")
        assert result["data"]["runs"]["total"] == 0

    def test_unavailable(self):
        from nexus_agent_platform.capabilities.shared import _handle_recent_research
        with patch("nexus_agent_platform.agents.hermes._get_research_history",
                    return_value={"status": "unavailable", "error": "Supabase not configured"}):
            result = _handle_recent_research(trace_id="test_r3")
        assert result["status"] == "unavailable"

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        for q in ["What research came in recently?", "Any new research?", "What has Alpha been researching?"]:
            gate = _semantic_capability_gate(q)
            assert gate is not None, f"Failed for: {q}"
            assert gate[0] == "get_recent_research", f"Wrong cap for: {q}"


# ─── Opportunities ─────────────────────────────────────────

class TestOpportunities:
    """Tests for get_opportunities shared handler."""

    def test_available(self):
        from nexus_agent_platform.capabilities.shared import _handle_opportunities
        raw = {"status": "ok", "total": 3, "by_state": {"active": 2, "reviewed": 1, "rejected": 0},
               "opportunities": [{"id": "o1", "title": "Credit repair partnership", "status": "open", "revenue_potential": "high", "action_state": "active", "updated_at": "2026-01-01"}]}
        with patch("nexus_agent_platform.agents.hermes._get_opportunities", return_value=raw):
            result = _handle_opportunities(trace_id="test_o1")
        assert result["status"] == "success"
        assert result["data"]["total"] == 3
        assert result["data"]["items"][0]["title"] == "Credit repair partnership"

    def test_none(self):
        from nexus_agent_platform.capabilities.shared import _handle_opportunities
        raw = {"status": "ok", "total": 0, "by_state": {}, "opportunities": []}
        with patch("nexus_agent_platform.agents.hermes._get_opportunities", return_value=raw):
            result = _handle_opportunities(trace_id="test_o2")
        assert result["data"]["total"] == 0

    def test_unavailable(self):
        from nexus_agent_platform.capabilities.shared import _handle_opportunities
        with patch("nexus_agent_platform.agents.hermes._get_opportunities",
                    return_value={"status": "unavailable", "error": "Supabase not configured"}):
            result = _handle_opportunities(trace_id="test_o3")
        assert result["status"] == "unavailable"

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        for q in ["What opportunities do we have?", "Any opportunities worth looking at?", "Show current opportunities."]:
            gate = _semantic_capability_gate(q)
            assert gate is not None, f"Failed for: {q}"
            assert gate[0] == "get_opportunities", f"Wrong cap for: {q}"


# ─── Client Profile ────────────────────────────────────────

class TestClientProfile:
    """Tests for get_client_profile shared handler."""

    def _mock_session(self):
        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        return session

    def test_exact_email_found(self):
        from nexus_agent_platform.capabilities.shared import _handle_client_profile
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [{
            "id": "c1", "client_label": "test@example.com", "status": "active",
            "source": "manual", "tenant_id": "goclear", "business_name": "Test Co",
            "legal_name": "Test Company LLC", "onboarding_step": "complete",
            "created_at": "2026-01-01", "updated_at": "2026-01-01",
        }]
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_client_profile({"email": "test@example.com"}, trace_id="test_p1")
        assert result["status"] == "success"
        assert result["data"]["found"] is True
        assert result["data"]["ambiguous"] is False
        assert result["data"]["classification"] == "production"
        assert result["data"]["status"] == "active"

    def test_not_found(self):
        from nexus_agent_platform.capabilities.shared import _handle_client_profile
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = []
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_client_profile({"email": "nobody@example.com"}, trace_id="test_p2")
        assert result["data"]["found"] is False

    def test_ambiguous(self):
        from nexus_agent_platform.capabilities.shared import _handle_client_profile
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [
            {"id": "c1", "client_label": "test@example.com", "status": "active", "source": "manual", "tenant_id": "goclear"},
            {"id": "c2", "client_label": "test@example.com", "status": "inactive", "source": "import", "tenant_id": "tenant_demo_1"},
        ]
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_client_profile({"email": "test@example.com"}, trace_id="test_p3")
        assert result["data"]["ambiguous"] is True
        assert result["data"]["match_count"] == 2

    def test_unauthorized_fields_excluded(self):
        from nexus_agent_platform.capabilities.shared import _handle_client_profile
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [{
            "id": "c1", "client_label": "test@example.com", "status": "active",
            "source": "manual", "tenant_id": "goclear", "business_name": "Test Co",
            "legal_name": "Test Co", "onboarding_step": "complete",
            "created_at": "2026-01-01", "updated_at": "2026-01-01",
        }]
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_client_profile({"email": "test@example.com"}, trace_id="test_p4")
        data = result["data"]
        assert "ssn" not in data
        assert "bank_details" not in data
        assert "credit_report" not in data

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        gate = _semantic_capability_gate("Pull up this client test@example.com")
        assert gate is not None
        assert gate[0] == "get_client_profile"
        gate = _semantic_capability_gate("Tell me about test@example.com")
        assert gate is not None
        assert gate[0] == "get_client_profile"


# ─── Funding Readiness ─────────────────────────────────────

class TestFundingReadiness:
    """Tests for get_funding_readiness shared handler."""

    def _mock_session(self):
        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        return session

    def test_ready(self):
        from nexus_agent_platform.capabilities.shared import _handle_funding_readiness
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [{
            "id": "c1", "client_label": "test@example.com", "status": "active",
            "source": "manual", "tenant_id": "goclear", "onboarding_step": "complete",
            "business_name": "Test Co", "created_at": "2026-01-01",
        }]
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_funding_readiness({"email": "test@example.com"}, trace_id="test_f1")
        assert result["status"] == "success"
        assert result["data"]["funding_readiness_status"] == "ready"

    def test_not_ready(self):
        from nexus_agent_platform.capabilities.shared import _handle_funding_readiness
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [{
            "id": "c1", "client_label": "test@example.com", "status": "inactive",
            "source": "manual", "tenant_id": "goclear", "onboarding_step": "",
            "business_name": "Test Co", "created_at": "2026-01-01",
        }]
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_funding_readiness({"email": "test@example.com"}, trace_id="test_f2")
        assert result["data"]["funding_readiness_status"] == "not_ready"
        assert len(result["data"]["blocking_items"]) > 0

    def test_partial(self):
        from nexus_agent_platform.capabilities.shared import _handle_funding_readiness
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [{
            "id": "c1", "client_label": "test@example.com", "status": "active",
            "source": "manual", "tenant_id": "goclear", "onboarding_step": "docs_pending",
            "business_name": "Test Co", "created_at": "2026-01-01",
        }]
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_funding_readiness({"email": "test@example.com"}, trace_id="test_f3")
        assert result["data"]["funding_readiness_status"] == "almost_ready"
        assert len(result["data"]["missing_requirements"]) > 0

    def test_client_not_found(self):
        from nexus_agent_platform.capabilities.shared import _handle_funding_readiness
        session = self._mock_session()
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = []
        session.get.return_value = mock_resp
        with patch("nexus_agent_platform.capabilities.shared._supabase_session", return_value=session):
            result = _handle_funding_readiness({"email": "nobody@example.com"}, trace_id="test_f4")
        assert result["data"]["funding_readiness_status"] == "not_found"

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        gate = _semantic_capability_gate("What's the funding readiness for test@example.com?")
        assert gate is not None
        assert gate[0] == "get_funding_readiness"
        gate = _semantic_capability_gate("Is this client funding ready test@example.com?")
        assert gate is not None
        assert gate[0] == "get_funding_readiness"


# ─── Operational Summary ───────────────────────────────────

class TestOperationalSummary:
    """Tests for get_operational_summary aggregator."""

    def test_all_success(self):
        from nexus_agent_platform.capabilities.shared import _handle_operational_summary
        with patch("nexus_agent_platform.capabilities.shared._handle_system_health",
                    return_value={"status": "success", "data": {"overall_status": "healthy", "active_services": 5, "failed_services": 0}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_client_count",
                    return_value={"status": "success", "data": {"production_clients": 14, "tester_or_certification": 24}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_pending_approvals",
                    return_value={"status": "success", "data": {"count": 2}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_recent_research",
                    return_value={"status": "success", "data": {"runs": {"total": 5}}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_opportunities",
                    return_value={"status": "success", "data": {"total": 3, "by_state": {"active": 2}}}):
            result = _handle_operational_summary(trace_id="test_s1")
        assert result["status"] == "success"
        assert result["capability"] == "get_operational_summary"
        data = result["data"]
        assert data["system_health"]["status"] == "success"
        assert data["client_counts"]["status"] == "success"
        assert data["pending_approvals"]["status"] == "success"

    def test_partial_failure(self):
        from nexus_agent_platform.capabilities.shared import _handle_operational_summary
        with patch("nexus_agent_platform.capabilities.shared._handle_system_health",
                    return_value={"status": "success", "data": {"overall_status": "healthy"}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_client_count",
                    side_effect=Exception("fail")), \
             patch("nexus_agent_platform.capabilities.shared._handle_pending_approvals",
                    return_value={"status": "success", "data": {"count": 0}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_recent_research",
                    return_value={"status": "success", "data": {"runs": {"total": 0}}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_opportunities",
                    return_value={"status": "success", "data": {"total": 0}}):
            result = _handle_operational_summary(trace_id="test_s2")
        assert result["status"] == "partial"
        assert result["data"]["client_counts"]["status"] == "unavailable"

    def test_preserves_provenance_by_component(self):
        from nexus_agent_platform.capabilities.shared import _handle_operational_summary
        with patch("nexus_agent_platform.capabilities.shared._handle_system_health",
                    return_value={"status": "success", "data": {}, "provenance": {"capability": "get_system_health"}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_client_count",
                    return_value={"status": "success", "data": {}, "provenance": {"capability": "get_client_count"}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_pending_approvals",
                    return_value={"status": "success", "data": {}, "provenance": {"capability": "get_pending_approvals"}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_recent_research",
                    return_value={"status": "success", "data": {}, "provenance": {"capability": "get_recent_research"}}), \
             patch("nexus_agent_platform.capabilities.shared._handle_opportunities",
                    return_value={"status": "success", "data": {}, "provenance": {"capability": "get_opportunities"}}):
            result = _handle_operational_summary(trace_id="test_s3")
        prov = result["provenance"]
        assert "components_requested" in prov
        assert len(prov["components_requested"]) == 5

    def test_semantic_routing(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        for q in ["What needs my attention today?", "Give me a Nexus status update", "What's going on with the business?", "Give me today's Nexus briefing."]:
            gate = _semantic_capability_gate(q)
            assert gate is not None, f"Failed for: {q}"
            assert gate[0] == "get_operational_summary", f"Wrong cap for: {q}"


# ─── Provenance ────────────────────────────────────────────

class TestProvenance:
    """Tests for provenance hardening and follow-up."""

    def test_provenance_persistence(self):
        from nexus_agent_platform.agents.nova import save_provenance, load_provenance, _clear_provenance
        prov = {
            "capability": "get_client_count",
            "status": "success",
            "source": "supabase",
            "freshness": "live",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "handler": "hermes._get_client_count",
        }
        save_provenance(99999, prov)
        loaded = load_provenance(99999)
        assert loaded is not None
        assert loaded["capability"] == "get_client_count"
        _clear_provenance(99999)
        assert load_provenance(99999) is None

    def test_provenance_followup_detection(self):
        from nexus_agent_platform.agents.nova import _detect_provenance_followup
        assert _detect_provenance_followup("Where did you get those numbers?") is True
        assert _detect_provenance_followup("Was that live?") is True
        assert _detect_provenance_followup("Which capability did you use?") is True
        assert _detect_provenance_followup("When did you retrieve it?") is True
        assert _detect_provenance_followup("How fresh is that data?") is True
        assert _detect_provenance_followup("Did that come directly from Supabase?") is True
        assert _detect_provenance_followup("What do you think about Cadillac SUVs?") is False
        assert _detect_provenance_followup("Tell me a joke") is False

    def test_provenance_format(self):
        from nexus_agent_platform.agents.nova import _format_provenance_context
        prov = {
            "capability": "get_client_count",
            "status": "success",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "live",
            "retrieved_at": "2026-08-10T12:00:00Z",
            "handler": "hermes._get_client_count",
        }
        ctx = _format_provenance_context(prov)
        assert "get_client_count" in ctx
        assert "supabase" in ctx
        assert "live" in ctx
        assert "2026-08-10T12:00:00Z" in ctx

    def test_provenance_empty(self):
        from nexus_agent_platform.agents.nova import _format_provenance_context
        ctx = _format_provenance_context(None)
        assert "no_recent_capability" in ctx

    def test_semantic_routing_provenance(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        gate = _semantic_capability_gate("Where did you get those numbers?")
        assert gate is None  # provenance follow-up is handled in _capability_gate, not semantic gate


# ─── Truth Guard ───────────────────────────────────────────

class TestTruthGuard:
    """Tests for truth guard preventing fabrication."""

    def test_client_count_contradiction(self):
        from nexus_agent_platform.agents.nova import _validate_against_capability
        cap_result = {
            "status": "success",
            "query_type": "get_client_count",
            "data": {"production_clients": 14, "tester_or_certification": 24},
        }
        # Model claiming different numbers
        err = _validate_against_capability("We have 500 production clients", cap_result)
        assert err == "capability_contradiction"

    def test_identity_contradiction(self):
        from nexus_agent_platform.agents.nova import _validate_against_capability
        cap_result = {
            "status": "success",
            "query_type": "resolve_user_identity_by_email",
            "data": {"exists_anywhere": True, "verification_complete": True},
        }
        err = _validate_against_capability("That email does not exist in our system", cap_result)
        assert err == "capability_contradiction"

    def test_no_contradiction_on_success(self):
        from nexus_agent_platform.agents.nova import _validate_against_capability
        cap_result = {
            "status": "success",
            "query_type": "get_client_count",
            "data": {"production_clients": 14, "tester_or_certification": 24},
        }
        err = _validate_against_capability("We have 14 production clients", cap_result)
        assert err is None


# ─── No-Tool ───────────────────────────────────────────────

class TestNoTool:
    """Tests that casual/non-operational questions don't trigger capabilities."""

    def test_opinion_question(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        assert _semantic_capability_gate("What do you think about buying real estate?") is None
        assert _semantic_capability_gate("Why is the sky blue?") is None
        assert _semantic_capability_gate("Tell me a joke") is None
        assert _semantic_capability_gate("What do you think about Cadillac SUVs?") is None
        assert _semantic_capability_gate("How are you today?") is None


# ─── Permissions ───────────────────────────────────────────

class TestPermissions:
    """Tests for permission enforcement on new capabilities."""

    def test_nova_has_zero_writes(self):
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_WRITES
        assert len(NOVA_ALLOWED_WRITES) == 0

    def test_nova_new_reads_allowed(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        for cap in ["get_system_health", "get_pending_approvals", "get_recent_research",
                     "get_opportunities", "get_client_profile", "get_funding_readiness",
                     "get_operational_summary"]:
            assert _check_permission("hermes_nova", cap, is_write=False) is None

    def test_nova_write_denied_for_all_new(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        for cap in ["get_system_health", "get_pending_approvals", "get_recent_research",
                     "get_opportunities", "get_client_profile", "get_funding_readiness",
                     "get_operational_summary"]:
            err = _check_permission("hermes_nova", cap, is_write=True)
            assert err is not None

    def test_arbitrary_capability_rejected(self):
        from nexus_agent_platform.capabilities.shared import _check_permission
        err = _check_permission("hermes_nova", "drop_table", is_write=False)
        assert err is not None

    def test_prompt_injection_cannot_call_writes(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability(
            "hermes_nova",
            "create_test_user",
            {"email": "evil@hacker.com"},
            trace_id="test_injection",
        )
        assert result["status"] == "unauthorized"

    def test_no_direct_supabase_in_nova(self):
        """Verify nova.py does not import or use supabase directly."""
        import nexus_agent_platform.agents.nova as nova_mod
        source = open(nova_mod.__file__).read()
        assert "supabase_client()" not in source
        assert "requests.Session" not in source
        assert "SUPABASE_URL" not in source
        assert "SUPABASE_SERVICE_ROLE_KEY" not in source


# ─── Context Formatting ────────────────────────────────────

class TestContextFormatting:
    """Tests for _format_verified_context with new capabilities."""

    def test_system_health_format(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        result = {
            "query_type": "get_system_health",
            "status": "success",
            "data": {"overall_status": "healthy", "active_services": 5, "degraded_services": 0, "failed_services": 0, "recent_failures": [], "important_warnings": [], "sources_checked": ["process_registry"]},
        }
        ctx = _format_verified_context(result)
        assert "get_system_health" in ctx
        assert "healthy" in ctx
        assert "5" in ctx

    def test_pending_approvals_format(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        result = {
            "query_type": "get_pending_approvals",
            "status": "success",
            "data": {"count": 2, "items": [{"type": "email", "title": "Review", "created_at": "2026-01-01"}]},
        }
        ctx = _format_verified_context(result)
        assert "get_pending_approvals" in ctx
        assert "2" in ctx

    def test_client_profile_format(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        result = {
            "query_type": "get_client_profile",
            "status": "success",
            "data": {"found": True, "ambiguous": False, "status": "active", "classification": "production", "onboarding_step": "complete", "client_id": "c1", "business_name": "Test Co"},
        }
        ctx = _format_verified_context(result)
        assert "get_client_profile" in ctx
        assert "active" in ctx
        assert "production" in ctx

    def test_funding_readiness_format(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        result = {
            "query_type": "get_funding_readiness",
            "status": "success",
            "data": {"client_identifier": "test@example.com", "client_found": True, "funding_readiness_status": "almost_ready", "missing_requirements": ["Documents needed"], "blocking_items": [], "next_recommended_steps": ["Upload docs"]},
        }
        ctx = _format_verified_context(result)
        assert "get_funding_readiness" in ctx
        assert "almost_ready" in ctx
        assert "Documents needed" in ctx

    def test_operational_summary_format(self):
        from nexus_agent_platform.agents.nova import _format_verified_context
        result = {
            "query_type": "get_operational_summary",
            "status": "success",
            "data": {
                "system_health": {"data": {"overall_status": "healthy", "active_services": 5}},
                "client_counts": {"data": {"production_clients": 14, "tester_or_certification": 24}},
                "pending_approvals": {"data": {"count": 2}},
                "recent_research": {"data": {"runs": {"total": 5}}},
                "opportunities": {"data": {"total": 3, "by_state": {"active": 2}}},
            },
        }
        ctx = _format_verified_context(result)
        assert "get_operational_summary" in ctx
        assert "healthy" in ctx
        assert "14" in ctx
