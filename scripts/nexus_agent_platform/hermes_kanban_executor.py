"""Governed Nexus -> Oracle Hermes Kanban execution adapter.

Nexus owns the task contract and verification. Hermes owns task lifecycle,
claims, skills, tools, and review. The transport is deliberately narrow: it
only invokes the Hermes CLI inside the already-running, protected container.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HermesKanbanExecutionError(RuntimeError):
    pass


ALLOWED_PROFILES = {"nexus_orchestrator_test", "nexus_engineer_test", "nexus_research_test", "nexus_review_test", "nova_nexus"}
ALLOWED_SKILLS = {"research-intelligence", "repo-intelligence", "software-engineering", "test-debugging", "worktree-safety", "sdlc-review", "codebase-inspection"}
HERMES_SKILL_ALIASES = {"research-intelligence": "sdlc-review", "repo-intelligence": "codebase-inspection", "software-engineering": "codebase-inspection"}


def _validate(spec: dict[str, Any]) -> None:
    required = ("goal_id", "criterion_id", "task_id", "task_requirements")
    missing = [key for key in required if spec.get(key) is None or spec.get(key) == ""]
    if missing:
        raise HermesKanbanExecutionError("missing task fields: " + ",".join(missing))
    profile = spec.get("profile_requirements") or spec.get("profile") or "nexus_research_test"
    if profile not in ALLOWED_PROFILES:
        raise HermesKanbanExecutionError("profile is not allowlisted")
    skills = spec.get("skill_requirements") or spec.get("skills") or []
    if any(skill not in ALLOWED_SKILLS for skill in skills):
        raise HermesKanbanExecutionError("skill is not allowlisted")
    if spec.get("authority_class", "INTERNAL_SAFE") != "INTERNAL_SAFE":
        raise HermesKanbanExecutionError("only INTERNAL_SAFE Hermes tasks are routable")


def _ssh_runner(command: str, timeout: float) -> dict[str, Any]:
    key = os.path.expanduser(os.getenv("NEXUS_ORACLE_SSH_KEY", "~/.ssh/oracle_vm"))
    host = os.getenv("NEXUS_ORACLE_SSH_HOST", "161.153.40.41")
    user = os.getenv("NEXUS_ORACLE_SSH_USER", "opc")
    result = subprocess.run(
        ["ssh", "-i", key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", f"{user}@{host}", command],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise HermesKanbanExecutionError(f"Oracle Hermes command failed ({result.returncode})")
    try:
        value = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise HermesKanbanExecutionError("Oracle Hermes returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise HermesKanbanExecutionError("Oracle Hermes returned non-object JSON")
    return value


def _cli_command(args: list[str]) -> str:
    """Build only allowlisted Hermes CLI commands; task text is quoted."""
    safe = ["podman", "exec", "--user", "hermes", "nexus-hermes-0206", "/opt/hermes/.venv/bin/hermes", "kanban", *args]
    return " ".join(shlex.quote(str(item)) for item in safe)


def execute_with_hermes_kanban(task_spec: dict[str, Any], *, runner: Callable[[str, float], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Execute one governed task through the normal Oracle Hermes surface."""
    _validate(task_spec)
    runner = runner or _ssh_runner
    execution_id = f"nexus-hermes-exec-{uuid.uuid4().hex}"
    profile = task_spec.get("profile_requirements") or task_spec.get("profile") or "nexus_research_test"
    skills = list(task_spec.get("skill_requirements") or task_spec.get("skills") or [])
    hermes_skills = list(dict.fromkeys(HERMES_SKILL_ALIASES.get(skill, skill) for skill in skills))
    title = str(task_spec.get("title") or task_spec["criterion_id"])[:180]
    body = {
        "nexus_execution_id": execution_id,
        "goal_id": task_spec["goal_id"], "criterion_id": task_spec["criterion_id"],
        "task_id": task_spec["task_id"], "task_requirements": task_spec["task_requirements"],
        "authority_class": "INTERNAL_SAFE", "verification_expectations": task_spec.get("verification_expectations", {}),
        "instruction": task_spec.get("instruction") or "Perform the bounded task and report concrete evidence; do not claim criterion completion.",
    }
    max_runtime = int(task_spec.get("time_budget", 90))
    started = _now()
    create_args = ["create", title, "--json", "--body", json.dumps(body, separators=(",", ":")), "--assignee", profile, "--workspace", "scratch", "--max-runtime", str(max_runtime)]
    for skill in hermes_skills:
        create_args.extend(["--skill", skill])
    try:
        created = runner(_cli_command(create_args), 20)
        kanban_id = str(created.get("id") or created.get("task_id") or created.get("task", {}).get("id") or "")
        if not kanban_id:
            raise HermesKanbanExecutionError("Hermes task create returned no task id")
        runner(_cli_command(["dispatch", "--max", "1", "--json"]), min(30, max_runtime))
        deadline = time.monotonic() + max_runtime + 15
        latest: dict[str, Any] = created
        while time.monotonic() < deadline:
            latest = runner(_cli_command(["show", kanban_id, "--json"]), 20)
            status = str(latest.get("task", {}).get("status") or latest.get("status") or "").upper()
            if status in {"COMPLETED", "COMPLETE", "DONE", "FAILED", "BLOCKED", "REVIEW"}:
                break
            time.sleep(2)
        # One final read ensures a timeout/reclaim event is reflected rather
        # than returning the last in-flight snapshot as if it were progress.
        if str(latest.get("task", {}).get("status") or latest.get("status") or "").upper() in {"RUNNING", "READY", "TODO"}:
            latest = runner(_cli_command(["show", kanban_id, "--json"]), 20)
        status = str(latest.get("task", {}).get("status") or latest.get("status") or "UNKNOWN").upper()
        runs = latest.get("runs") or []
        last_run = runs[-1] if isinstance(runs, list) and runs else {}
        run_error = last_run.get("error") if isinstance(last_run, dict) else None
        if status not in {"COMPLETED", "COMPLETE", "DONE", "REVIEW"}:
            if "timed_out" in str(last_run.get("status", "")) or "elapsed" in str(run_error):
                error_class = "MODEL_RESPONSE_TIMEOUT"
            elif "crashed" in str(last_run.get("status", "")):
                error_class = "WORKER_PROCESS_CRASH"
            else:
                error_class = "RESULT_RETURN_TIMEOUT" if status == "UNKNOWN" else "WORKER_FAILED"
        else:
            error_class = "NONE"
        result = latest.get("task", {}).get("result") or latest.get("result") or latest.get("output") or latest.get("comment") or latest.get("latest_summary")
        return {
            "schema_version": "nexus.hermes-kanban-execution.v1", "execution_id": execution_id,
            "kanban_task_id": kanban_id, "goal_id": task_spec["goal_id"], "criterion_id": task_spec["criterion_id"],
            "profile": profile, "skills": hermes_skills, "nexus_skills_requested": skills, "tools": latest.get("tools", []), "clis": latest.get("clis", []),
            "artifacts": latest.get("artifacts", []), "result": result, "review_result": latest.get("review_result"),
            "status": status, "material_delta": bool(result or latest.get("artifacts")),
            "evidence": latest.get("evidence", result), "error_class": error_class,
            "run_error": run_error, "recovery_hint": "verify criterion; reselect with material delta" if error_class != "NONE" else "NEXUS_VERIFIER",
            "started_at": started, "completed_at": _now(), "transport": "ORACLE_SSH_PODMAN_HERMES",
        }
    except (OSError, subprocess.SubprocessError, HermesKanbanExecutionError) as exc:
        return {"schema_version": "nexus.hermes-kanban-execution.v1", "execution_id": execution_id,
                "goal_id": task_spec["goal_id"], "criterion_id": task_spec["criterion_id"], "status": "FAILED",
                "error_class": type(exc).__name__, "error": str(exc), "material_delta": False,
                "started_at": started, "completed_at": _now(), "transport": "ORACLE_SSH_PODMAN_HERMES"}
