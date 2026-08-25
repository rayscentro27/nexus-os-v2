"""Bounded, non-production recovery contracts for release failures.

This module describes and orchestrates internal release-pipeline repair only.
It never approves, deploys, retries production, or accepts model commands.
Production authority remains in the existing approved-release dispatcher.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

from nexus_agent_platform.builders.runtime import BuildTaskSpec


MAX_REPAIR_CYCLES = 2
REPAIRABLE_CLASSES = {
    "CANDIDATE_URL", "DEPLOY_METADATA", "CANDIDATE_HTTP", "CORS",
    "RECEIPT_RECONCILIATION", "INSPECTION_SCOPING",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def classify_release_failure(failure: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify a bounded failure from its persisted code and phase."""
    code = _text(failure.get("failure_code") or failure.get("reason") or failure.get("blocker")).upper()
    phase = _text(failure.get("phase")).lower()
    if "AUTH" in code or "CREDENTIAL" in code:
        failure_class = "DEPLOY_AUTH"
    elif "CLI" in code or "EXECUTABLE" in code:
        failure_class = "DEPLOY_CLI"
    elif "BUILD" in code or phase in {"npm_ci", "npm_build", "build"}:
        failure_class = "DEPLOY_BUILD"
    elif "UPLOAD" in code or "DEPLOY_FAILED" in code:
        failure_class = "DEPLOY_UPLOAD"
    elif "METADATA" in code:
        failure_class = "DEPLOY_METADATA"
    elif "URL" in code:
        failure_class = "CANDIDATE_URL"
    elif "HTTP" in code:
        failure_class = "CANDIDATE_HTTP"
    elif "ARTIFACT" in code:
        failure_class = "CANDIDATE_ARTIFACT"
    elif "SHA" in code:
        failure_class = "BUILD_SHA"
    elif "VOICE" in code:
        failure_class = "VOICE_CONTRACT"
    elif "CORS" in code:
        failure_class = "CORS"
    elif "PUBLISH" in code:
        failure_class = "NETLIFY_PUBLISH"
    elif "PROPAGATION" in code:
        failure_class = "PRODUCTION_PROPAGATION"
    elif "PRODUCTION" in code:
        failure_class = "PRODUCTION_ARTIFACT"
    elif "ROLLBACK" in code:
        failure_class = "ROLLBACK"
    elif "RECEIPT" in code:
        failure_class = "RECEIPT_RECONCILIATION"
    elif "SCOP" in code:
        failure_class = "INSPECTION_SCOPING"
    else:
        failure_class = "UNKNOWN"
    repairable = failure_class in REPAIRABLE_CLASSES
    return {
        "failure_class": failure_class,
        "failure_code": code or "UNKNOWN",
        "phase": phase or "UNKNOWN",
        "repairable_internal": repairable,
        "human_required": not repairable,
    }


def failure_signature(failure: Mapping[str, Any]) -> str:
    classified = classify_release_failure(failure)
    body = {
        "failure_class": classified["failure_class"],
        "failure_code": classified["failure_code"],
        "component": failure.get("component") or failure.get("phase") or "UNKNOWN",
        "release_id": failure.get("release_id", "UNKNOWN"),
        "candidate_sha": failure.get("candidate_sha") or failure.get("commit") or "UNKNOWN",
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def make_failure_receipt(failure: Mapping[str, Any]) -> Dict[str, Any]:
    classified = classify_release_failure(failure)
    return {
        **classified,
        "release_id": failure.get("release_id", "UNKNOWN"),
        "candidate_sha": failure.get("candidate_sha") or failure.get("commit", "UNKNOWN"),
        "candidate_deploy_id": failure.get("candidate_deploy_id", "UNKNOWN"),
        "production_deploy_before": failure.get("production_deploy_before", "UNKNOWN"),
        "production_deploy_after": failure.get("production_deploy_after", "UNKNOWN"),
        "reversible": bool(failure.get("reversible", False)),
        "evidence": dict(failure.get("evidence") or {}),
        "timestamp": failure.get("timestamp") or _now(),
        "signature": failure_signature(failure),
    }


@dataclass(frozen=True)
class RepairContract:
    problem: str
    root_cause_evidence: Dict[str, Any]
    allowed_paths: list[str]
    protected_paths: list[str]
    acceptance_criteria: list[str]
    tests: list[str]
    safety_constraints: list[str]
    max_repair_cycles: int = MAX_REPAIR_CYCLES

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem": self.problem,
            "root_cause_evidence": dict(self.root_cause_evidence),
            "allowed_paths": list(self.allowed_paths),
            "protected_paths": list(self.protected_paths),
            "acceptance_criteria": list(self.acceptance_criteria),
            "tests": list(self.tests),
            "safety_constraints": list(self.safety_constraints),
            "max_repair_cycles": self.max_repair_cycles,
        }


