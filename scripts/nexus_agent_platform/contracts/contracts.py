"""Executable capability contracts.

Every production-reachable capability must have a CapabilityContract
that declares its versioned handler, source, authorization, freshness,
fallback, and lifecycle state.  Only certified capabilities may execute
in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class LifecycleState(str, Enum):
    DRAFT = "draft"
    SHADOW = "shadow"
    CERTIFIED_READ = "certified_read"
    CERTIFIED_ACTION = "certified_action"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


class SideEffectClass(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"


@dataclass
class CapabilityContract:
    """Versioned executable contract for a single capability."""
    capability_id: str
    capability_version: str
    semantic_definition_id: str
    description: str
    supported_operations: List[str] = field(default_factory=list)
    negative_patterns: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    canonical_handler_id: str = ""
    authoritative_source: str = ""
    cache_policy: str = "none"
    freshness_policy: str = "real_time"
    tenant_scope_policy: str = "server_injected"
    authorization_policy: str = "admin_only"
    filter_policy: Dict[str, Any] = field(default_factory=dict)
    query_or_template_id: str = ""
    side_effect_class: str = SideEffectClass.READ.value
    confirmation_required: bool = False
    idempotency_policy: str = "none"
    timeout_seconds: int = 30
    retry_policy: str = "none"
    fallback_policy: str = "fail_closed"
    trace_attributes: Dict[str, str] = field(default_factory=dict)
    response_renderer: str = "deterministic"
    owner: str = ""
    lifecycle: str = LifecycleState.DRAFT.value
    test_fixture: Optional[str] = None
    certification_result: Optional[str] = None

    def is_certified(self) -> bool:
        return self.lifecycle in (
            LifecycleState.CERTIFIED_READ.value,
            LifecycleState.CERTIFIED_ACTION.value,
        )

    def is_production_allowed(self) -> bool:
        return self.is_certified()

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


class ContractRegistry:
    """Registry of all capability contracts."""

    def __init__(self):
        self._contracts: Dict[str, CapabilityContract] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, contract: CapabilityContract, handler: Optional[Callable] = None) -> None:
        key = f"{contract.capability_id}@{contract.capability_version}"
        self._contracts[key] = contract
        if handler:
            self._handlers[key] = handler

    def get(self, capability_id: str, version: str = "") -> Optional[CapabilityContract]:
        if version:
            return self._contracts.get(f"{capability_id}@{version}")
        candidates = [c for k, c in self._contracts.items()
                      if k.startswith(f"{capability_id}@")]
        if not candidates:
            return None
        return sorted(candidates, key=lambda c: c.capability_version)[-1]

    def get_handler(self, capability_id: str, version: str = "") -> Optional[Callable]:
        if version:
            return self._handlers.get(f"{capability_id}@{version}")
        candidates = [(k, h) for k, h in self._handlers.items()
                      if k.startswith(f"{capability_id}@")]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[-1][1]

    def list_contracts(self) -> List[CapabilityContract]:
        return list(self._contracts.values())

    def list_certified(self) -> List[CapabilityContract]:
        return [c for c in self._contracts.values() if c.is_certified()]

    def list_quarantined(self) -> List[CapabilityContract]:
        return [c for c in self._contracts.values()
                if c.lifecycle == LifecycleState.QUARANTINED.value]

    def list_production_allowed(self) -> List[CapabilityContract]:
        return [c for c in self._contracts.values() if c.is_production_allowed()]


# ─── Singleton ─────────────────────────────────────────────────

contract_registry = ContractRegistry()


# ─── Built-in contracts ────────────────────────────────────────

def _register_builtins():
    """Register certified capability contracts."""

    from nexus_agent_platform.agents.hermes import (
        _get_client_count,
        _get_system_status,
        _get_failure_report,
        _get_alpha_status,
        _get_process_status,
        _get_process_failures,
        _get_research_history,
        _get_opportunities,
        _get_trading_status,
        _get_pending_approvals,
    )

    # ── Certified Read: Client Count ───────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="get_client_count",
        capability_version="v2",
        semantic_definition_id="production_client_summary@v1",
        description="Query Supabase client_profiles for authoritative production counts",
        supported_operations=["retrieve_metric"],
        canonical_handler_id="hermes._get_client_count",
        authoritative_source="supabase_table:client_profiles",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="server_injected_goclear",
        authorization_policy="admin_only",
        filter_policy={
            "tenant_id": "goclear",
            "exclude_sources": ["tester_invitation", "static_import", "synthetic_certification"],
        },
        query_or_template_id="GET /rest/v1/client_profiles?select=tenant_id,status,client_visible,source",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="deterministic_client_count",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_client_count)

    # ── Certified Read: System Status ──────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="get_system_status",
        capability_version="v1",
        semantic_definition_id="current_running_process_summary@v1",
        description="Read process registry for system status",
        supported_operations=["retrieve_status"],
        canonical_handler_id="hermes._get_system_status",
        authoritative_source="runtime_file:nexus_process_registry.json",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="global",
        authorization_policy="admin_only",
        query_or_template_id="READ nexus_process_registry.json",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="ceo_formatter",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_system_status)

    # ── Certified Read: Failure Report ─────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="get_failure_report",
        capability_version="v1",
        semantic_definition_id="current_failure_summary@v1",
        description="Read heartbeat log for today's failures",
        supported_operations=["retrieve_status"],
        canonical_handler_id="hermes._get_failure_report",
        authoritative_source="runtime_file:nexus_active_operator_heartbeat_latest.json",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="global",
        authorization_policy="admin_only",
        query_or_template_id="READ nexus_active_operator_heartbeat_latest.json",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="ceo_formatter",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_failure_report)

    # ── Certified Read: Alpha Status ───────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="get_alpha_status",
        capability_version="v1",
        semantic_definition_id="current_alpha_status@v1",
        description="Read Alpha agent operational status",
        supported_operations=["retrieve_status"],
        canonical_handler_id="hermes._get_alpha_status",
        authoritative_source="runtime_file:alpha_telegram_status.json",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="global",
        authorization_policy="admin_only",
        query_or_template_id="READ alpha_telegram_status.json",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="deterministic",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_alpha_status)

    # ── Advisory: Client Acquisition ───────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="client_acquisition_advisory",
        capability_version="v1",
        semantic_definition_id="",
        description="Provide client acquisition advice",
        supported_operations=["advise"],
        canonical_handler_id="hermes._client_acquisition_advisory",
        authoritative_source="internal_knowledge",
        cache_policy="none",
        freshness_policy="static",
        tenant_scope_policy="global",
        authorization_policy="admin_only",
        side_effect_class=SideEffectClass.NONE.value,
        fallback_policy="static_response",
        response_renderer="deterministic",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=None)

    # ── Quarantined: Send Email ────────────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="send_email",
        capability_version="v1",
        semantic_definition_id="",
        description="Send email via Resend (requires approval)",
        supported_operations=["execute_action"],
        canonical_handler_id="",
        authoritative_source="resend_api",
        side_effect_class=SideEffectClass.EXTERNAL.value,
        confirmation_required=True,
        idempotency_policy="mission_id_based",
        fallback_policy="fail_closed",
        owner="Ray",
        lifecycle=LifecycleState.QUARANTINED.value,
        certification_result=None,
    ))

    # ── Quarantined: Schedule Report ───────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="schedule_report",
        capability_version="v1",
        semantic_definition_id="",
        description="Schedule a recurring report (requires approval)",
        supported_operations=["schedule_action"],
        canonical_handler_id="",
        authoritative_source="temporal_workflow",
        side_effect_class=SideEffectClass.WRITE.value,
        confirmation_required=True,
        idempotency_policy="mission_id_based",
        fallback_policy="fail_closed",
        owner="Ray",
        lifecycle=LifecycleState.QUARANTINED.value,
        certification_result=None,
    ))

    # ── Quarantined: Create Work Order ─────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="create_work_order",
        capability_version="v1",
        semantic_definition_id="",
        description="Create a work order for execution",
        supported_operations=["execute_action"],
        canonical_handler_id="",
        authoritative_source="internal_registry",
        side_effect_class=SideEffectClass.WRITE.value,
        confirmation_required=True,
        idempotency_policy="mission_id_based",
        fallback_policy="fail_closed",
        owner="Ray",
        lifecycle=LifecycleState.QUARANTINED.value,
        certification_result=None,
    ))

    # ── Certified Read: Create Prompt ──────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="create_opencode_prompt",
        capability_version="v1",
        semantic_definition_id="",
        description="Create an OpenCode prompt from current context",
        supported_operations=["create_draft"],
        canonical_handler_id="hermes._create_opencode_prompt",
        authoritative_source="internal_context",
        side_effect_class=SideEffectClass.NONE.value,
        fallback_policy="static_response",
        response_renderer="deterministic",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ))

    # ── Certified Read: Process Status ─────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="process_status",
        capability_version="v1",
        semantic_definition_id="process_definition_summary@v1",
        description="Query Supabase for process definitions and runs",
        supported_operations=["retrieve_status", "retrieve_list"],
        canonical_handler_id="hermes._get_process_status",
        authoritative_source="supabase_table:nexus_process_definitions,nexus_process_runs",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="server_injected",
        authorization_policy="admin_only",
        query_or_template_id="GET /rest/v1/nexus_process_definitions,nexus_process_runs",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="ceo_formatter",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_process_status)

    # ── Certified Read: Process Failures ───────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="process_failures",
        capability_version="v1",
        semantic_definition_id="process_failure_summary@v1",
        description="Query Supabase for failed process runs in last 24 hours",
        supported_operations=["retrieve_status"],
        canonical_handler_id="hermes._get_process_failures",
        authoritative_source="supabase_table:nexus_process_runs",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="server_injected",
        authorization_policy="admin_only",
        query_or_template_id="GET /rest/v1/nexus_process_runs?status=FAILED",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="ceo_formatter",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_process_failures)

    # ── Certified Read: Research History ───────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="research_history",
        capability_version="v1",
        semantic_definition_id="research_run_summary@v1",
        description="Query Supabase for research runs and results",
        supported_operations=["retrieve_list"],
        canonical_handler_id="hermes._get_research_history",
        authoritative_source="supabase_table:nexus_research_runs,nexus_research_results",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="server_injected",
        authorization_policy="admin_only",
        query_or_template_id="GET /rest/v1/nexus_research_runs,nexus_research_results",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="ceo_formatter",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_research_history)

    # ── Certified Read: Opportunities ──────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="opportunities",
        capability_version="v1",
        semantic_definition_id="business_opportunity_summary@v1",
        description="Query Supabase for business opportunities",
        supported_operations=["retrieve_list"],
        canonical_handler_id="hermes._get_opportunities",
        authoritative_source="supabase_table:business_opportunities",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="server_injected",
        authorization_policy="admin_only",
        query_or_template_id="GET /rest/v1/business_opportunities",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="ceo_formatter",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_opportunities)

    # ── Certified Read: Trading Status ─────────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="trading_status",
        capability_version="v1",
        semantic_definition_id="current_trading_status@v1",
        description="Read Oanda practice trading engine status",
        supported_operations=["retrieve_status"],
        canonical_handler_id="hermes._get_trading_status",
        authoritative_source="runtime_file:oanda_practice_engine_status_latest.json",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="global",
        authorization_policy="admin_only",
        query_or_template_id="READ oanda_practice_engine_status_latest.json",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="deterministic",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_trading_status)

    # ── Certified Read: Pending Approvals ──────────────────────
    contract_registry.register(CapabilityContract(
        capability_id="pending_approvals",
        capability_version="v1",
        semantic_definition_id="pending_approval_summary@v1",
        description="Read pending approvals from review queue",
        supported_operations=["retrieve_list"],
        canonical_handler_id="hermes._get_pending_approvals",
        authoritative_source="runtime_file:ray_review_queue_latest.json",
        cache_policy="none",
        freshness_policy="real_time",
        tenant_scope_policy="global",
        authorization_policy="admin_only",
        query_or_template_id="READ ray_review_queue_latest.json",
        side_effect_class=SideEffectClass.READ.value,
        fallback_policy="fail_closed",
        response_renderer="deterministic",
        owner="Ray",
        lifecycle=LifecycleState.CERTIFIED_READ.value,
        certification_result="passed",
    ), handler=_get_pending_approvals)


_register_builtins()
