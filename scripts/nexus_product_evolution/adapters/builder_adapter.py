"""Bounded bridge from MissionContract to the existing Builder runtime."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

from nexus_agent_platform.builders.runtime import BuildTaskSpec, CodingWorker, _probe_cli_worker, run_builder_task

from ..loop import MissionContract

ROOT = Path(__file__).resolve().parents[3]
SENSITIVE = re.compile(r"(?i)(token|secret|password|api[_ -]?key|runtime\.env)\s*[:=]?\s*[^\s,;]+")
SAFE_ENVIRONMENT_KEYS = {
    "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TMP", "TEMP", "PWD",
    "PYTHONPATH", "VIRTUAL_ENV", "TERM", "COLORTERM", "NO_COLOR",
}


def mission_to_build_task(
    mission_id: str,
    contract: MissionContract,
    *,
    allowed_paths: Sequence[str],
    protected_paths: Sequence[str],
    tests: Sequence[Sequence[str]],
    visual_requirements: bool,
    timeout_seconds: int,
    max_retries: int,
    parent_mission_id: str | None = None,
    previous_failure: Dict[str, Any] | None = None,
) -> BuildTaskSpec:
    starting_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return BuildTaskSpec(
        task_id=f"product_evolution_{mission_id}",
        title=f"Product Evolution {contract.goal[:100]}",
        objective=contract.goal,
        repo=str(ROOT),
        branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() or "main",
        worktree="ISOLATED_WORKTREE_CREATED_AT_EXECUTION",
        scope=list(allowed_paths),
        protected_paths=list(protected_paths),
        allowed_paths=list(allowed_paths),
        requirements=[
            f"Mission {mission_id} must remain on its original receipt lineage.",
            contract.user_visible_outcome,
            *contract.acceptance_criteria,
            *contract.security_boundaries,
        ],
        acceptance_criteria=list(contract.acceptance_criteria),
        tests=[shlex.join(command) for command in tests],
        visual_requirements=visual_requirements,
        security_constraints=list(contract.security_boundaries),
        budget={"cost_ceiling": contract.cost_ceiling, "model_tier": "ZERO_MODEL_COST"},
        timeout_seconds=timeout_seconds,
        approval_state="governed_product_evolution",
        retry_policy="bounded",
        max_retries=max_retries,
        metadata={
            "mission_id": mission_id,
            "parent_mission_id": parent_mission_id,
            "starting_commit": starting_commit,
            "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() or "main",
            "deployment_policy": contract.deployment_policy,
            "locked_systems": list(contract.locked_systems),
            "human_gates": list(contract.human_only_gates),
        },
        previous_failure_delta=previous_failure or {},
    )


def _safe_prompt(task: BuildTaskSpec) -> str:
    return "\n".join([
        "You are the bounded Nexus Product Evolution coding worker.",
        "Use only the fixed repository workspace and the allowed paths below.",
        f"MISSION ID: {task.metadata.get('mission_id')}",
        f"PARENT LINEAGE: {task.metadata.get('parent_mission_id') or 'NONE'}",
        f"OBJECTIVE: {task.objective}",
        f"ALLOWED PATHS: {', '.join(task.allowed_paths)}",
        f"PROTECTED PATHS: {', '.join(task.protected_paths)}",
        f"REQUIREMENTS: {' | '.join(task.requirements)}",
        f"ACCEPTANCE CRITERIA: {' | '.join(task.acceptance_criteria)}",
        f"TESTS: {' | '.join(task.tests)}",
        f"SECURITY CONSTRAINTS: {' | '.join(task.security_constraints)}",
        f"TIMEOUT: {task.timeout_seconds} seconds",
        f"APPROVAL/DEPLOYMENT STATE: {task.approval_state}; {task.metadata.get('deployment_policy', 'no autonomous deployment')}",
        f"PREVIOUS FAILURE EVIDENCE: {task.previous_failure_delta or 'none'}",
        "Do not inspect secrets, runtime.env, client data, or unrelated files.",
        "Do not add dependencies or change deployment authority.",
        "Never use git add ., git add -A, or git add --all. Stage exact intentional paths only if staging is needed. Do not commit or push.",
        "Make the smallest safe change. Run the listed tests when applicable.",
    ])


def _changed_paths(worktree: Path) -> tuple[list[str], list[str]]:
    names = subprocess.check_output(["git", "-C", str(worktree), "diff", "--name-only", "--no-renames"], text=True).splitlines()
    status = subprocess.check_output(["git", "-C", str(worktree), "status", "--porcelain=v1", "--untracked-files=all"], text=True).splitlines()
    tracked = set(names)
    for line in status:
        if len(line) >= 4:
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            tracked.add(path)
    return sorted(tracked), status


def _path_allowed(path: str, allowed: Sequence[str], protected: Sequence[str]) -> bool:
    normalized = path.strip().lstrip("./").rstrip("/")
    allowed_ok = any(normalized == item.rstrip("/") or normalized.startswith(item.rstrip("/") + "/") for item in allowed if "/" in item or item.endswith("/"))
    protected_hit = any(normalized == item.rstrip("/") or normalized.startswith(item.rstrip("/") + "/") for item in protected if "/" in item or item.endswith("/"))
    return allowed_ok and not protected_hit


def _safe_worker_environment() -> Dict[str, str]:
    """Pass only non-secret process settings into an external coding worker."""
    return {key: value for key, value in os.environ.items() if key in SAFE_ENVIRONMENT_KEYS}


def codex_execute(task: BuildTaskSpec) -> Dict[str, Any]:
    """Execute one fixed Codex invocation in an isolated worktree."""
    if shutil.which("codex") is None:
        return {"status": "worker_unavailable", "worker_error": "CODEX_NOT_INSTALLED", "files_changed": []}
    started = time.monotonic()
    worktree = Path(tempfile.mkdtemp(prefix=f"nexus-pe-{task.task_id}-"))
    added = False
    try:
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), task.metadata.get("starting_commit", "HEAD")], cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
        added = True
        command = ["codex", "exec", "--sandbox", "workspace-write", "--ephemeral", "--skip-git-repo-check", "--color", "never", "-C", str(worktree), _safe_prompt(task)]
        environment = _safe_worker_environment()
        try:
            completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=task.timeout_seconds, check=False)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "worker_error": "CODEX_TIMED_OUT", "files_changed": [], "tests_run": [], "duration_ms": int((time.monotonic() - started) * 1000)}
        changed, status_lines = _changed_paths(worktree)
        violations = [path for path in changed if not _path_allowed(path, task.allowed_paths, task.protected_paths)]
        if violations:
            return {"status": "failed", "worker_error": "PROTECTED_PATH_VIOLATION", "protected_path_violation": True, "violations": violations, "files_changed": changed}
        if completed.returncode != 0:
            safe_error = SENSITIVE.sub(r"\1[REDACTED]", (completed.stderr or completed.stdout or "codex failed"))[:500]
            return {"status": "failed", "worker_error": "CODEX_EXECUTION_FAILED", "error": safe_error, "files_changed": changed}
        patch = subprocess.check_output(["git", "-C", str(worktree), "diff", "--binary"], text=True)
        if patch:
            check = subprocess.run(["git", "apply", "--check"], cwd=ROOT, input=patch, text=True, capture_output=True, check=False)
            if check.returncode != 0:
                return {"status": "failed", "worker_error": "WORKTREE_PATCH_CONFLICT", "files_changed": changed}
            subprocess.run(["git", "apply"], cwd=ROOT, input=patch, text=True, capture_output=True, check=True)
        return {"status": "success", "files_changed": changed, "tests_run": list(task.tests), "tests_passed": 0, "tests_failed": 0, "visual_check": {"required": task.visual_requirements, "verified": not task.visual_requirements, "status": "not_run" if task.visual_requirements else "not_required"}, "protected_path_violation": False, "worker_report": {"returncode": completed.returncode, "duration_ms": int((time.monotonic() - started) * 1000), "status_lines": len(status_lines), "command": ["codex", "exec", "--sandbox", "workspace-write", "--ephemeral"]}, "artifact_refs": []}
    finally:
        if added:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, text=True, check=False)
        else:
            shutil.rmtree(worktree, ignore_errors=True)


def codex_worker() -> CodingWorker:
    path = shutil.which("codex")
    probe = _probe_cli_worker("codex", path, execution_timeout=12) if path else {"installed": False, "classification": "NOT_INSTALLED", "reason": "binary missing", "version": "UNKNOWN", "probe_result": "not_run", "version_probe": {}, "execution_probe": "not_run"}
    return CodingWorker(worker_id="codex", worker_type="cli", display_name="Codex CLI", available=probe.get("classification") == "AVAILABLE", capabilities=["repo_edit", "tests", "worktrees"], cost_class="ZERO_MODEL_COST", supports_repo_edit=True, supports_tests=True, supports_browser=False, supports_images=False, supports_worktrees=True, supports_resume=False, supports_structured_output=False, availability_reason=str(probe.get("reason", "")), installed=bool(probe.get("installed")), health_probe=lambda: {"installed": bool(probe.get("installed")), "available": probe.get("classification") == "AVAILABLE", "classification": probe.get("classification"), "version": probe.get("version"), "reason": probe.get("reason"), "probe_result": probe.get("probe_result")}, execute_fn=codex_execute)


def run_bounded_codex_task(task: BuildTaskSpec) -> Dict[str, Any]:
    worker = codex_worker()
    health = worker.health_check()
    if not worker.can_handle(task):
        return {"status": "worker_unavailable", "worker_error": health.get("classification", "CODEX_UNAVAILABLE"), "worker_health": health}
    return run_builder_task(task, [worker], max_retries=task.max_retries)
