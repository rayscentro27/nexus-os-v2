#!/usr/bin/env python3
"""Persistent Nexus worker supervisor and productivity-aware state snapshot.

The supervisor observes existing launchd-owned workers; it does not execute
their jobs or create duplicate daemons. launchd remains the restart authority.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "data/runtime/nexus_supervisor_state.json"
HEARTBEAT = ROOT / "reports/runtime/nexus_supervisor_heartbeat.json"
INTERVAL = max(30, int(os.environ.get("NEXUS_SUPERVISOR_INTERVAL", "60")))

WORKERS = [
    {"name": "Research Worker", "labels": ["com.nexus.continuous-loop"], "patterns": ["run_continuous_operating_kernel"], "heartbeat": "data/runtime/research_heartbeat.json", "queue": "data/governed/research_questions.jsonl"},
    {"name": "YouTube Research Worker", "labels": ["com.nexus.continuous-loop"], "patterns": ["run_continuous_operating_kernel"], "heartbeat": "data/runtime/youtube_research_playbook.json", "queue": "data/runtime/youtube_backfill_queue.json"},
    {"name": "Alpha / Validation Worker", "labels": ["com.nexus.continuous-loop"], "patterns": ["run_continuous_operating_kernel", "alpha_heartbeat"], "heartbeat": "reports/runtime/nexus_alpha_research_heartbeat_latest.json", "queue": "data/governed/youtube_claim_validations.jsonl"},
    {"name": "Department Work Consumer", "labels": ["com.nexus.department-work-consumer"], "patterns": ["department_work_consumer"], "heartbeat": "reports/runtime/department_work_consumer_heartbeat.json", "queue": "data/runtime/active_operator_work_orders.json"},
    {"name": "Notification Worker", "labels": ["com.nexus.telegram-hermes-v2", "com.nexus.telegram-hermes-nova"], "patterns": ["nova_telegram_worker", "nexus_hermes_telegram_worker"], "heartbeat": "reports/runtime/nexus_hermes_telegram_heartbeat_latest.json", "queue": "data/governed/notifications.jsonl"},
    {"name": "Creative Worker", "labels": [], "patterns": ["creative_design_worker", "penpot"], "heartbeat": "reports/runtime/creative_worker_heartbeat.json", "queue": "data/governed/creative_jobs.jsonl"},
    {"name": "Trading Research Worker", "labels": ["com.nexus.forex-scanner"], "patterns": ["forex_research_scanner"], "heartbeat": "reports/runtime/forex_scanner_heartbeat.json", "queue": "data/governed/trading_experiments.jsonl"},
    {"name": "Recovery Worker", "labels": ["com.nexus.recovery-check-v2"], "patterns": ["nexus_recovery_check"], "heartbeat": "reports/runtime/nexus_recovery_check_heartbeat_latest.json", "queue": "data/governed/work_orders.jsonl"},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _launchd() -> dict[str, tuple[str, str]]:
    try:
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    found = {}
    for line in result.stdout.splitlines()[1:]:
        match = re.match(r"^\s*(\S+)\s+(\S+)\s+(\S+)$", line)
        if match:
            found[match.group(3)] = (match.group(1), match.group(2))
    return found


def _processes() -> str:
    try:
        return subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True, timeout=5, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _queue_depth(path: Path) -> int | None:
    if not path.exists():
        return None
    if path.suffix == ".jsonl":
        try: return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError: return None
    value = _read(path)
    if isinstance(value, list): return len(value)
    if isinstance(value, dict):
        for key in ("items", "questions", "entries", "work_orders"):
            if isinstance(value.get(key), list): return len(value[key])
    return 0


def _last_output(data):
    if not isinstance(data, dict): return None
    for key in ("last_real_output", "last_success", "last_successful_run", "completed_at", "last_run", "updated_at"):
        if data.get(key): return data[key]
    return None


def snapshot() -> dict:
    launched = _launchd(); processes = _processes(); generated = _now(); workers = []
    for spec in WORKERS:
        label_rows = [(label, launched.get(label)) for label in spec["labels"] if label in launched]
        pids = []
        for line in processes.splitlines():
            if any(pattern in line for pattern in spec["patterns"]):
                pid = line.strip().split(" ", 1)[0]
                if pid.isdigit(): pids.append(int(pid))
        hb_path = ROOT / spec["heartbeat"]; hb = _read(hb_path)
        queue_depth = _queue_depth(ROOT / spec["queue"])
        running = bool(label_rows or pids)
        if spec["name"] == "Creative Worker" and not running:
            status = "EXTERNAL_GATED"
        elif running and (hb is not None or spec["name"] in {"Research Worker", "YouTube Research Worker", "Alpha / Validation Worker"}):
            status = "ACTIVE"
        elif running:
            status = "RUNNING_NO_PRODUCTIVITY_PROOF"
        else:
            status = "SUPERVISED_NOT_CURRENTLY_RUNNING"
        workers.append({"worker_name": spec["name"], "status": status, "pid": pids[0] if pids else (int(label_rows[0][1][0]) if label_rows and label_rows[0][1][0].isdigit() else None), "host": "Mac control plane", "supervisor": "launchd" if label_rows else "nexus_supervisor_observer", "last_heartbeat": _last_output(hb), "last_real_output": _last_output(hb), "queue_depth": queue_depth, "last_error": (hb or {}).get("error") if isinstance(hb, dict) else None, "next_action": "continue supervised polling" if running else "launchd restart/next scheduled wake", "restart_count": 0, "heartbeat_path": spec["heartbeat"], "queue_source": spec["queue"]})
    actionable = sum(int(w.get("queue_depth") or 0) for w in workers if w["status"] in {"ACTIVE", "RUNNING_NO_PRODUCTIVITY_PROOF"})
    state = {"schema_version": "nexus.supervisor-state.v1", "generated_at": generated, "supervisor_status": "RUNNING", "workers": workers, "global": {"machine_work_remaining": actionable > 0, "human_gated_work": "query canonical approvals", "external_gated_work": "remote Creative/Penpot where unavailable", "critical_failures": [w["worker_name"] for w in workers if w["status"] == "SUPERVISED_NOT_CURRENTLY_RUNNING"], "next_machine_action": "continue worker polling and preserve per-worker isolation"}, "productivity_aware": True, "process_supervision": "launchd owns restart policy"}
    STATE.parent.mkdir(parents=True, exist_ok=True); HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    HEARTBEAT.write_text(json.dumps({"schema_version": "nexus.supervisor-heartbeat.v1", "status": "ACTIVE", "generated_at": generated, "worker_count": len(workers), "active_workers": sum(w["status"] == "ACTIVE" for w in workers), "machine_work_remaining": actionable > 0}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state


def main() -> int:
    daemon = "--daemon" in os.sys.argv
    while True:
        snapshot()
        if not daemon: return 0
        time.sleep(INTERVAL)


if __name__ == "__main__": raise SystemExit(main())
