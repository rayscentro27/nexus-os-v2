"""Small canonical contract for continuous, cooperative Nexus operation.

This module owns state transitions and receipts, not provider calls or arbitrary
process execution.  Existing Research/Alpha workers remain the executors.  A
cycle may finish, but an enabled objective or program always gets a durable
next action and wake time.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
HEARTBEAT_PATH = ROOT / "data/runtime/research_heartbeat.json"
PROGRAM_PATH = ROOT / "data/runtime/research_program_registry.json"
RECEIPT_PATH = ROOT / "reports/runtime/continuous_operating_kernel_latest.json"

PROGRAMS = (
    ("YOUTUBE_INTELLIGENCE", "approved YouTube source monitoring"),
    ("WEB_SOURCE_WATCH", "bounded public website review"),
    ("GITHUB_LAST_30_DAYS", "recent capability and repository intelligence"),
    ("SEO_INTELLIGENCE", "search-intent and content-gap intelligence"),
    ("NEXUS_SYSTEM_IMPROVEMENT", "safe internal capability comparison"),
    ("MARKETING_INTELLIGENCE", "audience, offer, and channel research"),
    ("BUSINESS_OPPORTUNITY_DISCOVERY", "evidence-backed opportunity discovery"),
    ("TRADING_RESEARCH", "paper/demo research and backtest feedback"),
    ("FUNDING_INTELLIGENCE", "public funding and lending intelligence"),
    ("GRANT_INTELLIGENCE", "public grant intelligence"),
    ("COMPETITOR_INTELLIGENCE", "competitor and positioning evidence"),
    ("CAPABILITY_INTELLIGENCE", "tools, models, methods, and version research"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def build_program_registry(*, source_registry: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Materialize enabled programs over existing source policy, idempotently."""
    sources = source_registry or []
    existing = _read(PROGRAM_PATH, [])
    by_id = {row.get("program_id"): row for row in existing if isinstance(row, dict)}
    timestamp = now()
    for program_id, purpose in PROGRAMS:
        prior = by_id.get(program_id, {})
        by_id[program_id] = {
            **prior,
            "program_id": program_id,
            "purpose": purpose,
            "enabled": True,
            "frequency_or_trigger": prior.get("frequency_or_trigger", "next_cycle_or_due_source"),
            "last_run": prior.get("last_run"),
            "last_success": prior.get("last_success"),
            "next_run": prior.get("next_run"),
            "health": prior.get("health", "HEALTHY"),
            "sources_or_query_policy": prior.get("sources_or_query_policy", "existing canonical registries; bounded read-only"),
            "new_items_found": int(prior.get("new_items_found", 0)),
            "claims_verified": int(prior.get("claims_verified", 0)),
            "knowledge_updated": int(prior.get("knowledge_updated", 0)),
            "work_generated": int(prior.get("work_generated", 0)),
            "updated_at": timestamp,
        }
    result = list(by_id.values())
    _write(PROGRAM_PATH, result)
    return result


def build_source_registry() -> list[dict[str, Any]]:
    """Project curated source config into a durable monitoring registry."""
    config_path = ROOT / "configs/youtube_research_channels.json"
    config = _read(config_path, {})
    targets = config.get("channels", []) if isinstance(config, dict) else []
    targets += config.get("videos", []) if isinstance(config, dict) else []
    # Alpha already owns the durable source registry.  Extend that canonical
    # file instead of introducing a second source database.
    registry_path = ROOT / "data/runtime/alpha_source_registry.json"
    prior = _read(registry_path, [])
    by_id = {row.get("source_id"): row for row in prior if isinstance(row, dict)}
    for target in targets:
        if not isinstance(target, dict) or not target.get("approved_by_ray"):
            continue
        url = target.get("url") or target.get("channel_url") or target.get("video_url")
        if not url:
            continue
        source_id = "src_" + fingerprint(url)
        prior_row = by_id.get(source_id, {})
        kind = "YOUTUBE_VIDEO" if "video" in url or target.get("video_id") else "YOUTUBE_CHANNEL"
        by_id[source_id] = {
            **prior_row,
            "source_id": source_id,
            "source_type": kind,
            "name": target.get("name") or target.get("channel_name") or target.get("video_id") or url,
            "url_or_safe_identifier": url.split("&", 1)[0],
            "owner_department": "RESEARCH",
            "parent_objective": "ray_curated_youtube_intelligence",
            "created_by": "RAY_CURATED",
            "monitoring_enabled": True,
            "monitoring_policy": "bounded metadata/transcript availability; no media download",
            "initial_research_policy": "approved-only bounded read",
            "ongoing_research_policy": "check due source and persist content identity",
            "health": prior_row.get("health", "UNVERIFIED"),
            "last_checked": prior_row.get("last_checked"),
            "next_check": prior_row.get("next_check"),
            "processed_content_identifiers": prior_row.get("processed_content_identifiers", []),
        }
    result = list(by_id.values())
    _write(registry_path, result)
    return result


