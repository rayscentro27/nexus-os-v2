"""Versioned semantic-definition registry.

Every metric or status that Hermes may report must have a declared
semantic definition.  The definition specifies exactly what records
are included, what is excluded, and how the result should be
interpreted.  This prevents the "correct intent, wrong data" class
of defects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SemanticDefinition:
    """A versioned, certified semantic definition for a business metric."""
    definition_id: str
    version: str
    business_meaning: str
    business_owner: str
    technical_owner: str
    included_records: str
    excluded_records: str
    tenant_policy: str
    status_policy: str
    time_policy: str
    distinctness_policy: str
    freshness_requirement: str
    approved_source: str
    approved_fallback: str
    expected_result_type: str
    zero_is_valid: bool = True
    empty_is_valid: bool = True
    stale_allowed: bool = False
    display_requirements: str = ""
    lifecycle_state: str = "draft"
    certification_date: Optional[str] = None
    certification_evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


class SemanticRegistry:
    """Registry of all certified semantic definitions."""

    def __init__(self):
        self._definitions: Dict[str, SemanticDefinition] = {}

    def register(self, definition: SemanticDefinition) -> None:
        key = f"{definition.definition_id}@{definition.version}"
        self._definitions[key] = definition

    def get(self, definition_id: str, version: str = "") -> Optional[SemanticDefinition]:
        if version:
            return self._definitions.get(f"{definition_id}@{version}")
        # Latest version
        candidates = [d for k, d in self._definitions.items()
                      if k.startswith(f"{definition_id}@")]
        if not candidates:
            return None
        return sorted(candidates, key=lambda d: d.version)[-1]

    def list_definitions(self) -> List[SemanticDefinition]:
        return list(self._definitions.values())

    def list_ids(self) -> List[str]:
        return sorted(set(d.definition_id for d in self._definitions.values()))


# ─── Singleton ─────────────────────────────────────────────────

semantic_registry = SemanticRegistry()


# ─── Built-in definitions ──────────────────────────────────────

def _register_builtins():
    """Register the core semantic definitions for Nexus Hermes."""

    semantic_registry.register(SemanticDefinition(
        definition_id="production_client_summary",
        version="v1",
        business_meaning=(
            "Count of production client profiles in the GoClear tenant, "
            "excluding demo, certification, and tester records."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "client_profiles rows where tenant_id='goclear' AND "
            "source NOT IN ('tester_invitation', 'static_import', 'synthetic_certification')"
        ),
        excluded_records=(
            "tenant_demo_* tenants, tenant-cert-* tenants, "
            "tester_invitation source, static_import source, "
            "synthetic_certification source"
        ),
        tenant_policy="server_injected_goclear",
        status_policy="all_statuses_counted_separately",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_client_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:client_profiles",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_production_total_active_onboarding_inactive_hidden_tester",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        display_requirements=(
            "Show production total, then breakdown by status. "
            "Show tester/cert count separately. "
            "Never label onboarding as active."
        ),
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Live Ray test passed, Langfuse trace verified",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="active_client_count",
        version="v1",
        business_meaning=(
            "Count of production client profiles whose status is 'active'."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "client_profiles rows where tenant_id='goclear' AND status='active' AND "
            "source NOT IN ('tester_invitation', 'static_import', 'synthetic_certification')"
        ),
        excluded_records="same as production_client_summary plus non-active status",
        tenant_policy="server_injected_goclear",
        status_policy="active_only",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_client_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:client_profiles",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="integer",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Derived from production_client_summary v1",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="onboarding_client_count",
        version="v1",
        business_meaning=(
            "Count of production client profiles whose status is 'onboarding'."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "client_profiles rows where tenant_id='goclear' AND status='onboarding' AND "
            "source NOT IN ('tester_invitation', 'static_import', 'synthetic_certification')"
        ),
        excluded_records="same as production_client_summary plus non-onboarding status",
        tenant_policy="server_injected_goclear",
        status_policy="onboarding_only",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_client_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:client_profiles",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="integer",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="draft",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="current_running_process_summary",
        version="v1",
        business_meaning="Count and list of currently running operational processes.",
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records="nexus_process_registry entries with status=running",
        excluded_records="disabled, paused, or manual-only processes",
        tenant_policy="global",
        status_policy="running_only",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_process_id",
        freshness_requirement="real_time_file_read",
        approved_source="runtime_file:nexus_process_registry.json",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_count_and_list",
        zero_is_valid=True,
        lifecycle_state="draft",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="process_run_summary",
        version="v1",
        business_meaning=(
            "Summary of process execution runs from Supabase, "
            "including running, completed, failed, and blocked."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "nexus_process_runs rows, grouped by status, "
            "ordered by last_run_at DESC"
        ),
        excluded_records="deleted runs",
        tenant_policy="server_injected",
        status_policy="all_statuses",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_run_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:nexus_process_runs",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_counts_and_recent_runs",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_process_status",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="process_definition_summary",
        version="v1",
        business_meaning=(
            "Summary of configured process definitions from Supabase, "
            "including enabled/disabled state and schedule."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records="nexus_process_definitions rows",
        excluded_records="deleted definitions",
        tenant_policy="server_injected",
        status_policy="all_statuses",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_definition_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:nexus_process_definitions",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_counts_and_definitions",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_process_status",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="process_failure_summary",
        version="v1",
        business_meaning=(
            "Failed, blocked, timed out, cancelled, or partial process runs "
            "from the last 24 hours. Distinguishes active failures from resolved."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "nexus_process_runs where status IN "
            "('FAILED','BLOCKED','TIMED_OUT','CANCELLED','PARTIAL') "
            "AND last_run_at > now() - interval '24 hours'"
        ),
        excluded_records="successful runs, runs older than 24 hours",
        tenant_policy="server_injected",
        status_policy="failed_only",
        time_policy="last_24_hours",
        distinctness_policy="one_row_per_run_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:nexus_process_runs",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_failures_and_counts",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_failures",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="research_run_summary",
        version="v1",
        business_meaning=(
            "Summary of research runs and results from Supabase, "
            "including recent completions, failures, and source breakdown."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "nexus_research_runs (25 rows) and nexus_research_results (40 rows), "
            "ordered by created_at DESC"
        ),
        excluded_records="deleted runs",
        tenant_policy="server_injected",
        status_policy="all_statuses",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_run_id_and_result_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:nexus_research_runs,nexus_research_results",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_runs_and_results",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_research_history",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="business_opportunity_summary",
        version="v1",
        business_meaning=(
            "Current business opportunities from Supabase, "
            "including status, revenue potential, and action state."
        ),
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records=(
            "business_opportunities rows ordered by updated_at DESC"
        ),
        excluded_records="deleted opportunities",
        tenant_policy="server_injected",
        status_policy="all_statuses",
        time_policy="current_snapshot",
        distinctness_policy="one_row_per_opportunity_id",
        freshness_requirement="real_time_supabase_query",
        approved_source="supabase_table:business_opportunities",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_opportunities",
        zero_is_valid=True,
        empty_is_valid=True,
        stale_allowed=False,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_opportunities",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="current_failure_summary",
        version="v1",
        business_meaning="Today's failures from the heartbeat log.",
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records="Entries from nexus_active_operator_heartbeat_latest.json",
        excluded_records="Successful runs, historical failures before today",
        tenant_policy="global",
        status_policy="failed_only_today",
        time_policy="today",
        distinctness_policy="one_entry_per_failure",
        freshness_requirement="real_time_file_read",
        approved_source="runtime_file:nexus_active_operator_heartbeat_latest.json",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_working_and_needs_attention",
        zero_is_valid=True,
        lifecycle_state="draft",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="current_alpha_status",
        version="v1",
        business_meaning="Current Alpha agent operational status.",
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records="Alpha telegram status from alpha_telegram_status.json",
        excluded_records="Historical Alpha research results",
        tenant_policy="global",
        status_policy="current_only",
        time_policy="current_snapshot",
        distinctness_policy="single_status_record",
        freshness_requirement="real_time_file_read",
        approved_source="runtime_file:alpha_telegram_status.json",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_status_fields",
        zero_is_valid=True,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy hermes.py _get_alpha_status",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="current_trading_status",
        version="v1",
        business_meaning="Current Oanda practice trading engine status.",
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records="Trading engine status from oanda_practice_engine_status_latest.json",
        excluded_records="Historical trades, account balances",
        tenant_policy="global",
        status_policy="current_only",
        time_policy="current_snapshot",
        distinctness_policy="single_status_record",
        freshness_requirement="real_time_file_read",
        approved_source="runtime_file:oanda_practice_engine_status_latest.json",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_status_fields",
        zero_is_valid=True,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_trading_status",
    ))

    semantic_registry.register(SemanticDefinition(
        definition_id="pending_approval_summary",
        version="v1",
        business_meaning="Items awaiting Ray's approval in the review queue.",
        business_owner="Ray",
        technical_owner="Hermes Platform",
        included_records="ray_review_queue_latest.json entries with status=pending",
        excluded_records="Approved, rejected, or expired items",
        tenant_policy="global",
        status_policy="pending_only",
        time_policy="current_snapshot",
        distinctness_policy="one_entry_per_item_id",
        freshness_requirement="real_time_file_read",
        approved_source="runtime_file:ray_review_queue_latest.json",
        approved_fallback="unavailable_status_no_fabrication",
        expected_result_type="dict_with_count_and_items",
        zero_is_valid=True,
        lifecycle_state="certified_read",
        certification_date="2026-08-05",
        certification_evidence="Migrated from legacy bridge tool_get_pending_approvals",
    ))


_register_builtins()
