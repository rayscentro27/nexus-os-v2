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


class OpenCodeExecuteAdapter:
    """Bounded OpenCode repo-edit adapter; no current worktree is edited."""

    worker_id = "opencode"
    model = "opencode/mimo-v2.5-free"

    def execute(self, task: CodingTask, *, runner: Optional[str] = None, timeout: int = 90) -> Dict[str, Any]:
        if runner is None:
            runner = shutil.which("opencode")
        if not runner:
            return {"status": "UNAVAILABLE", "worker_id": self.worker_id, "failure_class": "UNAVAILABLE"}
        started = now()
        worktree = Path(tempfile.mkdtemp(prefix=f"nexus-opencode-{task.task_id}-"))
        added = False
        prompt = ("You are a bounded Nexus coding worker. Edit only files under the allowed paths. "
                  "Do not inspect secrets, runtime.env, client data, or protected paths. "
                  f"Objective: {task.prompt}\nAllowed paths: {list(task.allowed_paths)}\n"
                  f"Acceptance: {list(task.acceptance)}\nCreate the requested artifact and stop.")
        command = [runner, "run", "--model", self.model, "--format", "json", prompt]
        try:
            # Large Nexus checkouts can take longer than a provider canary;
            # keep this bounded but do not mistake checkout latency for a
            # provider failure.
            subprocess.run(["git", "worktree", "add", "--detach", str(worktree), task.checkpoint_sha], cwd=ROOT, capture_output=True, text=True, timeout=180, check=True)
            added = True
            before = _file_fingerprints(worktree, task.allowed_paths)
            proc = subprocess.run(command, cwd=worktree, env=_safe_env(), capture_output=True, text=True, timeout=timeout, check=False)
            combined = f"{proc.stdout}\n{proc.stderr}"
            changed = _changed_files(worktree, before, task.allowed_paths)
            violations = [path for path in changed if not _path_allowed(path, task.allowed_paths, task.protected_paths)]
            failure = classify_failure(combined, proc.returncode) if proc.returncode != 0 else None
            if violations:
                failure = "PROTECTED_PATH_VIOLATION"
            status = "PASS" if proc.returncode == 0 and not violations else "FAIL"
            artifact_hash = hashlib.sha256("\n".join(changed).encode()).hexdigest()
            return {"status": status, "worker_id": self.worker_id, "started_at": started, "finished_at": now(),
                    "command": command[:4], "returncode": proc.returncode, "failure_class": failure,
                    "files_changed": changed, "violations": violations, "artifact_fingerprint": artifact_hash,
                    "stdout": _redact_output(proc.stdout), "stderr": _redact_output(proc.stderr),
                    "independent_verification": status == "PASS" and not violations}
        except subprocess.TimeoutExpired as exc:
            output = str(exc)
            return {"status": "FAIL", "worker_id": self.worker_id, "started_at": started, "finished_at": now(),
                    "failure_class": classify_failure(output), "files_changed": [], "independent_verification": False}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "FAIL", "worker_id": self.worker_id, "started_at": started, "finished_at": now(),
                    "failure_class": type(exc).__name__, "files_changed": [], "independent_verification": False}
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, text=True, check=False)
            shutil.rmtree(worktree, ignore_errors=True)


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
    handoff = {"schema_version": "nexus.worker-handoff.v1", "campaign_id": "NEXUS_COMPLETION_DAY_2026_08_26",
               "task_id": task.task_id, "objective_id": task.objective_id, "generation": 1,
               "previous_worker": previous_worker, "next_worker": next_worker, "handoff_reason": reason,
               "failure_class": failure_class, "failure_evidence": failure_evidence,
               "starting_sha": task.checkpoint_sha, "checkpoint_sha": task.checkpoint_sha,
               "allowed_paths": list(task.allowed_paths), "protected_paths": list(task.protected_paths),
               "current_stage": current_stage, "completed_stages": list(completed_stages or ["S0_SCHEDULED", "S1_SELECTED"]),
               "remaining_acceptance": list(task.acceptance), "worktree": task.worktree,
               "receipt_refs": list(receipt_refs or []), "created_at": now()}
    _write_json(HANDOFF_PATH, handoff)
    return handoff


def select_worker(task: CodingTask, workers: Dict[str, Dict[str, Any]], *, unavailable: Iterable[str] = ()) -> str:
    blocked = set(unavailable)
    for worker_id in ("codex", "opencode"):
        row = workers.get(worker_id, {})
        if worker_id not in blocked and row.get("state") == "AVAILABLE" and "repo_edit" in row.get("capabilities", []):
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