def next_research_action(*, queue_empty: bool, incomplete_objectives: int, alpha_feedback: int = 0,
                         due_sources: int = 0, knowledge_gaps: int = 0, stale_claims: int = 0) -> str:
    if incomplete_objectives:
        return "CONTINUE_INCOMPLETE_OBJECTIVE"
    if alpha_feedback:
        return "RUN_TARGETED_FEEDBACK_RESEARCH"
    if due_sources:
        return "CHECK_DUE_MONITORED_SOURCE"
    if knowledge_gaps:
        return "RESEARCH_DEPARTMENT_KNOWLEDGE_GAP"
    if stale_claims:
        return "REFRESH_STALE_KNOWLEDGE"
    if queue_empty:
        return "RUN_BOUNDED_AUTONOMOUS_DISCOVERY"
    return "PROCESS_QUEUED_RESEARCH"


def alpha_feedback_decision(score: float, missing_evidence: list[str], *, revision: int = 0) -> dict[str, Any]:
    """Turn a weak result into bounded targeted research, never terminal rejection."""
    if score >= 0.70:
        decision = "ACCEPT_USE_OR_MONITOR"
    elif missing_evidence and revision < 2:
        decision = "FOLLOW_UP_RESEARCH"
    else:
        decision = "REJECT_BRANCH_KEEP_PARENT_OPEN"
    return {"decision": decision, "score": score, "missing_evidence": missing_evidence,
            "revision": revision, "parent_objective_remains_open": decision != "ACCEPT_USE_OR_MONITOR",
            "next_action": "target_missing_evidence" if decision == "FOLLOW_UP_RESEARCH" else "search_alternative" if decision.startswith("REJECT") else "monitor"}


def consequence_threshold(*, reversible: bool, external_impact: bool, financial_impact: bool) -> str:
    if financial_impact or external_impact:
        return "HIGH_APPROVAL_GATED"
    return "MODERATE_REVERSIBLE_EXPERIMENT" if reversible else "HIGH_INTERNAL_CHANGE"


def resource_decision(*, pressure: float, checkpoint: dict[str, Any]) -> dict[str, Any]:
    if pressure >= 0.8:
        return {"state": "YIELDING", "research_enabled": True, "next_action": "resume_checkpoint",
                "checkpoint": checkpoint, "resume_without_manual_restart": True}
    return {"state": "RUNNING", "research_enabled": True, "next_action": "continue_cycle",
            "checkpoint": checkpoint, "resume_without_manual_restart": True}


def watchdog_decision(*, enabled: bool, state: str, heartbeat_age_seconds: int | None,
                      max_age_seconds: int = 900) -> dict[str, Any]:
    stale = heartbeat_age_seconds is None or heartbeat_age_seconds > max_age_seconds
    if enabled and (state in {"STOPPED", "FAILED"} or stale):
        return {"status": "RECOVERY_REQUIRED", "action": "BOUNDED_RESTART_OR_RECONNECT", "circuit_breaker": True}
    return {"status": "HEALTHY", "action": "NO_ACTION", "circuit_breaker": True}


