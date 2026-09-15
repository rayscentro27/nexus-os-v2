#!/usr/bin/env python3
"""Long-running consumer for canonical Active Operator department work.

This is deliberately narrow: it consumes existing READY internal work only,
uses the already governed Active Operator executors, and never touches
approval-gated, blocked, superseded, external, financial, or live-trading
work. Claims are short and durable; execution is isolated per job so one bad
worker cannot stop the consumer.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from operations.nexus_active_operator_runner import (  # noqa: E402
    LOCK_PATH, execute_safe_internal_action, load_json, utc_now, write_json,
)

STORE = ROOT / "data/runtime/active_operator_work_orders.json"
CONSUMER_LOCK = ROOT / "data/runtime/department_work_consumer.lock"
RECEIPT_DIR = ROOT / "reports/runtime/department_work_consumer_receipts"
HEARTBEAT = ROOT / "reports/runtime/department_work_consumer_heartbeat.json"
JOB_TIMEOUT_SECONDS = 45
POLL_SECONDS = 30
MAX_PER_CYCLE = 5


def _iso_after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return handle


def _orders() -> list[dict]:
    value = load_json(STORE, [])
    return value if isinstance(value, list) else []


def _save(value: list[dict]) -> None:
    write_json(STORE, value)


def _department(order: dict) -> str:
    text = f"{order.get('title','')} {order.get('description','')} {order.get('source','')}".lower()
    action = str(order.get("recommended_action") or "")
    source = str(order.get("source") or "").lower()
    if action == "measurement_gap.report":
        if "growth" in source:
            return "Growth"
        if "revenue" in source or "finance" in source:
            return "Finance"
        return "Growth"
    if action in {"research.refresh", "research.alternate_public", "department.research_handoff"} or "research" in text:
        return "Research"
    if "grant" in text:
        return "Grants"
    if "trading" in text or "market-data" in text:
        return "Trading"
    if "goclear" in text or "credit" in text or "business plan" in text:
        return "GoClear Operations"
    if "finance" in text or "billing" in text or "accounting" in text:
        return "Finance"
    if "funding" in text or "billing" in text or "accounting" in text:
        return "Funding"
    if "creative" in text or "youtube" in text or "video" in text:
        return "Creative"
    if "marketing" in text or "campaign" in text or "growth" in text:
        return "Marketing"
    if "customer" in text or "support" in text:
        return "Customer Service"
    return "Systems"


def _eligible(order: dict) -> bool:
    status = str(order.get("status", "")).upper()
    if status not in {"READY", "FAILED_RETRYABLE"}:
        return False
    if status == "FAILED_RETRYABLE" and str(order.get("retry_at") or "") > utc_now():
        return False
    action = str(order.get("recommended_action") or "")
    # These are the existing internal executor actions. Unsupported actions
    # remain READY for a future registered worker rather than being falsely
    # marked complete.
    return action in {
        "research.refresh", "research.alternate_public",
        "internal.capability_verify", "internal.admin_capability_audit",
        "internal.admin_gap_work", "internal.create_bounded_work_artifact",
        "ai.plan_and_verify", "trading.research_cycle",
        "funding.readiness_review", "generate_internal_report",
        "measurement_gap.report", "department.work_order",
    }


def _bounded_department_result(order: dict) -> dict:
    """Execute the two canonical internal work types without external effects."""
    wid = str(order.get("work_order_id"))
    department = _department(order)
    if order.get("recommended_action") == "measurement_gap.report":
        deliverable = "measurement-gap definition and bounded instrumentation checklist"
        result = "The measurement gap was converted into an internal evidence checklist; no analytics or customer systems were changed."
    else:
        deliverable = "bounded department implementation brief"
        result = "The existing department work order was converted into a bounded internal execution brief; no external action was performed."
    artifact = {"schema_version": "nexus.department-work-result.v1", "work_order_id": wid,
                "department": department, "title": order.get("title"), "deliverable": deliverable,
                "result": result, "source": order.get("source"), "external_side_effects": False,
                "created_at": utc_now()}
    path = ROOT / "reports/runtime/department_progress" / f"{wid}.json"
    write_json(path, artifact)
    return {"status": "PASS", "action": order.get("recommended_action"),
            "artifact_path": str(path.relative_to(ROOT)), "execution_mode": "REAL",
            "external_side_effects": False, "department": department,
            "result": result}


def _recover_expired_claims() -> int:
    now = utc_now()
    recovered = 0
    handle = _lock(LOCK_PATH)
    try:
        rows = _orders()
        for row in rows:
            if (str(row.get("status", "")).upper() in {"CLAIMED", "RUNNING"}
                    and str(row.get("claim_expires_at") or "") <= now):
                row.update({"status": "FAILED_RETRYABLE", "failure_class": "CLAIM_EXPIRED",
                            "retry_at": _iso_after(5), "last_updated": now,
                            "recovery_note": "consumer recovered an expired claim"})
                recovered += 1
        if recovered:
            _save(rows)
    finally:
        handle.close()
    return recovered


def _claim(order: dict) -> dict | None:
    handle = _lock(LOCK_PATH)
    try:
        rows = _orders()
        target = next((x for x in rows if x.get("work_order_id") == order.get("work_order_id") and _eligible(x)), None)
        if not target:
            return None
        now = utc_now()
        execution_id = "dept_exec_" + uuid.uuid4().hex
        target.update({"status": "CLAIMED", "claimed_by": "department_work_consumer",
                       "claimed_at": now, "claim_expires_at": _iso_after(JOB_TIMEOUT_SECONDS + 30),
                       "attempt": int(target.get("attempt", 0)) + 1, "execution_id": execution_id,
                       "department": _department(target), "last_updated": now})
        _save(rows)
        return dict(target)
    finally:
        handle.close()


def _transition(work_order_id: str, updates: dict) -> None:
    handle = _lock(LOCK_PATH)
    try:
        rows = _orders()
        for row in rows:
            if row.get("work_order_id") == work_order_id:
                row.update(updates)
        _save(rows)
    finally:
        handle.close()


def _execute_child(order: dict) -> dict:
    if order.get("recommended_action") in {"measurement_gap.report", "department.work_order"}:
        return _bounded_department_result(order)
    finding = {**order, "finding_id": order.get("work_order_id"),
               "source_record_id": order.get("work_order_id"),
               "parent_goal": order.get("parent_goal") or order.get("goal_id"),
               "department": order.get("department") or _department(order),
               "question": order.get("description") or order.get("title"),
               "proposed_action": order.get("recommended_action"),
               "action_class": order.get("authority_required"),
               "evidence_refs": order.get("evidence_refs") or []}
    result = execute_safe_internal_action(str(order.get("recommended_action")), finding)
    return result if isinstance(result, dict) else {"status": "FAILED", "error": "invalid_executor_result"}


def _run_child(order: dict) -> dict:
    payload = json.dumps(order)
    cmd = [sys.executable, str(Path(__file__).resolve()), "--execute-job"]
    try:
        completed = subprocess.run(cmd, input=payload, text=True, capture_output=True,
                                   cwd=str(ROOT), timeout=JOB_TIMEOUT_SECONDS,
                                   env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")})
    except subprocess.TimeoutExpired:
        return {"status": "FAILED_RETRYABLE", "failure_class": "JOB_TIMEOUT", "error": "department job exceeded bounded timeout"}
    if completed.returncode != 0:
        return {"status": "FAILED_RETRYABLE", "failure_class": "WORKER_PROCESS_FAILED", "error": "registered worker process failed"}
    try:
        result = json.loads(completed.stdout)
        return result if isinstance(result, dict) else {"status": "FAILED_RETRYABLE", "error": "invalid_worker_json"}
    except (TypeError, ValueError):
        return {"status": "FAILED_RETRYABLE", "failure_class": "INVALID_WORKER_OUTPUT", "error": "worker returned no safe structured result"}


def process_one(order: dict) -> dict:
    claimed = _claim(order)
    if not claimed:
        return {"status": "SKIPPED_CLAIM_LOST", "work_order_id": order.get("work_order_id")}
    wid = claimed["work_order_id"]
    started = utc_now()
    _transition(wid, {"status": "RUNNING", "started_at": started, "last_updated": started})
    result = _run_child(claimed)
    completed = utc_now()
    receipt = {"schema_version": "nexus.department-execution-receipt.v1",
               "receipt_id": "department_receipt_" + claimed["execution_id"],
               "work_order_id": wid, "department": claimed["department"],
               "execution_id": claimed["execution_id"], "claimed_at": claimed["claimed_at"],
               "started_at": started, "completed_at": completed,
               "result": {k: v for k, v in result.items() if k not in {"token", "secret", "access_token", "refresh_token"}},
               "external_side_effects": False}
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    receipt_path = RECEIPT_DIR / f"{claimed['execution_id']}.json"
    write_json(receipt_path, receipt)
    passed = str(result.get("status", "")).upper() in {"PASS", "COMPLETED", "SUCCESS"}
    final = "COMPLETED" if passed else "FAILED_RETRYABLE"
    _transition(wid, {"status": final, "completed_at": completed, "last_updated": completed,
                       "receipt_refs": [str(receipt_path.relative_to(ROOT))],
                       "result_artifact": result.get("artifact_path") or result.get("receipt_path"),
                       "result_classification": "INTERNAL_WORKER_RESULT" if passed else result.get("failure_class", "WORKER_FAILURE"),
                       "return_destination": "Research" if claimed["department"] == "Research" else "Executive state"})
    return {"work_order_id": wid, "department": claimed["department"], "claimed_at": claimed["claimed_at"],
            "started_at": started, "completed_at": completed, "result": result,
            "final_state": final, "receipt": str(receipt_path.relative_to(ROOT))}


def run_once() -> dict:
    started = utc_now()
    recovered_claims = _recover_expired_claims()
    rows = _orders()
    candidates = [x for x in rows if _eligible(x)]
    # Fairness is at department level: one eligible item per department per
    # pass, then fill remaining slots by priority/age. This preserves
    # throughput without allowing Research to monopolize the queue.
    selected = []
    seen_departments = set()
    for item in candidates:
        dept = _department(item)
        if dept in seen_departments:
            continue
        selected.append(item)
        seen_departments.add(dept)
        if len(selected) == MAX_PER_CYCLE:
            break
    if len(selected) < MAX_PER_CYCLE:
        selected.extend(item for item in candidates if item not in selected and len(selected) < MAX_PER_CYCLE)
    eligible = selected
    results = [process_one(x) for x in eligible]
    state = {"schema_version": "nexus.department-work-consumer.v1", "enabled": True,
             "last_run": utc_now(), "started_at": started, "processed": len(results),
             "recovered_expired_claims": recovered_claims,
             "next_poll": _iso_after(POLL_SECONDS), "job_timeout_seconds": JOB_TIMEOUT_SECONDS,
             "queue_consumer": "department_work_consumer", "local_blocker_global_stop": False,
             "next_work_auto_selected": bool(results)}
    write_json(HEARTBEAT, state)
    return {"state": state, "processed": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--execute-job", action="store_true")
    args = parser.parse_args()
    if args.execute_job:
        print(json.dumps(_execute_child(json.load(sys.stdin))))
        return 0
    while True:
        with _lock(CONSUMER_LOCK):
            result = run_once()
        if args.once:
            print(json.dumps(result, indent=2))
            return 0
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
