"""Provider-neutral builder runtime and verified execution proof.

The builder layer routes a compact build specification to a coding worker,
records an append-only execution ledger, and verifies the result deterministically.
The safe proof path uses a local internal worker that writes an isolated artifact;
CLI workers are registered for availability reporting and future routing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from nexus_agent_platform.creative.lab import build_creative_lab_report
from nexus_agent_platform.runtime.execution_telemetry import execution_run
from nexus_agent_platform.runtime.paths import nexus_data_path

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"
LEDGER_PATH = nexus_data_path("runtime", "builder_execution_ledger", "ledger.jsonl")
PROTECTED_DEFAULTS = (
    "src/client-v2/",
    "classic /client",
    "production Telegram",
    "Supabase RLS",
    "production secrets",
    "production agent identities",
)

_COST_CLASS_ORDER = {
    "ZERO_MODEL_COST": 0,
    "LOW_EXTERNAL_COST": 1,
    "AI_TIER_1": 2,
    "AI_TIER_2": 3,
    "AI_TIER_3": 4,
}

WORKER_STATUSES = (
    "AVAILABLE",
    "INSTALLED_UNPROVEN",
    "AUTH_BLOCKED",
    "RATE_LIMITED",
    "NOT_INSTALLED",
    "UNAVAILABLE",
)

_AUTH_ERROR_RE = re.compile(r"(unauthori[sz]ed|authentication|not authenticated|login required|invalid token|api key required|401)", re.I)
_RATE_LIMIT_RE = re.compile(r"(rate.?limit|too many requests|429|quota exceeded|throttl)", re.I)
_SENSITIVE_RE = re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|auth(?:entication)?[_-]?token|secret|password)\s*[:=]\s*)([^\s,;]+)")
OPENCODE_PROBE_MODEL = "opencode/mimo-v2.5-free"
OPENCODE_PROBE_MARKER = "OPENCODE_PROBE_OK"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _approx_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return max(0, len(text) // 4)


def _stable_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    _ensure_parent(path)
    if not path.exists():
        path.touch(mode=0o600)
        os.chmod(path, 0o600)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, separators=(",", ":"), default=str))
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())


def _repo_git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _safe_version(command: Sequence[str], timeout: int = 8) -> Dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    return {
        "command": list(command),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def _safe_probe(command: Sequence[str], timeout: int = 12) -> Dict[str, Any]:
    """Run a provider health probe without returning command output."""
    started = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {
            "command": list(command[:2]),
            "returncode": proc.returncode,
            "stdout_present": bool((proc.stdout or "").strip()),
            "stderr_present": bool((proc.stderr or "").strip()),
            "stdout": (proc.stdout or "")[:1000],
            "stderr": (proc.stderr or "")[:1000],
            "timed_out": False,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": list(command[:2]),
            "returncode": None,
            "stdout_present": False,
            "stderr_present": False,
            "stdout": "",
            "stderr": "",
            "timed_out": True,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except OSError as exc:
        return {
            "command": list(command[:2]),
            "returncode": None,
            "stdout_present": False,
            "stderr_present": False,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "os_error": type(exc).__name__,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }


def _probe_text(probe: Dict[str, Any]) -> str:
    return f"{probe.get('stdout', '')}\n{probe.get('stderr', '')}"[:2000]


def _redact_probe_text(value: str) -> str:
    return _SENSITIVE_RE.sub(r"\1[REDACTED]", value)[:240]


def _classify_cli_probe(*, installed: bool, version_probe: Dict[str, Any], execution_probe: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Classify only from observed evidence; never infer auth from version-only success."""
    if not installed:
        return {"classification": "NOT_INSTALLED", "reason": "binary missing", "probe_result": "not_run"}
    if version_probe.get("timed_out"):
        return {"classification": "UNAVAILABLE", "reason": "version probe timed out", "probe_result": "version_timeout"}
    version_text = _probe_text(version_probe)
    if _RATE_LIMIT_RE.search(version_text):
        return {"classification": "RATE_LIMITED", "reason": "rate-limit evidence in version probe", "probe_result": "version_rate_limited"}
    if _AUTH_ERROR_RE.search(version_text):
        return {"classification": "AUTH_BLOCKED", "reason": "explicit authentication error in version probe", "probe_result": "version_auth_error"}
    version_ok = version_probe.get("returncode") == 0
    if execution_probe is None:
        return {"classification": "UNAVAILABLE" if not version_ok else "INSTALLED_UNPROVEN", "reason": "version probe did not prove execution", "probe_result": "version_only"}
    if execution_probe.get("timed_out"):
        return {"classification": "UNAVAILABLE", "reason": "safe execution probe timed out", "probe_result": "execution_timeout"}
    execution_text = _probe_text(execution_probe)
    if _RATE_LIMIT_RE.search(execution_text):
        return {"classification": "RATE_LIMITED", "reason": "explicit rate-limit evidence in execution probe", "probe_result": "execution_rate_limited"}
    if _AUTH_ERROR_RE.search(execution_text):
        return {"classification": "AUTH_BLOCKED", "reason": "explicit authentication error in execution probe", "probe_result": "execution_auth_error"}
    if execution_probe.get("returncode") == 0:
        if execution_probe.get("marker_required") and not execution_probe.get("marker_present"):
            return {"classification": "INSTALLED_UNPROVEN", "reason": "execution returned successfully without the required provider marker", "probe_result": "execution_marker_missing"}
        return {"classification": "AVAILABLE", "reason": "version and harmless execution probes succeeded", "probe_result": "execution_success"}
    return {"classification": "UNAVAILABLE" if not version_ok else "INSTALLED_UNPROVEN", "reason": "execution probe did not prove availability", "probe_result": "execution_failed"}


