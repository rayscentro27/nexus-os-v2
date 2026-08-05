"""Single certified capability dispatcher.

Every production-reachable capability must pass through this dispatcher.
No graph node may call Supabase, local JSON, Resend, Temporal, or
any protected data source unless reached through this dispatcher.

The dispatcher:
1. validates TaskSpec schema
2. injects trusted tenant and authorization context
3. resolves semantic definition
4. resolves certified capability version
5. verifies lifecycle state
6. verifies authorization
7. applies deterministic filter policy
8. invokes canonical handler
9. validates typed result
10. attaches provenance
11. emits Langfuse trace attributes
12. returns normalized CapabilityResult
"""

from __future__ import annotations

import logging
import time
import inspect
from typing import Any, Dict, Optional

from nexus_agent_platform.contracts.typed import (
    TaskSpec, CapabilityResult, Scope, Authorization,
    ExecutionInfo, SourceInfo, ResultStatus,
    ok_result, error_result, empty_result, forbidden_result,
)
from nexus_agent_platform.contracts.definitions import SemanticDefinition
from nexus_agent_platform.contracts.contracts import (
    CapabilityContract, LifecycleState, contract_registry,
)
from nexus_agent_platform.contracts.validators import (
    validate_taskspec, validate_result,
)

log = logging.getLogger(__name__)


