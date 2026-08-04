"""Capability registry — Nexus-owned interface for tool/ability discovery.

Capabilities are registered at startup per-agent. The graph adapter
checks the registry to know which tools a particular agent may invoke.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class Capability:
    name: str
    description: str
    handler: Callable
    requires_approval: bool = False
    safety_boundary: str = "standard"
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """Central registry of tool capabilities per agent.

    Each agent (hermes / alpha) maintains its own registry instance.
    Capabilities are added at startup from a declarative manifest so
    the graph nodes can look them up at runtime.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._capabilities: Dict[str, Capability] = {}

    def register(self, name: str, description: str, handler: Callable,
                 requires_approval: bool = False, safety_boundary: str = "standard",
                 metadata: Optional[Dict] = None) -> None:
        self._capabilities[name] = Capability(
            name=name,
            description=description,
            handler=handler,
            requires_approval=requires_approval,
            safety_boundary=safety_boundary,
            metadata=metadata or {},
        )
        log.info("Registered capability %s for agent %s", name, self.agent_id)

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": c.name,
                "description": c.description,
                "requires_approval": c.requires_approval,
                "safety_boundary": c.safety_boundary,
            }
            for c in self._capabilities.values()
        ]

    def has(self, name: str) -> bool:
        return name in self._capabilities

    def remove(self, name: str) -> bool:
        if name in self._capabilities:
            del self._capabilities[name]
            return True
        return False

    def clear(self) -> None:
        self._capabilities.clear()
