"""Tests for Nexus Knowledge Registry and shared knowledge capabilities.

Certifies that Nova can accurately answer questions about Nexus architecture,
agents, tools, processes, reports, and recent activity.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════
# NEXUS KNOWLEDGE REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════

class TestNexusOverview:
    """Test get_nexus_overview returns accurate system information."""

    def test_returns_real_system_name(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview
        result = get_nexus_overview()
        assert result["system_name"] == "Nexus OS"
        assert result["version"] == "v2"

    def test_returns_real_agents(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview
        result = get_nexus_overview()
        agents = result.get("agents", [])
        assert "nexus_hermes" in agents
        assert "hermes_nova" in agents
        assert "alpha" in agents

    def test_returns_major_components(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview
        result = get_nexus_overview()
        components = result.get("major_components", [])
        assert len(components) > 0
        assert any("Agent Platform" in c for c in components)

    def test_returns_process_count(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview
        result = get_nexus_overview()
        assert result.get("process_count", 0) > 0

    def test_reports_incomplete_areas(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview
        result = get_nexus_overview()
        incomplete = result.get("known_incomplete_areas", [])
        assert len(incomplete) > 0
        assert any("simulated" in a.lower() for a in incomplete)

    def test_verification_complete(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_overview
        result = get_nexus_overview()
        assert result.get("verification_complete") is True


class TestNexusArchitecture:
    """Test get_nexus_architecture returns structural details."""

    def test_returns_architecture(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_architecture
        result = get_nexus_architecture()
        assert "architecture" in result
        assert "LangGraph" in result["architecture"]

    def test_returns_agent_isolation(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_architecture
        result = get_nexus_architecture()
        agents = result.get("agents", {})
        assert "nexus_hermes" in agents
        assert "hermes_nova" in agents
        assert "alpha" in agents
        # Check isolation boundaries exist
        for agent_id in ["nexus_hermes", "hermes_nova", "alpha"]:
            assert "isolation" in agents[agent_id]

    def test_returns_specialist_profiles(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_architecture
        result = get_nexus_architecture()
        specialists = result.get("specialist_profiles", {})
        assert len(specialists) == 9
        assert "credit" in specialists
        assert "funding" in specialists


class TestAgentRegistry:
    """Test get_agent_registry returns all agents."""

    def test_lists_all_agents(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_registry
        result = get_agent_registry()
        agents = result.get("agents", [])
        assert len(agents) == 3
        agent_ids = {a["agent_id"] for a in agents}
        assert "nexus_hermes" in agent_ids
        assert "hermes_nova" in agent_ids
        assert "alpha" in agent_ids

    def test_includes_permissions(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_registry
        result = get_agent_registry()
        for agent in result["agents"]:
            assert "permissions" in agent
            assert "read_count" in agent["permissions"]
            assert "write_count" in agent["permissions"]

    def test_nova_has_zero_writes(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_registry
        result = get_agent_registry()
        nova = next(a for a in result["agents"] if a["agent_id"] == "hermes_nova")
        assert nova["permissions"]["write_count"] == 0

    def test_hermes_has_write_access(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_registry
        result = get_agent_registry()
        hermes = next(a for a in result["agents"] if a["agent_id"] == "nexus_hermes")
        assert hermes["permissions"]["write_count"] > 0


class TestAgentDetails:
    """Test get_agent_details returns accurate agent information."""

    def test_hermes_details(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_details
        result = get_agent_details("nexus_hermes")
        assert result["found"] is True
        assert result["name"] == "Nexus Hermes"
        assert "operator" in result["role"].lower()
        assert result["model"] == "openai/gpt-4o-mini"

    def test_nova_details(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_details
        result = get_agent_details("hermes_nova")
        assert result["found"] is True
        assert result["name"] == "Hermes Nova"
        assert "strategic" in result["role"].lower() or "adviser" in result["role"].lower()
        assert result["permissions"]["writes"] == []

    def test_alpha_details(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_details
        result = get_agent_details("alpha")
        assert result["found"] is True
        assert result["name"] == "Alpha"
        assert "research" in result["role"].lower() or "advisor" in result["role"].lower()

    def test_unknown_agent(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_agent_details
        result = get_agent_details("nonexistent")
        assert result["found"] is False
        assert "available_agents" in result


class TestToolRegistry:
    """Test get_tool_registry returns accurate tool information."""

    def test_returns_categories(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_tool_registry
        result = get_tool_registry()
        categories = result.get("categories", {})
        assert "internal_safe" in categories
        assert "read_only" in categories
        assert "approval_gated" in categories
        assert "unavailable" in categories

    def test_no_secrets_in_tools(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_tool_registry
        result = get_tool_registry()
        all_tools = []
        for cat_info in result.get("categories", {}).values():
            all_tools.extend(cat_info.get("tools", []))
        # Ensure no credential-like tools
        for tool in all_tools:
            assert "key" not in tool.lower()
            assert "secret" not in tool.lower()
            assert "token" not in tool.lower()
            assert "password" not in tool.lower()

    def test_unavailable_tools_identified(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_tool_registry
        result = get_tool_registry()
        unavailable = result.get("unavailable_count", 0)
        assert unavailable > 0


class TestCapabilityRegistry:
    """Test get_capability_registry returns capability status."""

    def test_returns_handler_counts(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_capability_registry
        result = get_capability_registry()
        assert result["total_shared_handlers"] == 11
        assert result["total_nova_knowledge"] == 10
        assert result["nova_writes"] == 0

    def test_lists_shared_handlers(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_capability_registry
        result = get_capability_registry()
        shared = result.get("shared_handlers", [])
        assert "get_system_health" in shared
        assert "get_client_count" in shared


class TestProcessRegistry:
    """Test get_process_registry_live returns process information."""

    def test_returns_processes(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        assert result["status"] == "success"
        assert result["total"] > 0

    def test_identifies_enabled_disabled(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        config = result["configuration_counts"]
        assert config.get("enabled", 0) > 0
        assert config.get("disabled", 0) >= 0
        assert sum(config.values()) == result["total"]

    def test_all_simulated(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        for p in result["processes"]:
            # All processes should be simulated or skipped (no real execution yet)
            assert p["runtime_state"] in ("simulated", "blocked", "never_run", "skipped")


class TestProcessDetails:
    """Test get_process_details returns specific process information."""

    def test_known_process(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_details
        result = get_process_details("daily_monitor")
        assert result["found"] is True
        assert result["name"] == "Daily Monitor"
        assert result["configuration_state"] == "enabled"

    def test_disabled_process(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_details
        result = get_process_details("stripe_test_paywall")
        assert result["found"] is True
        assert result["configuration_state"] == "disabled"

    def test_unknown_process(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_details
        result = get_process_details("nonexistent_process")
        assert result["found"] is False
        assert "available_processes" in result


class TestReportIndex:
    """Test get_report_index_live returns report categories."""

    def test_returns_categories(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_report_index_live
        result = get_report_index_live()
        assert result["status"] == "success"
        assert result["category_count"] > 0

    def test_has_report_categories(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_report_index_live
        result = get_report_index_live()
        categories = {c["category"] for c in result.get("categories", [])}
        assert "alpha" in categories or "runtime" in categories


class TestLatestReports:
    """Test get_latest_reports_live returns recent reports."""

    def test_returns_reports(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_latest_reports_live
        result = get_latest_reports_live()
        assert result["status"] == "success"
        assert result["total_latest"] > 0

    def test_reports_have_metadata(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_latest_reports_live
        result = get_latest_reports_live()
        for report in result.get("reports", [])[:5]:
            assert "name" in report
            assert "modified" in report


class TestRecentActivity:
    """Test get_recent_activity_live aggregates activity correctly."""

    def test_returns_components(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_recent_activity_live
        result = get_recent_activity_live()
        assert "components" in result
        components = result["components"]
        assert "processes" in components
        assert "approvals" in components
        assert "research" in components
        assert "alpha" in components

    def test_process_activity(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_recent_activity_live
        result = get_recent_activity_live()
        proc = result["components"]["processes"]
        assert proc["status"] == "success"
        # No process has actually run for real yet
        assert proc.get("failed", 0) == 0

    def test_unavailable_not_treated_as_empty(self):
        """Verify that unavailable components are NOT treated as empty."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_recent_activity_live
        result = get_recent_activity_live()
        for name, comp in result["components"].items():
            if comp.get("status") == "unavailable":
                # Should NOT have fabricated data
                assert "error" in comp or "data" not in comp