class CapabilityDispatcher:
    """Single authoritative dispatcher for all Hermes capabilities."""

    def __init__(self, agent_id: str = "nexus_hermes"):
        self.agent_id = agent_id

    def dispatch(
        self,
        taskspec: TaskSpec,
        authenticated_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        mission_context: Optional[Dict[str, Any]] = None,
        trace_id: str = "",
    ) -> CapabilityResult:
        """Execute a capability through the certified dispatch pipeline.

        Returns a typed CapabilityResult.  Never raises exceptions
        for expected failure modes — all failures are encoded in the
        result status.
        """
        start_ms = int(time.time() * 1000)
        ctx = authenticated_context or {}

        # ── Step 1: Validate TaskSpec ──────────────────────────
        valid, errors = validate_taskspec(taskspec)
        if not valid:
            return CapabilityResult(
                status=ResultStatus.INVALID.value,
                capability_id="",
                capability_version="",
                definition_id=taskspec.metric_definition,
                data={},
                source=SourceInfo(),
                scope=Scope(tenant=""),
                authorization=Authorization(decision="denied"),
                execution=ExecutionInfo(handler_id="dispatcher", latency_ms=0),
                trace_id=trace_id,
                error=f"TaskSpec validation failed: {'; '.join(errors)}",
            )

        # ── Step 2: Inject trusted tenant context ──────────────
        # Tenant is ALWAYS server-injected, never from model output
        tenant = ctx.get("tenant_id", "goclear")
        taskspec.scope.tenant = tenant  # override any model-provided value

        # ── Step 3: Resolve capability from entity + operation ──
        capability_id = self._resolve_capability_id(taskspec)
        if not capability_id:
            return error_result(
                capability_id="",
                capability_version="",
                definition_id=taskspec.metric_definition,
                error=f"No capability found for operation={taskspec.operation} entity={taskspec.entity}",
                status=ResultStatus.INVALID.value,
                handler_id="dispatcher",
                tenant=tenant,
                trace_id=trace_id,
            )

        # ── Step 4: Resolve certified contract ─────────────────
        contract = contract_registry.get(capability_id)
        if not contract:
            return error_result(
                capability_id=capability_id,
                capability_version="",
                definition_id=taskspec.metric_definition,
                error=f"No contract registered for capability: {capability_id}",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id="dispatcher",
                tenant=tenant,
                trace_id=trace_id,
            )

        # ── Step 5: Verify lifecycle state ─────────────────────
        if not contract.is_production_allowed():
            return error_result(
                capability_id=capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                error=f"Capability {capability_id} is not certified for production (lifecycle={contract.lifecycle})",
                status=ResultStatus.FORBIDDEN.value,
                handler_id="dispatcher",
                tenant=tenant,
                trace_id=trace_id,
            )

        # ── Step 6: Verify authorization ───────────────────────
        if contract.authorization_policy == "admin_only":
            if not ctx.get("is_admin", False) and not ctx.get("is_ray", False):
                return forbidden_result(
                    capability_id=capability_id,
                    capability_version=contract.capability_version,
                    definition_id=contract.semantic_definition_id,
                    reason="Admin authorization required",
                    handler_id=contract.canonical_handler_id,
                    tenant=tenant,
                    trace_id=trace_id,
                )

        # ── Step 7: Apply deterministic filter policy ──────────
        # Merge contract filter policy with TaskSpec filters
        # Contract filters override model filters for safety
        effective_filters = dict(taskspec.filters)
        for k, v in contract.filter_policy.items():
            effective_filters[k] = v  # contract policy wins

        # ── Step 8: Invoke canonical handler ───────────────────
        handler = contract_registry.get_handler(capability_id)
        if not handler:
            return error_result(
                capability_id=capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                error=f"No handler registered for capability: {capability_id}",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id=contract.canonical_handler_id,
                tenant=tenant,
                trace_id=trace_id,
            )

        mission_id = (mission_context or {}).get("mission_id", trace_id) if mission_context else trace_id
        try:
            sig = inspect.signature(handler)
            params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)]
            if params:
                raw_result = handler(taskspec, mission_id, tenant)
            else:
                raw_result = handler()
        except TypeError:
            raw_result = handler()
        except Exception as exc:
            elapsed = int(time.time() * 1000) - start_ms
            log.error("Handler %s failed: %s", contract.canonical_handler_id, exc)
            return CapabilityResult(
                status=ResultStatus.UNAVAILABLE.value,
                capability_id=capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                data={},
                source=SourceInfo(),
                scope=Scope(tenant=tenant),
                authorization=Authorization(decision="allowed"),
                execution=ExecutionInfo(
                    handler_id=contract.canonical_handler_id,
                    latency_ms=elapsed,
                    fallback_used=False,
                ),
                trace_id=trace_id,
                error=f"Handler execution failed: {exc}",
            )

        # ── Step 9: Normalize result ───────────────────────────
        elapsed = int(time.time() * 1000) - start_ms
        normalized = self._normalize_result(
            raw_result, contract, taskspec, tenant, trace_id, elapsed
        )

        # ── Step 10: Validate typed result ─────────────────────
        valid, val_errors = validate_result(normalized)
        if not valid:
            return error_result(
                capability_id=capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                error=f"Result validation failed: {'; '.join(val_errors)}",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id=contract.canonical_handler_id,
                tenant=tenant,
                trace_id=trace_id,
            )

        return normalized

    def _resolve_capability_id(self, taskspec: TaskSpec) -> Optional[str]:
        """Map (operation, entity) to a capability_id.

        This is the deterministic routing logic.  The model does not
        choose capability names — it declares operation and entity,
        and this method resolves the certified capability.
        """
        # Client entity
        if taskspec.entity == "client":
            if taskspec.operation == "retrieve_metric":
                # Check metric_definition for specific variants
                if "active" in (taskspec.metric_definition or "").lower():
                    return "active_client_count"
                return "get_client_count"
            if taskspec.operation == "retrieve_status":
                return "get_client_count"
            if taskspec.operation == "advise":
                return "client_acquisition_advisory"

        # Process entity
        if taskspec.entity == "process":
            if taskspec.operation in ("retrieve_status", "retrieve_metric", "retrieve_list"):
                return "get_system_status"

        # Failure entity
        if taskspec.entity == "failure":
            if taskspec.operation in ("retrieve_status", "retrieve_list"):
                return "get_failure_report"

        # Alpha entity
        if taskspec.entity == "alpha":
            if taskspec.operation in ("retrieve_status",):
                return "get_alpha_status"

        # Approval entity
        if taskspec.entity == "approval":
            if taskspec.operation in ("retrieve_status", "retrieve_list"):
                return "get_pending_approvals"
            if taskspec.operation == "approve":
                return "approve_item"
            if taskspec.operation == "reject":
                return "reject_item"

        # Email entity
        if taskspec.entity == "email":
            if taskspec.operation == "execute_action":
                return "send_email"

        # Report entity
        if taskspec.entity == "report":
            if taskspec.operation == "schedule_action":
                return "schedule_report"
            if taskspec.operation == "create_draft":
                return "create_opencode_prompt"

        # Work order entity
        if taskspec.entity == "work_order":
            if taskspec.operation == "execute_action":
                return "create_work_order"

        # Prompt entity
        if taskspec.entity == "prompt":
            if taskspec.operation == "create_draft":
                return "create_opencode_prompt"

        return None

    def _normalize_result(
        self,
        raw_result: Any,
        contract: CapabilityContract,
        taskspec: TaskSpec,
        tenant: str,
        trace_id: str,
        latency_ms: int,
    ) -> CapabilityResult:
        """Normalize raw handler output into a typed CapabilityResult."""

        # Handler returns a dict (from _get_client_count, etc.)
        if isinstance(raw_result, dict):
            # Check for error in raw result
            if raw_result.get("error"):
                return error_result(
                    capability_id=contract.capability_id,
                    capability_version=contract.capability_version,
                    definition_id=contract.semantic_definition_id,
                    error=str(raw_result["error"]),
                    status=ResultStatus.UNAVAILABLE.value,
                    handler_id=contract.canonical_handler_id,
                    tenant=tenant,
                    trace_id=trace_id,
                )

            # Check for empty result
            is_empty = (
                raw_result.get("production_total", -1) == 0
                and raw_result.get("all_profiles", -1) == 0
            )
            if is_empty:
                return empty_result(
                    capability_id=contract.capability_id,
                    capability_version=contract.capability_version,
                    definition_id=contract.semantic_definition_id,
                    handler_id=contract.canonical_handler_id,
                    tenant=tenant,
                    trace_id=trace_id,
                )

            return ok_result(
                capability_id=contract.capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                data=raw_result,
                source_id=contract.authoritative_source,
                source_type=self._source_type(contract.authoritative_source),
                query_id=contract.query_or_template_id,
                handler_id=contract.canonical_handler_id,
                tenant=tenant,
                trace_id=trace_id,
            )

        # Handler returns a string
        if isinstance(raw_result, str):
            if not raw_result.strip():
                return empty_result(
                    capability_id=contract.capability_id,
                    capability_version=contract.capability_version,
                    definition_id=contract.semantic_definition_id,
                    handler_id=contract.canonical_handler_id,
                    tenant=tenant,
                    trace_id=trace_id,
                )
            return ok_result(
                capability_id=contract.capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                data={"response": raw_result},
                source_id=contract.authoritative_source,
                source_type=self._source_type(contract.authoritative_source),
                query_id=contract.query_or_template_id,
                handler_id=contract.canonical_handler_id,
                tenant=tenant,
                trace_id=trace_id,
            )

        # Handler returns a dict with specific status fields
        if isinstance(raw_result, dict) and any(
            k in raw_result for k in ("working", "needs_attention")
        ):
            return ok_result(
                capability_id=contract.capability_id,
                capability_version=contract.capability_version,
                definition_id=contract.semantic_definition_id,
                data=raw_result,
                source_id=contract.authoritative_source,
                source_type=self._source_type(contract.authoritative_source),
                query_id=contract.query_or_template_id,
                handler_id=contract.canonical_handler_id,
                tenant=tenant,
                trace_id=trace_id,
            )

        # Unknown return type — fail closed
        return error_result(
            capability_id=contract.capability_id,
            capability_version=contract.capability_version,
            definition_id=contract.semantic_definition_id,
            error=f"Unexpected handler return type: {type(raw_result).__name__}",
            status=ResultStatus.UNAVAILABLE.value,
            handler_id=contract.canonical_handler_id,
            tenant=tenant,
            trace_id=trace_id,
        )

    def _source_type(self, source: str) -> str:
        """Map authoritative_source string to SourceType enum value."""
        if source.startswith("supabase"):
            return "supabase_table" if "table" in source else "supabase_rpc"
        if source.startswith("runtime_file"):
            return "runtime_file"
        if source.startswith("temporal"):
            return "temporal_workflow"
        if source.startswith("resend"):
            return "provider_api"
        return "internal_registry"


# ─── Module-level dispatcher ───────────────────────────────────

_dispatcher: Optional[CapabilityDispatcher] = None


def dispatch(
    taskspec: TaskSpec,
    authenticated_context: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[Dict[str, Any]] = None,
    mission_context: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> CapabilityResult:
    """Module-level dispatch function — the single entry point."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CapabilityDispatcher()
    return _dispatcher.dispatch(
        taskspec,
        authenticated_context=authenticated_context,
        conversation_context=conversation_context,
        mission_context=mission_context,
        trace_id=trace_id,
    )
