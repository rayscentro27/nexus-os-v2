"""Dependency-aware scheduler metadata for the persisted V5 owner objective.

This module describes ordering and resource waits. Execution still goes through
the canonical durable-job store and its registered department handlers.
"""
from __future__ import annotations

from typing import Any, Iterable


WORKSTREAMS: dict[str, dict[str, Any]] = {
    "RESEARCH": {"depends_on": [], "resources": ["SEARXNG", "NOTEBOOKLM"]},
    "NOTEBOOKLM": {"depends_on": [], "resources": ["NOTEBOOKLM"]},
    "ALPHA": {"depends_on": ["RESEARCH"]},
    "BUSINESS": {"depends_on": ["ALPHA"]},
    "FINANCE": {"depends_on": ["BUSINESS"]},
    "FUNDING": {"depends_on": ["BUSINESS", "FINANCE"]},
    "MARKETING": {"depends_on": ["BUSINESS", "CREATIVE"]},
    "CREATIVE": {"depends_on": ["BUSINESS"]},
    "GOCLEAR_FUNNEL": {"depends_on": ["BUSINESS", "MARKETING", "CREATIVE"]},
    "EMAIL": {"depends_on": []},
    "SOCIAL": {"depends_on": []},
    "NOVA": {"depends_on": []},
    "META_AI": {"depends_on": []},
    "MODAL": {"depends_on": []},
    "KAGGLE": {"depends_on": []},
    "HUGGING_FACE": {"depends_on": []},
    "NEEDLE": {"depends_on": []},
    "TRADING_RESEARCH": {"depends_on": ["SYSTEMS"]},
    "TRADING_BACKTEST": {"depends_on": ["TRADING_RESEARCH"]},
    "PAPER_TRADING": {"depends_on": ["TRADING_BACKTEST"]},
    "TRADING_TOURNAMENT": {"depends_on": ["PAPER_TRADING"]},
    "SYSTEMS": {"depends_on": []},
    "RESOURCE_GUARDS": {"depends_on": ["SYSTEMS"]},
    "HERMES": {"depends_on": []},
    "CODEX_OPENCODE_FAILOVER": {"depends_on": ["HERMES"]},
    "OPENCODE_MODEL_BENCHMARK": {"depends_on": ["CODEX_OPENCODE_FAILOVER"]},
    "OWNER_PORTAL": {"depends_on": ["BUSINESS"]},
}

DEPENDENCY_JOB_TYPES = {
    "RESEARCH": "RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
    "NOTEBOOKLM": "NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9",
    "ALPHA": "CERTIFICATION_ATLAS_ANALYSIS",
    "BUSINESS": "CERTIFICATION_ATLAS_ANALYSIS",
    "FINANCE": "FINANCE_CAMPAIGN_REVIEW",
    "FUNDING": "CERTIFICATION_FUNDING_REVIEW",
    "MARKETING": "MARKETING_CAMPAIGN_BUILD",
    "CREATIVE": "CREATIVE_ASSET_GENERATE",
    "GOCLEAR_FUNNEL": "LANDING_PAGE_VERIFY",
    "EMAIL": "CONTROLLED_EMAIL_SEND",
    "SOCIAL": "CONTROLLED_SOCIAL_POST",
    "NOVA": "CERTIFICATION_NOVA_SUMMARY",
    "META_AI": "NEXUS_DEPARTMENT_QUERY",
    "MODAL": "NEXUS_DEPARTMENT_QUERY",
    "KAGGLE": "NEXUS_DEPARTMENT_QUERY",
    "HUGGING_FACE": "NEXUS_DEPARTMENT_QUERY",
    "NEEDLE": "NEXUS_DEPARTMENT_QUERY",
    "TRADING_RESEARCH": "V5_TRADING_MARKET_SCAN",
    "TRADING_BACKTEST": "CERTIFICATION_TRADING_BACKTEST",
    "PAPER_TRADING": "NEXUS_DEPARTMENT_QUERY",
    "TRADING_TOURNAMENT": "NEXUS_DEPARTMENT_QUERY",
    "SYSTEMS": "NEXUS_DEPARTMENT_QUERY",
    "RESOURCE_GUARDS": "NEXUS_DEPARTMENT_QUERY",
    "HERMES": "NEXUS_DEPARTMENT_QUERY",
    "CODEX_OPENCODE_FAILOVER": "V5_OPENCODE_MODEL_BENCHMARK",
    "OPENCODE_MODEL_BENCHMARK": "V5_OPENCODE_MODEL_BENCHMARK",
    "OWNER_PORTAL": "NEXUS_DEPARTMENT_QUERY",
}

