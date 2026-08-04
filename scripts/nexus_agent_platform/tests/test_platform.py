"""Tests for the Nexus Agent Platform adapters and core modules."""

import os
import sys
import pytest

# Add scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.state import AgentState
from nexus_agent_platform.capabilities.registry import CapabilityRegistry
from nexus_agent_platform.missions.mission import Mission
from nexus_agent_platform.reports.ceo_formatter import format_ceo_report, format_research_summary
from nexus_agent_platform.context.resolver import (
    load_context, save_context, update_active_context, get_active_context, clear_context,
)
from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
from nexus_agent_platform.adapters.otel_adapter import OtelAdapter
from nexus_agent_platform.flags import status as feature_flags
from nexus_agent_platform.workflows.temporal_adapter import TemporalAdapter
from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter


class TestAgentState:
    def test_default_state(self):
        state = AgentState()
        assert state.agent_id == ""
        assert state.messages == []
        assert state.user_message == ""
        assert state.intent is None

    def test_to_dict_roundtrip(self):
        state = AgentState(agent_id="hermes", user_message="test")
        d = state.to_dict()
        restored = AgentState.from_dict(d)
        assert restored.agent_id == "hermes"
        assert restored.user_message == "test"

    def test_state_schema(self):
        schema = AgentState.state_schema()
        assert "agent_id" in schema.__annotations__
        assert "user_message" in schema.__annotations__


class TestCapabilityRegistry:
    def test_register_and_get(self):
        reg = CapabilityRegistry("test")
        reg.register("web_search", "Search the web", lambda: None)
        cap = reg.get("web_search")
        assert cap is not None
        assert cap.name == "web_search"
        assert cap.description == "Search the web"

    def test_list_capabilities(self):
        reg = CapabilityRegistry("test")
        reg.register("cap1", "Cap 1", lambda: None)
        reg.register("cap2", "Cap 2", lambda: None)
        caps = reg.list_capabilities()
        assert len(caps) == 2
        names = [c["name"] for c in caps]
        assert "cap1" in names
        assert "cap2" in names

    def test_remove(self):
        reg = CapabilityRegistry("test")
        reg.register("cap1", "Cap 1", lambda: None)
        assert reg.remove("cap1") is True
        assert reg.get("cap1") is None
        assert reg.remove("cap1") is False

    def test_has(self):
        reg = CapabilityRegistry("test")
        reg.register("cap1", "Cap 1", lambda: None)
        assert reg.has("cap1") is True
        assert reg.has("cap2") is False


class TestMission:
    def test_create_mission(self, tmp_path):
        os.environ.setdefault("AGENT_PLATFORM_DATA_DIR", str(tmp_path))
        # Patch _MISSIONS_DIR for testing
        import nexus_agent_platform.missions.mission as mod
        original_dir = mod._MISSIONS_DIR
        mod._MISSIONS_DIR = str(tmp_path / "missions")
        try:
            m = Mission.create(agent_id="test", user_message="hello")
            assert m.agent_id == "test"
            assert m.user_message == "hello"
            assert m.status == "RECEIVED"
            assert m.mission_id is not None
        finally:
            mod._MISSIONS_DIR = original_dir


class TestCeoFormatter:
    def test_format_ceo_report(self):
        report = format_ceo_report(
            headline="System Status: All Operational",
            working="Backend services running normally",
            needs_attention="",
            recommendation="Continue monitoring",
        )
        assert "System Status: All Operational" in report
        assert "Working: Backend services running normally" in report
        assert "Recommendation: Continue monitoring" in report
        assert "Phoenix:" in report

    def test_format_research_summary(self):
        summary = format_research_summary(
            topic="Market Analysis",
            key_findings=["Finding 1", "Finding 2"],
            sources=["Source A", "Source B"],
            recommendation="Proceed with caution",
        )
        assert "Research: Market Analysis" in summary
        assert "Finding 1" in summary
        assert "Source A" in summary
        assert "Proceed with caution" in summary


