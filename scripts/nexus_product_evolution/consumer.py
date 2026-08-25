"""Receipt-backed Product Evolution handoff for the canonical scheduler.

This is an adapter to the existing Phase 15 dispatch, not a scheduler. It
claims queued receipts under one lock and records an honest blocker when no
bounded execution adapter is registered for that mission.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .adapters.registry import default_registry
from .loop import MissionContract
from .deployment import inspect_netlify_control_plane, verify_release_markers
from .netlify_adapter import deploy_exact_sha, rollback_exact_deploy
from .release import append_release_event, approval_valid, bounded_deploy, repair_approved_release_binding, verify_or_rollback
from .recovery import build_repair_contract, make_failure_receipt

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "reports/product_evolution"
LOCK_PATH = ROOT / "data/runtime/product_evolution_dispatch.lock"
RELEASE_ONLY_STAGES = {"APPROVED_RELEASE_PENDING_DEPLOYMENT", "RELEASE_DISPATCH_CLAIMED", "DEPLOYING", "PRODUCTION_VERIFY"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _claim(path: Path, scheduler_instance: str) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    result = value.get("result") or {}
    if result.get("current_stage") in RELEASE_ONLY_STAGES:
        return {"mission_id": result.get("mission_id"), "status": result.get("status"), "claimed": False, "reason": "RELEASE_ONLY_STATE"}
    if result.get("status") != "QUEUED":
        return {"mission_id": result.get("mission_id"), "status": result.get("status"), "claimed": False}
    now = _now()
    dispatch = result.get("dispatch") or {}
    result.update({
        "status": "RUNNING",
        "current_stage": "DISPATCH_CLAIMED",
        "updated_at": now,
        "dispatch": {**dispatch, "pickup_state": "PICKED_UP", "claimed_at": now, "scheduler_instance": scheduler_instance, "last_dispatch_observation": now},
    })
    _write(path, {**value, "result": result})
    return {"mission_id": result.get("mission_id"), "status": "RUNNING", "claimed": True, "receipt_path": str(path)}


def _dispatch_approved_release(path: Path, scheduler_instance: str, *, deploy_fn=deploy_exact_sha, verify_fn=verify_release_markers, rollback_fn=rollback_exact_deploy) -> Dict[str, Any]:
    """Claim one approved release through the same canonical consumer lock."""
    value = json.loads(path.read_text(encoding="utf-8"))
    result = value.get("result") or {}
    package = result.get("release") or {}
    if package.get("approval_state") != "APPROVED" or result.get("current_stage") != "APPROVED_RELEASE_PENDING_DEPLOYMENT":
        return {"claimed": False, "mission_id": result.get("mission_id"), "status": result.get("status")}
    retry_count = int(package.get("retry_count") or 0)
    retry_auth = package.get("second_retry_authorization") or {}
    if retry_count >= 1 and retry_auth.get("status") != "PENDING":
        return {"claimed": False, "mission_id": result.get("mission_id"), "status": result.get("status"), "reason": "RETRY_LIMIT_REACHED"}
    now = _now()
    if retry_auth.get("status") == "PENDING":
        valid, reason = approval_valid(result, release_id=str(package.get("release_id")), commit=str(package.get("release_candidate_commit")), target=str(package.get("target_url")))
        if not valid:
            result["status"] = "BLOCKED"
            result["current_stage"] = "BLOCKED"
            result["blocker"] = reason
            _write(path, {**value, "result": result})
            return {"claimed": False, "mission_id": result.get("mission_id"), "status": "BLOCKED", "reason": reason}
        expires = retry_auth.get("expires_at")
        if not expires:
            reason = "RETRY_AUTHORIZATION_EXPIRY_MISSING"
        else:
            try:
                reason = "RETRY_AUTHORIZATION_EXPIRED" if datetime.fromisoformat(str(expires)) <= datetime.now(timezone.utc) else ""
            except ValueError:
                reason = "RETRY_AUTHORIZATION_EXPIRY_INVALID"
        if reason:
            result["status"] = "BLOCKED"
            result["current_stage"] = "BLOCKED"
            result["blocker"] = reason
            result["release"] = {**package, "second_retry_authorization": {**retry_auth, "status": "INVALIDATED", "invalidated_at": now, "invalidation_reason": reason}}
            result = append_release_event(result, "SECOND_RETRY_BLOCKED", release_id=package.get("release_id"), reason=reason)
            _write(path, {**value, "result": result})
            return {"claimed": False, "mission_id": result.get("mission_id"), "status": "BLOCKED", "reason": reason}
        try:
            production = inspect_netlify_control_plane()
        except Exception as exc:
            production = {"published_deploy_id": "UNKNOWN", "published_commit": "UNKNOWN", "probe_error": type(exc).__name__}
        published_deploy = str(production.get("published_deploy_id") or "UNKNOWN")
        published_commit = str(production.get("published_commit") or "UNKNOWN")
        bound_deploy = str(retry_auth.get("current_production_deploy") or "UNKNOWN")
        candidate = str(package.get("release_candidate_commit") or "UNKNOWN")
        revalidation = {"checked_at": now, "published_deploy_id": published_deploy, "published_commit": published_commit, "candidate_published": published_commit == candidate}
        if published_deploy != bound_deploy or published_deploy == "UNKNOWN" or published_commit == candidate:
            reason = "PRODUCTION_STATE_CHANGED_AFTER_RETRY_AUTHORIZATION" if published_deploy != bound_deploy or published_commit == candidate else "PRODUCTION_STATE_UNKNOWN_AFTER_RETRY_AUTHORIZATION"
            result["status"] = "BLOCKED"
            result["current_stage"] = "BLOCKED"
            result["blocker"] = reason
            result["release"] = {**package, "production_state_revalidated_at_dispatch": revalidation, "second_retry_authorization": {**retry_auth, "status": "INVALIDATED", "invalidated_at": now, "invalidation_reason": reason}}
            result = append_release_event(result, "SECOND_RETRY_BLOCKED", release_id=package.get("release_id"), reason=reason, production_state=revalidation)
            _write(path, {**value, "result": result})
            return {"claimed": False, "mission_id": result.get("mission_id"), "status": "BLOCKED", "reason": reason}
        package = {**package, "retry_count": retry_count + 1, "production_state_revalidated_at_dispatch": revalidation, "second_retry_authorization": {**retry_auth, "status": "CONSUMED", "consumed_at": now}}
        result["release"] = package
        result = append_release_event(result, "SECOND_RETRY_CONSUMED", release_id=package.get("release_id"), attempt_number=2, consumed_at=now, production_state=revalidation)
    result = append_release_event(result, "RELEASE_DISPATCH_CLAIMED", release_id=package.get("release_id"), scheduler_instance=scheduler_instance)
    result["current_stage"] = "RELEASE_DISPATCH_CLAIMED"
    result["release"] = {**package, "dispatch_claimed_at": now, "dispatch_scheduler": scheduler_instance}
    _write(path, {**value, "result": result})
    result["current_stage"] = "DEPLOYING"
    result = append_release_event(result, "DEPLOYMENT_STARTED", release_id=package.get("release_id"), commit=package.get("release_candidate_commit"), target=package.get("target_url"))
    deployment = bounded_deploy(result, release_id=str(package.get("release_id")), commit=str(package.get("release_candidate_commit")), target=str(package.get("target_url")), deploy_fn=deploy_fn)
    if deployment.get("status") != "DEPLOYED":
        result["status"] = "BLOCKED"
        result["current_stage"] = "BLOCKED"
        result["blocker"] = deployment.get("reason") or (deployment.get("outcome") or {}).get("reason") or "DEPLOYMENT_BLOCKED"
        failure = make_failure_receipt({
            "failure_code": result["blocker"],
            "phase": deployment.get("phase", "deployment"),
            "release_id": package.get("release_id"),
            "candidate_sha": package.get("release_candidate_commit"),
            "candidate_deploy_id": (deployment.get("outcome") or {}).get("deploy_id", "UNKNOWN"),
            "production_deploy_before": package.get("rollback_deploy_id", "UNKNOWN"),
            "production_deploy_after": package.get("production_deploy_id", "UNKNOWN"),
            "reversible": bool(package.get("rollback_executable") == "PASS"),
            "evidence": {"deployment_status": deployment.get("status"), "reason": result["blocker"]},
        })
        repair_contract = build_repair_contract(failure)
        result["release"] = {
            **result.get("release", {}),
            "deployment_result": deployment,
            "failure_receipt": failure,
            "recovery": {
                "eligible": repair_contract is not None,
                "status": "PENDING_INTERNAL_REPAIR" if repair_contract else "HUMAN_OR_GOVERNANCE_REQUIRED",
                "failure_signature": failure.get("signature"),
                "max_repair_cycles": repair_contract.max_repair_cycles if repair_contract else 0,
            },
        }
        _write(path, {**value, "result": result})
        return {"claimed": True, "mission_id": result.get("mission_id"), "status": "BLOCKED", "reason": result["blocker"]}
    result["current_stage"] = "PRODUCTION_VERIFY"
    result["release"] = {
        **(result.get("release") or {}),
        "deployment_result": deployment,
        "attempted_candidate_commit": package.get("release_candidate_commit"),
    }
    verify_kwargs = {
        "expected_deploy_id": ((deployment.get("outcome") or {}).get("deploy_id") if isinstance(deployment.get("outcome"), dict) else None),
        "deployment_outcome": deployment.get("outcome"),
    }
    try:
        parameters = inspect.signature(verify_fn).parameters
        supports_extended = any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()) or any(name in parameters for name in verify_kwargs)
    except (TypeError, ValueError):
        supports_extended = False
    if supports_extended:
        observed = verify_fn({**value, "result": result}, str(package.get("release_candidate_commit")), target=str(package.get("target_url")), **verify_kwargs)
    else:
        observed = verify_fn({**value, "result": result}, str(package.get("release_candidate_commit")), target=str(package.get("target_url")))
    verified = verify_or_rollback(result, release_id=str(package.get("release_id")), expected_commit=str(package.get("release_candidate_commit")), observed=observed, rollback_fn=rollback_fn)
    result = verified.get("result") or result
    result["release"] = {**result.get("release", {}), "deployment_result": deployment, "verification_observed": observed}
    _write(path, {**value, "result": result})
    return {"claimed": True, "mission_id": result.get("mission_id"), "status": verified.get("status"), "checks": verified.get("checks")}


def prepare_approved_release_retry(mission_id: str, *, release_id: str, candidate_commit: str, target: str, current_production_deploy: str, candidate_published: bool = False) -> Dict[str, Any]:
    """Restore one unchanged, approved release to the canonical queue.

    This function only repairs receipt binding and eligibility.  It never
    invokes the consumer, deploy adapter, scheduler, or rollback adapter.
    """
    path = RECEIPT_DIR / f"{mission_id}.json"
    if not path.exists():
        return {"status": "NOT_FOUND", "mission_id": mission_id}
    value = json.loads(path.read_text(encoding="utf-8"))
    result = value.get("result") or {}
    package = result.get("release") or {}
    if (result.get("status"), result.get("current_stage")) != ("BLOCKED", "BLOCKED"):
        return {"status": "NOT_ELIGIBLE", "reason": "RELEASE_NOT_BLOCKED"}
    if (package.get("release_id"), package.get("release_candidate_commit"), package.get("target_url")) != (release_id, candidate_commit, target):
        return {"status": "REJECTED", "reason": "RELEASE_BINDING_MISMATCH"}
    if package.get("approval_state") != "APPROVED":
        return {"status": "REJECTED", "reason": "APPROVAL_REQUIRED"}
    if package.get("precheck_status") != "PASS" or package.get("rollback_executable") != "PASS":
        return {"status": "BLOCKED", "reason": "RELEASE_PRECHECK_NOT_PASS"}
    if candidate_published or current_production_deploy != "6a8afe4e3f3b97d82a138f28":
        return {"status": "BLOCKED", "reason": "PRODUCTION_MUTATION_UNCERTAIN"}
    events = list(result.get("execution_history") or [])
    if any(item.get("event") in {"DEPLOYMENT_COMPLETE", "ROLLBACK_STARTED", "ROLLBACK_COMPLETE"} for item in events):
        return {"status": "BLOCKED", "reason": "PRIOR_PRODUCTION_MUTATION"}
    if int(package.get("retry_count") or 0) >= 1:
        return {"status": "BLOCKED", "reason": "RETRY_LIMIT_REACHED"}
    repaired = repair_approved_release_binding(result)
    if repaired.get("status") not in {"REPAIRED", "UNCHANGED"}:
        return repaired
    result = repaired.get("result") or result
    valid, reason = approval_valid(result, release_id=release_id, commit=candidate_commit, target=target)
    if not valid:
        return {"status": "BLOCKED", "reason": reason}
    now = _now()
    result = append_release_event(result, "RELEASE_RETRY_READY", release_id=release_id, candidate=candidate_commit, target=target, retry_count=1, reason="EXACT_SHA_ADAPTER_REPAIRED")
    result["status"] = "PARTIAL"
    result["current_stage"] = "APPROVED_RELEASE_PENDING_DEPLOYMENT"
    result["blocker"] = None
    result["release"] = {**(result.get("release") or {}), "retry_count": 1, "retry_ready_at": now, "deployment_result": {"status": "BLOCKED", "reason": "MATERIAL_RELEASE_CHANGE", "retry_repaired": True}}
    result["dispatch"] = {**(result.get("dispatch") or {}), "pickup_state": "AWAITING_PHASE15", "retry_ready_at": now}
    _write(path, {**value, "result": result})
    return {"status": "RETRY_READY", "mission_id": mission_id, "release_id": release_id, "retry_count": 1, "current_stage": result["current_stage"], "receipt_path": str(path)}


def resume_mission(mission_id: str, *, reason: str = "bounded execution adapter registered") -> Dict[str, Any]:
    """Resume the same blocked receipt without creating a descendant mission."""
    path = RECEIPT_DIR / f"{mission_id}.json"
    if not path.exists():
        return {"status": "NOT_FOUND", "mission_id": mission_id}
    value = json.loads(path.read_text(encoding="utf-8"))
    result = value.get("result") or {}
    if result.get("status") not in {"BLOCKED", "PARTIAL"}:
        return {"status": result.get("status"), "mission_id": mission_id}
    now = _now()
    history = list(result.get("execution_history") or [])
    history.append({"at": now, "event": "RESUME", "prior_status": result.get("status"), "prior_blocker": result.get("blocker"), "reason": reason})
    result.update({"status": "QUEUED", "current_stage": "RESUMED", "blocker": None, "updated_at": now, "execution_history": history})
    dispatch = result.get("dispatch") or {}
    result["dispatch"] = {**dispatch, "resume_requested_at": now, "resume_reason": reason}
    _write(path, {**value, "result": result})
    return {"status": "QUEUED", "mission_id": mission_id, "receipt_path": str(path)}


def consume_queued_missions(*, scheduler_instance: str, receipt_dir: Path = RECEIPT_DIR) -> Dict[str, Any]:
    """Claim and execute each queued mission through an explicit adapter."""
    receipt_dir.mkdir(parents=True, exist_ok=True)
    claimed: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"consumer": "phase15_product_evolution_dispatch", "status": "SKIPPED_LOCKED", "claimed": [], "blocked": []}
        for path in sorted(receipt_dir.glob("*.json")):
            try:
                item = _claim(path, scheduler_instance)
            except (OSError, ValueError, TypeError):
                continue
            if not item.get("claimed"):
                continue
            claimed.append(item)
            value = json.loads(path.read_text(encoding="utf-8"))
            result = value.get("result") or {}
            now = _now()
            history = list(result.get("execution_history") or [])
            history.append({"at": now, "event": "CLAIM", "status": "RUNNING", "scheduler_instance": scheduler_instance})
            try:
                contract = MissionContract(**(value.get("contract") or {}))
                adapter = default_registry().resolve(contract)
            except (TypeError, ValueError):
                contract = None
                adapter = None
            if adapter is None:
                result.update({"status": "BLOCKED", "current_stage": "DISPATCH_CLAIMED", "blocker": "EXECUTION_ADAPTER_MISSING", "updated_at": now, "execution_history": history})
                dispatch = result.get("dispatch") or {}
                result["dispatch"] = {**dispatch, "last_dispatch_observation": "Claimed by canonical Phase 15 dispatcher; no bounded Product Evolution execution adapter is registered."}
                _write(path, {**value, "result": result})
                blocked.append({"mission_id": result.get("mission_id"), "status": "BLOCKED", "reason": result["blocker"]})
                continue
            execution = adapter.execute(str(result.get("mission_id")), contract)
            final_status = str(execution.get("status") or "FAIL")
            history.append({"at": _now(), "event": "ADAPTER_EXECUTION", "adapter_id": adapter.adapter_id, "status": final_status, "blocker": execution.get("blocker")})
            result.update({"status": final_status, "current_stage": "HUMAN_GATE" if final_status == "PARTIAL" else "COMPLETE", "blocker": execution.get("blocker"), "updated_at": _now(), "execution": execution, "execution_history": history})
            dispatch = result.get("dispatch") or {}
            result["dispatch"] = {**dispatch, "adapter_id": adapter.adapter_id, "last_dispatch_observation": "Adapter executed by canonical Phase 15 dispatcher."}
            _write(path, {**value, "result": result})
            if final_status in {"BLOCKED", "FAIL"}:
                blocked.append({"mission_id": result.get("mission_id"), "status": final_status, "reason": execution.get("blocker") or "ADAPTER_EXECUTION_FAILED"})
        for path in sorted(receipt_dir.glob("*.json")):
            try:
                release_item = _dispatch_approved_release(path, scheduler_instance)
            except (OSError, ValueError, TypeError):
                continue
            if release_item.get("claimed"):
                claimed.append(release_item)
                if release_item.get("status") == "BLOCKED":
                    blocked.append({"mission_id": release_item.get("mission_id"), "status": "BLOCKED", "reason": release_item.get("reason", "RELEASE_BLOCKED")})
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return {"consumer": "phase15_product_evolution_dispatch", "status": "COMPLETED", "claimed": claimed, "blocked": blocked}