# Only list workstreams as runnable when the canonical worker has a concrete
# dispatch path. Other objective requirements stay visible as planned work,
# but are not counted as executable until an adapter is registered.
EXECUTABLE_WORKSTREAMS = {
    "RESEARCH", "SYSTEMS", "RESOURCE_GUARDS", "HERMES",
    "CODEX_OPENCODE_FAILOVER", "OPENCODE_MODEL_BENCHMARK", "TRADING_RESEARCH",
    # These use the canonical NEXUS_DEPARTMENT_QUERY dispatch, which invokes
    # the owning department and reports unavailable integrations as blockers.
    "NEEDLE", "HUGGING_FACE", "MODAL", "KAGGLE", "META_AI", "NOVA",
    "EMAIL", "SOCIAL", "OWNER_PORTAL", "PAPER_TRADING", "TRADING_TOURNAMENT",
}


def inspect_graph(*, completed: Iterable[str], waiting_resources: set[str],
                  job_status: dict[str, str] | None = None) -> dict[str, Any]:
    """Return all workstreams with dependency, resource, and current status."""
    completed_set = set(completed)
    status_map = job_status or {}
    rows = []
    for name, spec in WORKSTREAMS.items():
        deps = list(spec["depends_on"])
        missing = [dep for dep in deps if dep not in completed_set]
        resources = [r for r in spec.get("resources", []) if r in waiting_resources]
        status = status_map.get(name)
        if name in completed_set:
            status = "COMPLETED"
        elif status is None:
            status = "WAITING_RESOURCE_WINDOW" if resources else ("WAITING_DEPENDENCY" if missing else "READY")
        if resources:
            status = "WAITING_RESOURCE_WINDOW"
        elif status == "WAITING_RESOURCE_WINDOW" and not missing:
            status = "READY"
        if status == "READY" and name not in EXECUTABLE_WORKSTREAMS:
            status = "WAITING_EXECUTOR"
        rows.append({
            "workstream": name,
            "job_type": DEPENDENCY_JOB_TYPES[name],
            "depends_on": deps,
            "can_run_while_research_waiting": "RESEARCH" not in deps and name != "RESEARCH",
            "can_run_while_notebooklm_waiting": "NOTEBOOKLM" not in deps and name != "NOTEBOOKLM",
            "current_status": status,
            "blocking_resource": resources[0] if resources else None,
            "blocking_dependencies": missing,
            "next_action": "execute_registered_handler" if status == "READY" else (
                "retry_same_job_when_resource_normal" if status == "WAITING_RESOURCE_WINDOW" else
                "wait_for_dependencies" if status == "WAITING_DEPENDENCY" else "none"),
        })
    runnable = [row for row in rows if row["current_status"] == "READY"]
    waiting = [row for row in rows if row["current_status"].startswith(("WAITING", "BLOCKED"))]
    # Favor Systems and integration certification before business deliverables.
    runnable.sort(key=lambda row: (0 if row["workstream"] in {
        "SYSTEMS", "RESOURCE_GUARDS", "NEEDLE", "HUGGING_FACE", "MODAL", "KAGGLE",
        "META_AI", "HERMES", "CODEX_OPENCODE_FAILOVER", "OPENCODE_MODEL_BENCHMARK",
        "NOVA", "EMAIL", "SOCIAL"} else 1, row["workstream"]))
    return {"workstreams": rows, "runnable": runnable, "waiting": waiting,
            "runnable_zero_cost_job_count": len(runnable),
            "global_stop_allowed": len(runnable) == 0}
