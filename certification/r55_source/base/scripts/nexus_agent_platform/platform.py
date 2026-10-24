"""Nexus Agent Platform — main package entry point.

Usage::

    from nexus_agent_platform import Platform

    platform = Platform()
    result = await platform.handle_message(agent_id="hermes", message="Status update")
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from nexus_agent_platform.flags import status as feature_flags
from nexus_agent_platform.state import AgentState
from nexus_agent_platform.missions.mission import Mission
from nexus_agent_platform.reports.ceo_formatter import format_ceo_report

log = logging.getLogger(__name__)


class Platform:
    """Top-level entry point for the Nexus Agent Platform."""

    def __init__(self) -> None:
        self._graphs: Dict[str, Any] = {}
        self._capabilities: Dict[str, Any] = {}
        self._otel: Dict[str, Any] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize all agent graphs and registries."""
        if self._initialized:
            return

        flags = feature_flags()
        log.info("Initializing Agent Platform (flags=%s)", flags)

        if flags.get("NEXUS_HERMES_LANGGRAPH_ENABLED"):
            from nexus_agent_platform.agents.hermes import get_hermes_graph, get_hermes_capabilities, get_hermes_otel
            self._graphs["hermes"] = get_hermes_graph()
            self._capabilities["hermes"] = get_hermes_capabilities()
            self._otel["hermes"] = get_hermes_otel()

        if flags.get("ALPHA_LANGGRAPH_ENABLED"):
            from nexus_agent_platform.agents.alpha import get_alpha_graph, get_alpha_capabilities, get_alpha_otel
            self._graphs["alpha"] = get_alpha_graph()
            self._capabilities["alpha"] = get_alpha_capabilities()
            self._otel["alpha"] = get_alpha_otel()

        self._initialized = True
        log.info("Agent Platform initialized (graphs=%s)", list(self._graphs.keys()))

    async def handle_message(self, agent_id: str, message: str,
                             metadata: Optional[Dict] = None) -> AgentState:
        """Process a message through the agent's graph."""
        self.initialize()

        state = AgentState(
            agent_id=agent_id,
            user_message=message,
            metadata=metadata or {},
        )

        graph = self._graphs.get(agent_id)
        if graph is None:
            log.warning("No graph for agent %s, returning state directly", agent_id)
            return state

        return await graph.ainvoke(state)

    def get_feature_flags(self) -> Dict[str, bool]:
        return feature_flags()

    def get_capabilities(self, agent_id: str) -> list[Dict[str, Any]]:
        reg = self._capabilities.get(agent_id)
        if reg is None:
            return []
        return reg.list_capabilities()
