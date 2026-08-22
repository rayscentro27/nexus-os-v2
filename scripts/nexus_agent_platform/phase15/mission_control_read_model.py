"""Bounded Mission Control read model.

This module aggregates existing Nexus evidence for display. It does not run
launchd, execute work, create approvals, or mutate any authoritative state.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.governed import approvals, work_orders  # noqa: E402
from nexus_agent_platform.opportunities.engine import opportunity_portfolio  # noqa: E402
from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.growth_operations import growth_portfolio  # noqa: E402

OUTPUT_PATH = ROOT / "public/runtime/nexus-mission-control.json"
PRIORITIES = ("P0", "P1", "P2", "P3", "P4")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def freshness(value: Any, now: datetime, cadence_seconds: int) -> str:
    timestamp = iso(value)
    if timestamp is None:
        return "UNKNOWN"
    age = (now - timestamp).total_seconds()
    if age < -300:
        return "TRANSIENT"
    if age <= cadence_seconds + 900:
        return "CURRENT"
    return "STALE"


def evidence(path: Path, updated: Any, now: datetime, cadence_seconds: int) -> Dict[str, Any]:
    return {
        "source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "last_updated": updated,
        "freshness": freshness(updated, now, cadence_seconds),
    }


def component_status(status: Any, updated: Any, path: Path, now: datetime, cadence: int, *, reason: str = "") -> Dict[str, Any]:
    status_text = str(status or "UNKNOWN").upper()
    return {"status": status_text, "reason": reason, **evidence(path, updated, now, cadence)}


def _latest_receipts(root: Path, limit: int = 8) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    paths = sorted(root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[: max(limit * 4, 32)] if root.exists() else []
    for path in paths:
        item = read_json(path, {})
        if not isinstance(item, dict):
            continue
        records.append({
            "receipt_id": item.get("receipt_id") or path.stem,
            "timestamp": item.get("completed_at") or item.get("created_at") or item.get("timestamp"),
            "status": item.get("status") or item.get("run_status") or item.get("outcome") or "RECORDED",
            "source": str(path.relative_to(ROOT)),
            "work_order_id": item.get("work_order_id") or item.get("created_work_order_id"),
        })
    return sorted(records, key=lambda row: row.get("timestamp") or "", reverse=True)[:limit]


def _latest_loop(root: Path) -> Dict[str, Any]:
    path = root / "data/runtime/nexus_loops/execution_ledger.jsonl"
    latest: Dict[str, Any] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]
    except OSError:
        return latest
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and (item.get("completed_at") or item.get("started_at")):
            latest = item
    return {key: latest.get(key) for key in ("completed_at", "started_at", "status", "result", "delta_status", "scheduled_for", "run_id") if key in latest}


def build_read_model(*, root: Path = ROOT, now: Optional[datetime] = None, approval_rows: Optional[List[Dict[str, Any]]] = None, work_rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    now = now or utc_now()
    live_path = root / "reports/hermes_modernization/live_runtime_status.json"
    live = read_json(live_path, {})
    scheduler_path = root / "reports/phase16a/scheduler_health.json"
    scheduler = read_json(scheduler_path, {})
    active_path = root / "reports/runtime/nexus_active_operator_heartbeat_latest.json"
    active = read_json(active_path, {})
    recovery_path = root / "reports/runtime/nexus_recovery_check_heartbeat_latest.json"
    recovery = read_json(recovery_path, {})
    hermes_path = root / "reports/runtime/nexus_hermes_telegram_heartbeat_latest.json"
    hermes = read_json(hermes_path, {})
    evidence_path = root / "reports/runtime/nexus_evidence_ingestion_heartbeat_latest.json"
    evidence_run = read_json(evidence_path, {})
    worker_path = root / "reports/runtime/nexus_remote_cpu_worker_heartbeat_latest.json"
    worker_run = read_json(worker_path, {})
    alpha_path = root / "reports/runtime/nexus_alpha_research_heartbeat_latest.json"
    alpha_run = read_json(alpha_path, {})
    registry_path = root / "data/operations/nexus_process_registry.json"
    registry = read_json(registry_path, [])

    core = (live.get("core_autonomy_runtime") or {}) if isinstance(live, dict) else {}
    optional = (live.get("optional_integrations") or {}) if isinstance(live, dict) else {}
    core_status = str(core.get("status", "UNKNOWN")).upper()
    active_last = active.get("last_successful_run") or active.get("last_run")
    recovery_last = recovery.get("last_successful_run") or recovery.get("last_run")
    hermes_last = hermes.get("last_run")
    scheduler_last = scheduler.get("last_heartbeat") or scheduler.get("updated_at")
    system = {
        "overall_status": "HEALTHY" if core_status == "HEALTHY" and active.get("operator_health") == "HEALTHY" and recovery.get("run_status") in {"NO_ACTION_REQUIRED", "RECOVERED", "HEALTHY"} and hermes.get("api_status") == "HEALTHY" else "DEGRADED",
        "core_runtime": component_status(core_status, live.get("generated_at"), live_path, now, 3600, reason="Phase 15 required core components"),
        "active_operator": component_status(active.get("operator_health"), active_last, active_path, now, 3600, reason="Bounded operator heartbeat"),
        "recovery_check": component_status(recovery.get("run_status"), recovery_last, recovery_path, now, 10800, reason="Governed recovery heartbeat"),
        "hermes": component_status(hermes.get("api_status"), hermes_last, hermes_path, now, 300, reason="Telegram polling heartbeat"),
    }

    approval_rows = approval_rows if approval_rows is not None else approvals.get_pending_approvals(requested_for="ray", include_self=True)
    work_rows = work_rows if work_rows is not None else work_orders.list_work_orders(limit=1000)
    def priority(row: Dict[str, Any]) -> str:
        return str((row.get("inputs") or {}).get("priority") or "P3").upper() if isinstance(row, dict) else "P3"
    open_rows = [row for row in work_rows if row.get("status") not in {"completed", "cancelled", "rejected", "expired"}]
    p0 = [row for row in open_rows if priority(row) == "P0"]
    p1 = [row for row in open_rows if priority(row) == "P1"]
    recovery_escalations = [row for row in open_rows if row.get("requested_by") == "recovery_check"]
    errors = [item for item in (active.get("errors", []), recovery.get("errors", []), hermes.get("errors", [])) for item in item]
    attention = {
        "pending_approvals": len(approval_rows), "p0_work": len(p0), "p1_work": len(p1),
        "recovery_escalations": len(recovery_escalations), "errors": errors,
    }
    schedule = {
        "continuous_loop": {"next": scheduler.get("next_dispatch"), "cadence": "Hourly", "source": str(scheduler_path.relative_to(root))},
        "active_operator": {"next": active.get("next_scheduled_run"), "cadence": "Hourly", "source": str(active_path.relative_to(root))},
        "recovery_check": {"next": recovery.get("next_scheduled_check"), "cadence": "Every 3 hours", "source": str(recovery_path.relative_to(root))},
        "hermes": {"next": None, "cadence": "Every 60 seconds", "source": str(hermes_path.relative_to(root))},
    }
    recent = _latest_receipts(root / "reports/runtime/nexus_active_operator_receipts")
    recent += _latest_receipts(root / "reports/runtime/nexus_recovery_check_receipts")
    recent += _latest_receipts(root / "reports/telegram/hermes_operator_receipts")
    recent.sort(key=lambda row: row.get("timestamp") or "", reverse=True)
    completed = [row for row in work_rows if row.get("status") == "completed"][:8]
    recent += [{"receipt_id": row.get("work_order_id"), "timestamp": row.get("completed_at"), "status": "WORK_COMPLETED", "source": "data/governed/work_orders.jsonl", "work_order_id": row.get("work_order_id")} for row in completed]
    optional_view = {}
    for name in ("alpha", "nova", "hermes", "mission_control"):
        value = optional.get(name) if isinstance(optional, dict) else None
        optional_view[name] = {"status": str((value or {}).get("status", "NOT_ENABLED")).upper(), "reason": (value or {}).get("reason", "No optional integration record")}
    if evidence_run:
        optional_view["evidence_ingestion"] = {
            "status": str(evidence_run.get("status", "UNKNOWN")).upper(),
            "reason": "Optional bounded MarkItDown/Crawl4AI capability; never a core-health dependency",
            "last_updated": evidence_run.get("updated_at") or evidence_run.get("last_run"),
            "last_result": evidence_run.get("last_result"),
            "adapter": evidence_run.get("last_adapter"),
        }
    else:
        optional_view["evidence_ingestion"] = {"status": "NOT_ENABLED", "reason": "No evidence-ingestion heartbeat recorded"}
    if worker_run:
        optional_view["remote_cpu_worker"] = {
            "status": str(worker_run.get("status", "UNKNOWN")).upper(),
            "reason": "Optional provider-neutral compute worker; never a core-health dependency",
            "last_updated": worker_run.get("last_seen"),
            "provider": worker_run.get("provider"),
            "worker_id": worker_run.get("worker_id"),
            "capabilities": worker_run.get("capabilities", {}),
        }
    else:
        optional_view["remote_cpu_worker"] = {"status": "NOT_CONFIGURED", "reason": "No remote worker heartbeat recorded"}
    if alpha_run:
        optional_view["alpha"] = {
            "status": str(alpha_run.get("status", "UNKNOWN")).upper(),
            "reason": "Optional bounded evidence-first research intelligence; never a core-health dependency",
            "last_updated": alpha_run.get("updated_at") or alpha_run.get("last_run"),
            "last_result": alpha_run.get("last_result"),
            "last_research_job": alpha_run.get("research_job_id"),
            "last_success": alpha_run.get("last_success"),
            "receipt_id": alpha_run.get("receipt_id"),
            "source_count": alpha_run.get("source_count", 0),
            "evidence_count": alpha_run.get("evidence_count", 0),
            "browser_evidence_used": alpha_run.get("browser_evidence_used", False),
            "freshness": alpha_run.get("freshness", {}),
            "core_health_dependency": False,
        }
    try:
        opportunity_view = opportunity_portfolio()
        opportunity_counts = opportunity_view.get("counts", {})
        opportunity_rows = opportunity_view.get("rankings", {}).get("best_overall", [])
        optional_view["opportunity_engine"] = {
            "status": "HEALTHY" if opportunity_view.get("total_active", 0) or opportunity_counts.get("NEEDS_RESEARCH", 0) else "IDLE",
            "reason": "Optional governed opportunity intelligence; never a core-health dependency",
            "active_opportunities": opportunity_view.get("total_active", 0),
            "qualified": opportunity_counts.get("QUALIFIED", 0),
            "needs_research": opportunity_counts.get("NEEDS_RESEARCH", 0),
            "needs_ray": opportunity_counts.get("NEEDS_RAY_REVIEW", 0),
            "approved": opportunity_counts.get("APPROVED_FOR_PLANNING", 0),
            "stale": opportunity_counts.get("STALE", 0),
            "top_opportunity": {"opportunity_id": opportunity_rows[0].get("opportunity_id"), "title": opportunity_rows[0].get("title"), "score": (opportunity_rows[0].get("scores") or {}).get("overall_score")} if opportunity_rows else None,
            "pipeline_value_estimate": opportunity_view.get("pipeline_value_estimate", {"status": "UNKNOWN"}),
            "freshness": "CURRENT" if opportunity_rows else "UNKNOWN",
            "core_health_dependency": False,
        }
    except Exception:
        optional_view["opportunity_engine"] = {"status": "DEGRADED", "reason": "Opportunity read model unavailable; core health unaffected", "core_health_dependency": False}
    try:
        revenue_snapshot = persistence.latest_record("revenue_snapshots")
        if revenue_snapshot:
            actual = (revenue_snapshot.get("metrics") or {}).get("actual_revenue", {})
            optional_view["revenue_hub"] = {
                "status": "HEALTHY" if revenue_snapshot.get("revenue_truth") in {"CONNECTED", "NOT_CONNECTED"} else "DEGRADED",
                "reason": "Optional GoClear Revenue Truth Layer; read-only and never a core-health dependency",
                "revenue_truth": revenue_snapshot.get("revenue_truth", "UNKNOWN"),
                "actual_revenue": {"value": actual.get("value"), "truth_class": actual.get("truth_class", "UNKNOWN"), "source_status": actual.get("source_status", "NOT_CONNECTED")},
                "pipeline_value": revenue_snapshot.get("pipeline", {}).get("value"),
                "opportunity_pipeline": revenue_snapshot.get("opportunity_pipeline", {}),
                "unknown_metrics": len(revenue_snapshot.get("unknown_metrics", [])),
                "needs_ray": len(revenue_snapshot.get("needs_ray", [])),
                "freshness": revenue_snapshot.get("freshness", "UNKNOWN"),
                "snapshot_id": revenue_snapshot.get("snapshot_id"),
                "core_health_dependency": False,
            }
        else:
            optional_view["revenue_hub"] = {"status": "NOT_CONNECTED", "reason": "No canonical revenue snapshot recorded", "revenue_truth": "NOT_CONNECTED", "core_health_dependency": False}
    except Exception:
        optional_view["revenue_hub"] = {"status": "DEGRADED", "reason": "Revenue read model unavailable; core health unaffected", "revenue_truth": "UNKNOWN", "core_health_dependency": False}
    try:
        growth = growth_portfolio()
        counts = growth.get("counts", {})
        top = growth.get("top_growth_opportunity")
        optional_view["growth_operations"] = {
            "status": growth.get("status", "IDLE"),
            "reason": "Optional draft-only SEO and growth operations; never a core-health dependency",
            "active_experiments": growth.get("total", 0),
            "needs_research": counts.get("NEEDS_RESEARCH", 0),
            "needs_ray": counts.get("NEEDS_RAY_REVIEW", 0),
            "ready_for_planning": counts.get("APPROVED_FOR_PLANNING", 0),
            "measurement_pending": counts.get("MEASUREMENT_PENDING", 0),
            "result_observed": counts.get("RESULT_OBSERVED", 0),
            "stale": counts.get("STALE", 0),
            "top_growth_opportunity": {"growth_id": top.get("growth_id"), "title": top.get("title")} if top else None,
            "keyword_scout": "CONNECTED_MANUAL",
            "search_console": growth.get("search_console", "NOT_CONNECTED"),
            "analytics": growth.get("analytics", "NOT_CONNECTED"),
            "measurement_source": growth.get("measurement_source", "NOT_CONNECTED"),
            "freshness": "CURRENT" if growth.get("total") else "UNKNOWN",
            "core_health_dependency": False,
        }
    except Exception:
        optional_view["growth_operations"] = {"status": "DEGRADED", "reason": "Growth read model unavailable; core health unaffected", "core_health_dependency": False}
    model = {
        "generated_at": now.isoformat(), "source": "canonical Nexus runtime artifacts and governed stores", "read_only": True,
        "system": system, "attention": attention,
        "needs_ray": {"count": len(approval_rows) + len(p0) + len(p1) + len(recovery_escalations), "pending_approvals": len(approval_rows), "p0_work": len(p0), "p1_work": len(p1), "recovery_escalations": len(recovery_escalations), "items": [{"kind": "approval", "id": row.get("id"), "status": row.get("status"), "action_id": row.get("action_id")} for row in approval_rows[:10]] + [{"kind": "work_order", "id": row.get("work_order_id"), "priority": priority(row), "status": row.get("status")} for row in (p0 + p1)[:10]]},
        "activity": {"last_continuous_loop": _latest_loop(root), "last_active_operator": {"run_id": active.get("operator_run_id"), "last_run": active_last, "status": active.get("run_status")}, "last_recovery_check": {"run_id": recovery.get("recovery_run_id"), "last_run": recovery_last, "status": recovery.get("run_status")}, "last_hermes_activity": {"last_run": hermes_last, "status": hermes.get("run_status"), "updates_processed": hermes.get("updates_processed")}, "recent": recent[:20]},
        "schedule": schedule,
        "work": {"open_work_orders": len(open_rows), "recent_completed": completed, "by_priority": {value: sum(1 for row in open_rows if priority(row) == value) for value in PRIORITIES}},
        "approvals": [{"id": row.get("id"), "action_id": row.get("action_id"), "requested_by": row.get("requested_by"), "requested_at": row.get("created_at"), "status": row.get("status"), "risk_level": row.get("risk_level"), "evidence_refs": row.get("evidence_refs", [])} for row in approval_rows[:50]],
        "process_registry": {"enabled": sum(1 for row in registry if row.get("enabled")), "records": len(registry) if isinstance(registry, list) else 0, "source": str(registry_path.relative_to(root))},
        "safety": {"stripe_autonomy": "DISABLED", "arbitrary_shell": "UNAVAILABLE", "external_actions": "BLOCKED", "source": "canonical runtime authority state"},
        "optional_integrations": optional_view,
        "freshness": {"core_runtime": system["core_runtime"]["freshness"], "active_operator": system["active_operator"]["freshness"], "recovery_check": system["recovery_check"]["freshness"], "hermes": system["hermes"]["freshness"], "scheduler": evidence(scheduler_path, scheduler_last, now, 3600), "evidence_ingestion": evidence(evidence_path, evidence_run.get("updated_at") or evidence_run.get("last_run"), now, 3600) if evidence_run else {"source": str(evidence_path.relative_to(root)), "last_updated": None, "freshness": "UNKNOWN"}, "remote_cpu_worker": evidence(worker_path, worker_run.get("last_seen"), now, 300) if worker_run else {"source": str(worker_path.relative_to(root)), "last_updated": None, "freshness": "UNKNOWN"}, "alpha": evidence(alpha_path, alpha_run.get("updated_at") or alpha_run.get("last_run"), now, 3600) if alpha_run else {"source": str(alpha_path.relative_to(root)), "last_updated": None, "freshness": "UNKNOWN"}, "opportunity_engine": {"freshness": optional_view.get("opportunity_engine", {}).get("freshness", "UNKNOWN"), "source": "governed opportunities collection"}, "revenue_hub": {"freshness": optional_view.get("revenue_hub", {}).get("freshness", "UNKNOWN"), "source": "governed revenue snapshots collection"}, "growth_operations": {"freshness": optional_view.get("growth_operations", {}).get("freshness", "UNKNOWN"), "source": "governed growth experiments collection"}},
    }
    return model


def write_snapshot(path: Path = OUTPUT_PATH) -> Dict[str, Any]:
    model = build_read_model()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a read-only Mission Control snapshot")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    model = write_snapshot(args.output)
    print(json.dumps({"output": str(args.output), "generated_at": model["generated_at"], "overall_status": model["system"]["overall_status"], "needs_ray": model["needs_ray"]["count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
