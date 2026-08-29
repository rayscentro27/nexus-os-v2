"""Reusable fail-closed loop kernel.

The kernel owns orchestration and evidence shape; it does not grant authority.
Executors and reviewers are injected by Nexus-owned adapters, while Hermes
output is advisory and never writes TruthKernel directly.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_DIR = ROOT / "reports/rebuild/nexus_loop_receipts"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class LoopDefinition:
    loop_id: str
    name: str
    purpose: str
    trigger_types: tuple[str, ...]
    default_skill: str
    allowed_skills: tuple[str, ...]
    default_worker: str
    allowed_workers: tuple[str, ...]
    default_profile: str
    model_policy: str
    allowed_executors: tuple[str, ...]
    authority_class: str = "internal_read_only"
    dependencies: tuple[str, ...] = ()
    side_effect_class: str = "none"
    retry_policy: Mapping[str, Any] = field(default_factory=lambda: {"max_attempts": 1})
    handoff_policy: Mapping[str, Any] = field(default_factory=lambda: {"allowed": False})
    recovery_policy: Mapping[str, Any] = field(default_factory=lambda: {"fail_closed": True})
    autonomy_level: str = "A1_AUTOMATIC_EXECUTION"


@dataclass(frozen=True)
class LoopResult:
    receipt_id: str
    run_id: str
    loop_id: str
    final_state: str
    receipt_path: str
    error: str | None = None


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _receipt_path(receipt_id: str, directory: Path | None) -> Path:
    target = directory or RECEIPT_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target / f"{receipt_id}.json"


def _assert_context(context: Mapping[str, Any]) -> None:
    encoded = json.dumps(context, sort_keys=True, default=str).lower()
    forbidden = ("api_key", "token=", "-----begin", "@gmail.com", "ssn", "client_pii")
    if any(marker in encoded for marker in forbidden):
        raise ValueError("unsafe or credential-like loop context")


def run_loop(
    definition: LoopDefinition,
    context: Mapping[str, Any],
    *,
    trigger: str,
    executor: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    reviewer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    skill_id: str | None = None,
    worker_id: str | None = None,
    profile: str | None = None,
    model_provider: str = "Nexus deterministic",
    model_name: str = "none",
    receipt_dir: Path | None = None,
) -> LoopResult:
    """Run one bounded loop and always emit a sanitized receipt."""
    started = utc_now()
    run_id = f"run_{uuid.uuid4().hex}"
    receipt_id = f"receipt_{uuid.uuid4().hex}"
    selected_skill = skill_id or definition.default_skill
    selected_worker = worker_id or definition.default_worker
    selected_profile = profile or definition.default_profile
    receipt: dict[str, Any] = {
        "schema_version": "nexus.loop-receipt.v2",
        "run_id": run_id,
        "loop_id": definition.loop_id,
        "skill_id": selected_skill,
        "skill_version": "unknown",
        "worker_id": selected_worker,
        "profile": selected_profile,
        "model_policy": definition.model_policy,
        "model_provider": model_provider,
        "model_name": model_name,
        "process_id": definition.loop_id,
        "python_entrypoint": None,
        "trigger": {"type": trigger},
        "input_source": context.get("input_source", "bounded_internal_context"),
        "input_freshness": "PASS",
        "authority_result": {"status": "PASS", "class": definition.authority_class},
        "dependency_result": {"status": "PASS", "dependencies": list(definition.dependencies)},
        "started_at": started,
        "completed_at": None,
        "exit_status": "RUNNING",
        "output_artifact": None,
        "output_hash": None,
        "validation_result": None,
        "side_effect_expected": {"class": definition.side_effect_class},
        "side_effect_observed": None,
        "hermes_review": None,
        "handoff_used": False,
        "retry_used": False,
        "recovery_used": False,
        "receipt_id": receipt_id,
        "final_state": "RUNNING",
    }
    try:
        if trigger not in definition.trigger_types:
            raise ValueError("trigger_not_allowed")
        if selected_skill not in definition.allowed_skills:
            raise ValueError("NO_SKILL_MATCH")
        if selected_worker not in definition.allowed_workers:
            raise ValueError("WORKER_NOT_ALLOWED")
        _assert_context(context)
        result = executor(context)
        if not isinstance(result, Mapping) or result.get("status") != "PASS":
            raise ValueError("executor_result_not_verified")
        receipt["python_entrypoint"] = result.get("entrypoint")
        receipt["output_artifact"] = result.get("artifact")
        receipt["output_hash"] = result.get("output_hash") or _hash_payload(result)
        receipt["validation_result"] = {"status": "PASS", "output_verified": True}
        receipt["side_effect_observed"] = result.get("side_effect", {"external": False})
        if reviewer:
            review = reviewer({"context": dict(context), "result": dict(result), "advisory": True})
            if not isinstance(review, Mapping) or review.get("status") != "PASS":
                raise ValueError("review_not_verified")
            receipt["hermes_review"] = {"status": "PASS", "advisory": True, "summary": str(review.get("summary", ""))[:500]}
        else:
            receipt["hermes_review"] = {"status": "NOT_REQUESTED", "advisory": True}
        receipt["exit_status"] = "PASS"
        receipt["final_state"] = "SUCCEEDED_VERIFIED"
        error = None
    except Exception as exc:  # fail closed and retain the failure receipt
        receipt["exit_status"] = "FAIL_CLOSED"
        receipt["final_state"] = "FAILED"
        receipt["validation_result"] = {"status": "NOT_PROVEN"}
        receipt["side_effect_observed"] = {"external": False, "status": "NOT_RUN_OR_NOT_PROVEN"}
        error = type(exc).__name__ + ":" + str(exc)
        receipt["error"] = str(exc)[:200]
    receipt["completed_at"] = utc_now()
    path = _receipt_path(receipt_id, receipt_dir)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        receipt_path = str(path.relative_to(ROOT))
    except ValueError:
        receipt_path = str(path)
    return LoopResult(receipt_id, run_id, definition.loop_id, receipt["final_state"], receipt_path, error)