def run_feedback_cycle(initial_fn: Callable[[], dict[str, Any]], followup_fn: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """Automatically turn weak Alpha evidence into one bounded follow-up."""
    initial = dict(initial_fn())
    decision = alpha_feedback_decision(float(initial.get("score", 0.0)), list(initial.get("missing_evidence", [])), revision=0)
    followup = dict(followup_fn(decision)) if decision["decision"] == "FOLLOW_UP_RESEARCH" else None
    return {"initial": initial, "alpha_decision": decision, "followup": followup,
            "objective_terminal": False if followup is not None else decision["decision"] != "REJECT_BRANCH_KEEP_PARENT_OPEN"}


def recover_loop(*, enabled: bool, state: str, heartbeat_age_seconds: int | None,
                 restart_fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Perform one governed recovery cycle and verify the replacement heartbeat."""
    decision = watchdog_decision(enabled=enabled, state=state, heartbeat_age_seconds=heartbeat_age_seconds)
    if decision["status"] != "RECOVERY_REQUIRED":
        return {"status": "NO_ACTION", "decision": decision}
    recovery = dict(restart_fn())
    return {"status": "RECOVERED" if recovery.get("result", {}).get("status") == "PASS" else "DEGRADED",
            "decision": decision, "recovery": recovery, "attempts": 1, "bounded": True}


def run_cycle(cycle_fn: Callable[[], dict[str, Any]], *, cycle_id: str | None = None,
              queue_empty: bool = True, incomplete_objectives: int = 0,
              alpha_feedback: int = 0, due_sources: int = 0, knowledge_gaps: int = 0,
              stale_claims: int = 0, pressure: float = 0.0) -> dict[str, Any]:
    """Run one bounded cycle and persist a heartbeat even when work is empty."""
    started = now()
    cycle_id = cycle_id or "cycle_" + fingerprint((started, os.getpid()))
    action = next_research_action(queue_empty=queue_empty, incomplete_objectives=incomplete_objectives,
                                  alpha_feedback=alpha_feedback, due_sources=due_sources,
                                  knowledge_gaps=knowledge_gaps, stale_claims=stale_claims)
    resources = resource_decision(pressure=pressure, checkpoint={"cycle_id": cycle_id, "next_action": action})
    result = dict(cycle_fn())
    finished = now()
    next_wake = (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat()
    heartbeat = {
        "schema_version": "nexus.research-heartbeat.v1", "enabled": True, "heartbeat": "ACTIVE",
        "scheduler": "ACTIVE_IN_PROCESS_CYCLE", "worker_state": "IDLE_BETWEEN_CYCLES",
        "cycle_id": cycle_id, "started_at": started, "last_success": finished,
        "next_wake": next_wake, "next_action": action, "resources": resources,
        "result_status": result.get("status", "PASS"), "objective_owner": "RESEARCH",
        "objective_has_durable_owner": True, "queue_empty_does_not_stop": True,
    }
    _write(HEARTBEAT_PATH, heartbeat)
    receipt = {"schema_version": "nexus.continuous-kernel-receipt.v1", "cycle_id": cycle_id,
               "started_at": started, "completed_at": finished, "heartbeat": heartbeat,
               "result": result, "single_final_outcome": True}
    _write(RECEIPT_PATH, receipt)
    return receipt


def current_kernel_contract() -> dict[str, Any]:
    heartbeat = _read(HEARTBEAT_PATH, {})
    scheduler_health = _read(ROOT / "reports/phase16a/scheduler_health.json", {})
    scheduler = heartbeat.get("scheduler", "INACTIVE")
    if scheduler_health.get("status") == "FAIL":
        scheduler = "INACTIVE"
    return {"research_enabled": True, "research_heartbeat": heartbeat.get("heartbeat", "UNKNOWN"),
            "research_scheduler": scheduler, "research_scheduler_reason": "existing launchd supervisor is not healthy" if scheduler == "INACTIVE" else None,
            "research_background_process_state": "IDLE_BETWEEN_CYCLES" if heartbeat.get("worker_state") else "STOPPED",
            "research_worker_state": heartbeat.get("worker_state", "UNKNOWN"), "research_next_wake": heartbeat.get("next_wake", "NONE"),
            "next_research_action": heartbeat.get("next_action", "INSPECT_OBJECTIVES"), "objective_owner": "RESEARCH",
            "heartbeat_path": str(HEARTBEAT_PATH.relative_to(ROOT)), "scheduler_health_path": "reports/phase16a/scheduler_health.json"}
