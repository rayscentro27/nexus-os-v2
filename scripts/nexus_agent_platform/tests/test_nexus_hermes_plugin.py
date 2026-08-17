"""Tests for the governed upstream Hermes Nexus plugin."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "nexus-hermes-plugin"
SCRIPTS_DIR = REPO_ROOT / "scripts"
UPSTREAM_HERMES_DIR = Path.home() / ".hermes" / "hermes-agent"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(UPSTREAM_HERMES_DIR) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_HERMES_DIR))


def _load_plugin_module():
    spec = importlib.util.spec_from_file_location(
        "nexus_hermes_plugin_test_module",
        PLUGIN_ROOT / "__init__.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _DummyCtx:
    def __init__(self) -> None:
        self.tools = []
        self.skills = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_skill(self, name, path, description=""):
        self.skills.append({"name": name, "path": Path(path), "description": description})


def test_plugin_registers_read_only_tools_and_skills():
    mod = _load_plugin_module()
    ctx = _DummyCtx()

    mod.register(ctx)

    tool_names = [tool["name"] for tool in ctx.tools]
    assert tool_names == [
        "nexus_capability_lookup",
        "nexus_system_status",
        "nexus_process_status",
        "nexus_runtime_status",
        "nexus_research_status",
        "nexus_marketing_status",
        "nexus_revenue_status",
        "nexus_pending_approvals",
        "nexus_automation_health",
        "nexus_client_summary",
        "nexus_credit_summary",
        "nexus_business_foundation_summary",
        "nexus_funding_readiness_summary",
    ]
    assert all(tool["toolset"] == "nexus-hermes" for tool in ctx.tools)
    assert all(tool["name"].startswith("nexus_") for tool in ctx.tools)
    assert len(ctx.skills) == 11
    assert {skill["name"] for skill in ctx.skills} == {
        "nexus-operator",
        "nexus-research-director",
        "nexus-opportunity-director",
        "nexus-creative-director",
        "nexus-marketing-director",
        "nexus-seo-director",
        "nexus-credit-readiness",
        "nexus-credit-result-verification",
        "nexus-business-foundation",
        "nexus-funding-readiness",
        "nexus-crj-handoff",
    }
    assert all(skill["path"].exists() for skill in ctx.skills)


def test_capability_lookup_prefers_deterministic_registry():
    mod = _load_plugin_module()
    result = mod.nexus_capability_lookup({"capability_id": "get_system_health"})

    assert result["status"] == "success"
    assert result["read_only_boundary"] is True
    assert result["result"]["capability"]["capability_id"] == "get_system_health"
    assert result["result"]["capability"]["execution_type"] == "DETERMINISTIC"
    assert result["result"]["capability"]["cost_class"] == "ZERO_MODEL_COST"


def test_capability_lookup_filters_by_cost_and_execution_type():
    mod = _load_plugin_module()
    result = mod.nexus_capability_lookup(
        {"execution_type": "DETERMINISTIC", "cost_class": "ZERO_MODEL_COST", "enabled": True}
    )

    assert result["status"] == "success"
    assert result["result"]["count"] > 0
    assert all(cap["execution_type"] == "DETERMINISTIC" for cap in result["result"]["capabilities"])
    assert all(cap["cost_class"] == "ZERO_MODEL_COST" for cap in result["result"]["capabilities"])


def test_system_status_uses_governed_reads(monkeypatch):
    mod = _load_plugin_module()
    calls = []

    def fake_execute(agent_id, capability_id, arguments=None, trace_id=""):
        calls.append((agent_id, capability_id, arguments or {}))
        return {
            "status": "success",
            "data": {"capability": capability_id},
            "provenance": {"trace_id": trace_id},
        }

    monkeypatch.setattr(mod, "execute_shared_capability", fake_execute)

    result = mod.nexus_system_status({"window": "last_24_hours"})
    assert result["read_only_boundary"] is True
    assert [call[1] for call in calls] == [
        "get_nexus_overview",
        "get_system_health",
        "get_process_registry",
        "get_runtime_execution_summary",
    ]
    assert result["result"]["runtime_summary"]["capability_selected"] == "get_runtime_execution_summary"


def test_read_only_boundary_excludes_writes_and_shell():
    mod = _load_plugin_module()
    tool_names = set(mod._TOOL_HANDLERS)
    assert "execute_sql" not in tool_names
    assert "arbitrary_shell" not in tool_names
    assert "generic_supabase_write" not in tool_names
    assert "delete_operations" not in tool_names


def test_tenant_scope_and_pii_boundary(monkeypatch):
    mod = _load_plugin_module()

    def fake_execute(agent_id, capability_id, arguments=None, trace_id=""):
        return {
            "status": "success",
            "data": {"client_id": "abc", "tenant_id": "goclear", "classification": "production"},
            "tenant_scoped": True,
            "pii_classification": "CLIENT_PII",
            "provenance": {"trace_id": trace_id},
        }

    monkeypatch.setattr(mod, "execute_shared_capability", fake_execute)

    missing = mod.nexus_funding_readiness_summary({})
    assert missing["status"] == "error"
    assert "client_id" in missing["result"]["error"]

    summary = mod.nexus_client_summary({"email": "client@example.com"})
    assert summary["status"] == "success"
    assert summary["result"]["tenant_scoped"] is True
    assert summary["result"]["pii_classification"] == "CLIENT_PII"


def test_skill_files_are_version_controlled():
    skill_paths = sorted(PLUGIN_ROOT.glob("skills/*/SKILL.md"))
    assert len(skill_paths) == 11
    assert all(path.read_text(encoding="utf-8").startswith("---") for path in skill_paths)


def test_plugin_loads_via_hermes_discovery(tmp_path, monkeypatch):
    hermes_home = tmp_path / "hermes_home"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - nexus-hermes-plugin\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(REPO_ROOT / "plugins"))

    from hermes_cli.plugins import discover_plugins, get_plugin_manager

    discover_plugins(force=True)
    manager = get_plugin_manager()
    assert "nexus-hermes-plugin" in manager._plugins
    loaded = manager._plugins["nexus-hermes-plugin"]
    assert loaded.enabled is True
    assert "nexus_capability_lookup" in manager._plugin_tool_names
    assert "nexus-hermes-plugin:nexus-operator" in manager._plugin_skills
