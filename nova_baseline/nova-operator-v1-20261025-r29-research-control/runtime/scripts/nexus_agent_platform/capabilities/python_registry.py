"""Deterministic Nexus Python capability registry.

This is a static, read-only inventory of deliberate Nexus capabilities.
It answers one question first: does Nexus already have a deterministic
or governed capability for this use case?

The registry is additive. It does not replace the existing per-agent
runtime capability registry in ``capabilities/registry.py``.
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REGISTRY_VERSION = "1.0"
REGISTRY_ID = "NEXUS_PYTHON_CAPABILITY_REGISTRY"


class CostClass(str, Enum):
    ZERO_MODEL_COST = "ZERO_MODEL_COST"
    LOW_EXTERNAL_COST = "LOW_EXTERNAL_COST"
    AI_TIER_1 = "AI_TIER_1"
    AI_TIER_2 = "AI_TIER_2"
    AI_TIER_3 = "AI_TIER_3"

    # Backwards-compatible aliases for older task language.
    TIER_1_CHEAP_AI = "AI_TIER_1"
    TIER_2_STANDARD_AI = "AI_TIER_2"
    TIER_3_PREMIUM_AI = "AI_TIER_3"


class RiskClass(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class TenantScope(str, Enum):
    SYSTEM = "SYSTEM"
    CLIENT = "CLIENT"
    TENANT = "TENANT"
    INHERITED = "INHERITED"


class PiiClassification(str, Enum):
    NONE = "NONE"
    CLIENT_AGGREGATE = "CLIENT_AGGREGATE"
    CLIENT_PII = "CLIENT_PII"


class ExecutionType(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    API = "API"
    AI_ASSISTED = "AI_ASSISTED"

    # Backwards-compatible alias.
    HYBRID = "AI_ASSISTED"


def _enum_from_value(enum_cls, value):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        if value in enum_cls.__members__:
            return enum_cls.__members__[value]
        try:
            return enum_cls(value)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"unknown {enum_cls.__name__} value: {value}") from exc
    raise TypeError(f"expected {enum_cls.__name__} or str, got {type(value).__name__}")


@dataclass(frozen=True)
class CapabilityMetadata:
    capability_id: str
    name: str
    description: str
    module: str
    callable_name: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    execution_type: ExecutionType = ExecutionType.DETERMINISTIC
    cost_class: CostClass = CostClass.ZERO_MODEL_COST
    side_effecting: bool = False
    risk_class: RiskClass = RiskClass.LOW
    tenant_scoped: bool = False
    tenant_scope: TenantScope = TenantScope.INHERITED
    pii_classification: PiiClassification = PiiClassification.NONE
    approval_required: bool = False
    timeout_seconds: Optional[float] = None
    retry_policy: str = "none"
    enabled: bool = True
    test_status: str = "untested"
    owner: str = "Nexus"
    source: str = ""
    notes: str = ""
    ai_usage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "callable": self.callable_name,
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
            "execution_type": self.execution_type.value,
            "cost_class": self.cost_class.value,
            "side_effecting": self.side_effecting,
            "risk_class": self.risk_class.value,
            "tenant_scoped": self.tenant_scoped,
            "tenant_scope": self.tenant_scope.value,
            "pii_classification": self.pii_classification.value,
            "approval_required": self.approval_required,
            "timeout": self.timeout_seconds,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self.retry_policy,
            "enabled": self.enabled,
            "test_status": self.test_status,
            "owner": self.owner,
            "source": self.source,
            "notes": self.notes,
            "ai_usage": self.ai_usage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityMetadata":
        capability_id = data.get("capability_id") or data.get("name")
        callable_name = data.get("callable") or data.get("callable_name") or data.get("entrypoint")
        tenant_scope = _enum_from_value(TenantScope, data.get("tenant_scope", TenantScope.INHERITED))
        pii_classification = _enum_from_value(
            PiiClassification,
            data.get("pii_classification", data.get("pii_scope", PiiClassification.NONE)),
        )
        execution_type = _enum_from_value(ExecutionType, data.get("execution_type", ExecutionType.DETERMINISTIC))
        cost_class = _enum_from_value(CostClass, data.get("cost_class", CostClass.ZERO_MODEL_COST))
        risk_class = _enum_from_value(RiskClass, data.get("risk_class", RiskClass.LOW))
        timeout = data.get("timeout", data.get("timeout_seconds"))
        tenant_scoped = data.get("tenant_scoped")
        if tenant_scoped is None:
            tenant_scoped = tenant_scope != TenantScope.INHERITED
        return cls(
            capability_id=str(capability_id or "").strip(),
            name=str(data.get("name") or capability_id or "").strip(),
            description=str(data.get("description") or "").strip(),
            module=str(data.get("module") or "").strip(),
            callable_name=str(callable_name or "").strip(),
            input_schema=dict(data.get("input_schema") or {}),
            output_schema=dict(data.get("output_schema") or {}),
            execution_type=execution_type,
            cost_class=cost_class,
            side_effecting=bool(data.get("side_effecting", False)),
            risk_class=risk_class,
            tenant_scoped=bool(tenant_scoped),
            tenant_scope=tenant_scope,
            pii_classification=pii_classification,
            approval_required=bool(data.get("approval_required", False)),
            timeout_seconds=float(timeout) if timeout is not None else None,
            retry_policy=str(data.get("retry_policy", "none")),
            enabled=bool(data.get("enabled", True)),
            test_status=str(data.get("test_status", "untested")),
            owner=str(data.get("owner", "Nexus")),
            source=str(data.get("source", "")),
            notes=str(data.get("notes", "")),
            ai_usage=str(data.get("ai_usage", "")),
        )


class PythonCapabilityRegistry:
    """Static, queryable inventory of deliberate Nexus capabilities."""

    def __init__(self, identifier: str = REGISTRY_ID):
        self.identifier = identifier
        self._capabilities: Dict[str, CapabilityMetadata] = {}

    def register(self, metadata: CapabilityMetadata) -> None:
        if not metadata.capability_id:
            raise ValueError("capability_id is required")
        if not metadata.name:
            raise ValueError(f"capability {metadata.capability_id!r} requires a name")
        if not metadata.module:
            raise ValueError(f"capability {metadata.capability_id!r} requires a module")
        if not metadata.callable_name:
            raise ValueError(f"capability {metadata.capability_id!r} requires a callable")
        if metadata.capability_id in self._capabilities:
            raise ValueError(f"duplicate capability_id: {metadata.capability_id}")
        if metadata.tenant_scoped and metadata.tenant_scope == TenantScope.INHERITED:
            raise ValueError(
                f"tenant_scoped capability {metadata.capability_id!r} must declare a tenant_scope"
            )
        if not metadata.tenant_scoped and metadata.tenant_scope not in (
            TenantScope.INHERITED,
            TenantScope.SYSTEM,
        ):
            raise ValueError(
                f"non-tenant capability {metadata.capability_id!r} cannot use tenant scope {metadata.tenant_scope.value}"
            )
        if metadata.execution_type == ExecutionType.AI_ASSISTED and metadata.cost_class == CostClass.ZERO_MODEL_COST:
            raise ValueError(
                f"AI-assisted capability {metadata.capability_id!r} must not be ZERO_MODEL_COST"
            )
        if metadata.timeout_seconds is not None and metadata.timeout_seconds <= 0:
            raise ValueError(f"capability {metadata.capability_id!r} must have positive timeout_seconds")
        self._capabilities[metadata.capability_id] = metadata

    def register_spec(self, spec: Dict[str, Any]) -> None:
        self.register(CapabilityMetadata.from_dict(spec))

    def get(self, capability_id: str) -> Optional[CapabilityMetadata]:
        return self._capabilities.get(capability_id)

    def lookup(self, capability_id: str) -> Optional[CapabilityMetadata]:
        return self.get(capability_id)

    def has(self, capability_id: str) -> bool:
        return capability_id in self._capabilities

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return [self._capabilities[k].to_dict() for k in sorted(self._capabilities)]

    def query(
        self,
        *,
        capability_id: Optional[str] = None,
        cost_class: Optional[CostClass] = None,
        execution_type: Optional[ExecutionType] = None,
        risk_class: Optional[RiskClass] = None,
        tenant_scoped: Optional[bool] = None,
        pii_classification: Optional[PiiClassification] = None,
        side_effecting: Optional[bool] = None,
        approval_required: Optional[bool] = None,
        enabled: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> List[CapabilityMetadata]:
        def match(c: CapabilityMetadata) -> bool:
            if capability_id is not None and c.capability_id != capability_id:
                return False
            if cost_class is not None and c.cost_class != cost_class:
                return False
            if execution_type is not None and c.execution_type != execution_type:
                return False
            if risk_class is not None and c.risk_class != risk_class:
                return False
            if tenant_scoped is not None and c.tenant_scoped != tenant_scoped:
                return False
            if pii_classification is not None and c.pii_classification != pii_classification:
                return False
            if side_effecting is not None and c.side_effecting != side_effecting:
                return False
            if approval_required is not None and c.approval_required != approval_required:
                return False
            if enabled is not None and c.enabled != enabled:
                return False
            if keyword:
                haystack = " ".join(
                    [
                        c.capability_id,
                        c.name,
                        c.description,
                        c.module,
                        c.callable_name,
                        c.source,
                        c.notes,
                        c.ai_usage,
                    ]
                ).lower()
                if keyword.lower() not in haystack:
                    return False
            return True

        return [c for c in self._capabilities.values() if match(c)]

    def cheapest_per_keyword(self, keyword: str) -> Optional[CapabilityMetadata]:
        candidates = self.query(keyword=keyword, enabled=True)
        if not candidates:
            return None
        order = {
            CostClass.ZERO_MODEL_COST: 0,
            CostClass.LOW_EXTERNAL_COST: 1,
            CostClass.AI_TIER_1: 2,
            CostClass.AI_TIER_2: 3,
            CostClass.AI_TIER_3: 4,
        }
        return min(candidates, key=lambda c: order[c.cost_class])

    def summary(self) -> Dict[str, Any]:
        caps = list(self._capabilities.values())
        counts = Counter()
        for cap in caps:
            counts[f"execution_type:{cap.execution_type.value}"] += 1
            counts[f"cost_class:{cap.cost_class.value}"] += 1
            counts[f"risk_class:{cap.risk_class.value}"] += 1
            counts["enabled" if cap.enabled else "disabled"] += 1
            counts["side_effecting" if cap.side_effecting else "read_only"] += 1
            counts["tenant_scoped" if cap.tenant_scoped else "system_scoped"] += 1
            counts[f"pii:{cap.pii_classification.value}"] += 1
            if cap.approval_required:
                counts["approval_required"] += 1

        return {
            "registry_id": self.identifier,
            "version": REGISTRY_VERSION,
            "count": len(caps),
            "execution_types": {
                "DETERMINISTIC": counts["execution_type:DETERMINISTIC"],
                "API": counts["execution_type:API"],
                "AI_ASSISTED": counts["execution_type:AI_ASSISTED"],
            },
            "cost_classes": {
                "ZERO_MODEL_COST": counts["cost_class:ZERO_MODEL_COST"],
                "LOW_EXTERNAL_COST": counts["cost_class:LOW_EXTERNAL_COST"],
                "AI_TIER_1": counts["cost_class:AI_TIER_1"],
                "AI_TIER_2": counts["cost_class:AI_TIER_2"],
                "AI_TIER_3": counts["cost_class:AI_TIER_3"],
            },
            "enabled": counts["enabled"],
            "disabled": counts["disabled"],
            "read_only": counts["read_only"],
            "side_effecting": counts["side_effecting"],
            "tenant_scoped": counts["tenant_scoped"],
            "system_scoped": counts["system_scoped"],
            "approval_required": counts["approval_required"],
            "pii": {
                "NONE": counts["pii:NONE"],
                "CLIENT_AGGREGATE": counts["pii:CLIENT_AGGREGATE"],
                "CLIENT_PII": counts["pii:CLIENT_PII"],
            },
            "risk_counts": dict(
                sorted(
                    {
                        "LOW": counts["risk_class:LOW"],
                        "MODERATE": counts["risk_class:MODERATE"],
                        "HIGH": counts["risk_class:HIGH"],
                        "PROHIBITED": counts["risk_class:PROHIBITED"],
                    }.items()
                )
            ),
        }

    def to_csv(self) -> str:
        cols = [
            "capability_id",
            "name",
            "execution_type",
            "cost_class",
            "risk_class",
            "tenant_scoped",
            "pii_classification",
            "enabled",
            "approval_required",
            "side_effecting",
            "timeout",
            "module",
            "callable",
            "source",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=cols)
        writer.writeheader()
        for capability in self.list_capabilities():
            writer.writerow({k: capability.get(k) for k in cols})
        return buf.getvalue()

    def to_markdown(self) -> str:
        summary = self.summary()
        rows = self.list_capabilities()
        lines = [
            "# Nexus Python Capability Registry",
            "",
            f"- Registry ID: `{summary['registry_id']}`",
            f"- Version: `{summary['version']}`",
            f"- Capability count: `{summary['count']}`",
            f"- Deterministic: `{summary['execution_types']['DETERMINISTIC']}`",
            f"- API-backed: `{summary['execution_types']['API']}`",
            f"- AI-assisted: `{summary['execution_types']['AI_ASSISTED']}`",
            f"- Zero model cost: `{summary['cost_classes']['ZERO_MODEL_COST']}`",
            f"- Low external cost: `{summary['cost_classes']['LOW_EXTERNAL_COST']}`",
            f"- Disabled: `{summary['disabled']}`",
            f"- Tenant scoped: `{summary['tenant_scoped']}`",
            f"- Client PII classified: `{summary['pii']['CLIENT_PII']}`",
            "",
            "| capability_id | execution_type | cost_class | enabled | tenant_scoped | pii | approval | side_effecting | owner | source |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for capability in rows:
            lines.append(
                "| {capability_id} | {execution_type} | {cost_class} | {enabled} | {tenant_scoped} | {pii_classification} | {approval_required} | {side_effecting} | {owner} | {source} |".format(
                    **capability
                )
            )
        return "\n".join(lines).rstrip() + "\n"

    def from_specs(self, specs: Iterable[Dict[str, Any]]) -> "PythonCapabilityRegistry":
        for spec in specs:
            self.register_spec(spec)
        return self

    def from_json(self, path: str | Path, *, allow_missing: bool = False) -> "PythonCapabilityRegistry":
        p = Path(path)
        if not p.exists():
            if allow_missing:
                return self
            raise FileNotFoundError(f"registry seed missing: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - strict on purpose
            raise ValueError(f"bad registry JSON at {p}: {exc}") from exc
        if isinstance(data, dict):
            specs = data.get("capabilities", [])
        elif isinstance(data, list):
            specs = data
        else:
            raise ValueError(f"registry JSON must be an object or list: {p}")
        for spec in specs:
            if not isinstance(spec, dict):
                raise ValueError(f"registry JSON contains non-object capability spec: {p}")
            self.register_spec(spec)
        return self


DEFAULT_CAPABILITY_SPECS: List[Dict[str, Any]] = [
    {
        "capability_id": "get_python_capability_registry",
        "name": "Python capability registry lookup",
        "description": "Read the deterministic Python capability inventory and filter it by id or class.",
        "module": "nexus_agent_platform.capabilities.python_registry",
        "callable": "get_python_capability_registry",
        "input_schema": {
            "type": "object",
            "properties": {
                "capability_id": {"type": "string"},
                "execution_type": {"type": "string"},
                "cost_class": {"type": "string"},
                "enabled": {"type": "boolean"},
            },
        },
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 1,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/python_registry.py",
    },
    {
        "capability_id": "get_runtime_capabilities",
        "name": "Runtime capability inventory",
        "description": "Return the currently approved runtime capabilities for an agent.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "get_runtime_capabilities",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 5,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_system_health",
        "name": "System health summary",
        "description": "Summarize current system health from canonical Hermes status and failure reports.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_system_health",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Hermes",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_process_registry_live",
        "name": "Live process registry",
        "description": "Read the normalized process registry with configuration, execution mode, and runtime state.",
        "module": "nexus_agent_platform.capabilities.nexus_knowledge",
        "callable": "get_process_registry_live",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/nexus_knowledge.py",
    },
    {
        "capability_id": "get_process_details",
        "name": "Process detail lookup",
        "description": "Read the normalized detail record for a single process id.",
        "module": "nexus_agent_platform.capabilities.nexus_knowledge",
        "callable": "get_process_details",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
            "required": ["process_id"],
        },
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/nexus_knowledge.py",
    },
    {
        "capability_id": "get_operational_summary",
        "name": "Operational summary",
        "description": "Return a governed, read-only summary of operational state, approvals, and recent activity.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_operational_summary",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 15,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Hermes",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_runtime_execution_summary",
        "name": "Runtime execution summary",
        "description": "Summarize verified runtime telemetry across all Nexus execution events.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_runtime_execution_summary",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_active_runs",
        "name": "Active run lookup",
        "description": "Return currently running execution telemetry events.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_active_runs",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_recent_runs",
        "name": "Recent run lookup",
        "description": "Return the most recent execution telemetry events within a bounded window.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_recent_runs",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_failed_runs",
        "name": "Failed run lookup",
        "description": "Return execution telemetry events whose terminal state is failed.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_failed_runs",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_process_execution_history",
        "name": "Process execution history",
        "description": "Return bounded execution telemetry history for one process.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_process_execution_history",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
        },
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_last_process_run",
        "name": "Last process run",
        "description": "Return the most recent run for a process id.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_last_process_run",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
        },
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_execution_evidence",
        "name": "Execution evidence",
        "description": "Return a bounded evidence envelope for verified runtime telemetry.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_execution_evidence",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_runtime_telemetry_health",
        "name": "Runtime telemetry health",
        "description": "Summarize whether the runtime telemetry system is healthy, partial, degraded, or unavailable.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_runtime_telemetry_health",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_pending_approvals",
        "name": "Pending approvals",
        "description": "Return the governed approval queue in read-only form.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_pending_approvals",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Governance",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_approval_status",
        "name": "Approval status",
        "description": "Return the current status of a single governed approval.",
        "module": "nexus_agent_platform.governed.actions_api",
        "callable": "get_approval_status",
        "input_schema": {
            "type": "object",
            "properties": {"approval_id": {"type": "string"}},
        },
        "output_schema": {"type": "object"},
        "execution_type": "API",
        "cost_class": "LOW_EXTERNAL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 15,
        "retry_policy": "single_retry",
        "enabled": True,
        "test_status": "certified",
        "owner": "Governance",
        "source": "scripts/nexus_agent_platform/governed/actions_api.py",
    },
    {
        "capability_id": "get_work_order_status",
        "name": "Work order status",
        "description": "Return the current status of a governed work order.",
        "module": "nexus_agent_platform.governed.actions_api",
        "callable": "get_work_order_status",
        "input_schema": {
            "type": "object",
            "properties": {"work_order_id": {"type": "string"}},
        },
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Governance",
        "source": "scripts/nexus_agent_platform/governed/actions_api.py",
    },
    {
        "capability_id": "get_work_queue",
        "name": "Work queue",
        "description": "Return the current governed work queue in bounded form.",
        "module": "nexus_agent_platform.governed.actions_api",
        "callable": "get_work_queue",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Governance",
        "source": "scripts/nexus_agent_platform/governed/actions_api.py",
    },
    {
        "capability_id": "get_funding_readiness",
        "name": "Funding readiness lookup",
        "description": "Read canonical funding readiness information for one client or tenant scope.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_funding_readiness",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "client_id": {"type": "string"},
            },
        },
        "output_schema": {"type": "object"},
        "execution_type": "API",
        "cost_class": "LOW_EXTERNAL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": True,
        "tenant_scope": "CLIENT",
        "pii_classification": "CLIENT_PII",
        "approval_required": False,
        "timeout": 20,
        "retry_policy": "single_retry",
        "enabled": True,
        "test_status": "certified",
        "owner": "Credit",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_client_profile",
        "name": "Client profile lookup",
        "description": "Read a tenant-scoped client profile with canonical field redaction.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_client_profile",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "client_id": {"type": "string"},
            },
        },
        "output_schema": {"type": "object"},
        "execution_type": "API",
        "cost_class": "LOW_EXTERNAL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": True,
        "tenant_scope": "CLIENT",
        "pii_classification": "CLIENT_PII",
        "approval_required": False,
        "timeout": 20,
        "retry_policy": "single_retry",
        "enabled": True,
        "test_status": "certified",
        "owner": "Client Ops",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
    },
    {
        "capability_id": "get_recent_research",
        "name": "Recent research intake",
        "description": "AI-assisted synthesis of recent research runs and results.",
        "module": "nexus_agent_platform.capabilities.shared",
        "callable": "_handle_recent_research",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "AI_ASSISTED",
        "cost_class": "AI_TIER_1",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": True,
        "timeout": 30,
        "retry_policy": "single_retry",
        "enabled": False,
        "test_status": "blocked_by_missing_search_keys",
        "owner": "Alpha",
        "source": "scripts/nexus_agent_platform/capabilities/shared.py",
        "notes": "Disabled until search/API keys are configured for live research intake.",
        "ai_usage": "research synthesis over bounded external evidence",
    },
    {
        "capability_id": "get_nexus_study_overview",
        "name": "Nexus study overview",
        "description": "Read the compact study snapshot used by live Nova study answers.",
        "module": "nexus_agent_platform.capabilities.nexus_study",
        "callable": "get_nexus_study_overview",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "reports/nova_study/nexus_study_snapshot.json",
    },
    {
        "capability_id": "get_nexus_study_snapshot",
        "name": "Nexus study snapshot",
        "description": "Read the full governed study snapshot artifact.",
        "module": "nexus_agent_platform.capabilities.nexus_study",
        "callable": "get_nexus_study_snapshot",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "reports/nova_study/nexus_study_snapshot.json",
    },
    {
        "capability_id": "get_nexus_gap_summary",
        "name": "Nexus gap summary",
        "description": "Read the bounded study gap summary with contradictions and unknowns.",
        "module": "nexus_agent_platform.capabilities.nexus_study",
        "callable": "get_nexus_gap_summary",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "reports/nova_study/nexus_gaps.json",
    },
    {
        "capability_id": "get_business_model_summary",
        "name": "Business model summary",
        "description": "Read the study-derived business model summary.",
        "module": "nexus_agent_platform.capabilities.nexus_study",
        "callable": "get_business_model_summary",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "reports/nova_study/nexus_study_snapshot.json",
    },
    {
        "capability_id": "get_integration_inventory",
        "name": "Integration inventory",
        "description": "Read the study-derived integration inventory.",
        "module": "nexus_agent_platform.capabilities.nexus_study",
        "callable": "get_integration_inventory",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "reports/nova_study/nexus_study_snapshot.json",
    },
    {
        "capability_id": "get_client_workflow_summary",
        "name": "Client workflow summary",
        "description": "Read the study-derived client workflow summary.",
        "module": "nexus_agent_platform.capabilities.nexus_study",
        "callable": "get_client_workflow_summary",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "execution_type": "DETERMINISTIC",
        "cost_class": "ZERO_MODEL_COST",
        "side_effecting": False,
        "risk_class": "LOW",
        "tenant_scoped": False,
        "tenant_scope": "SYSTEM",
        "pii_classification": "NONE",
        "approval_required": False,
        "timeout": 10,
        "retry_policy": "none",
        "enabled": True,
        "test_status": "certified",
        "owner": "Nexus",
        "source": "reports/nova_study/nexus_study_snapshot.json",
    },
]


def build_default_registry() -> PythonCapabilityRegistry:
    registry = PythonCapabilityRegistry()
    registry.from_specs(DEFAULT_CAPABILITY_SPECS)
    return registry


def get_default_registry() -> PythonCapabilityRegistry:
    return build_default_registry()


def get_python_capability_registry(
    capability_id: Optional[str] = None,
    *,
    execution_type: Optional[ExecutionType | str] = None,
    cost_class: Optional[CostClass | str] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    registry = get_default_registry()

    exec_type = _enum_from_value(ExecutionType, execution_type) if execution_type is not None else None
    cost = _enum_from_value(CostClass, cost_class) if cost_class is not None else None

    if capability_id:
        cap = registry.get(capability_id)
        return {
            "status": "success" if cap else "not_found",
            "registry_id": registry.identifier,
            "capability": cap.to_dict() if cap else None,
            "summary": registry.summary(),
            "source_type": "python_capability_registry",
            "source": "scripts/nexus_agent_platform/capabilities/python_registry.py",
        }

    caps = registry.query(execution_type=exec_type, cost_class=cost, enabled=enabled)
    return {
        "status": "success",
        "registry_id": registry.identifier,
        "summary": registry.summary(),
        "capabilities": [cap.to_dict() for cap in caps],
        "count": len(caps),
        "source_type": "python_capability_registry",
        "source": "scripts/nexus_agent_platform/capabilities/python_registry.py",
    }


def lookup_python_capability(capability_id: str) -> Optional[Dict[str, Any]]:
    registry = get_default_registry()
    cap = registry.get(capability_id)
    return cap.to_dict() if cap else None


def render_python_capability_registry_markdown() -> str:
    return get_default_registry().to_markdown()


__all__ = [
    "REGISTRY_ID",
    "REGISTRY_VERSION",
    "CostClass",
    "ExecutionType",
    "CapabilityMetadata",
    "PiiClassification",
    "RiskClass",
    "TenantScope",
    "PythonCapabilityRegistry",
    "build_default_registry",
    "get_default_registry",
    "get_python_capability_registry",
    "lookup_python_capability",
    "render_python_capability_registry_markdown",
]
