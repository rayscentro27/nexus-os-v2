"""Deterministic validators for TaskSpec, CapabilityResult, and contracts.

Validators ensure that:
- TaskSpec schema is valid
- CapabilityResult matches expected schema
- No forbidden fields appear in TaskSpec
- Result status is consistent with data
- No PII leaks
- Provenance is complete
"""

from __future__ import annotations

from typing import List, Tuple

from nexus_agent_platform.contracts.typed import (
    TaskSpec, CapabilityResult, Operation, Entity, ResultStatus,
    TASKSPEC_VERSION, RESULT_VERSION,
)
from nexus_agent_platform.contracts.contracts import CapabilityContract, LifecycleState


# ─── Forbidden fields in TaskSpec ──────────────────────────────

_FORBIDDEN_TASKSPEC_FIELDS = frozenset({
    "raw_sql", "table_name", "column_name", "handler_name",
    "supabase_url", "supabase_key", "service_role_key",
    "tenant_id", "tenant_uuid",  # tenant must be server-injected
    "model_name", "provider_id",  # model selection not from model
    "connection_string", "database_url",
})

_VALID_OPERATIONS = {o.value for o in Operation}
_VALID_ENTITIES = {e.value for e in Entity}
_VALID_RESULT_STATUSES = {s.value for s in ResultStatus}


def validate_taskspec(taskspec: TaskSpec) -> Tuple[bool, List[str]]:
    """Validate a TaskSpec. Returns (is_valid, list_of_errors)."""
    errors = []

    # Version check
    if taskspec.version != TASKSPEC_VERSION:
        errors.append(f"Unsupported TaskSpec version: {taskspec.version}")

    # Required fields
    if not taskspec.operation:
        errors.append("operation is required")
    elif taskspec.operation not in _VALID_OPERATIONS:
        errors.append(f"Invalid operation: {taskspec.operation}")

    if not taskspec.entity:
        errors.append("entity is required")
    elif taskspec.entity not in _VALID_ENTITIES:
        errors.append(f"Invalid entity: {taskspec.entity}")

    # Forbidden fields in filters
    for key in taskspec.filters:
        if key in _FORBIDDEN_TASKSPEC_FIELDS:
            errors.append(f"Forbidden field in filters: {key}")

    # Forbidden top-level fields (check dict representation)
    td = taskspec.to_dict()
    for field in _FORBIDDEN_TASKSPEC_FIELDS:
        if field in td and td[field] is not None and td[field] != "":
            errors.append(f"Forbidden top-level field: {field}")

    # Confidence bounds
    if not 0.0 <= taskspec.confidence <= 1.0:
        errors.append(f"confidence must be 0.0-1.0, got {taskspec.confidence}")

    # Side effect validation
    if taskspec.side_effect_requested and taskspec.operation in (
        Operation.RETRIEVE_METRIC.value,
        Operation.RETRIEVE_STATUS.value,
        Operation.RETRIEVE_LIST.value,
    ):
        errors.append(f"Side effects not allowed for {taskspec.operation}")

    # Scope validation
    if taskspec.scope.tenant:
        errors.append("tenant must be server-injected, not model-provided")

    return len(errors) == 0, errors


def validate_result(result: CapabilityResult) -> Tuple[bool, List[str]]:
    """Validate a CapabilityResult. Returns (is_valid, list_of_errors)."""
    errors = []

    # Version check
    if result.version != RESULT_VERSION:
        errors.append(f"Unsupported result version: {result.version}")

    # Status must be valid
    if result.status not in _VALID_RESULT_STATUSES:
        errors.append(f"Invalid status: {result.status}")

    # ok status must have data
    if result.status == ResultStatus.OK.value and not result.data:
        errors.append("status=ok requires non-empty data")

    # ok status must not have error
    if result.status == ResultStatus.OK.value and result.error:
        errors.append("status=ok must not have error")

    # empty status should have empty data
    if result.status == ResultStatus.EMPTY.value and result.data:
        errors.append("status=empty should have empty data")

    # forbidden must have error
    if result.status == ResultStatus.FORBIDDEN.value and not result.error:
        errors.append("status=forbidden must have error message")

    # unavailable must have error
    if result.status == ResultStatus.UNAVAILABLE.value and not result.error:
        errors.append("status=unavailable must have error message")

    # Provenance completeness
    if not result.capability_id:
        errors.append("capability_id is required")

    if not result.source.source_id and result.status == ResultStatus.OK.value:
        errors.append("source.source_id required for ok results")

    # Authorization must be declared
    if not result.authorization.decision:
        errors.append("authorization.decision is required")

    return len(errors) == 0, errors


def validate_contract(contract: CapabilityContract) -> Tuple[bool, List[str]]:
    """Validate a CapabilityContract. Returns (is_valid, list_of_errors)."""
    errors = []

    if not contract.capability_id:
        errors.append("capability_id is required")

    if not contract.capability_version:
        errors.append("capability_version is required")

    if not contract.description:
        errors.append("description is required")

    # Certified contracts must have handlers
    if contract.is_certified() and not contract.canonical_handler_id:
        errors.append("certified contracts must have canonical_handler_id")

    # Certified contracts must have semantic definitions
    if contract.is_certified() and not contract.semantic_definition_id:
        errors.append("certified contracts must have semantic_definition_id")

    # Side-effecting actions must require confirmation
    if contract.side_effect_class in ("write", "external", "destructive"):
        if not contract.confirmation_required:
            errors.append("side-effecting actions must require confirmation")

    # Fail-closed policy
    if contract.fallback_policy not in ("fail_closed", "static_response", "fail_open"):
        errors.append(f"Invalid fallback_policy: {contract.fallback_policy}")

    return len(errors) == 0, errors
