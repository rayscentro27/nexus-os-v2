#!/usr/bin/env python3
"""Read-only Systems Phase 1 manifest validation and local health checks.

This module intentionally performs no restart, acknowledgement, state repair,
credential access, network mutation, or scheduling. Remote checks remain on the
existing nexus_oracle_connection.py allowlisted path.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from secret_guard import redact
except ImportError:
    from scripts.systems.secret_guard import redact

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json"
REQUIRED_ENVIRONMENTS = {
    "MAC_MINI_RESEARCH", "ORACLE_NOVA", "ORACLE_HERMES", "SUPABASE", "GITHUB"
}
REQUIRED_REGISTRY_KEYS = {
    "environment_registry", "process_registry", "durable_state_registry",
    "minimum_sustainability_model", "health_framework", "research_degradation",
    "recovery_models", "credential_systems", "maintenance_plan",
}


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("systems_phase1"), dict):
        raise ValueError("Living Manifest is missing systems_phase1")
    return data


def validate_registry(manifest: dict[str, Any]) -> list[str]:
    phase = manifest["systems_phase1"]
    errors = sorted(REQUIRED_REGISTRY_KEYS - set(phase))
    envs = phase.get("environment_registry", [])
    ids = {item.get("environment_id") for item in envs if isinstance(item, dict)}
    missing = sorted(REQUIRED_ENVIRONMENTS - ids)
    if missing:
        errors.append("missing environments: " + ", ".join(missing))
    for section, required in (("environment_registry", {"environment_id", "role", "host_platform", "os_runtime", "responsibilities", "criticality", "dependencies", "health_method", "recovery_method", "status", "last_verified"}),
                              ("process_registry", {"component", "environment", "service_name", "entrypoint", "start_mechanism", "restart_mechanism", "expected_process_count", "dependencies", "health_check", "recovery_command", "failure_impact", "tier"}),
                              ("durable_state_registry", {"asset", "location", "environment", "owner", "criticality", "backup_requirement", "restore_requirement", "health_integrity_test", "loss_impact"})):
        for i, record in enumerate(phase.get(section, [])):
            absent = sorted(required - set(record))
            if absent:
                errors.append(f"{section}[{i}] missing {','.join(absent)}")
    return errors


def check_http(url: str, timeout: float = 3.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(4096)
            parsed = json.loads(body) if body else {}
            passed = response.status == 200 and parsed.get("status") == "ok"
            return {"status": "PASS" if passed else "FAIL", "http_status": response.status,
                    "runtime": parsed.get("runtime"), "worker_limit": parsed.get("worker_limit")}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def check_sqlite(path: str) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        return {"status": "NOT_PRESENT"}
    try:
        uri = p.resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True, timeout=2)
        con.execute("PRAGMA query_only=ON")
        result = con.execute("PRAGMA quick_check").fetchone()[0]
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts: dict[str, int] = {}
        for table in ("completion_events", "bridge_jobs", "bridge_results", "jobs"):
            if table in tables:
                counts[table] = int(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        if "jobs" in tables:
            columns = {r[1] for r in con.execute("PRAGMA table_info(jobs)")}
            if "payload" in columns:
                from collections import Counter
                states = Counter()
                for (payload,) in con.execute("SELECT payload FROM jobs"):
                    try:
                        item = json.loads(payload)
                        states[item.get("status") or item.get("state") or "UNKNOWN"] += 1
                    except (TypeError, json.JSONDecodeError):
                        states["INVALID_PAYLOAD"] += 1
                counts["job_statuses"] = dict(states)
        if "completion_events" in tables:
            columns = {r[1] for r in con.execute("PRAGMA table_info(completion_events)")}
            if "delivered_at" in columns:
                counts["completion_delivery"] = {
                    "delivered": int(con.execute("SELECT COUNT(*) FROM completion_events WHERE delivered_at IS NOT NULL").fetchone()[0]),
                    "pending": int(con.execute("SELECT COUNT(*) FROM completion_events WHERE delivered_at IS NULL").fetchone()[0]),
                }
        con.close()
        return {"status": "PASS" if result == "ok" else "FAIL", "quick_check": result,
                "table_counts": counts}
    except (sqlite3.Error, OSError) as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def check_launchd(label: str) -> dict[str, str]:
    proc = subprocess.run(["launchctl", "print", f"gui/501/{label}"],
                          capture_output=True, text=True, timeout=4)
    output = proc.stdout
    loaded = proc.returncode == 0
    exit_status = "UNKNOWN"
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("last exit code ="):
            exit_status = stripped.rsplit("=", 1)[-1].strip()
            break
    return {"status": "LOADED" if loaded else "NOT_LOADED", "last_exit": exit_status}


def local_report(manifest: dict[str, Any]) -> dict[str, Any]:
    phase = manifest["systems_phase1"]
    research = manifest["research_baseline"]
    dbs = [
        str(Path.home() / ".nexus/state/research/r10/research_r10_bridge.sqlite3"),
        str(Path.home() / ".nexus/state/research/r10/source_registry/youtube_channels.sqlite3"),
        str(Path.home() / ".nexus/state/research/r10/research_r10_batch_c.sqlite3"),
    ]
    registry_path = Path(dbs[1])
    source_status: dict[str, Any] = {"status": "NOT_PRESENT"}
    if registry_path.exists():
        try:
            con = sqlite3.connect(registry_path.resolve().as_uri() + "?mode=ro", uri=True)
            con.execute("PRAGMA query_only=ON")
            enabled_channels, missing_channel_checks = con.execute(
                "SELECT COUNT(*), SUM(CASE WHEN next_check IS NULL THEN 1 ELSE 0 END) FROM youtube_channels WHERE enabled=1"
            ).fetchone()
            channel_states = dict(con.execute("SELECT poll_status, COUNT(*) FROM youtube_channels WHERE enabled=1 GROUP BY poll_status"))
            enabled_external, missing_external_checks = con.execute(
                "SELECT COUNT(*), SUM(CASE WHEN next_check IS NULL THEN 1 ELSE 0 END) FROM external_research_sources WHERE enabled=1"
            ).fetchone()
            source_status = {"status":"PASS", "enabled_youtube_channels":enabled_channels,
                             "youtube_poll_status":channel_states,
                             "youtube_missing_next_check":missing_channel_checks or 0,
                             "enabled_external_sources":enabled_external,
                             "external_missing_next_check":missing_external_checks or 0}
            con.close()
        except sqlite3.Error as exc:
            source_status = {"status":"FAIL", "error_class":type(exc).__name__}
    labels = ["com.nexus.research-r10", "com.nexus.research-r10-autonomy",
              "com.nexus.research-mcp", "com.nexus.durable-dispatcher",
              "com.nexus.nexus-mcp-bridge"]
    return {
        "manifest_validation": "PASS" if not validate_registry(manifest) else "FAIL",
        "manifest_errors": validate_registry(manifest),
        "r10_http": check_http("http://127.0.0.1:18766/health"),
        "research_databases": {Path(p).name: check_sqlite(p) for p in dbs},
        "source_schedule_state": source_status,
        "launchd": {label: check_launchd(label) for label in labels},
        "queue_health_source": phase["research_degradation"]["r10_job_state_authority"],
        "stale_projection_demoted": phase["research_degradation"]["stale_projection"],
        "paused_resumable": phase["research_degradation"]["paused_resumable_count"],
        "failed_terminal": phase["research_degradation"]["failed_terminal_count"],
        "dispatcher_scope": phase["research_degradation"]["dispatcher_scope"],
        "research_mcp_auth_handshake": "NOT_RECHECKED_BY_THIS_LOCAL_CHECKER",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        errors = validate_registry(manifest)
        result = {"manifest": str(args.manifest), "validation": "PASS" if not errors else "FAIL",
                  "validation_errors": errors}
        if not args.validate_only:
            result["local_read_only_health"] = local_report(manifest)
        print(json.dumps(redact(result), indent=2, sort_keys=True))
        return 0 if not errors else 1
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        print(json.dumps({"validation": "FAIL", "error_class": type(exc).__name__,
                          "message": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