def build_repair_contract(failure: Mapping[str, Any]) -> Optional[RepairContract]:
    receipt = make_failure_receipt(failure)
    if not receipt["repairable_internal"]:
        return None
    return RepairContract(
        problem=f"Repair bounded release pipeline failure {receipt['failure_code']} for {receipt['release_id']}",
        root_cause_evidence=receipt,
        allowed_paths=[
            "scripts/nexus_product_evolution/deployment.py",
            "scripts/nexus_product_evolution/netlify_adapter.py",
            "scripts/nexus_product_evolution/release.py",
            "scripts/nexus_product_evolution/telegram_control.py",
            "scripts/nexus_product_evolution/recovery.py",
            "scripts/nexus_product_evolution/tests/",
        ],
        protected_paths=[
            "runtime.env", ".env", "secrets/", "supabase/", "src/client-v2/",
            "src/clientPortal/", "production agent identities",
        ],
        acceptance_criteria=[
            "reproduce the recorded failure with a deterministic fixture",
            "preserve exact-SHA approval and production authority boundaries",
            "pass focused release and deployment tests",
            "pass exact-SHA build and secret scan without production mutation",
            "prepare a new immutable candidate only after verified source repair",
        ],
        tests=[
            "focused Product Evolution release tests",
            "deployment parser and receipt reconciliation tests",
            "exact-SHA build preflight",
            "draft artifact verification only",
        ],
        safety_constraints=[
            "no production deploy, rollback, approval, or retry",
            "no arbitrary shell or model-generated command",
            "no secrets or client data in prompts, artifacts, or logs",
            "stop for Ray approval at RELEASE_CANDIDATE_READY",
        ],
    )


def repair_task_spec(failure: Mapping[str, Any], *, starting_commit: str, mission_id: str) -> Optional[BuildTaskSpec]:
    contract = build_repair_contract(failure)
    if contract is None:
        return None
    classified = classify_release_failure(failure)
    return BuildTaskSpec(
        task_id=f"release_repair_{failure_signature(failure)[:16]}",
        title=f"Bounded release repair: {classified['failure_code']}",
        objective=contract.problem,
        repo="NEXUS_REPOSITORY",
        branch="main",
        worktree="ISOLATED_WORKTREE_REQUIRED",
        scope=contract.allowed_paths,
        protected_paths=contract.protected_paths,
        allowed_paths=contract.allowed_paths,
        requirements=[contract.problem, "Do not change the approved production candidate payload."],
        acceptance_criteria=contract.acceptance_criteria,
        tests=contract.tests,
        visual_requirements=False,
        security_constraints=contract.safety_constraints,
        budget={"cost_ceiling": "$0 unless separately approved", "model_tier": "ZERO_MODEL_COST"},
        timeout_seconds=900,
        approval_state="governed_internal_release_repair",
        retry_policy="bounded",
        max_retries=MAX_REPAIR_CYCLES - 1,
        metadata={"mission_id": mission_id, "starting_commit": starting_commit, "failure_signature": failure_signature(failure)},
        previous_failure_delta=make_failure_receipt(failure),
    )


def run_recovery_cycle(
    failure: Mapping[str, Any],
    *,
    prior_cycles: int,
    build_fn: Callable[[RepairContract], Mapping[str, Any]],
    test_fn: Callable[[RepairContract], Mapping[str, Any]],
    preflight_fn: Callable[[RepairContract], Mapping[str, Any]],
    draft_verify_fn: Callable[[RepairContract], Mapping[str, Any]],
    candidate_fn: Callable[[RepairContract], Mapping[str, Any]],
) -> Dict[str, Any]:
    """Run at most one deterministic internal repair step; no production calls."""
    receipt = make_failure_receipt(failure)
    if not receipt["repairable_internal"]:
        return {"status": "HUMAN_REQUIRED", "failure": receipt}
    if prior_cycles >= MAX_REPAIR_CYCLES:
        return {"status": "REPAIR_EXHAUSTED", "failure": receipt, "repair_cycles": prior_cycles}
    contract = build_repair_contract(failure)
    assert contract is not None
    stages = {
        "build": dict(build_fn(contract)),
        "tests": dict(test_fn(contract)),
    }
    if stages["build"].get("status") != "PASS" or stages["tests"].get("status") != "PASS":
        return {"status": "REPAIR_FAILED", "failure": receipt, "repair_contract": contract.to_dict(), "stages": stages, "repair_cycles": prior_cycles + 1}
    stages["preflight"] = dict(preflight_fn(contract))
    if stages["preflight"].get("status") != "PASS":
        return {"status": "REPAIR_FAILED", "failure": receipt, "repair_contract": contract.to_dict(), "stages": stages, "repair_cycles": prior_cycles + 1}
    stages["draft_verification"] = dict(draft_verify_fn(contract))
    if stages["draft_verification"].get("status") != "PASS":
        return {"status": "REPAIR_FAILED", "failure": receipt, "repair_contract": contract.to_dict(), "stages": stages, "repair_cycles": prior_cycles + 1}
    candidate = dict(candidate_fn(contract))
    if candidate.get("status") != "PASS":
        return {"status": "REPAIR_FAILED", "failure": receipt, "repair_contract": contract.to_dict(), "stages": stages, "candidate": candidate, "repair_cycles": prior_cycles + 1}
    return {
        "status": "RELEASE_CANDIDATE_READY",
        "failure": receipt,
        "repair_contract": contract.to_dict(),
        "stages": stages,
        "candidate": candidate,
        "repair_cycles": prior_cycles + 1,
        "ray_interruption": "APPROVAL_ONLY",
    }
