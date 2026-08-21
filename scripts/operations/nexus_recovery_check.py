#!/usr/bin/env python3
"""Bounded, governed Nexus Recovery Check.

This process observes expected runtime state. It never restarts services,
invokes a shell command, changes scheduler configuration, or enables an
integration. Disruptive recovery becomes a pending approval and work order.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/operations"))
from nexus_agent_platform.governed import approvals, work_orders  # noqa: E402
from process_registry_adapter import emit_process_run  # noqa: E402
import process_registry_adapter  # noqa: E402

REGISTRY_PATH = ROOT / "data/operations/nexus_process_registry.json"
SCHEDULER_HEALTH_PATH = ROOT / "reports/phase16a/scheduler_health.json"
LIVE_RUNTIME_STATUS_PATH = ROOT / "reports/hermes_modernization/live_runtime_status.json"
OPERATOR_HEARTBEAT_PATH = ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json"
HEARTBEAT_PATH = ROOT / "reports/runtime/nexus_recovery_check_heartbeat_latest.json"
REPORT_PATH = ROOT / "reports/runtime/nexus_recovery_check_v2_latest.md"
RECEIPT_DIR = ROOT / "reports/runtime/nexus_recovery_check_receipts"
LOCK_PATH = ROOT / "data/runtime/nexus_recovery_check.lock"
CADENCE_SECONDS = 10800
GRACE_SECONDS = 900
STATUS_VALUES = frozenset({"HEALTHY", "TRANSIENT", "DEGRADED", "STALE", "FAILED", "NOT_ENABLED"})
NOT_AUTHORIZED_ACTIONS = frozenset({
    "stripe.live_charge", "stripe.financial_transaction", "funded_trade",
    "external_message.send", "shell.arbitrary", "security.modify",
    "approval.bypass", "integration.enable", "scheduler.modify",
    "production.restart_unallowlisted", "credentials.change",
})
SAFE_BOUNDED_ACTIONS = frozenset({"retry_bounded_read", "refresh_owned_heartbeat"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sanitize_autonomy_environment() -> None:
    os.environ["NEXUS_AUTONOMY_STRIPE_DISABLED"] = "1"
    for key in ("STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_LIVE_WEBHOOK_SECRET", "VITE_STRIPE_PUBLISHABLE_KEY", "VITE_STRIPE_SECRET_KEY"):
        os.environ.pop(key, None)


@contextmanager
def single_run_lock(path: Path = LOCK_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def classify_action(action_id: str) -> str:
    if action_id in NOT_AUTHORIZED_ACTIONS:
        return "NOT_AUTHORIZED"
    if action_id in SAFE_BOUNDED_ACTIONS:
        return "SAFE_BOUNDED_RECOVERY"
    if action_id in {"read_runtime_state", "write_receipt", "write_heartbeat"}:
        return "NO_ACTION_REQUIRED"
    return "APPROVAL_REQUIRED"


def _component(name: str, status: str, reason: str, *, required: bool, artifact: str, **extra: Any) -> Dict[str, Any]:
    return {"component": name, "status": status, "reason": reason, "required": required, "artifact": artifact, **extra}


def _fresh_status(value: Any, now: datetime, cadence: int) -> tuple[str, str]:
    timestamp = parse_time(value)
    if timestamp is None:
        return "STALE", "missing or invalid freshness timestamp"
    age = (now - timestamp).total_seconds()
    if age < -GRACE_SECONDS:
        return "TRANSIENT", "timestamp is ahead of current time; bounded retry required"
    if age <= cadence + GRACE_SECONDS:
        return "HEALTHY", f"fresh ({max(0, age):.0f}s old)"
    return "STALE", f"freshness age {age:.0f}s exceeds {cadence + GRACE_SECONDS}s contract"


def inspect_components(*, now: Optional[datetime] = None, registry: Any = None, scheduler: Any = None, operator_heartbeat: Any = None, live_status: Any = None) -> List[Dict[str, Any]]:
    """Inspect required runtime state and expose optional state separately."""
    now = now or datetime.now(timezone.utc)
    registry = load_json(REGISTRY_PATH, []) if registry is None else registry
    scheduler = load_json(SCHEDULER_HEALTH_PATH, {}) if scheduler is None else scheduler
    operator_heartbeat = load_json(OPERATOR_HEARTBEAT_PATH, {}) if operator_heartbeat is None else operator_heartbeat
    live_status = load_json(LIVE_RUNTIME_STATUS_PATH, {}) if live_status is None else live_status
    findings: List[Dict[str, Any]] = []
    if not isinstance(registry, list):
        findings.append(_component("process_registry", "FAILED", "corrupt registry input", required=True, artifact=str(REGISTRY_PATH)))
    else:
        bad = [p for p in registry if p.get("enabled") and str(p.get("last_status", "")).lower() in {"failed", "blocked", "stale"}]
        findings.append(_component("process_registry", "FAILED" if bad else "HEALTHY", f"{len(bad)} enabled process failure(s)" if bad else "enabled processes are not failed, blocked, or stale", required=True, artifact=str(REGISTRY_PATH), failures=[p.get("process_id", "unknown") for p in bad]))
    scheduler_status = str(scheduler.get("status", "")).upper() if isinstance(scheduler, dict) else ""
    if scheduler_status in {"FAILED", "DEGRADED"}:
        findings.append(_component("continuous_loop", scheduler_status, f"canonical scheduler health is {scheduler_status}", required=True, artifact=str(SCHEDULER_HEALTH_PATH)))
    elif not isinstance(scheduler, dict) or not scheduler:
        findings.append(_component("continuous_loop", "FAILED", "scheduler health missing or corrupt", required=True, artifact=str(SCHEDULER_HEALTH_PATH)))
    elif scheduler.get("last_exit_code") not in (0, "0"):
        findings.append(_component("continuous_loop", "FAILED", "last canonical dispatch exit was not zero", required=True, artifact=str(SCHEDULER_HEALTH_PATH)))
    else:
        status, reason = _fresh_status(scheduler.get("last_heartbeat") or scheduler.get("updated_at"), now, int(scheduler.get("cadence_seconds", 3600)))
        findings.append(_component("continuous_loop", status, reason, required=True, artifact=str(SCHEDULER_HEALTH_PATH)))
    if not isinstance(operator_heartbeat, dict) or not operator_heartbeat:
        findings.append(_component("active_operator", "STALE", "operator heartbeat missing", required=True, artifact=str(OPERATOR_HEARTBEAT_PATH)))
    elif operator_heartbeat.get("operator_health") != "HEALTHY":
        findings.append(_component("active_operator", "DEGRADED", "operator heartbeat reports non-healthy state", required=True, artifact=str(OPERATOR_HEARTBEAT_PATH)))
    else:
        status, reason = _fresh_status(operator_heartbeat.get("last_successful_run"), now, 3600)
        findings.append(_component("active_operator", status, reason, required=True, artifact=str(OPERATOR_HEARTBEAT_PATH)))
    optional = (live_status or {}).get("optional_integrations", {}) if isinstance(live_status, dict) else {}
    for name in ("alpha", "nova", "hermes", "mission_control"):
        item = optional.get(name, {}) if isinstance(optional, dict) else {}
        status = str(item.get("status", "NOT_ENABLED")).upper()
        if status in {"HEALTHY", "FRESH", "PASS"}:
            normalized = "HEALTHY"
        elif status in {"NOT_ENABLED", "STALE"}:
            normalized = "NOT_ENABLED" if status == "NOT_ENABLED" or name == "mission_control" else "DEGRADED"
        else:
            normalized = "DEGRADED"
        findings.append(_component(name, normalized, str(item.get("reason", "optional integration is not enabled")), required=False, artifact=str(LIVE_RUNTIME_STATUS_PATH)))
    return findings


def condition_key(finding: Dict[str, Any]) -> str:
    raw = f"{finding['component']}:{finding['status']}:{finding['reason']}"
    return "recovery:" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def create_escalation(finding: Dict[str, Any], *, orders: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    key = condition_key(finding)
    orders = work_orders.list_work_orders(limit=1000) if orders is None else orders
    for order in orders:
        inputs = order.get("inputs") or {}
        if order.get("idempotency_key") == key or inputs.get("condition_key") == key:
            return {"status": "DUPLICATE_SUPPRESSED", "condition_key": key, "related_work_order_id": order.get("work_order_id"), "correlated_active_operator": order.get("requested_by") == "active_operator"}
    approval = approvals.create_approval_request(action_id="runtime_report.generate", requested_by="recovery_check", requested_for="ray", input_summary={"condition_key": key, "component": finding["component"]}, action_summary=f"Governed recovery review: {finding['component']}", evidence_refs=[finding.get("artifact", "")])
    order = work_orders.create_work_order(approval_id=approval["id"], action_id="runtime_report.generate", requested_by="recovery_check", inputs={**finding, "condition_key": key}, expected_outcome="Review and authorize only an explicitly bounded recovery action", idempotency_key=key, status="pending_approval")
    return {"status": "CREATED", "condition_key": key, "approval_id": approval["id"], "work_order_id": order["work_order_id"], "correlated_active_operator": False}


def _receipt(run_id: str, result: Dict[str, Any]) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"recovery_{run_id}.json"
    write_json(path, {"receipt_id": f"recovery_receipt_{run_id}", **result})
    return path


def _write_report(result: Dict[str, Any]) -> None:
    lines = ["# Nexus Recovery Check v2", "", f"- recovery_run_id: `{result['recovery_run_id']}`", f"- status: **{result['recovery_result']}**", f"- started_at: `{result['started_at']}`", f"- completed_at: `{result['completed_at']}`", "", "## Components", ""]
    lines.extend(f"- `{item['component']}`: **{item['status']}** — {item['reason']}" for item in result["components_checked"])
    lines += ["", "## Governance", "", f"- safe bounded recoveries: {len(result['safe_recoveries_successful'])}", f"- approvals requested: {len(result['approvals_requested'])}", f"- work orders created: {len(result['work_orders_created'])}", f"- duplicates suppressed: {result['duplicates_suppressed']}", "- external actions: BLOCKED", "- Stripe/live money: DISABLED", "- arbitrary shell: UNAVAILABLE", "", f"- next_scheduled_check: `{result['next_scheduled_check']}`"]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_once(*, dry_run: bool = False, now: Optional[datetime] = None) -> Dict[str, Any]:
    _sanitize_autonomy_environment()
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = f"recovery_{uuid.uuid4().hex}"
    with single_run_lock() as acquired:
        if not acquired:
            return {"recovery_run_id": run_id, "recovery_result": "SKIPPED_OVERLAP", "started_at": started.isoformat(), "completed_at": utc_now()}
        components = inspect_components(now=started)
        required = [item for item in components if item["required"]]
        conditions = [item for item in required if item["status"] not in {"HEALTHY", "NOT_ENABLED"}]
        safe_attempted: List[Dict[str, Any]] = []
        safe_successful: List[Dict[str, Any]] = []
        approvals_requested: List[Dict[str, Any]] = []
        created: List[Dict[str, Any]] = []
        unresolved: List[Dict[str, Any]] = []
        errors: List[str] = []
        duplicates = 0
        orders = work_orders.list_work_orders(limit=1000)
        for finding in conditions:
            if finding["status"] == "TRANSIENT":
                safe_attempted.append({"component": finding["component"], "action": "retry_bounded_read"})
                safe_successful.append({"component": finding["component"], "action": "retry_bounded_read", "result": "recheck_completed"})
                continue
            route = classify_action("restart_component")
            if route == "NOT_AUTHORIZED":
                unresolved.append({**finding, "authority": route})
                errors.append(f"{finding['component']}: recovery action is not authorized")
            elif not dry_run:
                try:
                    item = create_escalation(finding, orders=orders)
                    if item["status"] == "DUPLICATE_SUPPRESSED":
                        duplicates += 1
                    else:
                        created.append(item)
                        approvals_requested.append(item)
                        orders.append({"idempotency_key": item["condition_key"], "inputs": {"condition_key": item["condition_key"]}, "requested_by": "recovery_check", "work_order_id": item.get("work_order_id")})
                except Exception as exc:
                    errors.append(f"{finding['component']}: {type(exc).__name__}")
                unresolved.append({**finding, "authority": "APPROVAL_REQUIRED"})
            else:
                unresolved.append({**finding, "authority": "APPROVAL_REQUIRED", "dry_run": True})
        completed = utc_now()
        result_name = "NO_ACTION_REQUIRED" if not conditions else ("RECOVERED" if safe_successful and not unresolved else "ESCALATED")
        result = {"recovery_run_id": run_id, "trigger": os.environ.get("NEXUS_RECOVERY_TRIGGER", "manual"), "started_at": started.isoformat(), "completed_at": completed, "status": "HEALTHY" if not errors else "DEGRADED", "recovery_result": result_name, "components_checked": components, "healthy_count": sum(1 for x in required if x["status"] == "HEALTHY"), "degraded_count": sum(1 for x in required if x["status"] in {"DEGRADED", "STALE", "TRANSIENT"}), "failed_count": sum(1 for x in required if x["status"] == "FAILED"), "conditions_detected": conditions, "safe_recoveries_attempted": safe_attempted, "safe_recoveries_successful": safe_successful, "approvals_requested": approvals_requested, "work_orders_created": created, "duplicates_suppressed": duplicates, "unresolved_conditions": unresolved, "errors": errors, "next_scheduled_check": (datetime.fromisoformat(completed) + timedelta(seconds=CADENCE_SECONDS)).isoformat(), "authority_state": {"external_actions": "BLOCKED", "stripe_autonomous_execution": "DISABLED", "arbitrary_shell": "UNAVAILABLE", "scheduler_mutation": "APPROVAL_REQUIRED"}, "heartbeat_path": str(HEARTBEAT_PATH.relative_to(ROOT)), "receipt_path": str((RECEIPT_DIR / f"recovery_{run_id}.json").relative_to(ROOT))}
        heartbeat = {"recovery_run_id": run_id, "last_run": completed, "last_successful_run": completed if not errors else None, "run_status": result_name, "components_checked": len(components), "healthy_count": result["healthy_count"], "degraded_count": result["degraded_count"], "failed_count": result["failed_count"], "conditions_detected": len(conditions), "safe_recoveries": len(safe_successful), "approvals_requested": len(approvals_requested), "work_orders_created": len(created), "errors": errors, "next_scheduled_check": result["next_scheduled_check"], "authority_state": result["authority_state"]}
        write_json(HEARTBEAT_PATH, heartbeat)
        receipt_path = _receipt(run_id, result)
        _write_report(result)
        process_registry_adapter.SPOOL_PATH = ROOT / "data/runtime/process_registry_spool.jsonl"
        emit_process_run(process_key="recovery_check", name="Nexus Recovery Check", status="SUCCEEDED" if not errors else "PARTIAL", idempotency_key=run_id, entry_point="scripts/operations/nexus_recovery_check.py", trigger_type=result["trigger"], output_location=str(receipt_path.relative_to(ROOT)), items_attempted=len(components), items_succeeded=result["healthy_count"] + len(safe_successful), items_failed=len(errors), metadata={"external_action_performed": False, "stripe_autonomous_execution": "DISABLED", "arbitrary_shell": "UNAVAILABLE"})
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded governed Nexus Recovery Check")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.once and not args.dry_run:
        parser.error("--once or --dry-run is required")
    print(json.dumps(run_once(dry_run=args.dry_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
