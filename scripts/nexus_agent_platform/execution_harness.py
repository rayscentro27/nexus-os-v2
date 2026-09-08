"""Small, governed execution-harness primitives shared by Nexus workers.

This module deliberately reports capability readiness, not permission to run
arbitrary commands.  Executors still own their fixed command allowlists.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _version(executable: str) -> str | None:
    try:
        p = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=5, check=False)
        return (p.stdout or p.stderr).strip().splitlines()[0] if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def worker_environment_preflight(action: str, root: Path) -> dict[str, Any]:
    """Check the actual worker environment using absolute executable paths."""
    root = root.resolve()
    required = {"git": True, "node": action.startswith("engineering."), "npm": action.startswith("engineering.")}
    executables: dict[str, Any] = {}
    for name, needed in required.items():
        path = shutil.which(name)
        executables[name] = {"required": needed, "available": bool(path), "path": path, "version": _version(path) if path else None}
    node_modules = (root / "node_modules").is_dir()
    command_policy = {"allowlisted_project_commands": ["git status", "git diff", "git log", "npm test", "npm run build"],
                      "arbitrary_shell": False, "production_deploy": False, "external_mutation": False}
    values = {"action": action, "cwd": str(root), "user": os.getuid(),
              "python": os.environ.get("PYTHON", ""), "path": os.environ.get("PATH", ""),
              "executables": executables, "project_node_modules": node_modules,
              "repo_readable": os.access(root, os.R_OK), "repo_writable": os.access(root, os.W_OK),
              "command_policy": command_policy}
    fingerprint = hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()[:20]
    missing = [name for name, info in executables.items() if info["required"] and not info["available"]]
    values.update({"ready": not missing and values["repo_readable"] and values["repo_writable"],
                   "missing": missing, "environment_fingerprint": fingerprint,
                   "failure_class": "COMMAND_NOT_FOUND" if missing else None})
    return values


def capability_readiness(action: str, root: Path) -> dict[str, Any]:
    preflight = worker_environment_preflight(action, root)
    rows = []
    for name in ("repository_read", "repository_task_scoped_write", "git", "node", "npm", "project_dependencies"):
        available = {"repository_read": preflight["repo_readable"], "repository_task_scoped_write": preflight["repo_writable"],
                     "git": preflight["executables"]["git"]["available"], "node": preflight["executables"]["node"]["available"],
                     "npm": preflight["executables"]["npm"]["available"], "project_dependencies": preflight["project_node_modules"]}[name]
        rows.append({"capability": name, "system_has": available, "worker_accessible": available, "unattended_runtime": available, "authorized": True, "real_tested": False, "status": "READY" if available else "MISSING"})
    return {"action": action, "ready": preflight["ready"], "preflight": preflight, "matrix": rows}


def classify_execution_failure(error: BaseException | str) -> str:
    text = str(error).lower()
    if "no such file" in text or "not found" in text:
        return "COMMAND_NOT_FOUND"
    if "timeout" in text:
        return "TRANSIENT_PROVIDER_FAILURE"
    if "permission" in text:
        return "PERMISSION_FAILURE"
    return "IMPLEMENTATION_FAILURE"


def material_delta(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    delta = []
    for key in ("strategy_fingerprint", "environment_fingerprint", "tools_used", "evidence"):
        if previous.get(key) != current.get(key):
            delta.append({"strategy_fingerprint": "NEW_STRATEGY", "environment_fingerprint": "NEW_ENVIRONMENT", "tools_used": "NEW_TOOL", "evidence": "NEW_EVIDENCE"}[key])
    return delta
