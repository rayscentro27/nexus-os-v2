"""Read-only safe-boot and recovery-baseline verifier for Nexus.

This command never starts/stops/enables services, claims jobs, or invokes a
provider. It emits sanitized status metadata to stdout and exits nonzero when
the machine differs from the PRE_ACTIVATION_RECOVERY_BASELINE.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import subprocess
import sys
import os.path
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from nexus_agent_platform.environment_drift_monitor import collect_local_state, compare  # noqa: E402
from nexus_agent_platform.task_request_eligibility import task_request_is_dispatch_eligible  # noqa: E402

STATUS_PATH = REPO / "reports/remediation/NEXUS_REMEDIATION_CLOSURE_STATUS_20261009.json"
TASK_CLASSIFICATION_PATH = REPO / "reports/remediation/task_request_classification_20261009.json"
PROVIDER_REGISTRY = REPO / "reports/remediation/provider_caller_registry_20261009.json"
SECRET_REGISTRY = REPO / "reports/remediation/local_secret_consumer_registry_20261009.json"
PROJECT_REF_PATH = REPO / "supabase/.temp/project-ref"
CRITICAL_FILES = (
    "configs/launchd/com.nexus.scheduler.plist",
    "configs/launchd/com.nexus.dispatcher.plist",
    "ops/launchd/com.nexus.scheduler.plist",
    "ops/launchd/com.nexus.dispatcher.plist",
    "scripts/systems/verify_safe_recovery.py",
    "scripts/systems/environment_baseline.py",
    "scripts/nexus_agent_platform/environment_drift_monitor.py",
    "scripts/nexus_agent_platform/task_request_eligibility.py",
    "reports/remediation/task_request_classification_20261009.json",
) + tuple(
    str(path.relative_to(REPO))
    for directory in (REPO / "configs/launchd", REPO / "ops/launchd", REPO / "launchd", REPO / "scripts/ops")
    for path in sorted(directory.glob("*.plist"))
)
CANONICAL_SOURCE_PATHS = {
    "python_environment": ".venv-agent-platform/bin/python3",
    "scheduler": "scripts/nexus_agent_platform/scheduler_once.py",
    "dispatcher": "scripts/nexus_agent_platform/dispatcher_once.py",
    "worker_control_plane": "scripts/nexus_agent_platform/durable_jobs.py",
    "environment_registry": "configs/environment_lifecycle_registry.json",
    "provider_registry": "reports/remediation/provider_caller_registry_20261009.json",
    "secret_registry": "reports/remediation/local_secret_consumer_registry_20261009.json",
    "drift_monitor": "scripts/nexus_agent_platform/environment_drift_monitor.py",
    "recovery_verifier": "scripts/systems/verify_safe_recovery.py",
    "legacy_recovery_inspector": "scripts/operations/nexus_recovery_check.py",
    "recovery_launchd_definition": "ops/launchd/com.nexus.recovery-check-v2.plist",
}
FORBIDDEN_RUNTIME = re.compile(
    r"scheduler_once\.py|dispatcher_once\.py|nexus_active_operator_runner|"
    r"nexus_continuous_kernel|pm2.*(?:nexus|workflow)|(?:nexus|workflow).*pm2|"
    r"playwright|puppeteer|chromium.*(?:headless|automation)|ffmpeg|ollama serve",
    re.I,
)


def _run(args: list[str], timeout: float = 4.0) -> tuple[int, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def _sha256(path: Path) -> str | None:
    import hashlib
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _active_processes() -> list[dict[str, str]]:
    code, out = _run(["ps", "-axo", "pid=,ppid=,command="], timeout=5.0)
    if code:
        return [{"status": "PROCESS_LIST_UNAVAILABLE"}]
    rows = []
    own_pid = str(os.getpid())
    for line in out.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 3 or fields[0] == own_pid:
            continue
        if FORBIDDEN_RUNTIME.search(fields[2]):
            rows.append({"pid": fields[0], "ppid": fields[1], "class": "FORBIDDEN_OR_HEAVY_RUNTIME"})
    return rows


def _loaded_nexus_launchd() -> list[str] | None:
    code, out = _run(["launchctl", "list"], timeout=6.0)
    if code:
        return None
    labels = []
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[-1].startswith("com.nexus."):
            labels.append(parts[-1])
    return sorted(set(labels))


def _user_nexus_cron_count() -> int | None:
    code, out = _run(["crontab", "-l"], timeout=4.0)
    if code == 0:
        return sum(1 for line in out.splitlines() if "nexus" in line.lower())
    # macOS returns nonzero when the user has no crontab. Do not print stderr,
    # which may contain arbitrary command text.
    return 0 if not out.strip() else None


def _definitions_are_canonical() -> tuple[bool, list[str]]:
    problems: list[str] = []
    canonical = str(REPO)
    paths = sorted({
        path
        for directory in (REPO / "configs/launchd", REPO / "ops/launchd", REPO / "launchd", REPO / "scripts/ops")
        for path in directory.glob("*.plist")
    })
    for path in paths:
        try:
            with path.open("rb") as stream:
                data = plistlib.load(stream)
        except (OSError, ValueError, plistlib.InvalidFileException):
            problems.append(f"INVALID_OR_MISSING:{path.relative_to(REPO)}")
            continue
        label = str(data.get("Label", ""))
        if not label.startswith("com.nexus."):
            continue
        if data.get("RunAtLoad") is True or data.get("KeepAlive") is True or data.get("Disabled") is not True:
            problems.append(f"AUTOSTART_NOT_DISABLED:{path.relative_to(REPO)}")
        if label in {"com.nexus.scheduler", "com.nexus.dispatcher", "com.nexus.recovery-check-v2"}:
            encoded = json.dumps(data, sort_keys=True)
            if canonical not in encoded or "/nexus-os-v2/" in encoded.replace(canonical + "/", ""):
                problems.append(f"NONCANONICAL_PATH:{path.relative_to(REPO)}")
    return not problems, problems


def _supabase_readonly_health(timeout: float = 45.0) -> str:
    """Bounded SELECT 1 using the linked CLI; discard all CLI output."""
    if not PROJECT_REF_PATH.is_file():
        return "PROJECT_NOT_LINKED"
    try:
        ref = PROJECT_REF_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return "PROJECT_LINK_UNREADABLE"
    if not re.fullmatch(r"[a-z0-9]{10,30}", ref):
        return "PROJECT_REF_INVALID"
    try:
        result = subprocess.run(
            ["supabase", "db", "query", "--linked", "--output", "json", "select 1 as health;"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except OSError:
        return "CLI_UNAVAILABLE"
    if result.returncode:
        return "UNAVAILABLE"
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        return "INVALID_RESPONSE"
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    return "READ_ONLY_SELECT_PASS" if rows and rows[0].get("health") == 1 else "INVALID_RESPONSE"


def verify(baseline_path: Path, *, check_supabase: bool = True) -> dict[str, Any]:
    baseline = _load_json(baseline_path)
    state = collect_local_state(REPO)
    diff = compare(baseline.get("EXPECTED_LOCAL_STATE", {}) if baseline else {}, state)
    status = _load_json(STATUS_PATH) or {}
    safe_mode = status.get("safe_mode", {})
    supabase = status.get("supabase_live", {})
    credit = status.get("supabase_remediation", {})
    task_classification = _load_json(TASK_CLASSIFICATION_PATH) or {}
    final35 = status.get("final_35_closure", {})
    processes = _active_processes()
    launchd = _loaded_nexus_launchd()
    user_cron_count = _user_nexus_cron_count()
    canonical_defs, definition_problems = _definitions_are_canonical()
    runtime = Path(sys.executable)
    historical_eligible = task_request_is_dispatch_eligible({
        "status": "requested", "approved_by_ray": False, "payload": {},
    })
    registry_checks = {
        "provider_registry_present": PROVIDER_REGISTRY.is_file(),
        "secret_registry_present": SECRET_REGISTRY.is_file(),
        "provider_hash_matches": _sha256(PROVIDER_REGISTRY) == baseline.get("PROVIDER_REGISTRY_HASH"),
        "secret_hash_matches": _sha256(SECRET_REGISTRY) == baseline.get("SECRET_REGISTRY_HASH"),
    }
    expected_critical = baseline.get("RECOVERY_CRITICAL_FILE_HASHES", {})
    actual_critical = {name: _sha256(REPO / name) for name in CRITICAL_FILES}
    critical_files_match = bool(expected_critical) and actual_critical == expected_critical
    expected_source_paths = baseline.get("CANONICAL_SOURCE_PATHS", {})
    source_paths_match = expected_source_paths == CANONICAL_SOURCE_PATHS and all(
        (REPO / relative).exists() for relative in CANONICAL_SOURCE_PATHS.values()
    )
    mem_bytes = None
    code, out = _run(["sysctl", "-n", "hw.memsize"])
    if code == 0:
        try:
            mem_bytes = int(out.strip())
        except ValueError:
            pass
    pressure_code, pressure_out = _run(["memory_pressure", "-Q"], timeout=4.0)
    pressure_match = re.search(r"System-wide memory free percentage:\s*(\d+)%", pressure_out)
    memory_free_percent = int(pressure_match.group(1)) if pressure_code == 0 and pressure_match else None
    try:
        load_average = list(os.getloadavg())
    except (AttributeError, OSError):
        load_average = None
    status_checks = {
        "scheduler_off": safe_mode.get("new_scheduler_running") is False,
        "dispatcher_off": safe_mode.get("new_dispatcher_running") is False,
        "old_kernel_off": safe_mode.get("old_continuous_kernel_running") is False,
        "active_operator_off": safe_mode.get("active_operator_running") is False,
        "certification_off": safe_mode.get("certification_resumed") is False,
        "historical_replay_prevented": task_classification.get("source_rows") == 636
        and task_classification.get("mutation_performed") is False
        and "explicit reviewed CURRENT_V2_MIGRATED marker required" in task_classification.get("dispatch_eligibility_policy", ""),
        "credit_upload_uses_durable_only": credit.get("document_upload_creates_durable_job") is True
        and credit.get("document_upload_creates_legacy_credit_job") is False,
        "legacy_credit_queue_retained_not_autonomous": credit.get("credit_analysis_jobs_status") == "STILL_REQUIRED_FOR_ROLLBACK"
        and credit.get("autonomous_credit_queue_consumer") is False
        and credit.get("post_canary_counts", {}).get("credit_analysis_jobs_total") == 25,
        "provider_bypass_zero": final35.get("global_provider_bypass_count") == 0,
        "provider_partial_zero": final35.get("global_provider_partial_count") == 0,
        "provider_unknown_zero": final35.get("global_provider_unknown_count") == 0,
        "task_gate_fail_closed": historical_eligible is False,
        "runtime_venv_is_canonical": str(runtime).startswith(str(REPO / ".venv-agent-platform"))
        and Path(sys.prefix) == REPO / ".venv-agent-platform",
        "production_plists_canonical_and_disabled": canonical_defs,
        "no_user_nexus_crontab_entries": user_cron_count == 0,
    }
    no_runtime_processes = processes == []
    no_loaded_executors = launchd == []
    supabase_health = _supabase_readonly_health() if check_supabase else "NOT_REQUESTED"
    checks = {
        "baseline_valid": bool(baseline and baseline.get("STATUS") == "PRE_ACTIVATION_RECOVERY_BASELINE"),
        "repo_canonical": state["repository"].get("path") == str(REPO),
        "runtime": status_checks,
        "no_forbidden_runtime_processes": no_runtime_processes,
        "no_loaded_nexus_launch_agents": no_loaded_executors,
        "provider_secret_registry_integrity": registry_checks,
        "critical_recovery_files_match": critical_files_match,
        "recovery_source_paths_canonical": source_paths_match,
        "local_drift_zero": diff.get("status") == "MATCH",
        "supabase_read_only_health": supabase_health,
        "memory_size_bytes": mem_bytes,
        "memory_free_percent": memory_free_percent,
        "load_average": load_average,
        "resource_sanity": memory_free_percent is not None and memory_free_percent >= 15
        and load_average is not None and max(load_average) < 8.0,
        "root_cron_evidence": "PREVIOUSLY_VERIFIED_NO_CRONTAB; current sudo read may require admin",
    }
    all_checks = (
        checks["baseline_valid"] and checks["repo_canonical"] and all(status_checks.values())
        and no_runtime_processes and no_loaded_executors and all(registry_checks.values())
        and critical_files_match
        and source_paths_match
        and user_cron_count == 0 and memory_free_percent is not None and memory_free_percent >= 15
        and load_average is not None and max(load_average) < 8.0
        and checks["local_drift_zero"]
        and supabase_health in {"READ_ONLY_SELECT_PASS", "NOT_REQUESTED"}
    )
    return {
        "schema_version": 1,
        "mode": "READ_ONLY",
        "mutates_state": False,
        "starts_services": False,
        "creates_business_work": False,
        "calls_paid_providers": False,
        "opens_browser": False,
        "deploys": False,
        "changes_supabase": False,
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "safe_boot_state": "YES" if all_checks else "NO",
        "checks": checks,
        "local_drift": diff,
        "forbidden_process_count": len(processes),
        "loaded_nexus_launchd_labels": launchd,
        "canonical_definition_problems": definition_problems,
        "recovery_cpu_profile": "BOUNDED_READ_ONLY; Supabase SELECT timeout <= 45s and other probes <= 12s; no browser/model/container start",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=REPO / "reports/recovery/NEXUS_RECOVERY_BASELINE_20261009.json")
    parser.add_argument("--skip-supabase", action="store_true", help="skip the bounded read-only SELECT 1")
    args = parser.parse_args()
    result = verify(args.baseline, check_supabase=not args.skip_supabase)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["safe_boot_state"] == "YES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
