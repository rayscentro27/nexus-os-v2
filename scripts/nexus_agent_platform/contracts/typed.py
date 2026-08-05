"""Typed TaskSpec and CapabilityResult schemas.

Versioned, validated data structures that govern what the model may
produce and what the capability dispatcher must return.

The model/router may produce only fields from this schema.
Internal handler names, SQL, table names, tenant IDs, and raw data
sources must never appear in TaskSpec.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


TASKSPEC_VERSION = "taskspec.v1"
RESULT_VERSION = "result.v1"


# ─── Enums ─────────────────────────────────────────────────────

class Operation(str, Enum):
    RETRIEVE_METRIC = "retrieve_metric"
    RETRIEVE_STATUS = "retrieve_status"
    RETRIEVE_LIST = "retrieve_list"
    CREATE_DRAFT = "create_draft"
    EXECUTE_ACTION = "execute_action"
    SCHEDULE_ACTION = "schedule_action"
    EXPLAIN = "explain"
    ADVISE = "advise"
    COMPARE = "compare"
    RETRY = "retry"
    APPROVE = "approve"
    REJECT = "reject"


class Entity(str, Enum):
    CLIENT = "client"
    PROCESS = "process"
    FAILURE = "failure"
    RESEARCH = "research"
    ALPHA = "alpha"
    APPROVAL = "approval"
    OPPORTUNITY = "opportunity"
    TRADING = "trading"
    EMAIL = "email"
    REPORT = "report"
    WORK_ORDER = "work_order"
    PROMPT = "prompt"
    TESTER = "tester"
    SYSTEM = "system"


class TimeRange(str, Enum):
    CURRENT = "current"
    TODAY = "today"
    LAST_24_HOURS = "last_24_hours"
    CUSTOM = "custom"


class RecordScope(str, Enum):
    SUMMARY = "summary"
    DETAILS = "details"


class RequestedOutput(str, Enum):
    SUMMARY = "summary"
    EXECUTIVE_BRIEF = "executive_brief"
    TECHNICAL_DETAILS = "technical_details"


class ResultStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    FORBIDDEN = "forbidden"
    STALE = "stale"
    INVALID = "invalid"
    PENDING = "pending"
    PARTIAL = "partial"


class CacheStatus(str, Enum):
    NONE = "none"
    HIT = "hit"
    MISS = "miss"
    STALE = "stale"


class SourceType(str, Enum):
    SUPABASE_RPC = "supabase_rpc"
    SUPABASE_TABLE = "supabase_table"
    RUNTIME_FILE = "runtime_file"
    PROVIDER_API = "provider_api"
    TEMPORAL_WORKFLOW = "temporal_workflow"
    INTERNAL_REGISTRY = "internal_registry"


# ─── TaskSpec ──────────────────────────────────────────────────

@dataclass
class Scope:
    """Request scope — tenant is always server-injected."""
    organization: str = "current"
    tenant: str = ""  # server-injected, never from model
    time_range: str = TimeRange.CURRENT.value
    record_scope: str = RecordScope.SUMMARY.value


@dataclass
class TaskSpec:
    """Typed task specification — the model may only produce these fields.

    Rules:
    - tenant IDs cannot come from model output
    - internal handler names cannot come from model output
    - raw table names cannot come from model output
    - SQL cannot come from model output
    - arbitrary provider/model names cannot come from model output
    """
    task_id: str = ""
    agent: str = "nexus_hermes"
    operation: str = ""
    entity: str = ""
    metric_definition: str = ""
    scope: Scope = field(default_factory=Scope)
    filters: Dict[str, Any] = field(default_factory=dict)
    context_reference: Optional[str] = None
    requested_output: str = RequestedOutput.SUMMARY.value
    side_effect_requested: bool = False
    confidence: float = 0.0
    missing_fields: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    version: str = TASKSPEC_VERSION

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSpec":
        scope_data = data.get("scope", {})
        scope = Scope(**scope_data) if isinstance(scope_data, dict) else Scope()
        return cls(
            task_id=data.get("task_id", ""),
            agent=data.get("agent", "nexus_hermes"),
            operation=data.get("operation", ""),
            entity=data.get("entity", ""),
            metric_definition=data.get("metric_definition", ""),
            scope=scope,
            filters=data.get("filters", {}),
            context_reference=data.get("context_reference"),
            requested_output=data.get("requested_output", "summary"),
            side_effect_requested=data.get("side_effect_requested", False),
            confidence=data.get("confidence", 0.0),
            missing_fields=data.get("missing_fields", []),
            ambiguities=data.get("ambiguities", []),
            version=data.get("version", TASKSPEC_VERSION),
        )

    def scope_hash(self) -> str:
        """Deterministic hash of scope for provenance."""
        raw = f"{self.scope.tenant}:{self.scope.organization}:{self.scope.time_range}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── CapabilityResult ──────────────────────────────────────────

@dataclass
class SourceInfo:
    """Provenance of the data source."""
    source_id: str = ""
    source_type: str = SourceType.INTERNAL_REGISTRY.value
    query_or_template_id: str = ""
    cache_status: str = CacheStatus.NONE.value
    as_of: str = ""


@dataclass
class Authorization:
    """Authorization decision."""
    decision: str = "allowed"
    policy_id: str = ""


@dataclass
class ExecutionInfo:
    """Execution metadata."""
    handler_id: str = ""
    latency_ms: int = 0
    retry_count: int = 0
    fallback_used: bool = False
    fallback_reason: Optional[str] = None


@dataclass
class CapabilityResult:
    """Typed result from a certified capability execution.

    Rules:
    - exception cannot become status=ok
    - timeout cannot become zero
    - authorization denial cannot become empty
    - stale cache cannot be labeled live
    - missing tenant context must be invalid
    - source outage must be unavailable
    - no matching records must be empty
    - partial result must identify missing components
    - fallback use must always be explicit
    - invalid output schema must fail closed
    """
    status: str = ResultStatus.OK.value
    capability_id: str = ""
    capability_version: str = ""
    definition_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    source: SourceInfo = field(default_factory=SourceInfo)
    scope: Scope = field(default_factory=Scope)
    authorization: Authorization = field(default_factory=Authorization)
    execution: ExecutionInfo = field(default_factory=ExecutionInfo)
    trace_id: str = ""
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    version: str = RESULT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityResult":
        source = SourceInfo(**data.get("source", {})) if isinstance(data.get("source"), dict) else SourceInfo()
        scope = Scope(**data.get("scope", {})) if isinstance(data.get("scope"), dict) else Scope()
        auth = Authorization(**data.get("authorization", {})) if isinstance(data.get("authorization"), dict) else Authorization()
        execution = ExecutionInfo(**data.get("execution", {})) if isinstance(data.get("execution"), dict) else ExecutionInfo()
        return cls(
            status=data.get("status", "ok"),
            capability_id=data.get("capability_id", ""),
            capability_version=data.get("capability_version", ""),
            definition_id=data.get("definition_id", ""),
            data=data.get("data", {}),
            source=source,
            scope=scope,
            authorization=auth,
            execution=execution,
            trace_id=data.get("trace_id", ""),
            warnings=data.get("warnings", []),
            error=data.get("error"),
            version=data.get("version", RESULT_VERSION),
        )


# ─── Convenience constructors ──────────────────────────────────

def ok_result(
    capability_id: str,
    capability_version: str,
    definition_id: str,
    data: Dict[str, Any],
    source_id: str = "",
    source_type: str = "internal_registry",
    query_id: str = "",
    handler_id: str = "",
    tenant: str = "",
    trace_id: str = "",
) -> CapabilityResult:
    """Construct a successful CapabilityResult."""
    now = datetime.now(timezone.utc).isoformat()
    return CapabilityResult(
        status=ResultStatus.OK.value,
        capability_id=capability_id,
        capability_version=capability_version,
        definition_id=definition_id,
        data=data,
        source=SourceInfo(
            source_id=source_id,
            source_type=source_type,
            query_or_template_id=query_id,
            as_of=now,
        ),
        scope=Scope(tenant=tenant),
        authorization=Authorization(decision="allowed"),
        execution=ExecutionInfo(handler_id=handler_id),
        trace_id=trace_id,
    )


def error_result(
    capability_id: str,
    capability_version: str,
    definition_id: str,
    error: str,
    status: str = ResultStatus.UNAVAILABLE.value,
    handler_id: str = "",
    tenant: str = "",
    trace_id: str = "",
) -> CapabilityResult:
    """Construct an error CapabilityResult — never status=ok."""
    return CapabilityResult(
        status=status,
        capability_id=capability_id,
        capability_version=capability_version,
        definition_id=definition_id,
        data={},
        source=SourceInfo(),
        scope=Scope(tenant=tenant),
        authorization=Authorization(decision="allowed"),
        execution=ExecutionInfo(handler_id=handler_id),
        trace_id=trace_id,
        error=error,
    )


def empty_result(
    capability_id: str,
    capability_version: str,
    definition_id: str,
    handler_id: str = "",
    tenant: str = "",
    trace_id: str = "",
) -> CapabilityResult:
    """Construct an empty-result CapabilityResult."""
    return CapabilityResult(
        status=ResultStatus.EMPTY.value,
        capability_id=capability_id,
        capability_version=capability_version,
        definition_id=definition_id,
        data={},
        source=SourceInfo(),
        scope=Scope(tenant=tenant),
        authorization=Authorization(decision="allowed"),
        execution=ExecutionInfo(handler_id=handler_id),
        trace_id=trace_id,
    )


def forbidden_result(
    capability_id: str,
    capability_version: str,
    definition_id: str,
    reason: str = "not authorized",
    handler_id: str = "",
    tenant: str = "",
    trace_id: str = "",
) -> CapabilityResult:
    """Construct a forbidden CapabilityResult."""
    return CapabilityResult(
        status=ResultStatus.FORBIDDEN.value,
        capability_id=capability_id,
        capability_version=capability_version,
        definition_id=definition_id,
        data={},
        source=SourceInfo(),
        scope=Scope(tenant=tenant),
        authorization=Authorization(decision="denied"),
        execution=ExecutionInfo(handler_id=handler_id),
        trace_id=trace_id,
        error=reason,
    )
