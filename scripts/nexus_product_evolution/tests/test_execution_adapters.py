from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.builders.runtime import BuildTaskSpec  # noqa: E402
from nexus_product_evolution.adapters.builder_adapter import mission_to_build_task, _path_allowed, _safe_worker_environment  # noqa: E402
from nexus_product_evolution.adapters.registry import AdapterRegistry, ProductEvolutionAdapter, default_registry  # noqa: E402
from nexus_product_evolution.adapters.voice import voice_adapter  # noqa: E402
from nexus_product_evolution.loop import MissionContract  # noqa: E402


def contract(goal: str = "Repair Voice transport") -> MissionContract:
    return MissionContract(goal=goal, user_visible_outcome="Improve Voice without a parallel system", acceptance_criteria=["preflight passes"], max_cycles=3)


def test_default_registry_selects_voice_and_rejects_unknown_surface() -> None:
    registry = default_registry()
    assert registry.resolve(contract()) is not None
    assert registry.resolve(contract("Improve Creative Studio")) is None


def test_registry_does_not_execute_unknown_surface() -> None:
    adapter = ProductEvolutionAdapter("X", "X", (), (), (), (), False, 1, 10, "none", (), lambda *_: {})
    registry = AdapterRegistry([adapter])
    assert registry.resolve(contract("Improve Voice")) is None


def test_mission_contract_maps_to_bounded_build_spec() -> None:
    task = mission_to_build_task("telegram-test", contract(), allowed_paths=voice_adapter().allowed_paths, protected_paths=voice_adapter().protected_paths, tests=voice_adapter().test_commands, visual_requirements=False, timeout_seconds=30, max_retries=2, parent_mission_id="parent")
    assert isinstance(task, BuildTaskSpec)
    assert task.metadata["mission_id"] == "telegram-test"
    assert task.metadata["parent_mission_id"] == "parent"
    assert task.metadata["starting_commit"]
    assert task.allowed_paths == list(voice_adapter().allowed_paths)
    assert "no arbitrary shell" not in task.objective
    assert task.max_retries == 2


def test_allowed_paths_and_protected_paths_are_independent() -> None:
    assert _path_allowed("scripts/nexus_agent_platform/voice/local_server.py", voice_adapter().allowed_paths, voice_adapter().protected_paths)
    assert not _path_allowed("src/hermes/agent.py", voice_adapter().allowed_paths, voice_adapter().protected_paths)
    assert not _path_allowed("src/admin/unapproved.py", voice_adapter().allowed_paths, voice_adapter().protected_paths)


def test_worker_environment_is_allowlist_only() -> None:
    env = _safe_worker_environment()
    assert not any("TOKEN" in key or "SECRET" in key or "KEY" in key for key in env)


def test_voice_adapter_has_bounded_contract() -> None:
    adapter = voice_adapter()
    assert adapter.adapter_id == "VOICE_PRODUCT_EVOLUTION"
    assert adapter.max_cycles == 3
    assert adapter.timeout_seconds == 900
    assert "https://goclearonline.cc" in " ".join(adapter.security_constraints) or "exact production origin only" in adapter.security_constraints
    assert adapter.execute_fn is not None


@pytest.mark.parametrize("path", ["src/clientPortal/data.ts", "supabase/policies.sql", "runtime.env"])
def test_voice_hard_boundaries_are_not_allowed(path: str) -> None:
    adapter = voice_adapter()
    assert not _path_allowed(path, adapter.allowed_paths, adapter.protected_paths)
