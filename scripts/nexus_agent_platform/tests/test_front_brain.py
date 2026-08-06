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
