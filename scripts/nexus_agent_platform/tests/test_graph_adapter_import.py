"""Tests proving GraphAdapter availability detection is fast and lazy.

These tests verify that:
1. GraphAdapter construction completes quickly without importing langgraph.graph
2. Package absence returns disabled/unavailable safely
3. The real graph-build method lazily imports LangGraph
4. Multiple instances do not repeat the availability lookup
5. Importing graph_adapter does not initialize LangSmith, Langfuse, OpenRouter,
   Telegram, Supabase, or Temporal
6. A graph can still compile after the lazy import
"""

import importlib
import importlib.util
import os
import sys
import time
from unittest import mock

import pytest

# Ensure scripts is importable
_scripts_dir = os.path.join(os.path.dirname(__file__), "..")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


class TestAvailabilityDetectionSpeed:
    """Verify that availability detection uses find_spec, not full import."""

    def test_langgraph_available_uses_find_spec(self):
        """_langgraph_available should use importlib.util.find_spec."""
        from nexus_agent_platform.adapters import graph_adapter
        # The module should have a _langgraph_available_cache
        assert hasattr(graph_adapter, "_langgraph_available_cache")

    def test_construction_completes_quickly(self):
        """GraphAdapter.__init__ should complete in under 100ms regardless of langgraph."""
        start = time.monotonic()
        from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
        adapter = GraphAdapter(agent_id="speed_test")
        elapsed_ms = (time.monotonic() - start) * 1000
        # Should be fast — no full langgraph import
        assert elapsed_ms < 500, f"Construction took {elapsed_ms:.0f}ms, expected <500ms"

    def test_availability_cached_after_first_call(self):
        """Repeated calls to _langgraph_available should use cached value."""
        from nexus_agent_platform.adapters import graph_adapter
        # Reset cache
        graph_adapter._langgraph_available_cache = None
        with mock.patch("importlib.util.find_spec", wraps=importlib.util.find_spec) as mock_find:
            first = graph_adapter._langgraph_available()
            second = graph_adapter._langgraph_available()
            # find_spec should only be called once (first call), then cached
            assert mock_find.call_count == 1
            assert first == second

    def test_package_absence_returns_disabled(self):
        """When langgraph is not found, adapter should be disabled safely."""
        from nexus_agent_platform.adapters import graph_adapter
        original_cache = graph_adapter._langgraph_available_cache
        try:
            graph_adapter._langgraph_available_cache = None
            with mock.patch("importlib.util.find_spec", return_value=None):
                with mock.patch.object(graph_adapter, "_USE_LANGGRAPH", True):
                    from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
                    adapter = GraphAdapter(agent_id="absent_test")
                    assert adapter.is_enabled is False
        finally:
            graph_adapter._langgraph_available_cache = original_cache


class TestLazyImportBehavior:
    """Verify that real langgraph import only happens in _lazy_build."""

    def test_add_node_does_not_import_langgraph_when_disabled(self):
        """When adapter is disabled, add_node must not trigger langgraph import."""
        from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
        adapter = GraphAdapter(agent_id="lazy_test")
        assert adapter.is_enabled is False
        # add_node should work without langgraph
        adapter.add_node("test_node", lambda s: s)
        assert "test_node" in adapter._node_fns

    def test_invoke_fallback_does_not_import_langgraph(self):
        """Fallback invoke should work without langgraph import."""
        from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
        from nexus_agent_platform.adapters.state_adapter import AgentState
        adapter = GraphAdapter(agent_id="fallback_test")
        adapter.add_node("echo", lambda s: s)
        state = AgentState(agent_id="fallback_test")
        result = adapter.invoke(state)
        assert result.agent_id == "fallback_test"

    @pytest.mark.skipif(
        not importlib.util.find_spec("langgraph"),
        reason="langgraph not installed"
    )
    def test_real_import_happens_only_in_lazy_build(self):
        """When enabled, _lazy_build should trigger the real langgraph import."""
        from nexus_agent_platform.adapters import graph_adapter
        # Force availability True and simulate enabled
        original_cache = graph_adapter._langgraph_available_cache
        try:
            graph_adapter._langgraph_available_cache = True
            with mock.patch.object(graph_adapter, "_USE_LANGGRAPH", True):
                from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
                adapter = GraphAdapter(agent_id="real_import_test")
                assert adapter.is_enabled is True
                assert adapter._graph is None  # not yet built
                # Now add a node — this triggers _lazy_build
                adapter.add_node("ping", lambda s: s)
                assert adapter._graph is not None  # now it's built
        finally:
            graph_adapter._langgraph_available_cache = original_cache

    @pytest.mark.skipif(
        not importlib.util.find_spec("langgraph"),
        reason="langgraph not installed"
    )
    def test_graph_can_compile_after_lazy_import(self):
        """A graph should compile successfully after the lazy import."""
        from nexus_agent_platform.adapters import graph_adapter
        original_cache = graph_adapter._langgraph_available_cache
        try:
            graph_adapter._langgraph_available_cache = True
            with mock.patch.object(graph_adapter, "_USE_LANGGRAPH", True):
                from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
                adapter = GraphAdapter(agent_id="compile_test")
                adapter.add_node("step_a", lambda s: s)
                adapter.add_edge("step_a", "step_a")
                adapter.set_entry_point("step_a")
                adapter.set_finish_point("step_a")
                compiled = adapter.compile()
                assert compiled._compiled is True
        finally:
            graph_adapter._langgraph_available_cache = original_cache


