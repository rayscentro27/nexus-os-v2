"""Read-only local environment drift check; never enables or starts services."""
from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(args: list[str], timeout: float = 5.0) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _git_status_snapshot(repo_root: Path) -> tuple[str, str]:
    """Return Git status and an explicit availability state.

    A timed out/failed Git command must never look like a clean empty tree.
    The repository can be large on this host, so this read-only operation has
    a bounded 30 second window and reports unavailability distinctly.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--untracked-files=normal"],
            capture_output=True, text=True, timeout=30.0, check=False,
        )
    except subprocess.TimeoutExpired:
        return "UNAVAILABLE_TIMEOUT", ""
    except OSError:
        return "UNAVAILABLE_EXEC", ""
    if result.returncode != 0:
        return f"UNAVAILABLE_EXIT_{result.returncode}", ""
    return "AVAILABLE", result.stdout


def _plist_metadata(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as stream:
            data = plistlib.load(stream)
    except Exception as exc:
        # Invalid Nexus-named launch definitions are recorded as inert evidence;
        # do not auto-rewrite a plist because that could make a stale launcher
        # loadable during safe mode.
        if "nexus" not in path.name.lower() and "hermes" not in path.name.lower():
            return None
        return {
            "path": str(path),
            "label": "UNPARSEABLE",
            "program": "",
            "arguments": [],
            "run_at_load": False,
            "keep_alive": False,
            "start_interval": None,
            "parse_status": "INVALID_PLIST",
            "parse_error_class": type(exc).__name__,
            "sha256": _file_sha256(path),
        }
    if not isinstance(data, dict):
        return {
            "path": str(path), "label": "INVALID_ROOT_TYPE", "program": "", "arguments": [],
            "run_at_load": False, "keep_alive": False, "start_interval": None,
            "parse_status": "INVALID_PLIST_ROOT", "sha256": _file_sha256(path),
        }
    raw_arguments = [str(value) for value in data.get("ProgramArguments", [])]
    safe_arguments = []
    redact_next = False
    for value in raw_arguments:
        if redact_next:
            safe_arguments.append("<redacted>")
            redact_next = False
            continue
        if re.search(r"token|password|secret|api[-_]?key|credential|private[-_]?key", value, re.I):
            if "=" in value:
                safe_arguments.append(value.split("=", 1)[0] + "=<redacted>")
            else:
                safe_arguments.append(value)
                redact_next = True
        else:
            safe_arguments.append(value)
    return {
        "path": str(path),
        "label": data.get("Label", ""),
        "program": data.get("Program", ""),
        "arguments": safe_arguments,
        "run_at_load": bool(data.get("RunAtLoad", False)),
        "keep_alive": bool(data.get("KeepAlive", False)),
        "start_interval": data.get("StartInterval"),
        "parse_status": "VALID",
    }


def collect_local_state(repo_root: Path, launch_agents: Path | None = None) -> dict[str, Any]:
    launch_roots = [launch_agents] if launch_agents else [
        Path.home() / "Library/LaunchAgents",
        Path("/Library/LaunchAgents"),
        Path("/Library/LaunchDaemons"),
    ]
    nexus_plists = []
    for launch_root in launch_roots:
        if launch_root and launch_root.is_dir():
            for path in sorted(launch_root.glob("*.plist")):
                metadata = _plist_metadata(path)
                if metadata and any("nexus" in str(value).lower() for value in metadata.values()):
                    nexus_plists.append(metadata)

    cron = _run(["crontab", "-l"])
    root_cron = _run(["sudo", "-n", "crontab", "-l", "-u", "root"])
    listeners = _run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-Fpnc"], timeout=8.0)
    # Keep command lines in memory only so scripts launched through Python can
    # be recognized. Reports contain hashes only, never command arguments.
    processes = _run(["ps", "-axo", "pid=,ppid=,command="])
    process_names = _run(["ps", "-axo", "comm"])
    launchctl = _run(["launchctl", "list"], timeout=8.0)
    stable_launch_labels = sorted({
        line.split()[-1] for line in launchctl.splitlines()
        if line.split() and line.split()[-1].startswith(("com.nexus.", "com.hermes.", "com.openclaw."))
    })
    git_status_state, git_status = _git_status_snapshot(repo_root)
    pm2_dump_path = Path.home() / ".pm2/dump.pm2"
    pm2_state = "UNREADABLE_OR_ABSENT"
    if pm2_dump_path.is_file():
        try:
            rows = json.loads(pm2_dump_path.read_text(encoding="utf-8"))
            pm2_state = json.dumps([
                {key: row.get(key) for key in ("name", "pm_exec_path", "exec_mode", "autorestart", "instances")}
                for row in rows if isinstance(row, dict)
            ], sort_keys=True)
        except (OSError, ValueError, TypeError):
            pm2_state = "UNREADABLE"
    hermes_cron_path = Path.home() / ".hermes/cron/jobs.json"
    hermes_cron = ""
    if hermes_cron_path.is_file():
        try:
            rows = json.loads(hermes_cron_path.read_text(encoding="utf-8"))
            hermes_cron = json.dumps([
                {key: row.get(key) for key in ("id", "name", "enabled", "schedule")}
                for row in rows if isinstance(row, dict)
            ], sort_keys=True)
        except (OSError, ValueError, TypeError):
            hermes_cron = "UNREADABLE"
    openclaw_cron = ""
    for openclaw_cron_path in (
        Path.home() / ".openclaw/cron/jobs.json",
        Path.home() / ".openclaw/cron.json",
    ):
        if openclaw_cron_path.is_file():
            try:
                raw_rows = json.loads(openclaw_cron_path.read_text(encoding="utf-8"))
                if isinstance(raw_rows, dict):
                    raw_rows = raw_rows.get("jobs", [])
                openclaw_cron = json.dumps([
                    {key: row.get(key) for key in ("id", "name", "enabled", "schedule")}
                    for row in raw_rows if isinstance(row, dict)
                ], sort_keys=True)
            except (OSError, ValueError, TypeError):
                openclaw_cron = "UNREADABLE"
            break
    docker = _run(["docker", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Status}}"], timeout=8.0)
    podman = _run(["podman", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Status}}"], timeout=8.0)
    try:
        branch = _run(["git", "-C", str(repo_root), "branch", "--show-current"]).strip()
        commit = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD"]).strip()
        commit_parent = _run(["git", "-C", str(repo_root), "rev-parse", "HEAD^"], timeout=4.0).strip()
        commit_subject = _run(["git", "-C", str(repo_root), "log", "-1", "--format=%s"], timeout=4.0).strip()
    except OSError:
        branch, commit, commit_parent, commit_subject = "", "", "", ""
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "repository": {"path": str(repo_root), "branch": branch, "commit": commit,
                       "commit_parent": commit_parent, "commit_subject": commit_subject},
        "working_tree_status": git_status_state,
        "working_tree_sha256": hashlib.sha256(git_status.encode()).hexdigest(),
        "working_tree_dirty": bool(git_status.strip()) if git_status_state == "AVAILABLE" else None,
        "launch_agents": nexus_plists,
        "user_cron_sha256": hashlib.sha256(cron.encode()).hexdigest() if cron else None,
        "root_cron_sha256": hashlib.sha256(root_cron.encode()).hexdigest() if root_cron else None,
        # The full launchctl table includes volatile Apple jobs and status
        # columns. Only Nexus-owned labels are part of this baseline.
        "loaded_launchd_sha256": hashlib.sha256("\n".join(stable_launch_labels).encode()).hexdigest()
            if launchctl else None,
        "hermes_schedule_sha256": hashlib.sha256(hermes_cron.encode()).hexdigest() if hermes_cron else None,
        "openclaw_schedule_sha256": hashlib.sha256(openclaw_cron.encode()).hexdigest() if openclaw_cron else None,
        "pm2_saved_state_sha256": hashlib.sha256(pm2_state.encode()).hexdigest(),
        "container_names_sha256": hashlib.sha256((docker + "\n" + podman).encode()).hexdigest() if docker or podman else None,
        "listener_snapshot_sha256": hashlib.sha256(listeners.encode()).hexdigest() if listeners else None,
        "process_name_snapshot_sha256": hashlib.sha256(processes.encode()).hexdigest() if processes else None,
        # Executable names avoid transient shell command text. The recovery
        # verifier separately checks Python-launched Nexus worker paths.
        "nexus_process_name_sha256": hashlib.sha256("\n".join(
            line for line in process_names.splitlines()
            if re.search(r"(?:^|/)(?:nexus(?:[-_].*)?|hermes(?:[-_].*)?|wp9(?:[-_].*)?)$", line.strip(), re.I)
        ).encode()).hexdigest(),
        "browser_automation_process_name_sha256": hashlib.sha256("\n".join(
            line for line in processes.splitlines()
            if re.search(r"playwright|chromium|puppeteer|ffmpeg|ollama", line, re.I)
        ).encode()).hexdigest(),
        "provider_caller_registry_sha256": _file_sha256(repo_root / "reports/remediation/provider_caller_registry_20261009.json"),
        "secret_consumer_registry_sha256": _file_sha256(repo_root / "reports/remediation/local_secret_consumer_registry_20261009.json"),
        "environment_registry_sha256": _file_sha256(repo_root / "configs/environment_lifecycle_registry.json"),
        "python_runtime": {"executable": sys.executable, "version": sys.version.split()[0]},
        "runtime_limits_sha256": _file_sha256(repo_root / "configs/host_resource_governor.json"),
        "scheduler_dispatcher_processes": sorted({
            line.strip().split()[-1] for line in launchctl.splitlines()
            if re.search(r"nexus.*(?:scheduler|dispatcher)|(?:scheduler|dispatcher).*nexus", line, re.I)
        }),
        "monitor_authority": {
            "can_create_business_work": False,
            "can_call_paid_provider": False,
            "can_enable_runtime": False,
            "can_restart_services": False,
        },
        "containment_policy": "REPORT_ONLY; never start, stop, enable, disable, or mutate remote services",
    }


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    differences = []
    expected_repo = expected.get("repository")
    actual_repo = actual.get("repository")
    if isinstance(expected_repo, dict) and isinstance(actual_repo, dict):
        for field in ("path", "branch"):
            if field in expected_repo and expected_repo.get(field) != actual_repo.get(field):
                differences.append({"field": f"repository.{field}", "expected": expected_repo.get(field), "actual": actual_repo.get(field)})
        if "commit" in expected_repo and expected_repo.get("commit") != actual_repo.get("commit"):
            freeze = expected.get("authorized_freeze_commit")
            allowed = (
                isinstance(freeze, dict)
                and freeze.get("parent_commit") == expected_repo.get("commit")
                and freeze.get("subject") == actual_repo.get("commit_subject")
                and freeze.get("parent_commit") == actual_repo.get("commit_parent")
            )
            if not allowed:
                differences.append({"field": "repository.commit", "expected": expected_repo.get("commit"), "actual": actual_repo.get("commit")})
    elif expected_repo != actual_repo and "repository" in expected:
        differences.append({"field": "repository", "expected": expected_repo, "actual": actual_repo})
    for key in (
        "working_tree_status", "working_tree_sha256", "working_tree_dirty",
        "launch_agents", "user_cron_sha256", "root_cron_sha256",
        "loaded_launchd_sha256", "hermes_schedule_sha256", "openclaw_schedule_sha256",
        "pm2_saved_state_sha256", "container_names_sha256", "listener_snapshot_sha256",
        "nexus_process_name_sha256", "browser_automation_process_name_sha256",
        "provider_caller_registry_sha256", "secret_consumer_registry_sha256",
        "environment_registry_sha256", "runtime_limits_sha256", "scheduler_dispatcher_processes",
    ):
        if key in expected and expected.get(key) != actual.get(key):
            differences.append({"field": key, "expected": expected.get(key), "actual": actual.get(key)})
    return {
        "status": "DRIFT_DETECTED" if differences else "MATCH",
        "differences": differences,
        "action": "RECORD_INCIDENT_AND_FLAG_OPERATOR" if differences else "NO_ACTION",
        "incident": {"kind": "ENVIRONMENT_DRIFT", "state": "OPEN"} if differences else None,
        "notification": "LOCAL_REPORT_ONLY",
        "safe_containment": "NONE_CONFIGURED",
        "autonomous_enablement": False,
        "can_create_business_work": False,
        "can_call_paid_provider": False,
        "can_enable_runtime": False,
        "can_restart_services": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    expected = json.loads(args.baseline.read_text(encoding="utf-8"))
    actual = collect_local_state(args.repo_root)
    result = {"expected_baseline_id": expected.get("baseline_id"), "actual": actual, "comparison": compare(expected.get("state", {}), actual)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["comparison"]["status"], "difference_count": len(result["comparison"]["differences"])}))
    return 1 if result["comparison"]["status"] == "DRIFT_DETECTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