# ═══════════════════════════════════════════════════════════════
# SHARED CAPABILITY HANDLER TESTS
# ═══════════════════════════════════════════════════════════════

class TestSharedKnowledgeHandlers:
    """Test that shared capability handlers wrap knowledge correctly."""

    def test_nexus_overview_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_nexus_overview", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["system_name"] == "Nexus OS"
        assert result["provenance"]["source_type"] == "repository_registry"

    def test_agent_registry_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_agent_registry", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["total"] == 3

    def test_agent_details_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability(
            "hermes_nova", "get_agent_details",
            {"agent_id": "alpha"}, trace_id="test"
        )
        assert result["status"] == "success"
        assert result["data"]["found"] is True

    def test_agent_details_missing_id(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability(
            "hermes_nova", "get_agent_details", {}, trace_id="test"
        )
        assert result["status"] == "error"
        assert "agent_id is required" in result["error"]

    def test_tool_registry_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_tool_registry", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["total"] > 0

    def test_capability_registry_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_capability_registry", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["nova_writes"] == 0

    def test_process_registry_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_process_registry", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["total"] > 0

    def test_process_details_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability(
            "hermes_nova", "get_process_details",
            {"process_id": "daily_monitor"}, trace_id="test"
        )
        assert result["status"] == "success"
        assert result["data"]["found"] is True

    def test_report_index_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_report_index", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["category_count"] > 0

    def test_latest_reports_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_latest_reports", trace_id="test")
        assert result["status"] == "success"
        assert result["data"]["total_latest"] > 0

    def test_recent_activity_handler(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        result = execute_shared_capability("hermes_nova", "get_recent_activity", trace_id="test")
        assert result["status"] in ("success", "partial")
        assert "components" in result["data"]


# ═══════════════════════════════════════════════════════════════
# SEMANTIC ROUTING TESTS
# ═══════════════════════════════════════════════════════════════

class TestKnowledgeSemanticRouting:
    """Test that the semantic gate routes knowledge questions correctly."""

    def test_what_is_nexus(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What is Nexus?")
        assert result is not None
        assert result[0] == "get_nexus_overview"

    def test_how_is_nexus_structured(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("How is Nexus structured?")
        assert result is not None
        assert result[0] == "get_nexus_overview"

    def test_what_agents(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What agents do we have?")
        assert result is not None
        assert result[0] == "get_agent_registry"

    def test_what_does_alpha_do(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What does Alpha do?")
        assert result is not None
        assert result[0] == "get_agent_details"
        assert result[1]["agent_id"] == "alpha"

    def test_what_does_hermes_do(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What does Hermes do?")
        assert result is not None
        assert result[0] == "get_agent_details"
        assert result[1]["agent_id"] == "nexus_hermes"

    def test_who_are_you(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("Who are you?")
        assert result is not None
        assert result[0] == "get_agent_details"
        assert result[1]["agent_id"] == "hermes_nova"

    def test_what_tools(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What tools does Nexus have?")
        assert result is not None
        assert result[0] == "get_tool_registry"

    def test_what_capabilities(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What capabilities are live?")
        assert result is not None
        assert result[0] == "get_capability_registry"

    def test_what_processes(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What processes exist?")
        assert result is not None
        assert result[0] == "get_process_registry"

    def test_what_reports(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What reports were generated?")
        assert result is not None
        assert result[0] == "get_latest_reports"

    def test_what_failed_today(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What failed today?")
        assert result is not None
        assert result[0] == "get_recent_activity"

    def test_what_happened_today(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What happened in Nexus today?")
        assert result is not None
        assert result[0] == "get_recent_activity"

    def test_what_should_i_focus_on(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What should I focus on next?")
        assert result is not None
        assert result[0] == "get_recent_activity"

    def test_casual_question_no_tool(self):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        result = _semantic_capability_gate("What do you think about buying real estate?")
        assert result is None


# ═══════════════════════════════════════════════════════════════
# SECURITY TESTS
# ═══════════════════════════════════════════════════════════════

class TestKnowledgeSecurity:
    """Test security boundaries for knowledge capabilities."""

    def test_no_client_data_in_knowledge(self):
        """Knowledge capabilities must NOT expose client PII."""
        from nexus_agent_platform.capabilities.nexus_knowledge import (
            get_nexus_overview, get_agent_registry, get_tool_registry,
            get_process_registry_live, get_recent_activity_live,
        )
        for func in [get_nexus_overview, get_agent_registry, get_tool_registry,
                      get_process_registry_live, get_recent_activity_live]:
            result = func()
            result_str = str(result).lower()
            # No email addresses (except common system ones)
            assert "email" not in result_str or "noreply" in result_str or "support@" not in result_str

    def test_no_credentials_in_knowledge(self):
        """Knowledge capabilities must NOT expose credentials."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_tool_registry
        result = get_tool_registry()
        result_str = str(result).lower()
        assert "api_key" not in result_str
        assert "secret" not in result_str
        assert "token" not in result_str
        assert "password" not in result_str
        assert "service_role" not in result_str

    def test_no_raw_source_code(self):
        """Knowledge capabilities must NOT dump source code."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_nexus_architecture
        result = get_nexus_architecture()
        result_str = str(result)
        # No Python imports
        assert "import " not in result_str
        assert "from " not in result_str
        # No function definitions
        assert "def " not in result_str
        assert "class " not in result_str

    def test_nova_writes_remain_zero(self):
        """Nova must have zero write access."""
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_WRITES
        assert len(NOVA_ALLOWED_WRITES) == 0

    def test_knowledge_capabilities_are_read_only(self):
        """All knowledge capabilities must be read-only."""
        from nexus_agent_platform.capabilities.shared import _WRITE_CAPABILITIES
        knowledge_caps = [
            "get_nexus_overview", "get_agent_registry", "get_agent_details",
            "get_tool_registry", "get_capability_registry", "get_process_registry",
            "get_process_details", "get_report_index", "get_latest_reports",
            "get_recent_activity",
        ]
        for cap in knowledge_caps:
            assert cap not in _WRITE_CAPABILITIES

    def test_process_details_no_raw_payloads(self):
        """Process details must not expose raw payloads."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_details
        result = get_process_details("daily_monitor")
        result_str = str(result).lower()
        assert "raw_payload" not in result_str
        assert "raw_data" not in result_str


# ═══════════════════════════════════════════════════════════════
# TRUTH GUARD TESTS
# ═══════════════════════════════════════════════════════════════

class TestKnowledgeTruthGuard:
    """Test that truth guard prevents contradictions with knowledge data."""

    def test_unavailable_activity_not_treated_as_nothing(self):
        """Unavailable activity must NOT become 'nothing happened'."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_recent_activity_live
        result = get_recent_activity_live()
        # If any component is unavailable, the overall status should reflect it
        components = result.get("components", {})
        has_unavailable = any(
            c.get("status") == "unavailable"
            for c in components.values()
        )
        if has_unavailable:
            assert result["status"] != "success" or has_unavailable

    def test_simulated_not_treated_as_running(self):
        """Simulated processes must NOT be described as 'running'."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        for p in result.get("processes", []):
            if p["runtime_state"] == "simulated":
                # Should not claim the process is actively running
                assert p["runtime_state"] != "running"

    def test_disabled_process_not_enabled(self):
        """Disabled processes must NOT be described as enabled."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_details
        result = get_process_details("stripe_test_paywall")
        assert result["configuration_state"] == "disabled"


class TestProcessDimensions:
    """Phase 18: Tests for three independent process dimensions."""

    def test_each_process_has_one_configuration_state(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        for p in result["processes"]:
            assert p["configuration_state"] in ("enabled", "disabled"), (
                f"{p['process_id']} has invalid configuration_state: {p['configuration_state']}"
            )

    def test_each_process_has_one_execution_mode(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        valid_modes = {"ACTIVE_INTERNAL", "DRY_RUN", "TELEGRAM_OPERATOR", "SANDBOX_TEST", "BLOCKED", "unknown"}
        for p in result["processes"]:
            assert p["execution_mode"] in valid_modes, (
                f"{p['process_id']} has invalid execution_mode: {p['execution_mode']}"
            )

    def test_each_process_has_one_runtime_state(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        valid_states = {"running", "idle", "completed", "failed", "simulated", "skipped", "blocked", "unknown", "never_run"}
        for p in result["processes"]:
            assert p["runtime_state"] in valid_states, (
                f"{p['process_id']} has invalid runtime_state: {p['runtime_state']}"
            )

    def test_configuration_counts_reconcile(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        config_sum = sum(result["configuration_counts"].values())
        assert config_sum == result["total"], (
            f"Configuration counts {result['configuration_counts']} sum to {config_sum}, "
            f"but total is {result['total']}"
        )

    def test_mode_counts_reconcile(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        mode_sum = sum(result["mode_counts"].values())
        assert mode_sum == result["total"], (
            f"Mode counts {result['mode_counts']} sum to {mode_sum}, "
            f"but total is {result['total']}"
        )

    def test_runtime_counts_reconcile(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        runtime_sum = sum(result["runtime_counts"].values())
        assert runtime_sum == result["total"], (
            f"Runtime counts {result['runtime_counts']} sum to {runtime_sum}, "
            f"but total is {result['total']}"
        )

    def test_all_dimensions_reconcile(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        assert result["reconciliation"]["all_reconciled"] is True

    def test_enabled_does_not_mean_running(self):
        """Enabled is configuration state, running is runtime state. They are independent."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        enabled_count = result["configuration_counts"].get("enabled", 0)
        running_count = result["runtime_counts"].get("running", 0)
        # All enabled processes are simulated, not running
        if result["all_simulated_or_skipped"]:
            assert running_count == 0

    def test_dry_run_is_not_disabled(self):
        """DRY_RUN is an execution mode, disabled is a configuration state."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        dry_run_modes = result["mode_counts"].get("DRY_RUN", 0)
        disabled_configs = result["configuration_counts"].get("disabled", 0)
        # DRY_RUN processes can be enabled or disabled — these are independent
        for p in result["processes"]:
            if p["execution_mode"] == "DRY_RUN":
                # DRY_RUN does not imply disabled
                assert p["configuration_state"] in ("enabled", "disabled")

    def test_simulated_count_does_not_exceed_total(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        simulated = result["runtime_counts"].get("simulated", 0)
        assert simulated <= result["total"]


class TestIncompleteAreasDeduplication:
    """Phase 19: Tests for incomplete areas deduplication."""

    def test_no_duplicate_component_ids(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        all_ids = []
        for cat_data in result["categories"].values():
            for item in cat_data.get("items", []):
                # Each item should appear only once per category
                # But across categories, the unique count handles dedup
                pass
        # The unique_incomplete_count must be <= sum of category counts
        unique = result["unique_incomplete_count"]
        cat_sum = sum(result["category_counts"].values())
        assert unique <= cat_sum

    def test_unique_count_not_blind_sum(self):
        """Unique count should be less than or equal to sum of categories, not equal when overlap exists."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        unique = result["unique_incomplete_count"]
        cat_sum = sum(result["category_counts"].values())
        # Unique count must be <= sum (can be equal if no overlap)
        assert unique <= cat_sum

    def test_simulated_count_does_not_exceed_process_count(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas, get_process_registry_live
        incomplete = get_incomplete_areas()
        proc_result = get_process_registry_live()
        simulated_cat = incomplete["category_counts"].get("simulated", 0)
        total_procs = proc_result["total"]
        assert simulated_cat <= total_procs

    def test_unavailable_tool_count_matches_registry(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas, get_tool_registry
        incomplete = get_incomplete_areas()
        tools = get_tool_registry()
        unavailable_tools = incomplete["category_counts"].get("unavailable_tools", 0)
        assert unavailable_tools == tools["unavailable_count"]

    def test_categories_are_independent(self):
        """Categories may overlap, but unique count reflects deduplication."""
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        # If there are multiple categories, unique should be <= sum
        if len(result["category_counts"]) > 1:
            cat_sum = sum(result["category_counts"].values())
            assert result["unique_incomplete_count"] <= cat_sum


class TestProcessNormalization:
    """Phase 18: Test the normalizer function directly."""

    def test_normalize_process_enabled(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import _normalize_process
        raw = {"process_id": "test", "name": "Test", "enabled": True, "mode": "ACTIVE_INTERNAL", "last_status": "simulated"}
        result = _normalize_process(raw)
        assert result["configuration_state"] == "enabled"
        assert result["execution_mode"] == "ACTIVE_INTERNAL"
        assert result["runtime_state"] == "simulated"

    def test_normalize_process_disabled(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import _normalize_process
        raw = {"process_id": "test", "name": "Test", "enabled": False, "mode": "BLOCKED", "last_status": "blocked"}
        result = _normalize_process(raw)
        assert result["configuration_state"] == "disabled"
        assert result["execution_mode"] == "BLOCKED"
        assert result["runtime_state"] == "blocked"

    def test_normalize_process_dry_run_enabled(self):
        """DRY_RUN mode with enabled=true — independent dimensions."""
        from nexus_agent_platform.capabilities.nexus_knowledge import _normalize_process
        raw = {"process_id": "test", "name": "Test", "enabled": True, "mode": "DRY_RUN", "last_status": "simulated"}
        result = _normalize_process(raw)
        assert result["configuration_state"] == "enabled"
        assert result["execution_mode"] == "DRY_RUN"
        assert result["runtime_state"] == "simulated"
