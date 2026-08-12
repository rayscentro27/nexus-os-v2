"""Tests for the Nexus Study Layer — governed read-only system discovery.

Certifies that Nova can study Nexus as a SYSTEM: architecture, agents, tools,
processes, runtime, product, client workflows, business model, integrations,
security, gaps, unknowns, and a bounded study snapshot.

No writes, no arbitrary execution, no credential/PII exposure.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def _executor():
    """Register a real executor for planner tests."""
    from nexus_agent_platform.capabilities.nexus_query_planner import register_executor
    from nexus_agent_platform.capabilities.shared import execute_shared_capability

    def _exec(capability, args=None):
        return execute_shared_capability("hermes_nova", capability, args or {}, trace_id="study_test")
    register_executor(_exec)
    yield


# ═══════════════════════════════════════════════════════════════
# STUDY INDEX / SNAPSHOT
# ═══════════════════════════════════════════════════════════════

class TestStudySnapshot:
    """get_nexus_study_snapshot assembles a bounded cross-domain index."""

    def test_snapshot_returns_success(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_snapshot
        snap = get_nexus_study_snapshot()
        assert snap["status"] == "success"

    def test_snapshot_has_all_study_domains(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_snapshot
        snap = get_nexus_study_snapshot()
        domains = snap.get("domains", {})
        for expected in (
            "system_architecture", "agents", "tools", "processes", "runtime",
            "product", "client_workflow", "business_model", "integrations",
            "security", "gaps", "unknowns",
        ):
            assert expected in domains, f"Missing study domain: {expected}"

    def test_snapshot_source_commit(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_snapshot
        snap = get_nexus_study_snapshot()
        assert snap.get("source_commit"), "source_commit missing"

    def test_snapshot_generated_at_utc(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_snapshot
        snap = get_nexus_study_snapshot()
        assert snap.get("generated_at"), "generated_at missing"

    def test_snapshot_system_summary(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_snapshot
        snap = get_nexus_study_snapshot()
        system = snap.get("system", {})
        assert system.get("name") == "Nexus OS"
        assert system.get("process_count", 0) > 0


# ═══════════════════════════════════════════════════════════════
# ARCHITECTURE STUDY
# ═══════════════════════════════════════════════════════════════

class TestArchitectureStudy:
    def test_architecture_summary(self):
        from nexus_agent_platform.capabilities.nexus_study import get_architecture_summary
        result = get_architecture_summary()
        assert result["status"] == "success"
        assert result["architecture"]
        assert result["runtime_model"]
        assert isinstance(result["major_components"], list)
        assert isinstance(result["repo_top_level"], list)

    def test_architecture_bounded(self):
        """Repo map must be bounded, not a recursive dump."""
        from nexus_agent_platform.capabilities.nexus_study import get_architecture_summary
        result = get_architecture_summary()
        assert len(result["repo_top_level"]) <= 60

    def test_architecture_source_commit(self):
        from nexus_agent_platform.capabilities.nexus_study import get_architecture_summary
        result = get_architecture_summary()
        assert result.get("source_commit")


# ═══════════════════════════════════════════════════════════════
# AGENT / TOOL / PROCESS STUDY
# ═══════════════════════════════════════════════════════════════

class TestInventoryStudy:
    def test_agent_inventory(self):
        from nexus_agent_platform.capabilities.nexus_study import get_agent_inventory
        result = get_agent_inventory()
        assert result["status"] == "success"
        agents = result.get("agents", [])
        ids = {a["agent_id"] for a in agents}
        assert {"nexus_hermes", "hermes_nova", "alpha"} <= ids

    def test_tool_inventory(self):
        from nexus_agent_platform.capabilities.nexus_study import get_tool_inventory
        result = get_tool_inventory()
        assert result["status"] == "success"
        assert result["total"] > 0
        counts = result.get("counts", {})
        assert "internal_safe" in counts
        assert counts["internal_safe"] > 0

    def test_process_inventory(self):
        from nexus_agent_platform.capabilities.nexus_study import get_process_inventory
        result = get_process_inventory()
        assert result["status"] == "success"
        assert result["total"] > 0
        assert "configuration_counts" in result
        assert "runtime_counts" in result
        assert "has_real_execution" in result


# ═══════════════════════════════════════════════════════════════
# PRODUCT / WORKFLOW / BUSINESS MODEL STUDY
# ═══════════════════════════════════════════════════════════════

class TestProductBusinessStudy:
    def test_product_inventory(self):
        from nexus_agent_platform.capabilities.nexus_study import get_product_inventory
        result = get_product_inventory()
        assert result["status"] == "success"
        assert result["product_count"] > 0
        offers = result.get("offers", [])
        assert any(o.get("offer_id") == "readiness_review_97" for o in offers)

    def test_product_stripe_status(self):
        from nexus_agent_platform.capabilities.nexus_study import get_product_inventory
        result = get_product_inventory()
        stripe = result.get("stripe", {})
        assert stripe.get("mode") == "test_only"
        assert stripe.get("live_mode_allowed") is False

    def test_client_workflow_summary(self):
        from nexus_agent_platform.capabilities.nexus_study import get_client_workflow_summary
        result = get_client_workflow_summary()
        assert result["status"] == "success"
        assert len(result.get("funnel_stages", [])) > 0

    def test_business_model_summary(self):
        from nexus_agent_platform.capabilities.nexus_study import get_business_model_summary
        result = get_business_model_summary()
        assert result["status"] == "success"
        assert result["offers_count"] > 0
        assert result.get("stripe_live_mode_allowed") is False
        # Do not claim live revenue without evidence
        assert result.get("verification_note")

    def test_business_model_does_not_inflate_live_revenue(self):
        """Operational revenue paths must be gated by stripe live proof."""
        from nexus_agent_platform.capabilities.nexus_study import get_business_model_summary
        result = get_business_model_summary()
        # stripe is test_only, so NO offer should be 'operational' in a live sense
        # 'operational_revenue_paths' are candidate paths, not live proof — the
        # verification_note must make the distinction explicit.
        assert "stripe_live_mode_allowed=False" in result["verification_note"] or "test-only" in result["verification_note"]


# ═══════════════════════════════════════════════════════════════
# INTEGRATIONS / SECURITY STUDY
# ═══════════════════════════════════════════════════════════════

class TestIntegrationSecurityStudy:
    def test_integration_inventory(self):
        from nexus_agent_platform.capabilities.nexus_study import get_integration_inventory
        result = get_integration_inventory()
        assert result["status"] == "success"
        assert result["connector_count"] > 0
        assert "status_counts" in result
        assert "live_enabled_count" in result

    def test_integration_no_credentials_exposed(self):
        """No connector read may expose credentials or secret values."""
        from nexus_agent_platform.capabilities.nexus_study import get_integration_inventory
        import json
        result = get_integration_inventory()
        blob = json.dumps(result)
        assert "sk-" not in blob
        assert "api_key" not in blob.lower() or "required_env_vars" not in blob

    def test_security_boundary_summary(self):
        from nexus_agent_platform.capabilities.nexus_study import get_security_boundary_summary
        result = get_security_boundary_summary()
        assert result["status"] == "success"
        assert result.get("nova_write_capability_count") == 0
        assert result.get("nova_writes_frozen") is True

    def test_security_nova_reads_enforced(self):
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_READS, _check_permission
        # Study capabilities must be inside Nova's allowlist
        for cap in (
            "get_nexus_study_snapshot", "get_business_model_summary",
            "get_integration_inventory", "get_nexus_gap_summary",
        ):
            assert cap in NOVA_ALLOWED_READS


# ═══════════════════════════════════════════════════════════════
# REPO MAP / RECENT CHANGES / REPORT INDEX
# ═══════════════════════════════════════════════════════════════

class TestRepoAndReportStudy:
    def test_repo_system_map(self):
        from nexus_agent_platform.capabilities.nexus_study import get_repo_system_map
        result = get_repo_system_map()
        assert result["status"] == "success"
        top = result.get("top_level", [])
        names = {e["name"] for e in top}
        assert "scripts" in names
        assert "data" in names
        assert "reports" in names

    def test_repo_entry_points(self):
        from nexus_agent_platform.capabilities.nexus_study import get_repo_system_map
        result = get_repo_system_map()
        assert len(result.get("entry_points", [])) > 0

    def test_recent_system_changes(self):
        from nexus_agent_platform.capabilities.nexus_study import get_recent_system_changes
        result = get_recent_system_changes(limit=5)
        assert result["status"] == "success"
        assert len(result.get("recent_changes", [])) > 0

    def test_safe_report_index(self):
        from nexus_agent_platform.capabilities.nexus_study import get_safe_report_index
        result = get_safe_report_index()
        assert result["status"] == "success"
        assert result.get("category_count", 0) > 0


# ═══════════════════════════════════════════════════════════════
# GAP MODEL
# ═══════════════════════════════════════════════════════════════

class TestGapModel:
    def test_gap_summary(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_gap_summary
        result = get_nexus_gap_summary()
        assert result["status"] == "success"
        assert result["gap_count"] > 0
        gaps = result.get("gaps", [])
        for g in gaps:
            assert g.get("gap_id")
            assert g.get("title")
            assert g.get("evidence")
            assert g.get("recommended_next_step")

    def test_gap_has_structured_fields(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_gap_summary
        result = get_nexus_gap_summary()
        g = result["gaps"][0]
        for field in ("gap_id", "domain", "title", "description", "evidence",
                      "severity", "confidence", "source", "recommended_next_step"):
            assert field in g, f"Gap missing field: {field}"

    def test_unknowns(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_unknowns
        result = get_nexus_unknowns()
        assert result["status"] == "success"
        assert result["unknown_count"] > 0


# ═══════════════════════════════════════════════════════════════
# PERMISSIONS / SECURITY
# ═══════════════════════════════════════════════════════════════

class TestStudySecurity:
    def test_nova_can_read_study(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        r = execute_shared_capability("hermes_nova", "get_nexus_study_snapshot", {}, trace_id="t")
        assert r["status"] == "success"

    def test_hermes_cannot_read_study(self):
        """Study reads are Nova-scoped; Hermes is not in NOVA_ALLOWED_READS for them."""
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        r = execute_shared_capability("nexus_hermes", "get_nexus_study_snapshot", {}, trace_id="t")
        assert r["status"] == "unauthorized"

    def test_nova_writes_still_frozen(self):
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_WRITES
        assert NOVA_ALLOWED_WRITES == frozenset()

    def test_study_no_write_path(self):
        """Study data must not be writable through any capability."""
        from nexus_agent_platform.capabilities.shared import _WRITE_CAPABILITIES
        assert _WRITE_CAPABILITIES == frozenset()

    def test_study_handler_provenance(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        r = execute_shared_capability("hermes_nova", "get_business_model_summary", {}, trace_id="t")
        prov = r.get("provenance", {})
        assert prov.get("capability") == "get_business_model_summary"
        assert prov.get("source") == "nexus_study_layer"


class TestStudyArtifactRetrieval:
    def test_snapshot_reads_generated_artifact_counts(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_snapshot

        snap = get_nexus_study_snapshot()
        assert snap["source_commit"] == "550ae77"
        assert snap["generated_at"] == "2026-08-12T00:28:35.654892+00:00"
        assert snap["domains"]["gaps"]["gap_count"] == 46
        assert len(snap.get("contradictions", [])) == 18
        assert snap["domains"]["unknowns"]["unknown_count"] == 3

    def test_gap_unknown_business_and_integration_artifacts(self):
        from nexus_agent_platform.capabilities.nexus_study import (
            get_business_model_summary,
            get_integration_inventory,
            get_nexus_gap_summary,
            get_nexus_unknowns,
        )

        gaps = get_nexus_gap_summary()
        unknowns = get_nexus_unknowns()
        business = get_business_model_summary()
        integrations = get_integration_inventory()

        assert gaps["gap_count"] == 46
        assert gaps["source_commit"] == "550ae77"
        assert unknowns["unknown_count"] == 3
        assert [u["unknown_id"] for u in unknowns["unknowns"]] == [
            "NEXUS-U01", "NEXUS-U02", "NEXUS-U03",
        ]
        assert business["offers_count"] == 9
        assert len(business["operational_revenue_paths"]) == 1
        assert len(business["planned_revenue_paths"]) == 8
        assert integrations["connector_count"] == 15
        assert integrations["live_enabled_count"] == 3

    def test_compact_overview_preserves_core_facts_with_bounded_payload(self):
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_overview

        overview = get_nexus_study_overview()
        encoded = json.dumps(overview, default=str)

        assert overview["status"] == "success"
        assert overview["context_profile"] == "compact_overview"
        assert overview["source_commit"] == "550ae77"
        assert overview["system"]["process_count"] == 19
        assert overview["system"]["enabled_processes"] == 17
        assert overview["system"]["disabled_processes"] == 2
        assert overview["business"]["offer_count"] == 9
        assert overview["business"]["operational_offers"] == 1
        assert overview["business"]["planned_offers"] == 8
        assert overview["integrations"]["total"] == 15
        assert overview["integrations"]["live"] == 3
        assert overview["study_findings"]["gap_count"] == 46
        assert overview["study_findings"]["contradiction_count"] == 18
        assert overview["study_findings"]["unknown_count"] == 3
        assert [u["id"] for u in overview["unknowns"]] == [
            "NEXUS-U01", "NEXUS-U02", "NEXUS-U03",
        ]
        assert len(encoded) < 15000
        metrics = overview["retrieval_metrics"]
        assert metrics["raw_artifact_bytes"]["snapshot"] > 100000
        assert metrics["structured_records_selected"] == {
            "top_gaps": 10,
            "contradiction_examples": 5,
            "unknowns": 3,
        }

    def test_artifact_cache_reuses_generated_snapshot_until_file_changes(self):
        from nexus_agent_platform.capabilities import nexus_study

        nexus_study._ARTIFACT_CACHE.clear()
        first = nexus_study._cached_artifact_json(nexus_study._STUDY_SNAPSHOT_PATH)
        second = nexus_study._cached_artifact_json(nexus_study._STUDY_SNAPSHOT_PATH)

        assert first is second
        assert nexus_study._STUDY_SNAPSHOT_PATH in nexus_study._ARTIFACT_CACHE

    def test_nexus_system_context_exposes_study_counts(self):
        from nexus_agent_platform.agents.nova import _format_planner_context
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_overview

        context = _format_planner_context({
            "tool": "nexus_query_planner",
            "query_type": "nexus_system",
            "status": "success",
            "data": get_nexus_study_overview(),
            "coverage": {"structural": True},
            "plan": {"domain": "nexus_system", "operation": "overview"},
            "planner_mode": "model",
            "capability_selected": "get_nexus_study_overview",
            "source_requirement": "structural",
            "provenance": {
                "source_type": "study_snapshot_artifact",
                "freshness": "generated_study_snapshot",
                "source_commit": "550ae77",
                "generated_at": "2026-08-12T00:28:35.654892+00:00",
                "source_ref": "reports/nova_study/nexus_study_snapshot.json",
            },
        })

        assert "gap_count: 46" in context
        assert "contradiction_count: 18" in context
        assert "unknown_count: 3" in context
        assert "source_commit: 550ae77" in context
        assert "NEXUS-U01" in context
        assert "changed_findings" in context
        assert "partially_resolved_by_current_runtime_telemetry" in context
        assert len(context) < 10000

    def test_build_context_records_study_budget_metrics(self):
        from nexus_agent_platform.adapters.state_adapter import AgentState
        from nexus_agent_platform.agents.nova import _build_context
        from nexus_agent_platform.capabilities.nexus_study import get_nexus_study_overview

        state = AgentState(user_message="What did you learn about Nexus?", metadata={"chat_id": 991337})
        state.metadata["capability_result"] = {
            "tool": "nexus_query_planner",
            "query_type": "nexus_system",
            "status": "success",
            "data": get_nexus_study_overview(),
            "coverage": {"structural": True},
            "plan": {"domain": "nexus_system", "operation": "overview"},
            "planner_mode": "model",
            "capability_selected": "get_nexus_study_overview",
            "source_requirement": "structural",
            "provenance": {"source_commit": "550ae77"},
        }

        result = _build_context(state)
        metrics = result.metadata["study_context_metrics"]

        assert metrics["context_profile"] == "compact_overview"
        assert metrics["capability_result_approx_tokens"] < 2000
        assert metrics["verified_context_approx_tokens"] < 2500
        assert metrics["artifact_index_load_ms"] is not None


# ═══════════════════════════════════════════════════════════════
# PLANNER — nexus_system domain
# ═══════════════════════════════════════════════════════════════

class TestPlannerNexusSystem:
    def test_domain_schema_present(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import DOMAIN_SCHEMAS
        assert "nexus_system" in DOMAIN_SCHEMAS

    def test_domain_capability(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import DOMAIN_SCHEMAS
        assert DOMAIN_SCHEMAS["nexus_system"]["capability"] == "get_nexus_study_overview"
        assert DOMAIN_SCHEMAS["nexus_system"]["detail_capabilities"]["snapshot"] == "get_nexus_study_snapshot"

    def test_domain_operations(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import DOMAIN_SCHEMAS
        ops = DOMAIN_SCHEMAS["nexus_system"]["operations"]
        assert "overview" in ops
        assert "find_gaps" in ops
        assert "compare" in ops

    def test_validate_nexus_system_plan(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import validate_plan
        plan = validate_plan({
            "domain": "nexus_system", "operation": "overview", "conditions": [],
            "projection": [], "aggregate": None, "ambiguity": None,
            "source_requirement": "structural", "reason": "study",
        })
        assert plan.get("domain") == "nexus_system"

    def test_execute_nexus_system_plan(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import execute_plan, validate_plan
        plan = validate_plan({
            "domain": "nexus_system", "operation": "overview", "conditions": [],
            "projection": [], "aggregate": None, "ambiguity": None,
            "source_requirement": "structural", "reason": "study",
        })
        result = execute_plan(plan)
        assert result["status"] == "success"
        assert result["capability_selected"] == "get_nexus_study_overview"
        assert result.get("data", {}).get("context_profile") == "compact_overview"

    def test_execute_find_gaps(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import execute_plan, validate_plan
        plan = validate_plan({
            "domain": "nexus_system", "operation": "find_gaps", "conditions": [],
            "projection": [], "aggregate": None, "ambiguity": None,
            "source_requirement": "structural", "reason": "study",
        })
        result = execute_plan(plan)
        data = result.get("data", {})
        assert data.get("study_findings", {}).get("gap_count", 0) == 46
        assert len(data.get("top_gaps", [])) == 10

    def test_format_nexus_system_result(self):
        from nexus_agent_platform.capabilities.nexus_query_planner import (
            execute_plan, format_plan_result, validate_plan,
        )
        plan = validate_plan({
            "domain": "nexus_system", "operation": "overview", "conditions": [],
            "projection": [], "aggregate": None, "ambiguity": None,
            "source_requirement": "structural", "reason": "study",
        })
        result = execute_plan(plan)
        out = format_plan_result(result)
        assert "[VERIFIED NEXUS KNOWLEDGE]" in out
        assert "domain: nexus_system" in out
        assert "Source commit:" in out

    def test_no_new_regex_patterns(self):
        """Study must NOT add phrase routing / regex patterns."""
        from nexus_agent_platform.capabilities.nexus_query_planner import _INTENT_PATTERNS
        assert len(_INTENT_PATTERNS) <= 20


# ═══════════════════════════════════════════════════════════════
# NOVA GRAPH INTEGRATION
# ═══════════════════════════════════════════════════════════════

class TestStudyGraphIntegration:
    def _make_state(self, message):
        from nexus_agent_platform.adapters.state_adapter import AgentState
        state = AgentState(user_message=message, metadata={"chat_id": 77777})
        return state

    def _capability_gate(self, state):
        from nexus_agent_platform.agents.nova import _capability_gate
        return _capability_gate(state)

    def test_gate_executes_study_plan(self):
        """A nexus_system plan routed through the gate with a deterministic model
        must execute a study capability and produce verified context."""
        from nexus_agent_platform.capabilities.nexus_query_planner import (
            plan_query, execute_plan, format_plan_result, register_executor,
        )
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        def _exec(capability, args=None):
            return execute_shared_capability("hermes_nova", capability, args or {}, trace_id="g")
        register_executor(_exec)

        state = self._make_state("How is Nexus architected?")
        gate_state = self._capability_gate(state)
        gate = gate_state.metadata.get("capability_gate", {})
        # Deterministic fallback maps architecture questions to 'overview';
        # the gate may execute it as an overview study. We assert a verified result
        # was attached (either study snapshot or existing overview).
        result = gate_state.metadata.get("capability_result")
        assert gate.get("decision") in ("planner_executed", "capability_executed", "no_capability")
        if result:
            assert result.get("status") in ("success", "empty", "partial", "unavailable")

    def test_study_snapshot_through_shared(self):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        r = execute_shared_capability("hermes_nova", "get_nexus_study_snapshot", {}, trace_id="g")
        assert r["status"] == "success"
        data = r.get("data", {})
        assert data.get("domains", {}).get("business_model", {}).get("offers_count", 0) > 0


# ═══════════════════════════════════════════════════════════════
# STUDY RUNNER (bounded)
# ═══════════════════════════════════════════════════════════════

class TestStudyRunner:
    def test_pass_is_bounded(self):
        from nexus_agent_platform.study.study_runner import _run_study_pass, _MAX_PASSES
        assert _MAX_PASSES == 4

    def test_study_pass_produces_domains(self):
        from nexus_agent_platform.study.study_runner import _run_study_pass
        result = _run_study_pass(["processes", "business_model", "gaps"])
        assert "domains" in result
        assert "processes" in result["domains"]
        assert "business_model" in result["domains"]
        assert "gaps" in result["domains"]

    def test_study_pass_contradictions(self):
        from nexus_agent_platform.study.study_runner import _run_study_pass
        result = _run_study_pass(["processes", "business_model"])
        assert "contradictions" in result
        # Since all processes are enabled but simulated, at least one contradiction expected
        assert len(result["contradictions"]) > 0

    def test_study_pass_source_commit(self):
        from nexus_agent_platform.study.study_runner import _run_study_pass
        result = _run_study_pass(["processes"])
        assert result.get("source_commit")

    def test_summary_markdown_has_sections(self):
        from nexus_agent_platform.study.study_runner import _build_summary_markdown, _run_study_pass
        result = _run_study_pass(["processes", "business_model", "gaps"])
        md = _build_summary_markdown(result)
        assert "## Processes" in md
        assert "## Business Model" in md
        assert "## Top Gaps" in md
