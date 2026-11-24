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
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from operations.productivity_monitor import evaluate_research, record_incident, close_incident
STATE = ROOT / "data/runtime/nexus_supervisor_state.json"
HEARTBEAT = ROOT / "reports/runtime/nexus_supervisor_heartbeat.json"
INTERVAL = max(30, int(os.environ.get("NEXUS_SUPERVISOR_INTERVAL", "60")))

WORKERS = [
    {"name": "Nexus MCP Bridge", "labels": ["com.nexus.nexus-mcp-bridge"], "patterns": ["uvicorn services.nexus_mcp.http_server:app"], "heartbeat": "reports/runtime/nexus_mcp_bridge_health.json", "queue": "data/runtime/nexus_mcp_receipts"},
    {"name": "Oracle Hermes Tunnel", "labels": ["com.nexus.oracle-hermes-tunnel"], "patterns": ["-R 127.0.0.1:18765"], "heartbeat": "reports/runtime/oracle_hermes_tunnel_health.json", "queue": ""},
    {"name": "Nova Telegram Worker", "labels": ["com.nexus.telegram-hermes-nova"], "patterns": ["scripts/nova/nova_telegram_worker.py"], "heartbeat": "reports/runtime/nova_telegram_worker_heartbeat.json", "queue": "data/runtime/nova_telegram_delivery"},
    {"name": "Durable Department Worker", "labels": ["com.nexus.durable-dispatcher"], "patterns": ["scripts/nexus_agent_platform/job_worker_once.py"], "heartbeat": "reports/runtime/durable_job_health_latest.json", "queue": "reports/runtime/durable_job_health_latest.json"},
    {"name": "Research Worker", "labels": ["com.nexus.durable-dispatcher"], "patterns": ["scripts/nexus_agent_platform/job_worker_once.py"], "heartbeat": "reports/runtime/durable_job_health_latest.json", "queue": "data/runtime/research_work_queue.json"},
    {"name": "Systems Worker", "labels": ["com.nexus.durable-dispatcher"], "patterns": ["scripts/nexus_agent_platform/job_worker_once.py"], "heartbeat": "reports/runtime/durable_job_health_latest.json", "queue": "reports/runtime/durable_job_health_latest.json"},
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


def _matching_worker_pids(processes: str, patterns: list[str]) -> list[int]:
    """Return real worker PIDs, not shells/search commands containing a pattern.

    The previous substring-only check could classify an audit shell (whose
    command text happened to mention the worker script) as the worker itself.
    This keeps the existing observation model but ignores command wrappers and
    requires the pattern to occur in an executable process command.
    """
    matches = []
    for line in processes.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        pid = int(parts[0]); command = parts[1].strip()
        if command.startswith(("/bin/zsh -c", "/bin/bash -c", "/bin/sh -c", "rg ")):
            continue
        if any(pattern in command for pattern in patterns):
            matches.append(pid)
    return matches


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


def _work_order_metrics(path: Path) -> dict[str, int]:
    """Count current work states; append-only history is not executable backlog."""
    metrics = {key: 0 for key in ("TOTAL_RECORDS", "READY", "CLAIMED", "RUNNING", "COMPLETED", "FAILED_RETRYABLE", "WAITING_APPROVAL", "BLOCKED", "SUPERSEDED")}
    if not path.exists(): return metrics
    try: rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError): return metrics
    if not isinstance(rows, list): return metrics
    for row in rows:
        metrics["TOTAL_RECORDS"] += 1
        state = str(row.get("status") or "").upper()
        if state in metrics: metrics[state] += 1
    return metrics


def _execution_events(path: Path) -> list[dict]:
    if not path.exists(): return []
    events = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if isinstance(row, dict): events.append(row)
    except (OSError, ValueError):
        return events
    return events[-100:]


def _latest_incidents(path: Path) -> list[dict]:
    latest = {}
    for row in _execution_events(path):
        if row.get("incident_id"):
            latest[row["incident_id"]] = row
    return list(latest.values())


def _last_output(data):
    if not isinstance(data, dict): return None
    for key in ("last_real_output", "last_success", "last_successful_run", "completed_at", "last_run", "updated_at"):
        if data.get(key): return data[key]
    return None