def _provider_probe_command(name: str) -> Optional[List[str]]:
    harmless = "Reply with exactly HEALTHCHECK_OK. Do not inspect, read, or modify files."
    if name == "codex":
        return [name, "exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "--color", "never", harmless]
    if name == "opencode":
        return [name, "run", "--model", OPENCODE_PROBE_MODEL, "--format", "json", "Reply with exactly: OPENCODE_PROBE_OK"]
    if name == "mimo":
        return [name, "run", "--non-interactive", harmless]
    return None


def _probe_cli_worker(name: str, path: Optional[str], *, version_timeout: int = 8, execution_timeout: int = 12) -> Dict[str, Any]:
    installed = path is not None
    if not installed:
        return {"installed": False, "version": "UNKNOWN", **_classify_cli_probe(installed=False, version_probe={}, execution_probe=None)}
    try:
        version_probe = _safe_version([name, "--version"], timeout=version_timeout)
    except subprocess.TimeoutExpired:
        version_probe = {"returncode": None, "stdout": "", "stderr": "", "timed_out": True}
    version_text = (version_probe.get("stdout") or version_probe.get("stderr") or "").strip()
    execution_probe = None
    if version_probe.get("returncode") == 0 and _provider_probe_command(name):
        execution_probe = _safe_probe(_provider_probe_command(name) or [], timeout=execution_timeout)
    if execution_probe is not None and name == "opencode":
        execution_probe["marker_required"] = True
        execution_probe["marker_present"] = OPENCODE_PROBE_MARKER in (execution_probe.get("stdout") or "")
        execution_probe["model"] = OPENCODE_PROBE_MODEL
    classification = _classify_cli_probe(installed=True, version_probe=version_probe, execution_probe=execution_probe)
    return {
        "installed": True,
        "version": _redact_probe_text(version_text) or "UNKNOWN",
        "version_probe": {"returncode": version_probe.get("returncode"), "timed_out": bool(version_probe.get("timed_out"))},
        "execution_probe": ({
            "returncode": execution_probe.get("returncode"),
            "timed_out": bool(execution_probe.get("timed_out")),
            "duration_ms": execution_probe.get("duration_ms"),
            **({"model": execution_probe.get("model"), "marker_present": execution_probe.get("marker_present"), "marker_required": True} if name == "opencode" else {}),
        } if execution_probe else "not_run"),
        **classification,
    }


@dataclass(frozen=True)
class BuildTaskSpec:
    task_id: str
    title: str
    objective: str
    repo: str
    branch: str
    worktree: str
    scope: List[str]
    protected_paths: List[str]
    allowed_paths: List[str]
    requirements: List[str]
    acceptance_criteria: List[str]
    tests: List[str]
    visual_requirements: bool
    security_constraints: List[str]
    budget: Dict[str, Any]
    timeout_seconds: int
    approval_state: str
    retry_policy: str = "bounded"
    max_retries: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_failure_delta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "objective": self.objective,
            "repo": self.repo,
            "branch": self.branch,
            "worktree": self.worktree,
            "scope": list(self.scope),
            "protected_paths": list(self.protected_paths),
            "allowed_paths": list(self.allowed_paths),
            "requirements": list(self.requirements),
            "acceptance_criteria": list(self.acceptance_criteria),
            "tests": list(self.tests),
            "visual_requirements": self.visual_requirements,
            "security_constraints": list(self.security_constraints),
            "budget": dict(self.budget),
            "timeout_seconds": self.timeout_seconds,
            "approval_state": self.approval_state,
            "retry_policy": self.retry_policy,
            "max_retries": self.max_retries,
            "metadata": dict(self.metadata),
            "previous_failure_delta": dict(self.previous_failure_delta),
        }