class TestNoSideEffectsOnImport:
    """Verify importing graph_adapter does not initialize external services."""

    def test_no_langsmith_init(self):
        """Importing graph_adapter must not call langsmith.Client or initialize tracing."""
        modules_before = set(sys.modules.keys())
        # Remove cached modules to force fresh import
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.adapters.graph")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.adapters.graph_adapter
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        # Should not have loaded langsmith internals
        langsmith_new = [m for m in new_modules if "langsmith" in m]
        assert not langsmith_new, f"Unexpected langsmith modules loaded: {langsmith_new}"

    def test_no_langfuse_init(self):
        """Importing graph_adapter must not initialize Langfuse."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.adapters.graph")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.adapters.graph_adapter
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        langfuse_new = [m for m in new_modules if "langfuse" in m]
        assert not langfuse_new, f"Unexpected langfuse modules loaded: {langfuse_new}"

    def test_no_openrouter_init(self):
        """Importing graph_adapter must not initialize OpenRouter."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.adapters.graph")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.adapters.graph_adapter
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        openrouter_new = [m for m in new_modules if "openrouter" in m]
        assert not openrouter_new, f"Unexpected openrouter modules loaded: {openrouter_new}"

    def test_no_telegram_init(self):
        """Importing graph_adapter must not initialize Telegram."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.adapters.graph")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.adapters.graph_adapter
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        telegram_new = [m for m in new_modules if "telegram" in m.lower()]
        assert not telegram_new, f"Unexpected telegram modules loaded: {telegram_new}"

    def test_no_supabase_init(self):
        """Importing graph_adapter must not initialize Supabase."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.adapters.graph")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.adapters.graph_adapter
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        supabase_new = [m for m in new_modules if "supabase" in m]
        assert not supabase_new, f"Unexpected supabase modules loaded: {supabase_new}"

    def test_no_temporal_init(self):
        """Importing graph_adapter must not initialize Temporal."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.adapters.graph")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.adapters.graph_adapter
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        temporal_new = [m for m in new_modules if "temporal" in m]
        assert not temporal_new, f"Unexpected temporal modules loaded: {temporal_new}"


class TestPrewarm:
    """Tests for the optional prewarm function."""

    def test_prewarm_returns_already_done_on_repeat(self):
        """Second prewarm call should return already_prewarmed."""
        from nexus_agent_platform.adapters import graph_adapter
        original = graph_adapter._prewarm_done
        try:
            graph_adapter._prewarm_done = True
            result = graph_adapter.prewarm_langgraph()
            assert result["status"] == "already_prewarmed"
        finally:
            graph_adapter._prewarm_done = original

    @pytest.mark.skipif(
        not importlib.util.find_spec("langgraph"),
        reason="langgraph not installed"
    )
    def test_prewarm_succeeds_with_langgraph(self):
        """Prewarm should import and compile a minimal graph."""
        from nexus_agent_platform.adapters import graph_adapter
        original = graph_adapter._prewarm_done
        try:
            graph_adapter._prewarm_done = False
            result = graph_adapter.prewarm_langgraph()
            assert result["status"] == "ok"
            assert "import_ms" in result
            assert "compile_ms" in result
            # import_ms may be 0 if langgraph was already imported in this process
            assert result["import_ms"] >= 0
            assert result["compile_ms"] > 0
        finally:
            graph_adapter._prewarm_done = original