def snapshot() -> dict:
    launched = _launchd(); processes = _processes(); generated = _now(); workers = []
    research_eval = None
    incidents = _latest_incidents(ROOT / "data/runtime/nexus_supervisor_incidents.jsonl")
    for spec in WORKERS:
        label_rows = [(label, launched.get(label)) for label in spec["labels"] if label in launched]
        pids = []
        pids = _matching_worker_pids(processes, spec["patterns"])
        hb_path = ROOT / spec["heartbeat"]; hb = _read(hb_path)
        queue_metrics = _work_order_metrics(ROOT / spec["queue"]) if spec["name"] == "Department Work Consumer" else None
        queue_depth = (queue_metrics["READY"] + queue_metrics["FAILED_RETRYABLE"] + queue_metrics["CLAIMED"] + queue_metrics["RUNNING"]) if queue_metrics else _queue_depth(ROOT / spec["queue"])
        running = bool(label_rows or pids)
        if spec["name"] == "Research Worker":
            research_eval = evaluate_research(process_running=running, heartbeat=hb if isinstance(hb, dict) else {}, execution_events=_execution_events(ROOT / "data/runtime/research_execution_jobs.jsonl"))
            if research_eval["classification"]:
                severity = "CRITICAL" if research_eval["productivity_health"] == "STALLED" else "DEGRADED"
                record_incident(worker="Research Worker", classification=research_eval["classification"], severity=severity, details={"summary": f"{research_eval['consecutive_failures']} consecutive scheduled wake failures" if research_eval["consecutive_failures"] else "Research heartbeat is stale", "last_heartbeat": research_eval.get("last_heartbeat"), "next_retry": "next supervised Research wake"}, recovery_action="retry the failed job and continue the next scheduled wake")
            elif research_eval["productivity_health"] == "HEALTHY":
                for incident in incidents:
                    if incident.get("state") == "OPEN" and incident.get("worker") == "Research Worker":
                        close_incident(incident["incident_id"], reason="healthy scheduled Research execution resumed")
            status = research_eval["productivity_health"]
            process_status = research_eval["process_health"]
        elif spec["name"] == "Creative Worker" and not running:
            status = "EXTERNAL_GATED"
        elif running and (hb is not None or spec["name"] in {"Nexus MCP Bridge", "Oracle Hermes Tunnel", "Durable Department Worker", "Research Worker", "Systems Worker"}):
            status = "ACTIVE"
        elif running:
            status = "RUNNING_NO_PRODUCTIVITY_PROOF"
        else:
            status = "SUPERVISED_NOT_CURRENTLY_RUNNING"
        process_health = process_status if spec["name"] == "Research Worker" else ("HEALTHY" if running else "DOWN")
        productivity_health = status if spec["name"] == "Research Worker" else ("HEALTHY" if running and hb is not None else "IDLE_LEGITIMATE")
        active_incident = next((i for i in reversed(incidents) if i.get("worker") == spec["name"] and i.get("state") == "OPEN"), None)
        row = {"worker_name": spec["name"], "status": status, "process_status": process_health, "productivity_status": productivity_health, "PROCESS_STATUS": process_health, "PRODUCTIVITY_STATUS": productivity_health, "active_incident": active_incident.get("incident_id") if active_incident else None, "next_recovery_action": active_incident.get("automatic_recovery_action") if active_incident else "continue supervised polling", "pid": pids[0] if pids else (int(label_rows[0][1][0]) if label_rows and label_rows[0][1][0].isdigit() else None), "host": "Mac control plane", "supervisor": "launchd" if label_rows else "nexus_supervisor_observer", "last_heartbeat": _last_output(hb), "last_real_output": _last_output(hb), "queue_depth": queue_depth, "queue_metrics": queue_metrics, "last_error": (hb or {}).get("error") if isinstance(hb, dict) else None, "next_action": "continue supervised polling" if running else "launchd restart/next scheduled wake", "restart_count": 0, "heartbeat_path": spec["heartbeat"], "queue_source": spec["queue"]}
        if research_eval and spec["name"] == "Research Worker": row.update(research_eval)
        workers.append(row)
    actionable = sum(int(w.get("queue_depth") or 0) for w in workers if w["status"] in {"ACTIVE", "RUNNING_NO_PRODUCTIVITY_PROOF"})
    state = {"schema_version": "nexus.supervisor-state.v1", "generated_at": generated, "supervisor_status": "RUNNING", "workers": workers, "queue_metrics": next((w["queue_metrics"] for w in workers if w["worker_name"] == "Department Work Consumer"), None), "global": {"machine_work_remaining": actionable > 0, "human_gated_work": "query canonical approvals", "external_gated_work": "remote Creative/Penpot where unavailable", "critical_failures": [w["worker_name"] for w in workers if w["status"] == "SUPERVISED_NOT_CURRENTLY_RUNNING" or w.get("productivity_status") == "STALLED"], "next_machine_action": "continue worker polling, revalidate productivity, and preserve per-worker isolation"}, "productivity_aware": True, "process_supervision": "launchd owns restart policy"}
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
