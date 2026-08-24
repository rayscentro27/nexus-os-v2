from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from ..loop import MissionContract


@dataclass(frozen=True)
class ProductEvolutionAdapter:
    adapter_id: str
    surface: str
    allowed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    security_constraints: tuple[str, ...]
    test_commands: tuple[tuple[str, ...], ...]
    visual_requirements: bool
    max_cycles: int
    timeout_seconds: int
    deployment_policy: str
    human_gates: tuple[str, ...]
    execute_fn: Callable[[str, MissionContract, "ProductEvolutionAdapter"], Dict[str, Any]]
    can_handle_fn: Optional[Callable[[MissionContract], bool]] = None

    def can_handle(self, contract: MissionContract) -> bool:
        if self.can_handle_fn:
            return bool(self.can_handle_fn(contract))
        return self.surface.lower() in contract.user_visible_outcome.lower() or self.surface.lower() in contract.goal.lower()

    def execute(self, mission_id: str, contract: MissionContract) -> Dict[str, Any]:
        return self.execute_fn(mission_id, contract, self)


class AdapterRegistry:
    def __init__(self, adapters: Iterable[ProductEvolutionAdapter] = ()) -> None:
        self._adapters = {adapter.adapter_id: adapter for adapter in adapters}

    def register(self, adapter: ProductEvolutionAdapter) -> None:
        self._adapters[adapter.adapter_id] = adapter

    def get(self, adapter_id: str) -> Optional[ProductEvolutionAdapter]:
        return self._adapters.get(adapter_id)

    def resolve(self, contract: MissionContract) -> Optional[ProductEvolutionAdapter]:
        for adapter in self._adapters.values():
            if adapter.can_handle(contract):
                return adapter
        return None

    def ids(self) -> list[str]:
        return sorted(self._adapters)


def default_registry() -> AdapterRegistry:
    from .voice import voice_adapter
    return AdapterRegistry([voice_adapter()])
