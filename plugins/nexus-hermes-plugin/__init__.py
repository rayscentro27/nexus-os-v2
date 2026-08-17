"""Governed Nexus plugin for upstream Hermes.

This plugin is read-only. It surfaces deterministic capability lookup and
bounded status views over existing Nexus readers. It does not expose shell
execution, SQL execution, filesystem mutation, or write paths.
"""

from __future__ import annotations

import json
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from nexus_agent_platform.capabilities.python_registry import (  # noqa: E402
    CostClass,
    ExecutionType,
    PiiClassification,
    build_default_registry,
    lookup_python_capability,
)
from nexus_agent_platform.capabilities.shared import execute_shared_capability  # noqa: E402


PLUGIN_NAME = "nexus-hermes-plugin"
READ_ONLY_BOUNDARY = "read_only_governed_capability"

_TOOL_SPECS = (
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
)

_SKILL_SPECS = (
    ("nexus-operator", "Operational control and governed read routing."),
    ("nexus-research-director", "Research triage, evidence intake, and synthesis."),
    ("nexus-opportunity-director", "Opportunity discovery, validation, and scoring."),
    ("nexus-creative-director", "Creative territory selection with research-first rules."),
    ("nexus-marketing-director", "Marketing status, planning, and bounded execution."),
    ("nexus-seo-director", "SEO opportunity evaluation and content planning."),
    ("nexus-credit-readiness", "Credit readiness assessment and evidence review."),
    ("nexus-credit-result-verification", "Verification of credit result evidence."),
    ("nexus-business-foundation", "Business foundation checks and operational readiness."),
    ("nexus-funding-readiness", "Funding readiness analysis and next-step routing."),
    ("nexus-crj-handoff", "CRJ handoff preparation and governed evidence transfer."),
)


def _utc_stamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _coerce_enum(enum_cls, value):
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls[value] if isinstance(value, str) and value in enum_cls.__members__ else enum_cls(value)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _registry():
    return build_default_registry()


def _serialize_capability(capability_id: str) -> Dict[str, Any]:
    cap = lookup_python_capability(capability_id)
    if not cap:
        return {
            "status": "not_found",
            "capability_id": capability_id,
            "read_only_boundary": True,
        }
    return {
        "status": "success",
        "capability_id": capability_id,
        "capability": cap,
        "read_only_boundary": True,
    }


def _registry_lookup(
    *,
    capability_id: Optional[str] = None,
    execution_type: Optional[str] = None,
    cost_class: Optional[str] = None,
    enabled: Optional[bool] = None,
    keyword: Optional[str] = None,
    tenant_scoped: Optional[bool] = None,
    pii_classification: Optional[str] = None,
) -> Dict[str, Any]:
    registry = _registry()
    query_kwargs: Dict[str, Any] = {}
    if capability_id:
        cap = registry.get(capability_id)
        return {
            "status": "success" if cap else "not_found",
            "registry_id": registry.identifier,
            "summary": registry.summary(),
            "capability": cap.to_dict() if cap else None,
            "capabilities": [cap.to_dict()] if cap else [],
            "count": 1 if cap else 0,
            "read_only_boundary": True,
            "source_requirement": "deterministic_python_registry",
            "retrieved_at": _utc_stamp(),
            "retrieval": {
                "approx_tokens": _approx_tokens(json.dumps(cap.to_dict() if cap else {}, default=str)),
                "mode": "lookup",
            },
        }

    if execution_type:
        coerced = _coerce_enum(ExecutionType, execution_type)
        if coerced is None:
            return {
                "status": "error",
                "registry_id": registry.identifier,
                "error": f"Unknown execution_type: {execution_type}",
                "read_only_boundary": True,
                "source_requirement": "deterministic_python_registry",
            }
        query_kwargs["execution_type"] = coerced
    if cost_class:
        coerced = _coerce_enum(CostClass, cost_class)
        if coerced is None:
            return {
                "status": "error",
                "registry_id": registry.identifier,
                "error": f"Unknown cost_class: {cost_class}",
                "read_only_boundary": True,
                "source_requirement": "deterministic_python_registry",
            }
        query_kwargs["cost_class"] = coerced
    if enabled is not None:
        query_kwargs["enabled"] = enabled
    pii = _coerce_enum(PiiClassification, pii_classification) if pii_classification else None
    if pii_classification and pii is None:
        return {
            "status": "error",
            "registry_id": registry.identifier,
            "error": f"Unknown pii_classification: {pii_classification}",
            "read_only_boundary": True,
            "source_requirement": "deterministic_python_registry",
        }
    caps = registry.query(
        **query_kwargs,
        keyword=keyword,
        tenant_scoped=tenant_scoped,
        pii_classification=pii,
    )
    serialized = [cap.to_dict() for cap in caps]
    return {
        "status": "success",
        "registry_id": registry.identifier,
        "summary": registry.summary(),
        "capabilities": serialized,
        "count": len(serialized),
        "read_only_boundary": True,
        "source_requirement": "deterministic_python_registry",
        "retrieved_at": _utc_stamp(),
        "retrieval": {
            "approx_tokens": _approx_tokens(json.dumps(serialized, default=str)),
            "mode": "query",
        },
    }


