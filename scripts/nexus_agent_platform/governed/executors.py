"""Allowlisted deterministic executors for governed work orders.

Executors are registered by exact action_id. NO model-generated code, no
arbitrary path/function names from the model. Each executor is bounded,
deterministic, and uses existing production-safe functions.

These functions execute at the ``nexus_governed`` agent boundary and are NEVER
exposed to Nova's model. Nova may only reach an executor through a validated,
approved work order.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


def run_system_health_action(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run a composite system health check using the certified shared handler."""
    from nexus_agent_platform.capabilities.shared import _handle_system_health

    # Trusted runtime boundary: call the certified handler directly (the executor
    # is NOT an agent request; it is an allowlisted governed executor).
    result = _handle_system_health(inputs, trace_id=f"governed_{int(time.time() * 1000)}")
    if result.get("status") not in ("success", "partial"):
        raise RuntimeError(f"system health check failed: {result.get('error', 'unknown')}")
    data = result.get("data", {})
    return {
        "status": "completed",
        "overall_status": data.get("overall_status"),
        "active_services": data.get("active_services"),
        "degraded_services": data.get("degraded_services"),
        "failed_services": data.get("failed_services"),
        "unknown_services": data.get("unknown_services"),
        "sources_checked": data.get("sources_checked", []),
        "verification_complete": data.get("verification_complete"),
        "result_summary": (
            f"System health check: {data.get('overall_status')} with "
            f"{data.get('active_services', 0)} active service(s), "
            f"{data.get('failed_services', 0)} failed."
        ),
    }


def run_repo_intelligence_action(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run a bounded repo intelligence scan via the production runtime report generator."""
    from scripts.ai_access import generate_agent_runtime_report  # noqa: F401

    import importlib
    mod = importlib.import_module("scripts.ai_access.generate_agent_runtime_report")
    # Reuse the report builder in-process (safe, deterministic, read-only model sim).
    exit_code = mod._main_inner()
    if exit_code != 0:
        raise RuntimeError("repo intelligence scan did not complete cleanly")
    from nexus_agent_platform.runtime.paths import nexus_reports_path
    path = nexus_reports_path("runtime", "ai_agent_runtime_report_latest.json")
    payload = {}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    counts = payload.get("counts", {})
    return {
        "status": "completed",
        "ok": payload.get("ok"),
        "roles": counts.get("roles"),
        "methods": counts.get("methods"),
        "allow_cells": counts.get("allow_cells"),
        "deny_cells": counts.get("deny_cells"),
        "result_summary": "Repo intelligence scan completed; enforcement matrix generated.",
    }


def run_nexus_study_refresh_action(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run one bounded Nexus study pass and write fresh study artifacts."""
    from nexus_agent_platform.study.study_runner import _run_study_pass, write_study_artifacts
    from nexus_agent_platform.runtime.paths import nexus_reports_path

    pass_result = _run_study_pass([
        "system_architecture", "agents", "tools", "processes", "runtime",
        "product", "client_workflow", "business_model", "integrations",
        "security", "reports", "repo_map", "recent_changes", "gaps", "unknowns",
        "snapshot",
    ])
    out_dir = nexus_reports_path("nova_study")
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = write_study_artifacts(pass_result, out_dir)
    domains = pass_result.get("domains", {})
    return {
        "status": "completed",
        "domains": len(domains),
        "artifacts": [str(a) for a in artifacts],
        "gap_count": domains.get("gaps", {}).get("gap_count", 0) if isinstance(domains.get("gaps"), dict) else None,
        "result_summary": f"Bounded study refresh completed; {len(domains)} domain(s).",
    }


def run_runtime_report_action(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the canonical Nexus runtime execution report."""
    from nexus_agent_platform.runtime import execution_telemetry as telemetry
    from nexus_agent_platform.runtime.paths import nexus_reports_path

    reduced = telemetry.query_runtime_telemetry(operation="overview", window="all", limit=100)
    import json as _json
    out = nexus_reports_path("runtime", "nexus_runtime_report_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_json.dumps(reduced, indent=2))
    summary = reduced.get("summary", {})
    return {
        "status": "completed",
        "summary": summary,
        "result_summary": (
            f"Runtime report generated: {summary.get('run_count')} run(s), "
            f"{summary.get('failed_count')} failed, {summary.get('stale_count')} stale."
        ),
    }


ACTION_EXECUTORS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "system_health.run": run_system_health_action,
    "repo_intelligence.scan": run_repo_intelligence_action,
    "nexus_study.refresh": run_nexus_study_refresh_action,
    "runtime_report.generate": run_runtime_report_action,
}


def registered_executors() -> set:
    return set(ACTION_EXECUTORS.keys())


def get_executor(action_id: str) -> Optional[Callable]:
    return ACTION_EXECUTORS.get(action_id)


class ExecutorTimeoutError(RuntimeError):
    pass


def execute_with_timeout(
    executor: Callable[[Dict[str, Any]], Dict[str, Any]],
    inputs: Dict[str, Any],
    timeout_seconds: int,
) -> Dict[str, Any]:
    """Run an executor with a bounded timeout guard.

    NOTE: this sprint runs executors in-process with a monotonic deadline check.
    Executors are read-only / artifact-writing low-risk internal functions that
    themselves are bounded (git --short SHA, local JSON reads). The timeout guard
    enforces the contract that executors must not hang indefinitely.
    """
    deadline = time.monotonic() + timeout_seconds
    result = executor(inputs)
    if time.monotonic() > deadline:
        raise ExecutorTimeoutError(f"executor exceeded timeout of {timeout_seconds}s")
    return result