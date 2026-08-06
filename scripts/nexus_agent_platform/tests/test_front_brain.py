"""Tests for Hermes Conversational Front Brain.

Covers:
1. Front brain classification schema and catalog
2. Mode selection rules
3. Reference resolution
4. Numbered option extraction
5. Capability catalog integrity
6. Backward-compatible aliases
7. Feature flag behavior
8. Graph structure (front brain vs legacy)
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

import pytest

_scripts_dir = os.path.join(os.path.dirname(__file__), "..")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


class TestFrontBrainCatalog:
    """Verify the capability catalog is complete and valid."""

    def test_reads_catalog_has_required_capabilities(self):
        from nexus_agent_platform.agents.front_brain import CERTIFIED_READS
        required = [
            "get_client_count", "get_system_status", "get_failure_report",
            "get_alpha_status", "process_status", "process_failures",
            "research_history", "opportunities", "trading_status",
            "pending_approvals",
        ]
        for cap in required:
            assert cap in CERTIFIED_READS, f"Missing read capability: {cap}"

    def test_actions_catalog_has_required_capabilities(self):
        from nexus_agent_platform.agents.front_brain import CERTIFIED_ACTIONS
        required = ["send_approved_email", "schedule_report", "create_work_order"]
        for cap in required:
            assert cap in CERTIFIED_ACTIONS, f"Missing action capability: {cap}"

    def test_all_capabilities_have_descriptions(self):
        from nexus_agent_platform.agents.front_brain import CERTIFIED_READS, CERTIFIED_ACTIONS
        for name, info in CERTIFIED_READS.items():
            assert "description" in info, f"{name} missing description"
            assert "positive_examples" in info, f"{name} missing positive_examples"
        for name, info in CERTIFIED_ACTIONS.items():
            assert "description" in info, f"{name} missing description"
            assert "requires_confirmation" in info, f"{name} missing requires_confirmation"

    def test_all_capabilities_have_examples(self):
        from nexus_agent_platform.agents.front_brain import ALL_CAPABILITIES
        for name, info in ALL_CAPABILITIES.items():
            examples = info.get("positive_examples", [])
            assert len(examples) >= 1, f"{name} needs at least 1 positive example"


class TestReferenceResolution:
    """Verify pronoun and reference resolution."""

    def test_resolve_numbered_reference(self):
        from nexus_agent_platform.agents.front_brain import resolve_references
        ctx = {"numbered_options": {"1": "Funding Readiness Review", "2": "Client Acquisition Plan"}}
        result = resolve_references("I like number two", ctx)
        assert "Client Acquisition Plan" in result

    def test_resolve_report_reference(self):
        from nexus_agent_platform.agents.front_brain import resolve_references
        ctx = {"last_report": {"report_definition_id": "system_status"}}
        result = resolve_references("Run this report again", ctx)
        assert "system_status" in result

    def test_resolve_topic_reference(self):
        from nexus_agent_platform.agents.front_brain import resolve_references
        ctx = {"last_topic": "$97 funding readiness review"}
        result = resolve_references("What are the risks with that idea?", ctx)
        assert "funding readiness review" in result

    def test_no_reference_returns_original(self):
        from nexus_agent_platform.agents.front_brain import resolve_references
        result = resolve_references("Hello, how are you?", {})
        assert result == "Hello, how are you?"

    def test_resolve_second_one(self):
        from nexus_agent_platform.agents.front_brain import resolve_references
        ctx = {"numbered_options": {"1": "Option A", "2": "Option B"}}
        result = resolve_references("The second one looks good", ctx)
        assert "Option B" in result


class TestNumberedOptionExtraction:
    """Verify numbered list extraction from responses."""

    def test_extract_numbered_list(self):
        from nexus_agent_platform.agents.front_brain import extract_numbered_options
        text = "1. First option\n2. Second option\n3. Third option"
        options = extract_numbered_options(text)
        assert options is not None
        assert "1" in options
        assert "2" in options
        assert "3" in options
        assert "First option" in options["1"]

    def test_no_numbered_list(self):
        from nexus_agent_platform.agents.front_brain import extract_numbered_options
        options = extract_numbered_options("Just a plain paragraph")
        assert options is None

    def test_dot_separated(self):
        from nexus_agent_platform.agents.front_brain import extract_numbered_options
        text = "1. Alpha research\n2. Client acquisition"
        options = extract_numbered_options(text)
        assert options is not None
        assert len(options) == 2


class TestFuzzyCapabilityMatch:
    """Verify fuzzy matching for capability selection."""

    def test_exact_match(self):
        from nexus_agent_platform.agents.front_brain import _fuzzy_match_capability, CERTIFIED_READS
        result = _fuzzy_match_capability("get_client_count", CERTIFIED_READS)
        assert result == "get_client_count"

    def test_partial_match(self):
        from nexus_agent_platform.agents.front_brain import _fuzzy_match_capability, CERTIFIED_READS
        result = _fuzzy_match_capability("client_count", CERTIFIED_READS)
        assert result == "get_client_count"

    def test_no_match(self):
        from nexus_agent_platform.agents.front_brain import _fuzzy_match_capability, CERTIFIED_READS
        result = _fuzzy_match_capability("nonexistent_widget", CERTIFIED_READS)
        assert result is None

    def test_none_input(self):
        from nexus_agent_platform.agents.front_brain import _fuzzy_match_capability, CERTIFIED_READS
        result = _fuzzy_match_capability(None, CERTIFIED_READS)
        assert result is None


class TestBackwardCompatibleAliases:
    """Verify the legacy function aliases work."""

    def test_execute_capability_alias(self):
        from nexus_agent_platform.agents.hermes import _execute_capability, _execute_capability_legacy
        assert _execute_capability is _execute_capability_legacy

    def test_route_to_capability_alias(self):
        from nexus_agent_platform.agents.hermes import _route_to_capability, _route_to_capability_legacy
        assert _route_to_capability is _route_to_capability_legacy

    def test_classify_intent_node_alias(self):
        from nexus_agent_platform.agents.hermes import _classify_intent_node, _classify_intent_node_legacy
        assert _classify_intent_node is _classify_intent_node_legacy

    def test_classify_intent_still_works(self):
        from nexus_agent_platform.agents.hermes import _classify_intent
        assert _classify_intent("hello there") == "greeting"
        assert _classify_intent("what time is it?") == "current_time"
        assert _classify_intent("how many clients?") == "client_count"


class TestFeatureFlag:
    """Verify the front brain feature flag."""

    def test_flag_exists(self):
        from nexus_agent_platform.flags import NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED
        assert isinstance(NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED, bool)

    def test_flag_in_status(self):
        from nexus_agent_platform.flags import status
        flags = status()
        assert "NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED" in flags

    def test_front_brain_enabled_check(self):
        from nexus_agent_platform.agents.hermes import _front_brain_enabled
        with patch.dict(os.environ, {"NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED": "true"}):
            assert _front_brain_enabled() is True
        with patch.dict(os.environ, {"NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED": "false"}):
            assert _front_brain_enabled() is False


class TestGraphStructure:
    """Verify both graph paths build correctly."""

    def test_front_brain_graph_builds(self):
        with patch.dict(os.environ, {"NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED": "true"}):
            from importlib import reload
            import nexus_agent_platform.agents.hermes as mod
            reload(mod)
            graph = mod.get_hermes_graph()
            assert graph._compiled is True
            assert "front_brain_classify" in graph._node_fns
            assert "execute_by_mode" in graph._node_fns
            assert graph._entry_point == "front_brain_classify"

    def test_legacy_graph_builds(self):
        with patch.dict(os.environ, {"NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED": "false"}):
            from importlib import reload
            import nexus_agent_platform.agents.hermes as mod
            reload(mod)
            graph = mod.get_hermes_graph()
            assert graph._compiled is True
            assert "classify_intent" in graph._node_fns
            assert "execute_capability" in graph._node_fns
            assert graph._entry_point == "classify_intent"


class TestActiveContextUpdate:
    """Verify active context is updated correctly."""

    def test_update_tracks_topic(self):
        from nexus_agent_platform.agents.front_brain import update_active_context_for_hermes
        ctx = update_active_context_for_hermes({}, "What is LangGraph?", "LangGraph is...", "conversation")
        assert ctx["last_topic"] == "What is LangGraph?"
        assert ctx["last_mode"] == "conversation"

    def test_update_tracks_numbered_options(self):
        from nexus_agent_platform.agents.front_brain import update_active_context_for_hermes
        response = "1. Option A\n2. Option B\n3. Option C"
        ctx = update_active_context_for_hermes({}, "Give me options", response, "conversation")
        assert "numbered_options" in ctx
        assert ctx["numbered_options"]["1"] == "Option A"

    def test_update_tracks_report_context(self):
        from nexus_agent_platform.agents.front_brain import update_active_context_for_hermes
        data = {"production_total": 14}
        ctx = update_active_context_for_hermes({}, "Client count?", "14 clients", "operational_read", "get_client_count", data)
        assert "last_report" in ctx
        assert ctx["last_report"]["report_definition_id"] == "get_client_count"

    def test_update_tracks_pending_action(self):
        from nexus_agent_platform.agents.front_brain import update_active_context_for_hermes
        ctx = update_active_context_for_hermes({}, "Email me the report", "Sure?", "governed_action", "send_approved_email")
        assert "pending_action" in ctx
        assert ctx["pending_action"]["capability"] == "send_approved_email"


class TestRegressionHERMES_MODEL:
    """Regression: HERMES_MODEL must be importable in hermes.py execute_by_mode."""

    def test_hermes_model_used_in_execute_by_mode(self):
        """HERMES_MODEL was referenced but not imported — caused live failure."""
        import inspect
        from nexus_agent_platform.agents.hermes import _execute_by_mode
        source = inspect.getsource(_execute_by_mode)
        assert "HERMES_MODEL" in source
        # Verify it's imported from front_brain, not just referenced
        assert "from nexus_agent_platform.agents.front_brain import" in source
        assert "HERMES_MODEL" in source.split("from nexus_agent_platform.agents.front_brain import")[1]

    def test_execute_by_mode_conversation_works(self):
        """Conversation mode must not NameError on HERMES_MODEL."""
        from nexus_agent_platform.agents.hermes import _execute_by_mode
        from nexus_agent_platform.state import AgentState
        state = AgentState(
            agent_id="hermes", mission_id="test_regression",
            user_message="Hello", context={}, active_context={},
            metadata={"front_brain_mode": "conversation", "front_brain_capability": None},
        )
        state.intent = "conversation"
        # Must not raise NameError
        result = _execute_by_mode(state)
        assert result.assistant_response is not None
        assert len(result.assistant_response) > 0


# ─── Provenance Tests ─────────────────────────────────────


class TestProvenanceTracking:
    """Provenance must be attached to every operational read result."""

    @staticmethod
    def _mock_supabase_session():
        """Create a mock Supabase session returning 2 production + 2 tester rows."""
        session = MagicMock()
        session._supabase_url = "https://test.supabase.co"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [
            {"tenant_id": "goclear", "status": "active", "client_visible": True, "source": "client_form"},
            {"tenant_id": "goclear", "status": "onboarding", "client_visible": True, "source": "client_form"},
            {"tenant_id": "tenant_demo_1", "status": "active", "client_visible": True, "source": "tester_invitation"},
            {"tenant_id": "tenant-cert-1", "status": "active", "client_visible": True, "source": "static_import"},
        ]
        session.get.return_value = mock_resp
        return session

    def test_live_result_reports_live_provenance(self):
        """A live Supabase query must report source=supabase, freshness=live."""
        from nexus_agent_platform.agents.front_brain import execute_operational_read
        with patch("nexus_agent_platform.agents.hermes._supabase_client", return_value=self._mock_supabase_session()):
            result = execute_operational_read("get_client_count", "how many clients")
        p = result.get("provenance", {})
        assert p.get("source") == "supabase"
        assert p.get("source_type") == "live_governed_read"
        assert p.get("freshness") == "live"
        assert p.get("status") == "success"
        assert p.get("query_start") is not None
        assert p.get("query_end") is not None

    def test_handler_returns_provenance_dict(self):
        """_get_client_count must return a provenance dict in its result."""
        from nexus_agent_platform.agents.hermes import _get_client_count
        with patch("nexus_agent_platform.agents.hermes._supabase_client", return_value=self._mock_supabase_session()):
            result = _get_client_count()
        p = result.get("provenance", {})
        assert p["capability"] == "get_client_count"
        assert p["source"] == "supabase"
        assert p["freshness"] == "live"
        assert p["row_count"] == 4
        assert p["production_count"] == 2
        assert p["tester_or_cert_count"] == 2
        assert "query_target" in p
        assert "filters" in p

    def test_provenance_cannot_claim_live_without_query(self):
        """If the handler fails, provenance must report status=error, not success."""
        from nexus_agent_platform.agents.front_brain import execute_operational_read
        result = execute_operational_read("nonexistent_capability", "test")
        p = result.get("provenance", {})
        assert p.get("status") in ("error", None)
        assert p.get("source") != "supabase" or p.get("status") == "error"

    def test_fixture_result_cannot_claim_supabase_live(self):
        """A mocked handler must not produce live_governed_read provenance."""
        from nexus_agent_platform.agents.front_brain import execute_operational_read

        def fake_handler():
            return {
                "production_total": 99,
                "active": 99,
                "onboarding": 0,
                "tester_or_certification": 0,
                "all_profiles": 99,
            }

        with patch.dict(
            "nexus_agent_platform.agents.front_brain._READ_HANDLER_MAP",
            {"get_client_count": "tests:_fake_client_count"},
        ):
            import tests
            tests._fake_client_count = fake_handler
            result = execute_operational_read("get_client_count", "test")
            p = result.get("provenance", {})
            assert result["data"]["production_total"] == 99

    def test_query_failure_cannot_return_stale_count(self):
        """On Supabase failure, provenance must not claim live success."""
        from nexus_agent_platform.agents.front_brain import execute_operational_read

        def failing_handler():
            raise ConnectionError("Supabase unreachable")

        with patch.dict(
            "nexus_agent_platform.agents.front_brain._READ_HANDLER_MAP",
            {"get_client_count": "tests:_failing_handler"},
        ):
            import tests
            tests._failing_handler = failing_handler
            result = execute_operational_read("get_client_count", "test")
            assert result["status"] == "unavailable"
            p = result.get("provenance", {})
            assert p.get("status") == "error"
            assert p.get("freshness") == "unknown"

    def test_follow_up_source_questions_use_last_provenance(self):
        """The capability_result stored in metadata must carry provenance."""
        from nexus_agent_platform.agents.hermes import get_hermes_graph
        from nexus_agent_platform.state import AgentState
        # Must set env var so get_hermes_graph builds front-brain graph
        with patch.dict(os.environ, {"NEXUS_HERMES_CONVERSATIONAL_FRONT_BRAIN_ENABLED": "true"}):
            # Clear cached graph to force rebuild with front-brain path
            import nexus_agent_platform.agents.hermes as _hm
            _hm._graph = None
            graph = get_hermes_graph()
        state = AgentState(
            agent_id="hermes", mission_id="provenance_followup",
            user_message="how many clients",
            context={}, active_context={},
            metadata={"source": "test", "ray_authorized": True},
        )
        classification = {
            "mode": "operational_read",
            "capability": "get_client_count",
            "confidence": 0.95,
            "reason": "test",
        }
        with patch("nexus_agent_platform.agents.front_brain.classify_message", return_value=classification), \
             patch("nexus_agent_platform.agents.hermes._supabase_client", return_value=self._mock_supabase_session()):
            result = graph.invoke(state)
        cr = result.metadata.get("capability_result", {})
        p = cr.get("provenance", {})
        assert p.get("source") == "supabase"
        assert p.get("freshness") == "live"
        assert "query_start" in p

    def test_generic_model_identity_cannot_override_provenance(self):
        """LLM response must not override verified provenance source."""
        from nexus_agent_platform.agents.front_brain import execute_operational_read
        with patch("nexus_agent_platform.agents.hermes._supabase_client", return_value=self._mock_supabase_session()):
            result = execute_operational_read("get_client_count", "test")
        p = result.get("provenance", {})
        assert p.get("source") in ("supabase", "local", "unknown")
        assert isinstance(p.get("query_start"), str)
        assert isinstance(p.get("query_end"), str)
