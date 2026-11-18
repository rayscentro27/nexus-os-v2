#!/usr/bin/env python3
"""Read-only executable probes for the active Research/Systems workflow."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json"
STATE = Path.home() / ".nexus/state/research/r10"
JOBS_DB = STATE / "research_r10_batch_c.sqlite3"
RESULTS_DB = STATE / "research_r10_bridge.sqlite3"
LEGACY_QUEUE = ROOT / "data/runtime/research_work_queue.json"


def _ro(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
    con.execute("PRAGMA query_only=ON")
    return con


def _tables(con: sqlite3.Connection) -> set[str]:
    return {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def research_snapshot(jobs_db: Path = JOBS_DB, results_db: Path = RESULTS_DB) -> dict[str, Any]:
    jobs = _ro(jobs_db)
    try:
        if "jobs" not in _tables(jobs):
            return {"status": "FAIL", "reason": "AUTHORITATIVE_JOBS_TABLE_MISSING"}
        counts: dict[str, int] = {}
        completed_ids: set[str] = set()
        paused_ages: list[float] = []
        runnable_ages: list[float] = []
        now = datetime.now(timezone.utc)
        for job_id, raw, updated in jobs.execute("SELECT job_id,payload,updated_at FROM jobs"):
            try:
                obj = json.loads(raw)
                state = str(obj.get("status") or obj.get("state") or "UNKNOWN").upper()
                counts[state] = counts.get(state, 0) + 1
                try:
                    age = (now - datetime.fromisoformat(str(updated).replace("Z", "+00:00"))).total_seconds()
                    if state == "PAUSED_RESUMABLE": paused_ages.append(age)
                    if state in {"READY", "QUEUED", "RETRYABLE", "EXECUTING", "RUNNING"}: runnable_ages.append(age)
                except (ValueError, TypeError):
                    pass
                if state in {"COMPLETED", "COMPLETED_WITH_LIMITATIONS"}:
                    completed_ids.add(job_id)
            except (TypeError, json.JSONDecodeError):
                counts["INVALID_PAYLOAD"] = counts.get("INVALID_PAYLOAD", 0) + 1
    finally:
        jobs.close()
    results = _ro(results_db)
    try:
        result_tables = _tables(results)
        if not {"bridge_results", "completion_events"} <= result_tables:
            return {"status": "FAIL", "reason": "RESULT_OR_OUTBOX_TABLE_MISSING", "job_statuses": counts}
        stored = {}
        summary_missing = 0
        for job_id, raw in results.execute("SELECT job_id,result_json FROM bridge_results ORDER BY updated_at"):
            try:
                record = json.loads(raw)
                stored[job_id] = record
                if str(record.get("status", "")).upper() in {"COMPLETED", "COMPLETED_WITH_LIMITATIONS"} and not record.get("summary"):
                    summary_missing += 1
            except (TypeError, json.JSONDecodeError):
                continue
        event_ids = {row[0] for row in results.execute("SELECT DISTINCT job_id FROM completion_events")}
        missing_result = len(completed_ids - set(stored))
        missing_event = len(completed_ids - event_ids)
        fields_missing = sum(1 for jid in completed_ids & set(stored)
                            if not stored[jid].get("summary") or not stored[jid].get("key_findings"))
        return {"status": "PASS" if missing_result == 0 and summary_missing == 0 and fields_missing == 0 and missing_event == 0 else "DEGRADED",
                "job_statuses": counts, "durable_result_count": len(stored),
                "completed_jobs_missing_result": missing_result,
                "completed_results_missing_summary": summary_missing,
                "completed_results_missing_summary_or_findings": fields_missing,
                "completed_jobs_missing_completion_event": missing_event,
                "paused_resumable_count": len(paused_ages),
                "oldest_paused_age_hours": round(max(paused_ages) / 3600, 2) if paused_ages else 0,
                "runnable_job_count": len(runnable_ages),
                "oldest_runnable_age_minutes": round(max(runnable_ages) / 60, 2) if runnable_ages else 0,
                "completion_event_count": int(results.execute("SELECT COUNT(*) FROM completion_events").fetchone()[0]),
                "latest_result_status": next((stored[j].get("status") for j in reversed(list(stored)) if j in stored), None)}
    finally:
        results.close()


def http_health(url: str = "http://127.0.0.1:18766/health") -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body = response.read(2048)
            data = json.loads(body) if body else {}
            return {"status": "PASS" if response.status == 200 and data.get("status") == "ok" else "FAIL", "http_status": response.status}
    except Exception as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def scheduler_check(label: str = "com.nexus.research-r10-autonomy") -> dict[str, Any]:
    try:
        p = subprocess.run(["launchctl", "print", f"gui/501/{label}"], capture_output=True, text=True, timeout=4)
        loaded = p.returncode == 0 and "run interval = 300 seconds" in p.stdout
        return {"status": "PASS" if loaded else "FAIL", "loaded": p.returncode == 0,
                "interval_seconds": 300 if "run interval = 300 seconds" in p.stdout else None,
                "last_exit_zero": "last exit code = 0" in p.stdout}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def _launchd_text(label: str) -> str:
    p = subprocess.run(["launchctl", "print", f"gui/501/{label}"], capture_output=True, text=True, timeout=4)
    return p.stdout if p.returncode == 0 else ""


def _scheduler_labels() -> list[str]:
    p = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
    return [line.split()[-1] for line in p.stdout.splitlines()
            if re.search(r"research.*(?:autonomy|scheduler)|(?:autonomy|scheduler).*research", line, re.I)]


def run(manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resolver = manifest.get("change_target_registry", {}).get("components", {}).get("research", {})
    legacy = resolver.get("historical_queue_flags", {})
    checks = {
        "authoritative_research_queue_reachable": {"status": "PASS" if JOBS_DB.is_file() else "FAIL", "path": str(JOBS_DB)},
        "legacy_queue_not_authoritative": {"status": "PASS" if legacy.get("historical_only") and legacy.get("do_not_use_for_live_operations") and legacy.get("do_not_patch") and resolver.get("authoritative_database", "").endswith("research_r10_batch_c.sqlite3") else "FAIL"},
        "r10_http_health": http_health(),
        "scheduler_single_owner": scheduler_check(),
        "research_durable_results_and_events": research_snapshot(),
    }
    r10_label = _launchd_text("com.nexus.research-r10")
    pid_match = re.search(r"\bpid = (\d+)", r10_label)
    r10_pid = int(pid_match.group(1)) if pid_match else None
    try:
        if r10_pid: os.kill(r10_pid, 0)
        worker_alive = bool(r10_pid)
    except OSError:
        worker_alive = False
    checks["expected_r10_worker_count"] = {"status": "PASS" if worker_alive else "FAIL", "service_instances": 1 if worker_alive else 0}
    snap = checks["research_durable_results_and_events"]
    checks["paused_work_age"] = {"status": "PASS" if snap.get("oldest_paused_age_hours", 0) <= 24 else "DEGRADED",
                                 "paused_count": snap.get("paused_resumable_count"), "oldest_age_hours": snap.get("oldest_paused_age_hours")}
    checks["runnable_work_progress"] = {"status": "PASS" if snap.get("runnable_job_count", 0) == 0 or snap.get("oldest_runnable_age_minutes", 0) <= 15 else "DEGRADED",
                                        "runnable_count": snap.get("runnable_job_count"), "oldest_age_minutes": snap.get("oldest_runnable_age_minutes")}
    schedulers = _scheduler_labels()
    checks["duplicate_scheduler_detection"] = {"status": "PASS" if schedulers == ["com.nexus.research-r10-autonomy"] else "DEGRADED", "matching_labels": schedulers}
    expected_entry = manifest.get("research_baseline", {}).get("scheduler", {}).get("entrypoint", "")
    scheduler_text = _launchd_text("com.nexus.research-r10-autonomy")
    checks["manifest_target_matches_production"] = {"status": "PASS" if expected_entry and expected_entry in scheduler_text else "FAIL",
                                                     "expected_entrypoint_match": bool(expected_entry and expected_entry in scheduler_text)}
    # Existing MCP exposure is known, but this local probe has no Nova production
    # identity; do not substitute a privileged local Research read for Nova.
    checks["nova_latest_result_read"] = {"status": "NOT_VERIFIED", "reason": "requires the authenticated active Nova MCP caller"}
    try:
        q = json.loads(LEGACY_QUEUE.read_text(encoding="utf-8")) if LEGACY_QUEUE.exists() else {}
        checks["legacy_queue_present_but_historical"] = {"status": "PASS" if checks["legacy_queue_not_authoritative"]["status"] == "PASS" else "FAIL", "read_only": True, "historical_item_count": len(q) if isinstance(q, list) else None}
    except (OSError, json.JSONDecodeError):
        checks["legacy_queue_present_but_historical"] = {"status": "PASS" if checks["legacy_queue_not_authoritative"]["status"] == "PASS" else "FAIL", "read_only": True, "historical_item_count": None}
    passed = sum(1 for c in checks.values() if c.get("status") == "PASS")
    return {"schema_version": "nexus.workflow-integrity-report.v1", "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if passed == len(checks) else "DEGRADED", "pass_count": passed,
            "check_count": len(checks), "checks": checks,
            "limitations": ["Nova latest-result retrieval requires the authenticated active Nova MCP caller."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    try:
        result = run(args.manifest)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "FAIL", "error_class": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
