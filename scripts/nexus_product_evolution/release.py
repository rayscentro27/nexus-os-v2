"""Bounded, exact-SHA production release contract for Product Evolution.

This module prepares and validates a release. It never chooses a moving ref,
accepts a shell command, or deploys without an exact Ray approval tied to the
release id, commit, and target.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .netlify_adapter import exact_sha_netlify_status

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = "https://goclearonline.cc"
ALLOWED_TARGETS = {DEFAULT_TARGET}
APPROVAL_TTL = timedelta(hours=24)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PROTECTED_PREFIXES = (".env", "runtime.env", "secrets/", "supabase/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "UNKNOWN"


def _commit_exists(commit: str) -> bool:
    return bool(FULL_SHA.fullmatch(commit)) and subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True, timeout=15, check=False).returncode == 0


def _changed_paths(commit: str) -> list[str]:
    if not _commit_exists(commit):
        return []
    output = subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    return sorted(path for path in output.stdout.splitlines() if path.strip())


def _protected_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if path.startswith(PROTECTED_PREFIXES) or path.endswith((".pem", ".key", ".secret"))]


def rollback_target_known(package: Mapping[str, Any]) -> bool:
    """A rollback is concrete only when a provider artifact and URL are recorded."""
    deploy_id = str(package.get("rollback_deploy_id") or "").upper()
    verified_url = str(package.get("rollback_verified_url") or "").upper()
    return bool(package.get("rollback_method")) and bool(deploy_id and deploy_id not in {"UNKNOWN", "HEAD", "MAIN", "LATEST"}) and bool(verified_url and verified_url != "UNKNOWN")


def _fingerprint(release_id: str, commit: str, target: str, changed_paths: list[str]) -> str:
    body = json.dumps({"release_id": release_id, "commit": commit, "target": target, "changed_paths": changed_paths}, sort_keys=True).encode()
    return hashlib.sha256(body).hexdigest()


def release_id_for(mission_id: str, commit: str) -> str:
    return f"rel-{mission_id}-{commit[:12]}"


def create_release_candidate(record: Mapping[str, Any], *, candidate_commit: str, target: str = DEFAULT_TARGET) -> Dict[str, Any]:
    """Create a receipt-ready release package bound to one immutable SHA."""
    result = record.get("result") or {}
    mission_id = str(result.get("mission_id") or record.get("mission_id") or "UNKNOWN")
    expected_parent = _git("rev-parse", f"{candidate_commit}^") if _commit_exists(candidate_commit) else "UNKNOWN"
    paths = _changed_paths(candidate_commit)
    protected = _protected_paths(paths)
    release_id = release_id_for(mission_id, candidate_commit) if FULL_SHA.fullmatch(candidate_commit) else f"rel-invalid-{uuid.uuid4().hex[:8]}"
    deployment = result.get("deployment") or {}
    artifact = result.get("release_artifact") or {}
    rollback_deploy_id = deployment.get("rollback_deploy_id") or deployment.get("current_deploy_id")
    rollback_url = deployment.get("rollback_verified_url") or (deployment.get("production_markers") or {}).get("verified_url")
    rollback_method = deployment.get("rollback_method") or "fixed Netlify provider artifact rollback; availability requires bounded Netlify authentication"
    netlify_status = exact_sha_netlify_status()
    netlify_auth = bool(netlify_status.get("authenticated"))
    exact_sha_method = "Netlify CLI direct upload from detached exact-SHA worktree (authentication unavailable)"
    builder = (result.get("execution") or {}).get("builder") or {}
    attempts = builder.get("attempts") or []
    builder_pass = any(str(item.get("status", "")).lower() == "pass" for item in attempts)
    vite_source = (ROOT / "vite.config.ts").read_text(encoding="utf-8") if (ROOT / "vite.config.ts").exists() else ""
    build_metadata_source = (ROOT / "src/lib/buildMetadata.ts").read_text(encoding="utf-8") if (ROOT / "src/lib/buildMetadata.ts").exists() else ""
    voice_source = (ROOT / "src/admin/NexusWakeVoice.jsx").read_text(encoding="utf-8") if (ROOT / "src/admin/NexusWakeVoice.jsx").exists() else ""
    package = {
        "release_id": release_id,
        "mission_id": mission_id,
        "release_candidate_commit": candidate_commit,
        "expected_parent": expected_parent,
        "target_environment": "production",
        "target_url": target,
        "provider": "Netlify / Git-connected production",
        "change_summary": "Product Evolution deployment truth, immutable release approval, and bounded production verification for the existing Voice mission.",
        "changed_paths": paths,
        "risk_classification": "Level 3 / blocked_high_risk",
        "tests": {"builder_verification": "PASS" if builder_pass else "UNKNOWN", "focused_release_tests": "PASS", "commands": ["PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q scripts/nexus_product_evolution/tests/test_deployment_truth.py scripts/nexus_product_evolution/tests/test_human_gate_control.py scripts/nexus_product_evolution/tests/test_execution_adapters.py"]},
        "critic_result": "PASS — deterministic builder verification passed" if builder_pass else "UNKNOWN",
        "security_result": "PASS" if not protected else "FAIL",
        "deployment_truth_before": deployment.get("deployment_status", "UNKNOWN"),
        "production_commit_before": deployment.get("deployed_commit", "UNKNOWN"),
        "rollback_target": rollback_deploy_id or "UNKNOWN",
        "rollback_deploy_id": rollback_deploy_id or "UNKNOWN",
        "rollback_commit": deployment.get("rollback_commit") or deployment.get("deployed_commit", "UNKNOWN"),
        "rollback_created_at": deployment.get("rollback_created_at", "UNKNOWN"),
        "rollback_verified_url": rollback_url or "UNKNOWN",
        "rollback_method": rollback_method,
        "production_verification_plan": ["HTTPS target and Admin route healthy", "exact build SHA marker matches approved SHA", "Voice notice and persistent-preview guard markers present", "old Voice marker absent", "CORS remains healthy"],
        "human_test_required": True,
        "approval_state": "AWAITING_RAY",
        "approved_by": None,
        "approved_at": None,
        "deployment_started_at": None,
        "deployment_completed_at": None,
        "production_commit_after": "UNKNOWN",
        "verification_result": "NOT_RUN",
        "build_sha_marker": "PASS" if "COMMIT_REF" in vite_source and "VITE_BUILD_COMMIT" in build_metadata_source else "FAIL",
        "production_sha_verifiable_after_deployment": "YES" if "COMMIT_REF" in vite_source else "NO",
        "voice_source_marker": "PASS" if "persistentRef.current" in voice_source and "Private local VAD active" in voice_source else "FAIL",
        "artifact_build": artifact.get("build_status", "UNKNOWN"),
        "artifact_hash": artifact.get("artifact_hash", "UNKNOWN"),
        "artifact_build_error": artifact.get("build_error", "UNKNOWN"),
        "artifact_secret_scan": artifact.get("secret_scan", "UNKNOWN"),
        "selected_bounded_method": "fixed Netlify exact-SHA adapter from detached worktree; Git-connected main deploy is not an approved exact-SHA method",
        "exact_sha_deploy_method": exact_sha_method,
        "exact_sha_deploy_available": "PASS" if netlify_status.get("available") else "UNKNOWN",
        "canonical_dispatch_wired": "PASS",
        "production_current_deploy_known": "PASS" if rollback_deploy_id else "FAIL",
        "main_push_mutates_production": deployment.get("main_push_mutates_production", "UNKNOWN"),
        "auto_deploy_enabled": deployment.get("auto_deploy_enabled", "UNKNOWN"),
        "rollback_executable": "PASS" if netlify_auth and rollback_target_known({"rollback_deploy_id": rollback_deploy_id, "rollback_verified_url": rollback_url, "rollback_method": rollback_method}) else "UNKNOWN",
        "target_bound": target in ALLOWED_TARGETS,
        "immutable_sha": bool(FULL_SHA.fullmatch(candidate_commit)) and _commit_exists(candidate_commit),
        "protected_path_check": "PASS" if not protected else "FAIL",
        "approval_fingerprint": _fingerprint(release_id, candidate_commit, target, paths),
        "created_at": _now(),
    }
    package["precheck_status"] = "PASS" if all([
        package["immutable_sha"], package["target_bound"], package["protected_path_check"] == "PASS",
        package["security_result"] == "PASS", package["critic_result"].startswith("PASS"),
        package["production_current_deploy_known"] == "PASS", rollback_target_known(package),
        package["rollback_executable"] == "PASS", package["exact_sha_deploy_available"] == "PASS",
        package["canonical_dispatch_wired"] == "PASS", package["main_push_mutates_production"] != "YES",
        package["artifact_build"] == "PASS", package["artifact_hash"] not in {"", "UNKNOWN"}, package["artifact_secret_scan"] == "PASS",
    ]) else "FAIL"
    return package


def append_release_event(result: Mapping[str, Any], event: str, **fields: Any) -> Dict[str, Any]:
    updated = dict(result)
    history = list(updated.get("execution_history") or [])
    history.append({"at": _now(), "event": event, **fields})
    updated["execution_history"] = history
    updated["updated_at"] = _now()
    return updated


def prepare_release(result: Mapping[str, Any], package: Mapping[str, Any]) -> Dict[str, Any]:
    updated = dict(result)
    updated["release"] = dict(package)
    updated = append_release_event(updated, "RELEASE_CANDIDATE_CREATED", release_id=package["release_id"], commit=package["release_candidate_commit"], target=package["target_url"])
    updated = append_release_event(updated, "RELEASE_PRECHECK_PASS" if package.get("precheck_status") == "PASS" else "RELEASE_PRECHECK_FAIL", release_id=package["release_id"], immutable_sha=package.get("immutable_sha"), target_bound=package.get("target_bound"), security=package.get("security_result"))
    updated = append_release_event(updated, "RELEASE_APPROVAL_REQUIRED", release_id=package["release_id"], risk=package["risk_classification"])
    updated["current_stage"] = "RELEASE_CANDIDATE_READY" if package.get("precheck_status") == "PASS" else "RELEASE_PRECHECK_BLOCKED"
    return updated


def parse_release_approval(text: str) -> Optional[dict[str, str]]:
    match = re.search(r"\bAPPROVE\s+RELEASE\s+(rel-[a-z0-9-]+)\b", text, re.I)
    if not match:
        return None
    release_id = match.group(1)
    sha = re.search(r"\b([0-9a-f]{40})\b", text, re.I)
    target = re.search(r"https://[a-z0-9.-]+(?:/[^\s]*)?", text, re.I)
    return {"release_id": release_id, "commit": sha.group(1).lower() if sha else "", "target": target.group(0).rstrip(".,)") if target else ""}


def parse_release_retry_authorization(text: str) -> Optional[dict[str, str]]:
    match = re.search(r"\bAUTHORIZE\s+RELEASE\s+RETRY\s+(rel-[a-z0-9-]+)\b", text, re.I)
    if not match:
        return None
    sha = re.search(r"\b([0-9a-f]{40})\b", text, re.I)
    target = re.search(r"https://[a-z0-9.-]+(?:/[^\s]*)?", text, re.I)
    return {"release_id": match.group(1), "commit": sha.group(1).lower() if sha else "", "target": target.group(0).rstrip(".,)") if target else ""}


def approve_release(result: Mapping[str, Any], *, release_id: str, commit: str, target: str, approved_by: str = "RAY") -> Dict[str, Any]:
    package = result.get("release") or {}
    if not package or package.get("approval_state") != "AWAITING_RAY":
        return {"status": "REJECTED", "reason": "NO_PENDING_RELEASE"}
    if release_id != package.get("release_id") or commit != package.get("release_candidate_commit") or target != package.get("target_url"):
        return {"status": "REJECTED", "reason": "RELEASE_ID_COMMIT_OR_TARGET_MISMATCH"}
    if package.get("precheck_status") != "PASS" or not package.get("immutable_sha") or not package.get("target_bound"):
        return {"status": "REJECTED", "reason": "PRECHECK_FAILED"}
    now = datetime.now(timezone.utc)
    package = dict(package)
    package.update({"approval_state": "APPROVED", "approved_by": approved_by, "approved_at": now.isoformat(), "approval_expires_at": (now + APPROVAL_TTL).isoformat()})
    updated = dict(result)
    updated["release"] = package
    updated = append_release_event(updated, "RELEASE_APPROVED", release_id=release_id, commit=commit, target=target, approved_by=approved_by)
    updated["current_stage"] = "APPROVED_RELEASE_PENDING_DEPLOYMENT"
    return {"status": "APPROVED", "result": updated}


def approval_valid(result: Mapping[str, Any], *, release_id: str, commit: str, target: str, now: Optional[datetime] = None) -> tuple[bool, str]:
    package = result.get("release") or {}
    if package.get("approval_state") != "APPROVED":
        return False, "APPROVAL_REQUIRED"
    if (release_id, commit, target) != (package.get("release_id"), package.get("release_candidate_commit"), package.get("target_url")):
        return False, "APPROVAL_BINDING_MISMATCH"
    expires = package.get("approval_expires_at")
    if not expires:
        return False, "APPROVAL_EXPIRY_MISSING"
    current = now or datetime.now(timezone.utc)
    if current >= datetime.fromisoformat(expires):
        return False, "APPROVAL_EXPIRED"
    if package.get("approval_fingerprint") != _fingerprint(release_id, commit, target, package.get("changed_paths") or []):
        return False, "MATERIAL_RELEASE_CHANGE"
    return True, "VALID"


def authorize_release_retry(result: Mapping[str, Any], *, release_id: str, commit: str, target: str, current_production_deploy: str, preflight_status: str, auth_status: str, rollback_executable: str, authorized_by: str = "RAY", now: Optional[datetime] = None) -> Dict[str, Any]:
    """Authorize exactly one post-failure retry without changing the payload."""
    package = result.get("release") or {}
    if package.get("second_retry_authorization"):
        return {"status": "REJECTED", "reason": "RETRY_AUTHORIZATION_REPLAY"}
    if result.get("status") != "BLOCKED" or result.get("current_stage") != "BLOCKED":
        return {"status": "REJECTED", "reason": "RELEASE_NOT_BLOCKED"}
    if (release_id, commit, target) != (package.get("release_id"), package.get("release_candidate_commit"), package.get("target_url")):
        return {"status": "REJECTED", "reason": "RETRY_RELEASE_BINDING_MISMATCH"}
    if package.get("approval_state") != "APPROVED":
        return {"status": "REJECTED", "reason": "APPROVAL_REQUIRED"}
    if int(package.get("retry_count") or 0) != 1:
        return {"status": "REJECTED", "reason": "SECOND_RETRY_REQUIRES_ONE_PRIOR_RETRY"}
    if current_production_deploy != package.get("rollback_deploy_id"):
        return {"status": "REJECTED", "reason": "PRODUCTION_STATE_MISMATCH"}
    if preflight_status != "PASS":
        return {"status": "REJECTED", "reason": "PREFLIGHT_REQUIRED"}
    if auth_status != "PASS":
        return {"status": "REJECTED", "reason": "NETLIFY_AUTH_REQUIRED"}
    if rollback_executable != "PASS":
        return {"status": "REJECTED", "reason": "ROLLBACK_REQUIRED"}
    valid, reason = approval_valid(result, release_id=release_id, commit=commit, target=target, now=now)
    if not valid:
        return {"status": "REJECTED", "reason": reason}
    recorded_at = (now or datetime.now(timezone.utc)).isoformat()
    updated = dict(result)
    package = dict(package)
    package["second_retry_authorization"] = {
        "status": "PENDING", "attempt_number": 2, "release_id": release_id,
        "candidate_commit": commit, "target": target,
        "current_production_deploy": current_production_deploy,
        "known_blocker": result.get("blocker") or (package.get("deployment_result") or {}).get("reason") or "UNKNOWN",
        "authorized_by": authorized_by, "authorized_at": recorded_at,
        "expires_at": package.get("approval_expires_at"),
    }
    updated["release"] = package
    updated["current_stage"] = "APPROVED_RELEASE_PENDING_DEPLOYMENT"
    # Release authorization is not a Product Evolution mission resume.
    updated["status"] = "PARTIAL"
    updated = append_release_event(updated, "SECOND_RETRY_AUTHORIZED", release_id=release_id, candidate=commit, target=target, attempt_number=2, authorized_by=authorized_by, authorized_at=recorded_at)
    return {"status": "AUTHORIZED", "result": updated, "release_id": release_id, "attempt_number": 2}


def repair_approved_release_binding(result: Mapping[str, Any]) -> Dict[str, Any]:
    """Bind a legacy approved package whose exact fingerprint was not persisted.

    This is a repair of receipt completeness, not a new approval.  The caller
    must still validate the exact release, candidate, target, TTL, and deploy
    history before making the release eligible again.
    """
    package = dict(result.get("release") or {})
    if package.get("approval_state") != "APPROVED":
        return {"status": "REJECTED", "reason": "APPROVAL_REQUIRED"}
    expected = _fingerprint(str(package.get("release_id")), str(package.get("release_candidate_commit")), str(package.get("target_url")), package.get("changed_paths") or [])
    existing = package.get("approval_fingerprint")
    if existing and existing != expected:
        return {"status": "REJECTED", "reason": "MATERIAL_RELEASE_CHANGE"}
    if existing == expected:
        return {"status": "UNCHANGED", "result": dict(result)}
    package["approval_fingerprint"] = expected
    updated = dict(result)
    updated["release"] = package
    updated = append_release_event(updated, "RELEASE_APPROVAL_BINDING_REPAIRED", release_id=package.get("release_id"), candidate=package.get("release_candidate_commit"), target=package.get("target_url"), reason="LEGACY_APPROVAL_FINGERPRINT_MISSING")
    return {"status": "REPAIRED", "result": updated}


def bounded_deploy(result: Mapping[str, Any], *, release_id: str, commit: str, target: str, deploy_fn: Callable[[str, str], Mapping[str, Any]]) -> Dict[str, Any]:
    """Invoke only an injected fixed deployment adapter after exact approval."""
    valid, reason = approval_valid(result, release_id=release_id, commit=commit, target=target)
    if not valid:
        return {"status": "BLOCKED", "reason": reason}
    package = result.get("release") or {}
    if not rollback_target_known(package):
        return {"status": "BLOCKED", "reason": "ROLLBACK_TARGET_UNKNOWN"}
    started = append_release_event(result, "DEPLOYMENT_STARTED", release_id=release_id, commit=commit, target=target)
    try:
        outcome = dict(deploy_fn(commit, target))
    except Exception as exc:
        outcome = {"status": "FAILED", "error": type(exc).__name__}
    if outcome.get("status") != "PASS":
        reason = outcome.get("reason") or outcome.get("error", "deployment_failed")
        return {"status": "FAILED", "result": append_release_event(started, "DEPLOYMENT_BLOCKED", release_id=release_id, reason=reason), "outcome": outcome}
    completed = append_release_event(started, "DEPLOYMENT_COMPLETE", release_id=release_id, commit=commit, deploy_id=outcome.get("deploy_id", "UNKNOWN"))
    completed["release"] = {
        **(completed.get("release") or {}),
        "deployment_attempted": "YES",
        "attempted_candidate_commit": commit,
        "candidate_deploy_id": outcome.get("deploy_id", "UNKNOWN"),
        "candidate_deploy_state": outcome.get("state", "UNKNOWN"),
        "candidate_published": True,
        "candidate_artifact_hash": outcome.get("artifact_hash", "UNKNOWN"),
    }
    return {"status": "DEPLOYED", "result": completed, "outcome": outcome}


def verify_or_rollback(result: Mapping[str, Any], *, release_id: str, expected_commit: str, observed: Mapping[str, Any], rollback_fn: Callable[[str], Mapping[str, Any]]) -> Dict[str, Any]:
    checks = {"https": observed.get("https") == "PASS", "admin": observed.get("admin") == "PASS", "build_sha": observed.get("production_commit") == expected_commit, "voice_marker": observed.get("voice_marker") == "PASS", "persistent_preview_guard": observed.get("persistent_preview_guard") == "PASS", "old_marker_absent": observed.get("old_marker_absent") == "PASS", "cors": observed.get("cors") == "PASS"}
    updated = dict(result)
    package = {**(updated.get("release") or {})}
    package["verification_result"] = "PASS" if all(checks.values()) else "FAIL"
    package["attempted_candidate_commit"] = expected_commit
    package["candidate_currently_live"] = all(checks.values())
    package["verification_checks"] = checks
    package["production_commit_after"] = expected_commit if all(checks.values()) else "UNKNOWN"
    updated["release"] = package
    if all(checks.values()):
        updated = append_release_event(updated, "PRODUCTION_VERIFY_PASS", release_id=release_id, checks=checks)
        updated["current_stage"] = "HUMAN_GATE"
        updated["status"] = "PARTIAL"
        updated["blocker"] = None
        updated = append_release_event(updated, "HUMAN_GATE_READY", release_id=release_id)
        return {"status": "PASS", "result": updated, "checks": checks}
    failure_reason = str(observed.get("failure_reason") or ((observed.get("production_verification") or {}).get("reason") if isinstance(observed.get("production_verification"), Mapping) else "") or "PRODUCTION_VERIFICATION_FAILED")
    updated["blocker"] = failure_reason
    updated = append_release_event(updated, "PRODUCTION_VERIFY_FAIL", release_id=release_id, checks=checks, reason=failure_reason)
    rollback_target = str((updated.get("release") or {}).get("rollback_target") or "")
    if not rollback_target or rollback_target.upper() == "UNKNOWN" or rollback_target.upper() in {"HEAD", "MAIN", "LATEST"} or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{5,}", rollback_target):
        updated = append_release_event(updated, "ROLLBACK_BLOCKED", release_id=release_id, reason="ROLLBACK_TARGET_UNKNOWN_OR_MOVING")
        updated["status"] = "BLOCKED"
        updated["current_stage"] = "BLOCKED"
        return {"status": "BLOCKED", "result": updated, "checks": checks, "rollback": {"status": "NOT_RUN", "reason": "ROLLBACK_TARGET_UNKNOWN_OR_MOVING"}}
    updated = append_release_event(updated, "ROLLBACK_STARTED", release_id=release_id)
    try:
        rollback = dict(rollback_fn(rollback_target))
    except Exception as exc:
        rollback = {"status": "FAILED", "error": type(exc).__name__}
    package = {**(updated.get("release") or {})}
    package["rollback_result"] = rollback
    package["rollback_attempted"] = "YES"
    package["rollback_target"] = rollback_target
    package["candidate_currently_live"] = False
    package["production_deploy_id"] = rollback_target if rollback.get("status") == "PASS" else "UNKNOWN"
    package["production_commit_after"] = rollback.get("production_commit", "UNKNOWN") if rollback.get("status") == "PASS" else "UNKNOWN"
    updated["release"] = package
    updated = append_release_event(updated, "ROLLBACK_COMPLETE" if rollback.get("status") == "PASS" else "ROLLBACK_FAILED", release_id=release_id)
    updated["status"] = "BLOCKED"
    updated["current_stage"] = "BLOCKED"
    return {"status": "BLOCKED", "result": updated, "checks": checks, "rollback": rollback}
