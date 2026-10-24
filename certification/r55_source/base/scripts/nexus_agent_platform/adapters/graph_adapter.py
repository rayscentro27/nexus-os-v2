"""Graph adapter — wraps LangGraph behind a Nexus-owned interface.

LangGraph is installed as an optional dependency behind
``NEXUS_HERMES_LANGGRAPH_ENABLED`` / ``ALPHA_LANGGRAPH_ENABLED`` flags.
When the flags are off the adapter returns stubs that execute nodes
synchronously so the rest of the system continues to work unchanged.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Sequence

from nexus_agent_platform.adapters.state_adapter import AgentState

log = logging.getLogger(__name__)

_USE_LANGGRAPH = os.getenv("NEXUS_AGENT_PLATFORM_ENABLED", "").lower() == "true"

# Module-level cache: availability is checked once per process via find_spec.
_langgraph_available_cache: Optional[bool] = None


def _langgraph_available() -> bool:
    """Check if langgraph is installed without importing its dependency tree.

    Uses importlib.util.find_spec which only inspects package metadata —
    it does not import langchain_core, langsmith, or any network-using code.
    """
    global _langgraph_available_cache
    if _langgraph_available_cache is not None:
        return _langgraph_available_cache
    spec = importlib.util.find_spec("langgraph")
    _langgraph_available_cache = spec is not None
    return _langgraph_available_cache


class GraphAdapter:
    """Nexus-owned wrapper around LangGraph ``StateGraph``.

    When LangGraph is disabled the adapter provides a synchronous
    fallback that executes nodes in order — this lets the legacy
    router continue to function while we validate the new graph.
    """

    def __init__(self, agent_id: str, state_schema: Any = None):
        self.agent_id = agent_id
        self._graph: Any = None
        self._node_fns: Dict[str, Callable] = {}
        self._node_order: List[str] = []
        self._edges: Dict[str, Any] = {}
        self._compiled: bool = False
        self._entry_point: Optional[str] = None
        self._enabled = _USE_LANGGRAPH and _langgraph_available()

    @staticmethod
    def _langgraph_available() -> bool:
        """Backward-compatible static method; delegates to cached module-level check."""
        return _langgraph_available()

    def add_node(self, name: str, fn: Callable) -> None:
        if self._enabled:
            self._lazy_build()
            self._graph.add_node(name, fn)
        self._node_fns[name] = fn
        self._node_order.append(name)

    def add_edge(self, source: str, target: str) -> None:
        if self._enabled:
            self._graph.add_edge(source, target)
        self._edges[source] = target

    def add_conditional_edge(
        self, source: str, condition: Callable, mapping: Dict[str, str]
    ) -> None:
        if self._enabled:
            self._graph.add_conditional_edges(source, condition, mapping)
        self._edges[source] = {"condition": condition, "mapping": mapping}

    def set_entry_point(self, name: str) -> None:
        if self._enabled:
            self._graph.set_entry_point(name)
        self._entry_point = name

    def set_finish_point(self, name: str) -> None:
        if self._enabled:
            self._graph.set_finish_point(name)

    def compile(self) -> "GraphAdapter":
        if self._enabled and self._graph is not None:
            self._graph = self._graph.compile()
        self._compiled = True
        return self

    async def ainvoke(self, state: AgentState, config: Optional[Dict] = None) -> AgentState:
        if self._enabled and self._compiled:
            result = await self._graph.ainvoke(state.to_dict(), config or {})
            return AgentState.from_dict(result)
        return await self._fallback_invoke(state, config)

    def invoke(self, state: AgentState, config: Optional[Dict] = None) -> AgentState:
        if self._enabled and self._compiled:
            result = self._graph.invoke(state.to_dict(), config or {})
            return AgentState.from_dict(result)
        # Synchronous fallback — execute nodes in order
        current = state
        for node_name in self._node_order:
            fn = self._node_fns.get(node_name)
            if fn:
                log.debug("GraphAdapter fallback: running node %s for agent %s", node_name, self.agent_id)
                current = fn(current)
        return current

    async def _fallback_invoke(self, state: AgentState, _config: Optional[Dict] = None) -> AgentState:
        current = state
        for node_name in self._node_order:
            fn = self._node_fns.get(node_name)
            if fn:
                log.debug("GraphAdapter async fallback: running node %s for agent %s", node_name, self.agent_id)
                import asyncio
                if asyncio.iscoroutinefunction(fn):
                    current = await fn(current)
                else:
                    current = fn(current)
        return current

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def _lazy_build(self) -> None:
        if self._graph is None:
            from langgraph.graph import StateGraph  # noqa: F811 — real lazy import
            self._graph = StateGraph(AgentState.state_schema())


# ─── Optional prewarm for long-running workers ──────────────

_prewarm_done: bool = False


def prewarm_langgraph(timeout_seconds: float = 60.0) -> dict:
    """Import LangGraph and compile a minimal graph once at worker startup.

    Intended for long-running Telegram workers after safe startup.
    Must not be called in simple CLI utilities or tests unless explicitly
    requested.

    Returns a dict with timing diagnostics.
    """
    global _prewarm_done
    import time

    if _prewarm_done:
        return {"status": "already_prewarmed"}

    result: dict = {"status": "ok"}

    t0 = time.monotonic()
    try:
        from langgraph.graph import StateGraph  # noqa: F811
        t_import = time.monotonic() - t0
        result["import_ms"] = round(t_import * 1000, 1)
    except Exception as exc:
        result["status"] = "import_failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["import_ms"] = round((time.monotonic() - t0) * 1000, 1)
        log.error("Prewarm: LangGraph import failed: %s", exc)
        return result

    t1 = time.monotonic()
    try:
        class _PrewarmState(dict):
            pass

        graph = StateGraph(_PrewarmState)
        graph.add_node("_ping", lambda s: s)
        graph.set_entry_point("_ping")
        graph.set_finish_point("_ping")
        compiled = graph.compile()
        t_compile = time.monotonic() - t1
        result["compile_ms"] = round(t_compile * 1000, 1)
    except Exception as exc:
        result["status"] = "compile_failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["compile_ms"] = round((time.monotonic() - t1) * 1000, 1)
        log.error("Prewarm: LangGraph compile failed: %s", exc)
        return result

    _prewarm_done = True
    result["total_ms"] = round((time.monotonic() - t0) * 1000, 1)
    log.info(
        "Prewarm complete: import=%sms compile=%sms total=%sms",
        result["import_ms"], result["compile_ms"], result["total_ms"],
    )
    return result
