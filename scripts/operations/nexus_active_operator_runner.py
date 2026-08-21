#!/usr/bin/env python3
"""Bounded Active Operator foundation.

This runner is deliberately closed-world: it reads Nexus state, classifies
attention, creates governed pending work orders for approval-required work,
and writes receipts/heartbeat. It never executes arbitrary registry commands,
network calls, external messaging, financial actions, or infrastructure work.
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
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/operations"))

from nexus_agent_platform.governed import approvals, work_orders  # noqa: E402
from process_registry_adapter import emit_process_run  # noqa: E402
import process_registry_adapter  # noqa: E402

REGISTRY_PATH = ROOT / "data/operations/nexus_process_registry.json"
SCHEDULER_HEALTH_PATH = ROOT / "reports/phase16a/scheduler_health.json"
HEARTBEAT_PATH = ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json"
RUNNER_REPORT_PATH = ROOT / "reports/runtime/nexus_active_operator_runner_latest.md"
RECEIPT_DIR = ROOT / "reports/runtime/nexus_active_operator_receipts"
LOCK_PATH = ROOT / "data/runtime/nexus_active_operator.lock"
CADENCE_SECONDS = 3600

SAFE_INTERNAL_ACTIONS = frozenset({
    "read_operational_state", "write_heartbeat", "write_receipt", "generate_internal_report",
})
NOT_AUTHORIZED_ACTIONS = frozenset({
    "stripe.live_activation", "financial.transactions", "place_trade", "charge_customer",
    "send_customer_email", "send_sms", "post_to_social_media", "submit_grant_application",
    "submit_credit_dispute", "shell.arbitrary", "restart_production_services",
    "modify_production_database",
})
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sanitize_autonomy_environment() -> None:
    """Keep shared application credentials out of this process."""
    os.environ["NEXUS_AUTONOMY_STRIPE_DISABLED"] = "1"
    for key in (
        "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET",
        "STRIPE_LIVE_WEBHOOK_SECRET", "VITE_STRIPE_PUBLISHABLE_KEY", "VITE_STRIPE_SECRET_KEY",
    ):
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


def priority_for(process: Dict[str, Any]) -> str:
    category = str(process.get("category", "")).lower()
    if any(term in category for term in ("safety", "security", "recovery", "system_health")):
        return "P0"
    if "client" in category:
        return "P1"
    if any(term in category for term in ("revenue", "funding", "money")):
        return "P2"
    if any(term in category for term in ("operation", "monitor", "process")):
        return "P3"
    return "P4"


def classify_action(action_id: str) -> str:
    if action_id in SAFE_INTERNAL_ACTIONS:
        return "AUTO_EXECUTE_INTERNAL_SAFE"
    if action_id in NOT_AUTHORIZED_ACTIONS:
        return "NOT_AUTHORIZED"
    return "APPROVAL_REQUIRED"


def discover_attention(registry: Iterable[Dict[str, Any]], scheduler_health: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for process in registry:
        if not process.get("enabled"):
            continue
        if str(process.get("last_status", "")).lower() not in {"failed", "blocked", "stale"}:
            continue
        process_id = str(process.get("process_id", "unknown"))
        findings.append({
            "finding_id": f"process:{process_id}:{process.get('last_status')}",
            "source": "process_registry",
            "priority": priority_for(process),
            "capability": process.get("category", "operations"),
            "summary": f"{process.get('name', process_id)} requires attention",
            "reason": f"process status is {process.get('last_status')}",
            "proposed_action": "runtime_report.generate",
            "related_artifact": process.get("report_path"),
        })
    if scheduler_health.get("status") in {"FAILED", "DEGRADED"}:
        findings.append({
            "finding_id": "scheduler:health",
            "source": "scheduler_health",
            "priority": "P0",
            "capability": "operations",
            "summary": "Scheduler health requires attention",
            "reason": str(scheduler_health.get("status")),
            "proposed_action": "runtime_report.generate",
            "related_artifact": "reports/phase16a/scheduler_health.json",
        })
    return sorted(findings, key=lambda item: (PRIORITY_RANK[item["priority"]], item["finding_id"]))


def _existing_idempotency_keys() -> set[str]:
    return {str(item.get("idempotency_key")) for item in work_orders.list_work_orders(limit=500)}


def create_pending_work_order(finding: Dict[str, Any]) -> Dict[str, Any]:
    key = "active_operator:" + hashlib.sha256(finding["finding_id"].encode()).hexdigest()[:24]
    if key in _existing_idempotency_keys():
        return {"status": "DUPLICATE_SUPPRESSED", "idempotency_key": key, "finding_id": finding["finding_id"]}
    approval = approvals.create_approval_request(
        action_id="runtime_report.generate",
        requested_by="active_operator",
        requested_for="ray",
        input_summary={"finding_id": finding["finding_id"], "priority": finding["priority"]},
        action_summary=finding["summary"],
        evidence_refs=[finding["related_artifact"]] if finding.get("related_artifact") else [],
    )
    order = work_orders.create_work_order(
        approval_id=approval["id"],
        action_id="runtime_report.generate",
        requested_by="active_operator",
        inputs=finding,
        expected_outcome="Internal report prepared for Ray review",
        idempotency_key=key,
        status="pending_approval",
    )
    return {
        "status": "CREATED", "idempotency_key": key, "finding_id": finding["finding_id"],
        "approval_id": approval["id"], "work_order_id": order["work_order_id"],
    }


def _receipt(run_id: str, result: Dict[str, Any]) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"operator_{run_id}.json"
    write_json(path, {"receipt_id": f"operator_receipt_{run_id}", "operator_run_id": run_id, **result})
    return path


def _write_report(result: Dict[str, Any]) -> None:
    lines = [
        "# Nexus Active Operator Report", "", f"- operator_run_id: `{result['operator_run_id']}`",
        f"- status: **{result['status']}**", f"- started_at: `{result['started_at']}`",
        f"- completed_at: `{result['completed_at']}`", "", "## Counts", "",
        f"- actions considered: {len(result['actions_considered'])}",
        f"- safe actions executed: {len(result['actions_executed'])}",
        f"- approvals requested: {len(result['approvals_requested'])}",
        f"- work orders created: {len(result['work_orders_created'])}",
        f"- duplicate work suppressed: {result['duplicates_suppressed']}",
        f"- errors: {len(result['errors'])}", "", "## Authority", "",
        "- external actions: blocked", "- Stripe/live money: unavailable to this process",
        "- arbitrary shell: unavailable", "", f"- next_scheduled_run: `{result['next_scheduled_run']}`",
    ]
    RUNNER_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNNER_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_once(*, dry_run: bool = False) -> Dict[str, Any]:
    _sanitize_autonomy_environment()
    started = utc_now()
    run_id = f"operator_{uuid.uuid4().hex}"
    with single_run_lock() as acquired:
        if not acquired:
            return {"operator_run_id": run_id, "status": "SKIPPED_OVERLAP", "started_at": started, "completed_at": utc_now()}
        registry = load_json(REGISTRY_PATH, [])
        scheduler_health = load_json(SCHEDULER_HEALTH_PATH, {})
        findings = discover_attention(registry if isinstance(registry, list) else [], scheduler_health)
        actions_considered = [item["proposed_action"] for item in findings]
        actions_executed = ["read_operational_state", "write_heartbeat"]
        approvals_requested: List[Dict[str, Any]] = []
        created: List[Dict[str, Any]] = []
        errors: List[str] = []
        duplicates = 0
        for finding in findings:
            route = classify_action(finding["proposed_action"])
            if route == "AUTO_EXECUTE_INTERNAL_SAFE":
                actions_executed.append(finding["proposed_action"])
            elif route == "APPROVAL_REQUIRED":
                if dry_run:
                    approvals_requested.append({"finding_id": finding["finding_id"], "status": "DRY_RUN"})
                else:
                    try:
                        item = create_pending_work_order(finding)
                        if item["status"] == "DUPLICATE_SUPPRESSED":
                            duplicates += 1
                        else:
                            created.append(item)
                            approvals_requested.append(item)
                    except Exception as exc:  # bounded per-finding failure
                        errors.append(f"{finding['finding_id']}: {type(exc).__name__}")
            else:
                errors.append(f"{finding['finding_id']}: NOT_AUTHORIZED")
        completed = utc_now()
        trigger_type = os.environ.get("NEXUS_OPERATOR_TRIGGER", "manual")
        heartbeat_path = str(HEARTBEAT_PATH.relative_to(ROOT))
        receipt_path = str((RECEIPT_DIR / f"operator_{run_id}.json").relative_to(ROOT))
        result = {
            "operator_run_id": run_id,
            "status": "NO_ACTION_REQUIRED" if not findings else "COMPLETED_WITH_FINDINGS",
            "started_at": started, "completed_at": completed,
            "actions_considered": actions_considered,
            "actions_executed": actions_executed if not dry_run else [],
            "approvals_requested": approvals_requested,
            "work_orders_created": created, "duplicates_suppressed": duplicates,
            "errors": errors,
            "next_scheduled_run": (datetime.fromisoformat(completed) + timedelta(seconds=CADENCE_SECONDS)).isoformat(),
            "operator_health": "HEALTHY" if not errors else "DEGRADED",
            "authority": {"external_actions": "BLOCKED", "stripe_autonomous_execution": "DISABLED", "arbitrary_shell": "UNAVAILABLE"},
            "dry_run": dry_run, "trigger_type": trigger_type,
            "heartbeat_path": heartbeat_path, "receipt_path": receipt_path,
        }
        heartbeat = {
            "operator_run_id": run_id, "last_run": completed,
            "last_successful_run": completed if not errors else None,
            "run_status": result["status"], "work_discovered": len(findings),
            "work_created": len(created), "safe_actions_executed": len(result["actions_executed"]),
            "approvals_requested": len(approvals_requested), "errors": errors,
            "next_scheduled_run": result["next_scheduled_run"], "operator_health": result["operator_health"],
            "authority": result["authority"],
        }
        write_json(HEARTBEAT_PATH, heartbeat)
        _receipt(run_id, result)
        _write_report(result)
        process_registry_adapter.SPOOL_PATH = ROOT / "data/runtime/process_registry_spool.jsonl"
        emit_process_run(
            process_key="active_operator", name="Nexus Active Operator",
            status="SUCCEEDED" if not errors else "PARTIAL", idempotency_key=run_id,
            entry_point="scripts/operations/nexus_active_operator_runner.py",
            trigger_type=trigger_type if not dry_run else "dry_run", output_location=result["receipt_path"],
            items_attempted=len(findings), items_succeeded=len(created), items_failed=len(errors),
            metadata={"dry_run": dry_run, "external_action_performed": False, "remote_registry_updated": False},
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded Nexus Active Operator dispatch")
    parser.add_argument("--once", action="store_true", help="run one bounded dispatch")
    parser.add_argument("--dry-run", action="store_true", help="write no governed work orders")
    args = parser.parse_args()
    if not args.once and not args.dry_run:
        parser.error("--once or --dry-run is required")
    print(json.dumps(run_once(dry_run=args.dry_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
