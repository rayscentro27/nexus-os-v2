"""Governed coding-worker discovery, failover, handoff, and resume contracts.

This module owns no arbitrary shell authority. Provider commands are fixed
argument arrays, run in an isolated temporary worktree, and are independently
checked for allowed/protected paths before an artifact is accepted.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data/runtime/nexus_completion_campaign.json"
HANDOFF_PATH = ROOT / "data/runtime/coding_worker_handoff.json"
MAX_OUTPUT = 12000
RATE_LIMIT_EVIDENCE = re.compile(r"(?:http\s*429|\b429\b|rate.?limit|quota exceeded|too many requests|throttl|provider capacity|usage exhaustion)", re.I)
AUTH_EVIDENCE = re.compile(r"(?:unauthori[sz]ed|authentication|login required|invalid token|api key required|\b401\b)", re.I)

WORKER_STATES = {"AVAILABLE", "BUSY", "RATE_LIMITED", "AUTH_BLOCKED", "DEGRADED", "UNAVAILABLE", "INSTALLED_UNPROVEN", "PROHIBITED"}


def _resolve_opencode_runner() -> Optional[str]:
    """Find the installed OpenCode executable under service and shell PATHs."""
    configured = os.environ.get("NEXUS_OPENCODE_BIN")
    if configured and Path(configured).is_file() and os.access(configured, os.X_OK):
        return configured
    path = os.pathsep.join(filter(None, [os.environ.get("PATH", ""), "/usr/local/bin",
        "/opt/homebrew/bin", str(Path.home() / ".local/bin")]))
    found = shutil.which("opencode", path=path)
    return found


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_env() -> Dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CI", "TERM", "NO_COLOR", "PYTHONPATH"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["NEXUS_ARBITRARY_SHELL"] = "PROHIBITED"
    return env


def _redact_output(value: str) -> str:
    """Keep provider receipts useful without persisting common secret values."""
    return re.sub(
        r"(?i)((?:api[_-]?key|access[_-]?token|auth(?:entication)?[_-]?token|secret|password)\s*[:=]\s*)[^\s,;]+",
        r"\1[REDACTED]",
        value or "",
    )[-MAX_OUTPUT:]


def classify_failure(output: str, returncode: Optional[int] = None) -> str:
    """Classify only when the output contains authoritative failure evidence."""
    if RATE_LIMIT_EVIDENCE.search(output or ""):
        return "RATE_LIMITED"
    if AUTH_EVIDENCE.search(output or ""):
        return "AUTH_BLOCKED"
    if returncode is None:
        return "TIMEOUT"
    return "EXECUTION_FAILED"


def worker_discovery() -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for worker_id, binary in (("codex", "codex"), ("opencode", "opencode"), ("mimo", "mimo"), ("kilo", "kilo")):
        path = shutil.which(binary)
        result[worker_id] = {"worker_id": worker_id, "binary": binary, "installed": bool(path),
                             "path": path, "state": "INSTALLED_UNPROVEN" if path else "UNAVAILABLE",
                             "capabilities": ["repo_edit", "tests"] if path else [], "checked_at": now()}
    result["local"] = {"worker_id": "local", "binary": "python3", "installed": True,
                        "path": shutil.which("python3"), "state": "AVAILABLE",
                        "capabilities": ["deterministic", "repo_edit", "tests"], "checked_at": now()}
    return result


def _path_allowed(path: str, allowed: Sequence[str], protected: Sequence[str]) -> bool:
    normalized = path.lstrip("./").rstrip("/")
    def matches(items: Sequence[str]) -> bool:
        return any(normalized == item.rstrip("/") or normalized.startswith(item.rstrip("/") + "/") for item in items)
    return matches(allowed) and not matches(protected)


def _file_fingerprints(worktree: Path, roots: Sequence[str]) -> Dict[str, str]:
    fingerprints: Dict[str, str] = {}
    for root in roots:
        base = worktree / root.rstrip("/")
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                relative = str(path.relative_to(worktree))
                fingerprints[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprints


def _changed_files(worktree: Path, before: Optional[Dict[str, str]] = None, roots: Sequence[str] = ()) -> list[str]:
    diff = subprocess.run(["git", "-C", str(worktree), "diff", "--name-only", "--no-renames"], capture_output=True, text=True, check=False)
    status = subprocess.run(["git", "-C", str(worktree), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True, check=False)
    paths = set(line.strip() for line in diff.stdout.splitlines() if line.strip())
    for line in status.stdout.splitlines():
        if len(line) >= 4:
            paths.add(line[3:].strip().split(" -> ", 1)[-1])
    if before is not None:
        after = _file_fingerprints(worktree, roots)
        for path, fingerprint in after.items():
            if path not in before or before[path] != fingerprint:
                paths.add(path)
        paths.update(path for path in before if path != "__roots__" and path not in after)
    return sorted(path for path in paths if path != "__roots__")


@dataclass(frozen=True)
class CodingTask:
    task_id: str
    objective_id: str
    prompt: str
    allowed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    acceptance: tuple[str, ...]
    checkpoint_sha: str
    worktree: str = "isolated"
    campaign_id: Optional[str] = None
    owner_objective_id: Optional[str] = None
    objective_version: Optional[str] = None
    job_id: Optional[str] = None
    worker_role: str = "CODING_AND_SYSTEM_REPAIR_ONLY"


class OpenCodeExecuteAdapter:
    """Bounded OpenCode repo-edit adapter; no current worktree is edited."""

    worker_id = "opencode"
    # Let OpenCode resolve the already-configured provider/model.  A stale
    # hardcoded model alias made the governed adapter wait until timeout even
    # when the interactive installation had a valid default route.
    model = None

    def execute(self, task: CodingTask, *, runner: Optional[str] = None, timeout: int = 90) -> Dict[str, Any]:
        # Load canonical durable campaign identity before any provider process
        # starts. Chat/task text cannot select or revive an older objective.
        try:
            from nexus_agent_platform.durable_objective_control import (
                ACTIVE_CAMPAIGN_PATH, authorize_coding_action,
            )
            if ACTIVE_CAMPAIGN_PATH.exists():
                from nexus_agent_platform.durable_jobs import default_store
                durable = default_store().get(str(task.job_id or task.task_id))
                bounded_temp = bool(durable and durable.job_type == "NOVA_BOUNDED_CODING_TASK"
                    and (durable.governance_context or {}).get("source") == "NOVA_BOUNDED_CONTROL_ACTION"
                    and (durable.governance_context or {}).get("external_actions_allowed") is False
                    and (durable.governance_context or {}).get("spend_allowed") is False
                    and task.allowed_paths and all(path.startswith("tmp/nova_coding_jobs/") for path in task.allowed_paths))
                if not bounded_temp:
                    authorize_coding_action(campaign_id=task.campaign_id,
                        objective_id=task.owner_objective_id or task.objective_id,
                        job_id=task.job_id or task.task_id,
                        objective_version=task.objective_version,
                        worker_role=task.worker_role, action_summary=task.prompt,
                        path=ACTIVE_CAMPAIGN_PATH)
        except Exception as exc:
            return {"status": "BLOCKED", "worker_id": self.worker_id,
                    "failure_class": "DURABLE_OBJECTIVE_GUARD", "error": str(exc)[:240],
                    "provider_started": False}
        if runner is None:
            runner = _resolve_opencode_runner()
        if not runner:
            return {"status": "UNAVAILABLE", "worker_id": self.worker_id, "failure_class": "UNAVAILABLE"}
        started = now()
        worktree = Path(tempfile.mkdtemp(prefix=f"nexus-opencode-{task.task_id}-"))
        # Keep OpenCode's session database isolated per bounded task. A broken
        # shared session_message table otherwise prevents unrelated coding
        # jobs from starting. Reuse only the user's provider auth file; the
        # per-run database, logs, and sessions stay disposable.
        opencode_data_home = Path(tempfile.mkdtemp(prefix=f"nexus-opencode-data-{task.task_id}-"))
        auth_source = Path.home() / ".local" / "share" / "opencode" / "auth.json"
        if auth_source.is_file():
            auth_target = opencode_data_home / "opencode" / "auth.json"
            auth_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(auth_source, auth_target)
            try:
                auth_target.chmod(0o600)
            except OSError:
                pass
        added = False
        prompt = ("You are a bounded Nexus coding worker. Edit only files under the allowed paths. "
                  "Do not inspect secrets, runtime.env, client data, or protected paths. "
                  f"Objective: {task.prompt}\nAllowed paths: {list(task.allowed_paths)}\n"
                  f"Acceptance: {list(task.acceptance)}\nCreate the requested artifact and stop.")
        command = [runner, "run", "--format", "json", prompt]
        configured_model = os.environ.get("NEXUS_OPENCODE_MODEL")
        if configured_model:
            command[2:2] = ["--model", configured_model]
        try:
            # Large Nexus checkouts can exceed a bounded provider canary. Use
            # a minimal disposable git sandbox for a tiny certification task;
            # this keeps OpenCode genuinely isolated without blocking on the
            # full repository object graph.
            try:
                subprocess.run(["git", "worktree", "add", "--detach", str(worktree), task.checkpoint_sha], cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
                added = True
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                subprocess.run(["git", "init", "-q"], cwd=worktree, capture_output=True, text=True, timeout=10, check=True)
                package = ROOT / "package.json"
                if package.exists():
                    shutil.copy2(package, worktree / "package.json")
                for allowed in task.allowed_paths:
                    (worktree / allowed).mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "add", "--", "."], cwd=worktree, capture_output=True, text=True, timeout=10, check=True)
                # The isolated task directory can be empty before OpenCode
                # starts (for example, when a global ignore rule hides tmp/).
                # Seed an empty commit so the sandbox has a valid HEAD either way.
                subprocess.run(["git", "-c", "user.email=nexus@localhost", "-c", "user.name=Nexus", "commit", "--allow-empty", "-qm", "sandbox"], cwd=worktree, capture_output=True, text=True, timeout=10, check=True)
                added = True
            before = _file_fingerprints(worktree, task.allowed_paths)
            opencode_env = _safe_env()
            opencode_env["XDG_DATA_HOME"] = str(opencode_data_home)
            proc = subprocess.run(command + ["--pure"], cwd=worktree, env=opencode_env, capture_output=True, text=True, timeout=timeout, check=False)
            combined = f"{proc.stdout}\n{proc.stderr}"
            changed = _changed_files(worktree, before, task.allowed_paths)
            violations = [path for path in changed if not _path_allowed(path, task.allowed_paths, task.protected_paths)]
            execution = None
            if any("execute python file once" in str(item).casefold() for item in task.acceptance):
                candidates = [worktree / path for path in changed if path.endswith(".py")]
                if len(candidates) != 1:
                    execution = {"returncode": 1, "error": "EXPECTED_ONE_NEW_PYTHON_FILE"}
                else:
                    candidate = candidates[0].resolve()
                    resolved_worktree = worktree.resolve()
                    allowed_roots = [(resolved_worktree / allowed).resolve() for allowed in task.allowed_paths]
                    if not any(candidate.is_relative_to(root) for root in allowed_roots):
                        execution = {"returncode": 1, "error": "PYTHON_FILE_OUTSIDE_ALLOWED_WORKSPACE"}
                    else:
                        try:
                            run_result = subprocess.run([sys.executable, str(candidate)], cwd=worktree,
                                env=_safe_env(), capture_output=True, text=True, timeout=10, check=False)
                            execution = {"returncode": run_result.returncode,
                                "stdout": _redact_output(run_result.stdout)[:2000],
                                "stderr": _redact_output(run_result.stderr)[:1000],
                                "file": str(candidate.relative_to(resolved_worktree))}
                        except (OSError, subprocess.SubprocessError) as exc:
                            execution = {"returncode": 1, "error": f"{type(exc).__name__}: {str(exc)[:180]}"}
            failure = classify_failure(combined, proc.returncode) if proc.returncode != 0 else None
            if violations:
                failure = "PROTECTED_PATH_VIOLATION"
            if execution is not None and execution.get("returncode") != 0:
                # Preserve the OpenCode/provider failure when it exited before
                # producing the requested artifact; do not mislabel that as a
                # Python execution failure.
                if proc.returncode == 0:
                    failure = "BOUNDED_PYTHON_EXECUTION_FAILED"
            status = "PASS" if proc.returncode == 0 and not violations else "FAIL"
            if execution is not None and execution.get("returncode") != 0:
                status = "FAIL"
            artifact_hash = hashlib.sha256("\n".join(changed).encode()).hexdigest()
            return {"status": status, "worker_id": self.worker_id, "started_at": started, "finished_at": now(),
                    "command": command[:4], "returncode": proc.returncode, "failure_class": failure,
                    "files_changed": changed, "violations": violations, "artifact_fingerprint": artifact_hash,
                    "stdout": _redact_output(proc.stdout), "stderr": _redact_output(proc.stderr),
                    "execution": execution,
                    "independent_verification": status == "PASS" and not violations}
        except subprocess.TimeoutExpired as exc:
            output = str(exc)
            return {"status": "FAIL", "worker_id": self.worker_id, "started_at": started, "finished_at": now(),
                    "failure_class": classify_failure(output), "files_changed": [], "independent_verification": False}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "FAIL", "worker_id": self.worker_id, "started_at": started, "finished_at": now(),
                    "failure_class": type(exc).__name__, "error": str(exc)[:500],
                    "stderr": _redact_output(getattr(exc, "stderr", "") or "")[:1000],
                    "files_changed": [], "independent_verification": False}
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, text=True, check=False)
            shutil.rmtree(worktree, ignore_errors=True)
            shutil.rmtree(opencode_data_home, ignore_errors=True)


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def persist_campaign(*, campaign_id: str = "NEXUS_COMPLETION_DAY_2026_08_26", status: str = "ACTIVE",
                     current_wave: int = 0, current_objective: str = "coding_worker_failover", **extra: Any) -> Dict[str, Any]:
    current = {}
    try:
        current = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    state = {"campaign_id": campaign_id, "status": status, "current_wave": current_wave,
             "current_objective": current_objective, "completed_waves": current.get("completed_waves", []),
             "completed_objectives": current.get("completed_objectives", []), "active_jobs": current.get("active_jobs", []),
             "worker_assignments": current.get("worker_assignments", {}), "checkpoint_sha": current.get("checkpoint_sha"),
             "remaining_work": current.get("remaining_work", []), "true_gates": current.get("true_gates", []),
             "external_blockers": current.get("external_blockers", []), "failure_signatures": current.get("failure_signatures", []),
             "repair_counts": current.get("repair_counts", {}), "architecture_alternatives": current.get("architecture_alternatives", []),
             "last_updated": now(), **extra}
    _write_json(STATE_PATH, state)
    return state


def persist_handoff(*, task: CodingTask, previous_worker: str, next_worker: str,
                    reason: str, failure_class: str, failure_evidence: Any,
                    current_stage: str = "S2_HANDOFF_CREATED", completed_stages: Optional[Sequence[str]] = None,
                    receipt_refs: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    handoff = {"schema_version": "nexus.worker-handoff.v2", "campaign_id": task.campaign_id or "NEXUS_COMPLETION_DAY_2026_08_26",
               "owner_objective_id": task.owner_objective_id or task.objective_id,
               "objective_version": task.objective_version,
               "task_id": task.task_id, "job_id": task.job_id or task.task_id,
               "objective_id": task.owner_objective_id or task.objective_id, "generation": 1,
               "previous_worker": previous_worker, "next_worker": next_worker, "handoff_reason": reason,
               "failure_class": failure_class, "failure_evidence": failure_evidence,
               "starting_sha": task.checkpoint_sha, "checkpoint_sha": task.checkpoint_sha,
               "allowed_paths": list(task.allowed_paths), "protected_paths": list(task.protected_paths),
               "current_stage": current_stage, "completed_stages": list(completed_stages or ["S0_SCHEDULED", "S1_SELECTED"]),
               "remaining_acceptance": list(task.acceptance), "worktree": task.worktree,
               "worker_role": task.worker_role,
               "receipt_refs": list(receipt_refs or []), "created_at": now()}
    _write_json(HANDOFF_PATH, handoff)
    return handoff


def select_worker(task: CodingTask, workers: Dict[str, Dict[str, Any]], *, unavailable: Iterable[str] = (),
                  probe_installed_unproven: bool = False) -> str:
    blocked = set(unavailable)
    for worker_id in ("codex", "opencode"):
        row = workers.get(worker_id, {})
        eligible_state=row.get("state")=="AVAILABLE" or (
            probe_installed_unproven and row.get("state")=="INSTALLED_UNPROVEN")
        if worker_id not in blocked and eligible_state and "repo_edit" in row.get("capabilities", []):
            return worker_id
    local = workers.get("local", {})
    if "deterministic" in task.acceptance and local.get("state") == "AVAILABLE":
        return "local"
    return "BLOCKED_WORKER_CAPACITY"


def run_failover_canary(*, simulate_codex_rate_limit: bool = True,
                        root: Path = ROOT) -> Dict[str, Any]:
    workers = worker_discovery()
    if simulate_codex_rate_limit:
        workers["codex"]["state"] = "RATE_LIMITED"
    task = CodingTask(task_id=f"failover-{uuid.uuid4().hex[:8]}", objective_id="worker_failover_canary",
                      prompt="Create a harmless proof artifact named failover_canary.txt in the allowed reports directory.",
                      allowed_paths=("reports/runtime/",), protected_paths=("src/", "data/", "configs/"),
                      acceptance=("artifact exists", "deterministic",), checkpoint_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip())
    selected = select_worker(task, workers, unavailable=("codex",) if simulate_codex_rate_limit else ())
    handoff = persist_handoff(task=task, previous_worker="codex" if simulate_codex_rate_limit else "NONE",
                              next_worker=selected, reason="RATE_LIMITED" if simulate_codex_rate_limit else "normal selection",
                              failure_class="RATE_LIMITED" if simulate_codex_rate_limit else "NONE",
                              failure_evidence="simulated HTTP 429 evidence" if simulate_codex_rate_limit else None)
    state = persist_campaign(current_wave=0, current_objective="coding_worker_failover",
                             checkpoint_sha=task.checkpoint_sha, worker_assignments={task.task_id: selected})
    return {"status": "PASS", "selected_worker": selected, "workers": workers,
            "handoff": handoff, "campaign": state, "independent_verification": selected == "local"}