class TestContextResolver:
    def test_save_and_load(self, tmp_path):
        import nexus_agent_platform.context.resolver as mod
        original_dir = mod._CONTEXT_DIR
        mod._CONTEXT_DIR = str(tmp_path / "context")
        try:
            save_context("test", {"active": {"key": {"value": "val", "expires_at": 9999999999}}})
            ctx = load_context("test")
            assert ctx["active"]["key"]["value"] == "val"
        finally:
            mod._CONTEXT_DIR = original_dir

    def test_update_and_get_active(self, tmp_path):
        import nexus_agent_platform.context.resolver as mod
        original_dir = mod._CONTEXT_DIR
        mod._CONTEXT_DIR = str(tmp_path / "context")
        try:
            update_active_context("test", "topic", "AI trends", ttl=600)
            active = get_active_context("test")
            assert active["topic"] == "AI trends"
        finally:
            mod._CONTEXT_DIR = original_dir


class TestGraphAdapter:
    def test_fallback_invoke(self):
        adapter = GraphAdapter(agent_id="test")
        state = AgentState(agent_id="test", user_message="hello")
        result = adapter.invoke(state)
        assert result.agent_id == "test"
        assert result.user_message == "hello"

    def test_is_enabled_when_flag_off(self):
        adapter = GraphAdapter(agent_id="test")
        assert adapter.is_enabled is False

    def test_nodes_registered(self):
        adapter = GraphAdapter(agent_id="test")
        adapter.add_node("node_a", lambda s: s)
        adapter.add_node("node_b", lambda s: s)
        adapter.add_edge("node_a", "node_b")
        assert len(adapter._node_fns) == 2
        assert adapter._edges["node_a"] == "node_b"


class TestOtelAdapter:
    def test_disabled_by_default(self):
        adapter = OtelAdapter(agent_id="test")
        assert adapter.is_enabled is False

    def test_noop_trace(self):
        adapter = OtelAdapter(agent_id="test")
        with adapter.trace("test_trace") as t:
            assert t is None

    def test_noop_span(self):
        adapter = OtelAdapter(agent_id="test")
        with adapter.span("test_span") as s:
            assert s is None


class TestTemporalAdapter:
    def test_disabled_by_default(self):
        adapter = TemporalAdapter(agent_id="test")
        assert adapter.is_enabled is False
        assert adapter.connected is False

    def test_register_activity(self):
        adapter = TemporalAdapter(agent_id="test")
        adapter.register_activity("my_activity", lambda x: x)
        assert "my_activity" in adapter._activities

    def test_direct_activity_execution(self):
        adapter = TemporalAdapter(agent_id="test")
        adapter.register_activity("add", lambda a, b: a + b)
        import asyncio
        result = asyncio.run(adapter.execute_activity("add", 2, 3))
        assert result == 5

    def test_direct_async_activity_execution(self):
        async def async_add(a, b):
            return a + b
        adapter = TemporalAdapter(agent_id="test")
        adapter.register_activity("async_add", async_add)
        import asyncio
        result = asyncio.run(adapter.execute_activity("async_add", 4, 5))
        assert result == 9

    def test_unknown_activity_raises(self):
        adapter = TemporalAdapter(agent_id="test")
        import asyncio
        with pytest.raises(ValueError, match="Unknown activity"):
            asyncio.run(adapter.execute_activity("nonexistent"))


class TestLlmGatewayAdapter:
    def test_disabled_by_default(self):
        adapter = LlmGatewayAdapter(agent_id="test")
        assert adapter.is_enabled is False

    @pytest.mark.asyncio
    async def test_fallback_completion_returns_error_message(self):
        adapter = LlmGatewayAdapter(agent_id="test")
        # Should not raise even without API key — returns error message
        result = await adapter.completion(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "test"}],
        )
        assert "content" in result
        assert "model" in result


class TestFeatureFlags:
    def test_defaults_all_off(self):
        flags = feature_flags()
        assert flags["NEXUS_AGENT_PLATFORM_ENABLED"] is False
        assert flags["NEXUS_HERMES_LANGGRAPH_ENABLED"] is False
        assert flags["ALPHA_LANGGRAPH_ENABLED"] is False
        assert flags["TEMPORAL_WORKFLOWS_ENABLED"] is False
        assert flags["LITELLM_GATEWAY_ENABLED"] is False
        assert flags["LANGFUSE_TRACING_ENABLED"] is False
        assert flags["LEGACY_HERMES_ROUTER_FALLBACK_ENABLED"] is True  # default on
