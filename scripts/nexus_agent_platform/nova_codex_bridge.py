"""Governed Nova -> existing Codex worker bridge.

The bridge reuses the existing coding-worker handoff artifact and bounded
builder adapter. It does not create a second coding worker or scheduler.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_PATH = ROOT / "data/runtime/coding_worker_handoff.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(payload: dict[str, Any]) -> None:
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HANDOFF_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(HANDOFF_PATH)


def read_assignment() -> dict[str, Any]:
    try:
        value = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def create_assignment(*, parent_objective_id: str, blocking_work_id: str,
                      defect_id: str, defect_summary: str,
                      affected_component: str, acceptance_criteria: list[str],
                      test_requirements: list[str], allowed_scope: list[str],
                      prohibited_actions: list[str], risk_class: str = "LOW") -> dict[str, Any]:
    required = (parent_objective_id, blocking_work_id, defect_id, defect_summary, affected_component)
    if any(len(str(value).strip()) < 3 for value in required):
        return {"status": "rejected", "error": "required_assignment_field_missing"}
    fingerprint = hashlib.sha256("|".join(map(str, required)).encode()).hexdigest()[:20]
    existing = read_assignment()
    current = existing.get("nova_codex_assignment") if isinstance(existing, dict) else None
    if isinstance(current, dict) and current.get("assignment_id") == f"nova_codex_{fingerprint}":
        return {"status": "idempotent_existing", **current}
    assignment = {
        "schema_version": "nexus.nova-codex-assignment.v1",
        "assignment_id": f"nova_codex_{fingerprint}",
        "parent_objective_id": parent_objective_id,
        "blocking_work_id": blocking_work_id,
        "defect_id": defect_id,
        "defect_summary": defect_summary,
        "affected_component": affected_component,
        "acceptance_criteria": list(acceptance_criteria),
        "test_requirements": list(test_requirements),
        "allowed_scope": list(allowed_scope),
        "prohibited_actions": list(prohibited_actions),
        "risk_class": risk_class,
        "requested_by": "nova",
        "return_to": "nova",
        "resume_objective_on_success": True,
        "status": "QUEUED",
        "created_at": _now(),
        "updated_at": _now(),
        "worker_id": None,
        "completion_receipt_id": None,
    }
    _write({"schema_version": "nexus.coding-worker-handoff.v2", "nova_codex_assignment": assignment})
    return {"status": "queued", **assignment}


def claim_assignment(*, worker_id: str = "codex") -> dict[str, Any]:
    payload = read_assignment()
    assignment = payload.get("nova_codex_assignment") or {}
    if assignment.get("status") != "QUEUED":
        return {"status": "not_claimable", "assignment": assignment}
    assignment.update({"status": "CLAIMED", "worker_id": worker_id, "claimed_at": _now(), "updated_at": _now()})
    payload["nova_codex_assignment"] = assignment
    _write(payload)
    return {"status": "claimed", **assignment}


def execute_claimed_assignment() -> dict[str, Any]:
    payload = read_assignment()
    assignment = payload.get("nova_codex_assignment") or {}
    if assignment.get("status") != "CLAIMED":
        return {"status": "not_claimed", "assignment_id": assignment.get("assignment_id")}
    from nexus_product_evolution.adapters.builder_adapter import codex_execute
    from nexus_agent_platform.builders.runtime import BuildTaskSpec
    checkpoint = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    task = BuildTaskSpec(
        task_id=assignment["assignment_id"], title=assignment["defect_id"],
        objective=assignment["defect_summary"], repo=str(ROOT), branch="main",
        worktree="ISOLATED_WORKTREE_CREATED_AT_EXECUTION", scope=assignment["allowed_scope"],
        protected_paths=assignment["prohibited_actions"], allowed_paths=assignment["allowed_scope"],
        requirements=assignment["acceptance_criteria"], acceptance_criteria=assignment["acceptance_criteria"],
        tests=assignment["test_requirements"], visual_requirements=False,
        security_constraints=assignment["prohibited_actions"], budget={"cost_ceiling": "ZERO_MODEL_COST", "model_tier": "ZERO_MODEL_COST"},
        timeout_seconds=180, approval_state="governed_nova_codex", retry_policy="bounded", max_retries=0,
        metadata={"assignment_id": assignment["assignment_id"], "starting_commit": checkpoint,
                  "parent_objective_id": assignment["parent_objective_id"]}, previous_failure_delta={})
    assignment.update({"status": "EXECUTING", "execution_started_at": _now(), "updated_at": _now()})
    payload["nova_codex_assignment"] = assignment
    _write(payload)
    result = codex_execute(task)
    receipt_id = f"codex_receipt_{uuid.uuid4().hex}"
    assignment.update({"status": "COMPLETED" if result.get("status") == "success" else "FAILED",
                       "updated_at": _now(), "completion_receipt_id": receipt_id,
                       "completion_receipt": {"receipt_id": receipt_id, "assignment_id": assignment["assignment_id"],
                                               "worker_id": "codex", "result": result, "completed_at": _now()}})
    payload["nova_codex_assignment"] = assignment
    _write(payload)
    return {"status": assignment["status"], **assignment}


__all__ = ["create_assignment", "read_assignment", "claim_assignment", "execute_claimed_assignment", "HANDOFF_PATH"]
