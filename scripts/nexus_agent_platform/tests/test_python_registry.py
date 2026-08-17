"""Tests for the deterministic Nexus Python capability registry."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.capabilities.python_registry import (
    CapabilityMetadata,
    CostClass,
    ExecutionType,
    PiiClassification,
    PythonCapabilityRegistry,
    RiskClass,
    TenantScope,
    build_default_registry,
    get_python_capability_registry,
    lookup_python_capability,
    render_python_capability_registry_markdown,
)


class TestPythonCapabilityRegistry:
    def test_registry_loads(self):
        registry = build_default_registry()
        summary = registry.summary()
        assert summary["registry_id"] == "NEXUS_PYTHON_CAPABILITY_REGISTRY"
        assert summary["count"] >= 10
        assert summary["execution_types"]["DETERMINISTIC"] > 0
        assert summary["cost_classes"]["ZERO_MODEL_COST"] > 0

    def test_unique_capability_ids(self):
        registry = build_default_registry()
        caps = registry.list_capabilities()
        ids = [cap["capability_id"] for cap in caps]
        assert len(ids) == len(set(ids))

    def test_lookup_by_capability_id(self):
        registry = build_default_registry()
        cap = registry.get("get_system_health")
        assert cap is not None
        assert cap.capability_id == "get_system_health"
        assert cap.module == "nexus_agent_platform.capabilities.shared"

    def test_lookup_helper(self):
        cap = lookup_python_capability("get_system_health")
        assert cap is not None
        assert cap["capability_id"] == "get_system_health"
        assert cap["execution_type"] == "DETERMINISTIC"

    def test_registry_lookup_capability(self):
        result = get_python_capability_registry("get_system_health")
        assert result["status"] == "success"
        assert result["capability"]["capability_id"] == "get_system_health"
        assert result["summary"]["registry_id"] == "NEXUS_PYTHON_CAPABILITY_REGISTRY"

    def test_invalid_capability_rejection(self):
        registry = PythonCapabilityRegistry()
        with pytest.raises(ValueError, match="unknown CostClass value"):
            registry.register_spec(
                {
                    "capability_id": "bad_cost",
                    "name": "Bad Cost",
                    "description": "invalid",
                    "module": "example.module",
                    "callable": "callable",
                    "execution_type": "DETERMINISTIC",
                    "cost_class": "NOT_REAL",
                }
            )

    def test_duplicate_capability_rejection(self):
        registry = PythonCapabilityRegistry()
        spec = {
            "capability_id": "dup",
            "name": "Duplicate",
            "description": "duplicate",
            "module": "example.module",
            "callable": "callable",
            "execution_type": "DETERMINISTIC",
            "cost_class": "ZERO_MODEL_COST",
        }
        registry.register_spec(spec)
        with pytest.raises(ValueError, match="duplicate capability_id"):
            registry.register_spec(spec)

    def test_from_json_loads(self, tmp_path):
        path = tmp_path / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "capabilities": [
                        {
                            "capability_id": "json_cap",
                            "name": "JSON Capability",
                            "description": "loaded from json",
                            "module": "example.module",
                            "callable": "run",
                            "execution_type": "DETERMINISTIC",
                            "cost_class": "ZERO_MODEL_COST",
                            "enabled": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        registry = PythonCapabilityRegistry().from_json(path)
        assert registry.has("json_cap")

    def test_deterministic_cost_classification(self):
        registry = build_default_registry()
        deterministic = registry.query(execution_type=ExecutionType.DETERMINISTIC)
        assert deterministic
        assert all(cap.cost_class == CostClass.ZERO_MODEL_COST for cap in deterministic)

    def test_side_effect_tenant_pii_approval_metadata(self):
        registry = build_default_registry()
        funding = registry.get("get_funding_readiness")
        research = registry.get("get_recent_research")
        assert funding is not None
        assert funding.side_effecting is False
        assert funding.tenant_scoped is True
        assert funding.tenant_scope == TenantScope.CLIENT
        assert funding.pii_classification == PiiClassification.CLIENT_PII
        assert funding.approval_required is False
        assert research is not None
        assert research.enabled is False
        assert research.approval_required is True
        assert research.execution_type == ExecutionType.AI_ASSISTED
        assert research.cost_class == CostClass.AI_TIER_1

    def test_disabled_capabilities(self):
        registry = build_default_registry()
        disabled = registry.query(enabled=False)
        assert disabled
        assert any(cap.capability_id == "get_recent_research" for cap in disabled)

    def test_filter_by_execution_type(self):
        registry = build_default_registry()
        api_caps = registry.query(execution_type=ExecutionType.API)
        ids = {cap.capability_id for cap in api_caps}
        assert {"get_approval_status", "get_funding_readiness", "get_client_profile"} <= ids

    def test_filter_by_cost_class(self):
        registry = build_default_registry()
        zero = registry.query(cost_class=CostClass.ZERO_MODEL_COST)
        ids = {cap.capability_id for cap in zero}
        assert "get_system_health" in ids
        assert "get_runtime_capabilities" in ids

    def test_markdown_render(self):
        md = render_python_capability_registry_markdown()
        assert "# Nexus Python Capability Registry" in md
        assert "get_system_health" in md
        assert "get_recent_research" in md

    def test_invalid_ai_assisted_zero_cost_rejected(self):
        registry = PythonCapabilityRegistry()
        with pytest.raises(ValueError, match="AI-assisted capability"):
            registry.register(
                CapabilityMetadata(
                    capability_id="bad_ai",
                    name="Bad AI",
                    description="invalid",
                    module="example.module",
                    callable_name="callable",
                    execution_type=ExecutionType.AI_ASSISTED,
                    cost_class=CostClass.ZERO_MODEL_COST,
                )
            )