def _call_shared(capability_id: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    started = time.monotonic()
    result = execute_shared_capability(
        "hermes_nova",
        capability_id,
        args,
        trace_id=f"{PLUGIN_NAME}:{capability_id}",
    )
    payload = result.get("data", result)
    return {
        "status": result.get("status", "success"),
        "capability_selected": capability_id,
        "source_requirement": "governed_shared_read",
        "read_only_boundary": True,
        "tenant_scoped": bool(result.get("tenant_scoped", False)),
        "pii_classification": result.get("pii_classification", "NONE"),
        "result": payload,
        "provenance": result.get("provenance", {}),
        "retrieval": {
            "duration_ms": int((time.monotonic() - started) * 1000),
            "approx_tokens": _approx_tokens(json.dumps(payload, default=str)),
        },
    }


def _call_client_scoped(capability_id: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    if not args.get("email") and not args.get("client_id"):
        return {
            "status": "error",
            "capability_selected": capability_id,
            "source_requirement": "tenant_scoped_client_read",
            "read_only_boundary": True,
            "tenant_scoped": True,
            "pii_classification": "CLIENT_PII",
            "error": "email or client_id is required for client-scoped reads",
        }
    return _call_shared(capability_id, args)


def nexus_capability_lookup(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    return {
        "status": "success",
        "tool": "nexus_capability_lookup",
        "read_only_boundary": True,
        "source_requirement": "deterministic_python_registry",
        "query": {
            "capability_id": args.get("capability_id"),
            "execution_type": args.get("execution_type"),
            "cost_class": args.get("cost_class"),
            "enabled": args.get("enabled"),
            "keyword": args.get("keyword"),
            "tenant_scoped": args.get("tenant_scoped"),
            "pii_classification": args.get("pii_classification"),
        },
        "result": _registry_lookup(
            capability_id=args.get("capability_id"),
            execution_type=args.get("execution_type"),
            cost_class=args.get("cost_class"),
            enabled=args.get("enabled"),
            keyword=args.get("keyword"),
            tenant_scoped=args.get("tenant_scoped"),
            pii_classification=args.get("pii_classification"),
        ),
    }


def nexus_system_status(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    return {
        "status": "success",
        "tool": "nexus_system_status",
        "read_only_boundary": True,
        "source_requirement": "deterministic_python_and_governed_reads",
        "result": {
            "overview": _call_shared("get_nexus_overview", {}),
            "system_health": _call_shared("get_system_health", {}),
            "process_registry": _call_shared("get_process_registry", {}),
            "runtime_summary": _call_shared("get_runtime_execution_summary", {"window": args.get("window", "last_24_hours")}),
        },
    }


def nexus_process_status(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    process_id = args.get("process_id")
    if process_id:
        result = _call_shared("get_process_details", {"process_id": process_id})
    else:
        result = _call_shared("get_process_registry", {})
    return {
        "status": result.get("status", "success"),
        "tool": "nexus_process_status",
        "read_only_boundary": True,
        "source_requirement": "governed_process_registry_read",
        "result": result,
    }


def nexus_runtime_status(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    window = args.get("window", "last_24_hours")
    limit = args.get("limit", 10)
    return {
        "status": "success",
        "tool": "nexus_runtime_status",
        "read_only_boundary": True,
        "source_requirement": "verified_execution_telemetry",
        "result": {
            "summary": _call_shared("get_runtime_execution_summary", {"window": window}),
            "active_runs": _call_shared("get_active_runs", {"window": window, "limit": limit}),
            "recent_runs": _call_shared("get_recent_runs", {"window": window, "limit": limit}),
            "failed_runs": _call_shared("get_failed_runs", {"window": window, "limit": limit}),
            "telemetry_health": _call_shared("get_runtime_telemetry_health", {"window": window}),
        },
    }


def nexus_research_status(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    return {
        "status": "success",
        "tool": "nexus_research_status",
        "read_only_boundary": True,
        "source_requirement": "bounded_report_and_activity_reads",
        "result": {
            "report_index": _call_shared("get_report_index", {}),
            "latest_reports": _call_shared("get_latest_reports", {"limit": args.get("limit", 10)}),
            "recent_activity": _call_shared("get_recent_activity", {"window": args.get("window", "last_24_hours")}),
        },
    }


def nexus_marketing_status(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "nexus_marketing_status",
        "read_only_boundary": True,
        "source_requirement": "governed_operational_summary",
        "result": {
            "operational_summary": _call_shared("get_operational_summary", {}),
            "recent_activity": _call_shared("get_recent_activity", {"window": "last_24_hours"}),
        },
    }


def nexus_revenue_status(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "nexus_revenue_status",
        "read_only_boundary": True,
        "source_requirement": "study_business_model_summary",
        "result": {
            "business_model": _call_shared("get_business_model_summary", {}),
            "opportunities": _call_shared("get_opportunities", {}),
            "nexus_overview": _call_shared("get_nexus_overview", {}),
        },
    }


def nexus_pending_approvals(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "nexus_pending_approvals",
        "read_only_boundary": True,
        "source_requirement": "governed_approval_queue",
        "result": _call_shared("get_pending_approvals", {}),
    }


def nexus_automation_health(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "nexus_automation_health",
        "read_only_boundary": True,
        "source_requirement": "governed_system_and_runtime_reads",
        "result": {
            "system_health": _call_shared("get_system_health", {}),
            "runtime_health": _call_shared("get_runtime_telemetry_health", {"window": (arguments or {}).get("window", "last_24_hours")}),
            "approvals": _call_shared("get_pending_approvals", {}),
            "operational_summary": _call_shared("get_operational_summary", {}),
        },
    }


def nexus_client_summary(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = arguments or {}
    if args.get("email") or args.get("client_id"):
        result = _call_client_scoped("get_client_profile", args)
    else:
        result = _call_shared("get_client_count", {})
    return {
        "status": result.get("status", "success"),
        "tool": "nexus_client_summary",
        "read_only_boundary": True,
        "source_requirement": "tenant_scoped_client_read" if args.get("email") or args.get("client_id") else "governed_client_count_read",
        "result": result,
    }


def nexus_credit_summary(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = _call_client_scoped("get_funding_readiness", arguments)
    return {
        "status": result.get("status", "success"),
        "tool": "nexus_credit_summary",
        "read_only_boundary": True,
        "source_requirement": "tenant_scoped_credit_read",
        "result": result,
    }


def nexus_business_foundation_summary(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "nexus_business_foundation_summary",
        "read_only_boundary": True,
        "source_requirement": "study_business_model_summary",
        "result": {
            "business_model": _call_shared("get_business_model_summary", {}),
            "integration_inventory": _call_shared("get_integration_inventory", {}),
            "study_snapshot": _call_shared("get_nexus_study_overview", {}),
        },
    }


def nexus_funding_readiness_summary(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = _call_client_scoped("get_funding_readiness", arguments)
    return {
        "status": result.get("status", "success"),
        "tool": "nexus_funding_readiness_summary",
        "read_only_boundary": True,
        "source_requirement": "tenant_scoped_funding_read",
        "result": result,
    }


_TOOL_HANDLERS = {
    "nexus_capability_lookup": nexus_capability_lookup,
    "nexus_system_status": nexus_system_status,
    "nexus_process_status": nexus_process_status,
    "nexus_runtime_status": nexus_runtime_status,
    "nexus_research_status": nexus_research_status,
    "nexus_marketing_status": nexus_marketing_status,
    "nexus_revenue_status": nexus_revenue_status,
    "nexus_pending_approvals": nexus_pending_approvals,
    "nexus_automation_health": nexus_automation_health,
    "nexus_client_summary": nexus_client_summary,
    "nexus_credit_summary": nexus_credit_summary,
    "nexus_business_foundation_summary": nexus_business_foundation_summary,
    "nexus_funding_readiness_summary": nexus_funding_readiness_summary,
}


def register(ctx) -> None:
    """Register read-only Nexus tools and versioned skills."""
    for tool_name in _TOOL_SPECS:
        handler = _TOOL_HANDLERS[tool_name]
        ctx.register_tool(
            name=tool_name,
            toolset="nexus-hermes",
            schema={
                "name": tool_name,
                "description": f"Read-only Nexus bridge tool: {tool_name}.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "capability_id": {"type": "string"},
                        "execution_type": {"type": "string"},
                        "cost_class": {"type": "string"},
                        "enabled": {"type": "boolean"},
                        "keyword": {"type": "string"},
                        "tenant_scoped": {"type": "boolean"},
                        "pii_classification": {"type": "string"},
                        "process_id": {"type": "string"},
                        "email": {"type": "string"},
                        "client_id": {"type": "string"},
                        "window": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "additionalProperties": True,
                },
            },
            handler=handler,
            description="Governed read-only Nexus bridge",
        )

    skill_root = Path(__file__).resolve().parent / "skills"
    for skill_name, description in _SKILL_SPECS:
        skill_path = skill_root / skill_name / "SKILL.md"
        if skill_path.exists():
            ctx.register_skill(skill_name, skill_path, description)


__all__ = [
    "PLUGIN_NAME",
    "READ_ONLY_BOUNDARY",
    "register",
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
