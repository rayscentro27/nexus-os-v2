"""Path-resolution and process-status semantic tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

pytest.importorskip("nexus_agent_platform")

from nexus_agent_platform.runtime.paths import (  # noqa: E402
    get_nexus_repo_root,
    nexus_data_path,
    nexus_reports_path,
)
from nexus_agent_platform.agents.hermes import _get_system_status, _get_process_status  # noqa: E402


REPO_ROOT = get_nexus_repo_root()


class TestRepoRootResolution:
    """get_nexus_repo_root must resolve the real repository root."""

    def test_real_repo_root_has_markers(self):
        assert (REPO_ROOT / "data").is_dir()
        assert (REPO_ROOT / "scripts").is_dir()
        assert (REPO_ROOT / "reports").is_dir()

    def test_system_status_resolves_repo_root_data(self):
        result = _get_system_status()
        registry = REPO_ROOT / "data" / "operations" / "nexus_process_registry.json"
        if registry.exists():
            assert "Unable to read process registry" != result["working"]
        else:
            assert "Unable to read process registry" == result["working"]

    def test_no_scripts_data_registry(self):
        bad = REPO_ROOT / "scripts" / "data" / "operations" / "nexus_process_registry.json"
        if bad.exists():
            pytest.fail("Canonical process registry must not live under scripts/")

    def test_process_status_returns_typed_result(self):
        result = _get_process_status()
        assert isinstance(result, dict)
        if result.get("status") == "ok":
            for key in ("definitions", "runs", "as_of"):
                assert key in result, f"missing key: {key}"

    def test_running_count_not_fabricated(self):
        result = _get_process_status()
        if result.get("status") == "ok":
            runs = result.get("runs", {})
            running = runs.get("running", 0)
            total = runs.get("total", 0)
            assert running <= total, (
                f"running ({running}) cannot exceed total ({total})"
            )