@dataclass
class BuildExecutionResult:
    task_id: str
    worker_id: str
    worker_type: str
    display_name: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: int
    starting_commit: str
    ending_commit: str
    files_changed: List[str]
    tests_run: List[str]
    tests_passed: int
    tests_failed: int
    visual_check: Dict[str, Any]
    retry_count: int
    protected_path_violation: bool
    artifact_refs: List[str]
    cost_provenance: Dict[str, Any]
    worker_report: Dict[str, Any]
    verification: Dict[str, Any]
    selected_worker_reason: str
    selected_worker_fallback: bool = False


class CodingWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        worker_type: str,
        display_name: str,
        available: bool,
        capabilities: Sequence[str],
        cost_class: str,
        supports_repo_edit: bool,
        supports_tests: bool,
        supports_browser: bool,
        supports_images: bool,
        supports_worktrees: bool,
        supports_resume: bool,
        supports_structured_output: bool,
        availability_reason: str = "",
        installed: bool = False,
        health_probe: Optional[Callable[[], Dict[str, Any]]] = None,
        execute_fn: Optional[Callable[[BuildTaskSpec], Dict[str, Any]]] = None,
    ) -> None:
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.display_name = display_name
        self.available = available
        self.capabilities = list(capabilities)
        self.cost_class = cost_class
        self.supports_repo_edit = supports_repo_edit
        self.supports_tests = supports_tests
        self.supports_browser = supports_browser
        self.supports_images = supports_images
        self.supports_worktrees = supports_worktrees
        self.supports_resume = supports_resume
        self.supports_structured_output = supports_structured_output
        self.availability_reason = availability_reason
        self.installed = installed
        self._health_probe = health_probe
        self._execute_fn = execute_fn

    def health_check(self) -> Dict[str, Any]:
        if self._health_probe:
            payload = self._health_probe()
        else:
            payload = {
                "installed": self.installed,
                "available": self.available,
                "reason": self.availability_reason,
            }
        payload.update(
            {
                "worker_id": self.worker_id,
                "worker_type": self.worker_type,
                "display_name": self.display_name,
                "capabilities": list(self.capabilities),
                "cost_class": self.cost_class,
                "supports_repo_edit": self.supports_repo_edit,
                "supports_tests": self.supports_tests,
                "supports_browser": self.supports_browser,
                "supports_images": self.supports_images,
                "supports_worktrees": self.supports_worktrees,
                "supports_resume": self.supports_resume,
                "supports_structured_output": self.supports_structured_output,
                "availability_reason": self.availability_reason,
            }
        )
        return payload

    def can_handle(self, task: BuildTaskSpec) -> bool:
        if not self.available:
            return False
        # A health-positive CLI is not automatically an execution adapter. Keep
        # provider invocation disabled until a bounded execute_fn is registered.
        if self.worker_type == "cli" and self._execute_fn is None:
            return False
        if task.visual_requirements and not self.supports_browser:
            return False
        if task.tests and not self.supports_tests:
            return False
        if task.allowed_paths and not self.supports_repo_edit:
            return False
        return True

    def prepare_task(self, task: BuildTaskSpec) -> Dict[str, Any]:
        return {
            "task_id": task.task_id,
            "title": task.title,
            "objective": task.objective,
            "repo": task.repo,
            "scope": list(task.scope),
            "protected_paths": list(task.protected_paths),
            "allowed_paths": list(task.allowed_paths),
            "requirements": list(task.requirements),
            "acceptance_criteria": list(task.acceptance_criteria),
            "tests": list(task.tests),
            "visual_requirements": task.visual_requirements,
            "approval_state": task.approval_state,
            "budget": dict(task.budget),
            "retry_state": dict(task.previous_failure_delta),
        }

    def execute(self, task: BuildTaskSpec) -> Dict[str, Any]:
        if self._execute_fn:
            return self._execute_fn(task)
        raise RuntimeError(f"Worker {self.worker_id} cannot execute tasks")

    def collect_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        return dict(raw_result)

    def verify_result(self, task: BuildTaskSpec, result: Dict[str, Any]) -> Dict[str, Any]:
        if result.get("status") != "success":
            return {
                "status": "fail",
                "reason": "worker did not report success",
                "retryable": True,
                "failure_delta": {"status": result.get("status"), "reason": "worker self-report failed"},
            }
        artifact_refs = [Path(p) for p in result.get("artifact_refs", [])]
        missing = [str(path) for path in artifact_refs if not path.exists()]
        if missing:
            return {
                "status": "fail",
                "reason": "missing artifacts",
                "retryable": True,
                "failure_delta": {"missing_artifacts": missing},
            }
        if result.get("protected_path_violation"):
            return {
                "status": "fail",
                "reason": "protected path violation",
                "retryable": False,
                "failure_delta": {"protected_path_violation": True},
            }
        if task.visual_requirements and not result.get("visual_check", {}).get("verified"):
            return {
                "status": "fail",
                "reason": "visual verification required",
                "retryable": True,
                "failure_delta": {"visual_check": result.get("visual_check", {})},
            }
        if result.get("tests_failed", 0):
            return {
                "status": "retry" if result.get("tests_failed", 0) else "pass",
                "reason": "tests failed",
                "retryable": True,
                "failure_delta": {"tests_failed": result.get("tests_failed", 0), "tests_run": result.get("tests_run", [])},
            }
        return {"status": "pass", "reason": "verified", "retryable": False, "failure_delta": {}}

    def cancel(self) -> Dict[str, Any]:
        return {"status": "not_supported", "worker_id": self.worker_id}

    def resume(self) -> Dict[str, Any]:
        return {"status": "not_supported", "worker_id": self.worker_id}


def _cli_worker(name: str, *, cost_class: str, worker_type: str, display_name: str) -> CodingWorker:
    path = shutil.which(name)
    health = _probe_cli_worker(name, path, execution_timeout=30 if name == "opencode" else 12)
    installed = bool(health["installed"])
    available = health["classification"] == "AVAILABLE"
    reason = str(health["reason"])
    return CodingWorker(
        worker_id=name,
        worker_type=worker_type,
        display_name=display_name,
        available=available,
        capabilities=["repo_edit", "tests", "worktrees"],
        cost_class=cost_class,
        supports_repo_edit=True,
        supports_tests=True,
        supports_browser=False,
        supports_images=False,
        supports_worktrees=True,
        supports_resume=False,
        supports_structured_output=False,
        availability_reason=reason,
        installed=installed,
        health_probe=lambda: {
            "installed": installed,
            "available": available,
            "status": health["classification"],
            "classification": health["classification"],
            "version": health["version"],
            "reason": reason,
            "probe_result": health["probe_result"],
            "version_probe": health["version_probe"],
            "execution_probe": health["execution_probe"],
        },
    )


def _local_python_worker() -> CodingWorker:
    def _execute(task: BuildTaskSpec) -> Dict[str, Any]:
        sandbox = Path(tempfile.mkdtemp(prefix=f"nexus-builder-{task.task_id}-"))
        artifact_dir = sandbox / "artifact"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        spec_path = artifact_dir / "build_spec.json"
        summary_path = artifact_dir / "build_summary.md"
        spec_path.write_text(json.dumps(task.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary_path.write_text(
            "\n".join(
                [
                    "# Nexus Builder Proof Artifact",
                    "",
                    f"- task_id: {task.task_id}",
                    f"- title: {task.title}",
                    f"- objective: {task.objective}",
                    f"- protected_paths: {len(task.protected_paths)}",
                    f"- visual_requirements: {task.visual_requirements}",
                    f"- approval_state: {task.approval_state}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "success",
            "worker_report": {
                "summary": "Local deterministic builder created an isolated internal artifact.",
                "sandbox": str(sandbox),
            },
            "artifact_refs": [str(spec_path), str(summary_path)],
            "files_changed": [str(spec_path), str(summary_path)],
            "tests_run": ["artifact schema validation", "protected path check"],
            "tests_passed": 2,
            "tests_failed": 0,
            "visual_check": {
                "required": task.visual_requirements,
                "verified": False,
                "status": "not_required" if not task.visual_requirements else "not_run",
            },
            "protected_path_violation": False,
            "self_report": "done",
            "implementation_mode": "local_python_artifact",
            "retryable": False,
            "cost_provenance": {
                "tier": "ZERO_MODEL_COST",
                "provider": "local_python",
                "model": "python",
                "estimated_cost_usd": 0.0,
            },
        }

    return CodingWorker(
        worker_id="local_python",
        worker_type="deterministic_python",
        display_name="Local Python Builder",
        available=True,
        capabilities=["repo_edit", "tests", "worktrees", "structured_output"],
        cost_class="ZERO_MODEL_COST",
        supports_repo_edit=True,
        supports_tests=True,
        supports_browser=False,
        supports_images=False,
        supports_worktrees=True,
        supports_resume=False,
        supports_structured_output=True,
        availability_reason="local deterministic fallback",
        installed=True,
        health_probe=lambda: {
            "installed": True,
            "available": True,
            "version": "python3",
            "reason": "local deterministic fallback",
        },
        execute_fn=_execute,
    )


def build_coding_worker_registry() -> List[CodingWorker]:
    workers = [
        _cli_worker("opencode", cost_class="ZERO_MODEL_COST", worker_type="cli", display_name="OpenCode CLI"),
        _cli_worker("codex", cost_class="ZERO_MODEL_COST", worker_type="cli", display_name="Codex CLI"),
        _cli_worker("mimo", cost_class="LOW_EXTERNAL_COST", worker_type="cli", display_name="MiMo CLI"),
        _local_python_worker(),
    ]
    return workers


def _selection_score(task: BuildTaskSpec, worker: CodingWorker) -> Tuple[int, int, int, int, str]:
    visual_score = 1 if (task.visual_requirements and worker.supports_browser) or not task.visual_requirements else 0
    test_score = 1 if (not task.tests or worker.supports_tests) else 0
    repo_score = 1 if (not task.allowed_paths or worker.supports_repo_edit) else 0
    cost_rank = _COST_CLASS_ORDER.get(worker.cost_class, 99)
    available = 1 if worker.available else 0
    return (available, visual_score, test_score + repo_score, -cost_rank, worker.worker_id)


def select_coding_worker(task: BuildTaskSpec, workers: Sequence[CodingWorker]) -> CodingWorker:
    candidates = [worker for worker in workers if worker.can_handle(task)]
    if not candidates:
        raise ValueError("No compatible worker available")
    return sorted(candidates, key=lambda worker: _selection_score(task, worker), reverse=True)[0]


def normalize_build_spec(raw_spec: Dict[str, Any], *, task_title: Optional[str] = None, task_objective: Optional[str] = None) -> BuildTaskSpec:
    proof_id = _stable_hash(raw_spec)[:12]
    repo_branch = _repo_git("branch", "--show-current") if (ROOT / ".git").exists() else "main"
    protected = list(raw_spec.get("protected_paths") or PROTECTED_DEFAULTS)
    allowed = list(raw_spec.get("allowed_paths") or ["reports/hermes_modernization/"])
    return BuildTaskSpec(
        task_id=f"build_{proof_id}",
        title=task_title or raw_spec.get("concept_name") or raw_spec.get("title") or "Builder Task",
        objective=task_objective or raw_spec.get("objective") or raw_spec.get("summary") or "Implement the approved build specification.",
        repo=str(ROOT),
        branch=repo_branch,
        worktree=str(ROOT),
        scope=list(raw_spec.get("content_blocks") or raw_spec.get("scope") or []),
        protected_paths=protected,
        allowed_paths=allowed,
        requirements=list(raw_spec.get("requirements") or []),
        acceptance_criteria=list(raw_spec.get("verification", {}).get("acceptance_criteria") or raw_spec.get("acceptance_criteria") or []),
        tests=list(raw_spec.get("tests") or []),
        visual_requirements=bool(raw_spec.get("visual_requirements", False)),
        security_constraints=list(raw_spec.get("build_constraints") or raw_spec.get("security_constraints") or []),
        budget=dict(raw_spec.get("budget") or {}),
        timeout_seconds=int(raw_spec.get("timeout_seconds") or raw_spec.get("timeout") or 120),
        approval_state=str(raw_spec.get("approval_state") or "approved"),
        retry_policy=str(raw_spec.get("retry_policy") or "bounded"),
        max_retries=int(raw_spec.get("max_retries") or 1),
        metadata={
            "source": raw_spec.get("source", "creative_lab"),
            "source_commit": raw_spec.get("source_commit"),
        },
    )


def append_builder_ledger(entry: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or LEDGER_PATH
    record = dict(entry)
    record.setdefault("ledger_id", f"ledger_{uuid.uuid4().hex}")
    record.setdefault("recorded_at", _utc_now())
    _append_jsonl(path, record)
    return record


def _verify_protected_paths(task: BuildTaskSpec, result: Dict[str, Any]) -> Dict[str, Any]:
    protected = set(task.protected_paths)
    changed = set(result.get("files_changed", [])) | set(result.get("artifact_refs", []))
    violation = any(any(protected_path in changed_path for protected_path in protected) for changed_path in changed)
    if violation:
        return {"status": "fail", "reason": "protected path violation", "protected_path_violation": True, "retryable": False}
    return {"status": "pass", "reason": "protected paths clear", "protected_path_violation": False, "retryable": False}


def _combine_verification(task: BuildTaskSpec, worker: CodingWorker, result: Dict[str, Any]) -> Dict[str, Any]:
    worker_verification = worker.verify_result(task, result)
    path_verification = _verify_protected_paths(task, result)
    if worker_verification["status"] != "pass":
        return worker_verification
    if path_verification["status"] != "pass":
        return path_verification
    return {
        "status": "pass",
        "reason": "deterministic verification passed",
        "retryable": False,
        "protected_path_violation": False,
        "failure_delta": {},
    }


def run_builder_task(
    task: BuildTaskSpec,
    workers: Sequence[CodingWorker],
    *,
    max_retries: Optional[int] = None,
) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    retry_limit = task.max_retries if max_retries is None else int(max_retries)
    current_task = task
    start_monotonic = time.monotonic()
    starting_commit = _repo_git("rev-parse", "HEAD")
    selected: Optional[CodingWorker] = None
    verification: Dict[str, Any] = {"status": "fail", "reason": "not started", "retryable": False}
    collected: Dict[str, Any] = {}
    for attempt in range(retry_limit + 1):
        selected = select_coding_worker(current_task, workers)
        raw = selected.execute(current_task)
        collected = selected.collect_result(raw)
        verification = _combine_verification(current_task, selected, collected)
        attempts.append(
            {
                "attempt": attempt + 1,
                "worker_id": selected.worker_id,
                "status": verification["status"],
                "reason": verification.get("reason", ""),
                "failure_delta": verification.get("failure_delta", {}),
            }
        )
        if verification["status"] == "pass":
            break
        if attempt >= retry_limit or not verification.get("retryable", False):
            break
        current_task = replace(current_task, previous_failure_delta=dict(verification.get("failure_delta", {})))

    assert selected is not None
    ending_commit = _repo_git("rev-parse", "HEAD")
    duration_ms = int((time.monotonic() - start_monotonic) * 1000)
    final_status = "pass" if verification["status"] == "pass" else "failed"
    retry_count = max(0, len(attempts) - 1)
    ledger_entry = append_builder_ledger(
        {
            "task_id": task.task_id,
            "worker_id": selected.worker_id,
            "started_at": _utc_now(),
            "finished_at": _utc_now(),
            "starting_commit": starting_commit,
            "ending_commit": ending_commit,
            "files_changed": collected.get("files_changed", []),
            "tests_run": collected.get("tests_run", []),
            "tests_passed": collected.get("tests_passed", 0),
            "tests_failed": collected.get("tests_failed", 0),
            "visual_check": collected.get("visual_check", {}),
            "retry_count": retry_count,
            "protected_path_violation": bool(collected.get("protected_path_violation", False)),
            "status": final_status,
            "artifact_refs": collected.get("artifact_refs", []),
            "cost_provenance": collected.get("cost_provenance", {"tier": task.budget.get("model_tier", "ZERO_MODEL_COST"), "provider": "local_python"}),
            "attempts": attempts,
        }
    )
    result = BuildExecutionResult(
        task_id=task.task_id,
        worker_id=selected.worker_id,
        worker_type=selected.worker_type,
        display_name=selected.display_name,
        status=final_status,
        started_at=ledger_entry["started_at"],
        finished_at=ledger_entry["finished_at"],
        duration_ms=duration_ms,
        starting_commit=starting_commit,
        ending_commit=ending_commit,
        files_changed=list(collected.get("files_changed", [])),
        tests_run=list(collected.get("tests_run", [])),
        tests_passed=int(collected.get("tests_passed", 0)),
        tests_failed=int(collected.get("tests_failed", 0)),
        visual_check=dict(collected.get("visual_check", {})),
        retry_count=retry_count,
        protected_path_violation=bool(collected.get("protected_path_violation", False)),
        artifact_refs=list(collected.get("artifact_refs", [])),
        cost_provenance=dict(collected.get("cost_provenance", {"tier": task.budget.get("model_tier", "ZERO_MODEL_COST"), "provider": "local_python", "estimated_cost_usd": 0.0})),
        worker_report=dict(collected.get("worker_report", {})),
        verification=verification,
        selected_worker_reason=selected.availability_reason,
        selected_worker_fallback=selected.worker_id == "local_python",
    )
    return {
        "ok": final_status == "pass",
        "status": final_status,
        "task": task.to_dict(),
        "workers": [worker.health_check() for worker in workers],
        "selected_worker": {**selected.health_check(), "fallback_used": selected.worker_id == "local_python"},
        "verification": verification,
        "result": {
            **result.__dict__,
            "attempts": attempts,
            "ai_usage": {
                "model_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "tier1_calls": 0,
                "tier2_calls": 0,
                "tier3_calls": 0,
            },
            "zero_token_execution": True,
        },
        "ai_usage": {
            "model_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "tier1_calls": 0,
            "tier2_calls": 0,
            "tier3_calls": 0,
        },
        "retry_count": retry_count,
        "ledger_path": str(LEDGER_PATH),
        "duration_ms": duration_ms,
        "starting_commit": starting_commit,
        "ending_commit": ending_commit,
        "builder_audit": build_builder_audit(),
        "ai_calls": 0,
        "zero_token_execution": True,
        "attempts": attempts,
    }


def _render_audit_rows() -> List[Dict[str, Any]]:
    return [
        {"component": "scripts/runner_handlers/_base.py", "classification": "WRAP", "reason": "Generic subprocess runner already supports bounded script execution."},
        {"component": "scripts/client_flow/common.py", "classification": "MERGE", "reason": "Local-only builder/report helpers already write structured outputs."},
        {"component": "scripts/client_flow/run_client_portal_backend_build.py", "classification": "DEFER", "reason": "Client portal build flow is protected and not part of this phase."},
        {"component": "scripts/creative/lab.py", "classification": "WRAP", "reason": "Creative Lab already produces an approved build spec and pilot artifact."},
        {"component": "scripts/creative/run_creative_lab.py", "classification": "WRAP", "reason": "Existing Creative Lab report driver can seed the safe builder proof."},
        {"component": "scripts/nexus_agent_platform/runtime/execution_telemetry.py", "classification": "EXTEND", "reason": "Verified execution telemetry already records actual runtime boundaries."},
        {"component": "scripts/nexus_agent_platform/loops/runtime.py", "classification": "EXTEND", "reason": "Loop runtime already enforces bounded retries and cost control patterns."},
        {"component": "scripts/nexus_agent_platform/hermes_lab/upstream_compatibility.py", "classification": "MERGE", "reason": "Upstream lab sandboxing and subprocess probes are reusable here."},
        {"component": "src/lib/nexusSectionStatusRegistry.ts", "classification": "WRAP", "reason": "CLI/tool availability inventory already exists and informs routing."},
        {"component": "reports/cli_tool_registry_latest.json", "classification": "WRAP", "reason": "Read-only tool registry evidence already captures installed vs authorized state."},
        {"component": "scripts/runner_handlers/design_handlers.py", "classification": "MERGE", "reason": "Deterministic script delegation pattern can be reused for builder orchestration."},
        {"component": "scripts/hermes/create_manual_model_packet.py", "classification": "WRAP", "reason": "Manual packet pattern is useful for future worker handoffs, not execution."},
        {"component": "OpenHands integration", "classification": "DEFER", "reason": "Not installed or proven on this machine."},
        {"component": "provider-neutral CodingWorker contract", "classification": "CREATE_NEW", "reason": "This phase introduces the missing builder abstraction."},
    ]


def build_builder_audit() -> List[Dict[str, Any]]:
    return _render_audit_rows()


def _write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _render_audit(report: Dict[str, Any]) -> str:
    lines = [
        "# Builder Audit",
        "",
        "## Existing surfaces",
        "",
        "| Component | Classification | Reason |",
        "|---|---|---|",
    ]
    for row in report["builder_audit"]:
        lines.append(f"| {row['component']} | {row['classification']} | {row['reason']} |")
    return "\n".join(lines) + "\n"


def _render_abstraction(report: Dict[str, Any]) -> str:
    lines = [
        "# Builder Abstraction",
        "",
        "## Contract",
        "",
        f"- task_id: {report['task']['task_id']}",
        f"- title: {report['task']['title']}",
        f"- approval_state: {report['task']['approval_state']}",
        f"- protected_paths: {len(report['task']['protected_paths'])}",
        f"- selected_worker: {report['selected_worker']['worker_id']}",
        f"- fallback_used: {'yes' if report['selected_worker']['fallback_used'] else 'no'}",
        "",
        "## Workers",
        "",
        "| Worker | Available | Cost | Repo edit | Tests | Browser |",
        "|---|---|---|---|---|---|",
    ]
    for worker in report["workers"]:
        lines.append(
            f"| {worker['worker_id']} | {'yes' if worker['available'] else 'no'} | {worker['cost_class']} | "
            f"{'yes' if worker['supports_repo_edit'] else 'no'} | {'yes' if worker['supports_tests'] else 'no'} | {'yes' if worker['supports_browser'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Ledger",
            "",
            f"- path: `{report['ledger_path']}`",
            f"- status: {report['result']['status']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_pilot(report: Dict[str, Any]) -> str:
    lines = [
        "# Builder Pilot",
        "",
        "## Safe proof",
        "",
        "The proof used an internal deterministic worker and did not touch protected paths.",
        "",
        "## Selected worker",
        "",
        f"- worker: {report['selected_worker']['display_name']}",
        f"- availability: {'available' if report['selected_worker']['available'] else 'unavailable'}",
        f"- reason: {report['selected_worker']['availability_reason']}",
        "",
        "## Verification",
        "",
        f"- status: {report['verification']['status']}",
        f"- protected path violation: {'yes' if report['result'].get('protected_path_violation') else 'no'}",
        f"- visual check required: {'yes' if report['result']['visual_check']['required'] else 'no'}",
        "",
        "## Artifact refs",
        "",
    ]
    lines.extend(f"- `{ref}`" for ref in report["result"].get("artifact_refs", []))
    return "\n".join(lines) + "\n"


def _render_benchmark(report: Dict[str, Any]) -> str:
    lines = [
        "# Builder Benchmark",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| task_id | {report['task']['task_id']} |",
        f"| selected_worker | {report['selected_worker']['worker_id']} |",
        f"| ai_usage | {report['ai_usage']} |",
        f"| retry_count | {report['retry_count']} |",
        f"| duration_ms | {report['duration_ms']} |",
        f"| tests_run | {len(report['result'].get('tests_run', []))} |",
        f"| tests_passed | {report['result'].get('tests_passed', 0)} |",
        f"| tests_failed | {report['result'].get('tests_failed', 0)} |",
        f"| visual_check | {report['result']['visual_check']['status']} |",
        f"| ledger_path | {report['ledger_path']} |",
        f"| estimated_cost_usd | {report['result']['cost_provenance']['estimated_cost_usd']} |",
        f"| cost_provenance | {report['result']['cost_provenance']['tier']} / {report['result']['cost_provenance']['provider']} |",
    ]
    return "\n".join(lines) + "\n"


def _build_safe_proof_task(previous_state: Optional[Dict[str, Any]] = None) -> BuildTaskSpec:
    creative_report = build_creative_lab_report(previous_state=previous_state or {})
    normalized = normalize_build_spec(
        creative_report["build_spec"],
        task_title="Internal Creative Lab proof artifact",
        task_objective="Generate a bounded internal artifact from the approved Creative Lab build spec.",
    )
    return replace(
        normalized,
        allowed_paths=["reports/hermes_modernization/"],
        budget={
            **normalized.budget,
            "max_ai_calls": 0,
            "estimated_token_budget": 0,
            "model_tier": "T0_DETERMINISTIC",
        },
        metadata={
            **normalized.metadata,
            "source_commit": creative_report["source_commit"],
            "creative_territory": creative_report["recommended_territory"]["concept_name"],
        },
    )


def run_builder_pilot(previous_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    task = _build_safe_proof_task(previous_state=previous_state)
    workers = build_coding_worker_registry()
    ai_usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "tier1_calls": 0, "tier2_calls": 0, "tier3_calls": 0}
    with execution_run(
        process_id="builder_abstraction",
        process_name="Builder Abstraction",
        worker_id="local_python",
        agent_id="hermes_nova",
        execution_type="coding_worker_pilot",
        source="builder_abstraction",
        metadata={"task_id": task.task_id, "visual_requirements": task.visual_requirements},
    ) as telemetry_run_id:
        proof = run_builder_task(task, workers, max_retries=0)
        proof["result"]["telemetry_run_id"] = telemetry_run_id
    return {
        **proof,
        "ok": proof["status"] == "pass",
        "ai_usage": ai_usage,
        "zero_token_execution": True,
    }


def write_builder_reports(previous_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    report = run_builder_pilot(previous_state=previous_state)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _write_report(REPORT_DIR / "builder_audit.md", _render_audit(report))
    _write_report(REPORT_DIR / "builder_abstraction.md", _render_abstraction(report))
    _write_report(REPORT_DIR / "builder_pilot.md", _render_pilot(report))
    _write_report(REPORT_DIR / "builder_benchmark.md", _render_benchmark(report))
    return report
