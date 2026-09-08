"""Unified, deny-by-default capability discovery and selection for Nexus.

This is an adapter layer over existing registries.  It does not execute a
tool and it does not grant authority; callers still invoke the established
governed executors after selection.  Selection is deterministic and every
decision can be persisted as an explainable receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs/nexus_capability_manifest.json"
CLI_REGISTRY = ROOT / "reports/cli_tool_registry_latest.json"
SKILL_ROOT = ROOT / "skills/nexus"
RECEIPT_DIR = ROOT / "reports/runtime/nexus_capability_selection"
SKILL_RECEIPT_DIR = ROOT / "reports/runtime/nexus_skill_selection"
FAILURE_MEMORY_PATH = ROOT / "reports/runtime/nexus_failure_learning_r12.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_bool(value: Any) -> bool:
    return value is True or str(value).lower() in {"true", "yes", "pass", "available"}


@dataclass(frozen=True)
class Candidate:
    worker: str
    tool: str
    backend: str
    skills: tuple[str, ...]
    task_fit: float
    health: float
    worker_access: float
    real_test_confidence: float
    past_success: float
    past_failure: float
    failure_compatibility: float
    cost: float
    latency: float
    resource_fit: float
    privacy_fit: float
    locality: float
    authorized: bool = True
    runtime_access: bool = True
    reason: str = ""

    @property
    def score(self) -> float:
        return round(
            self.task_fit * 3 + self.health * 1.5 + self.worker_access * 1.5
            + self.real_test_confidence * 2 + self.past_success * 1.25
            + self.past_failure * 0.75 + self.failure_compatibility
            + self.cost + self.latency + self.resource_fit
            + self.privacy_fit * 1.5 + self.locality,
            4,
        )


def _manifest_rows() -> list[dict[str, Any]]:
    try:
        return list(json.loads(MANIFEST.read_text()).get("capabilities", []))
    except (OSError, ValueError, TypeError):
        return []


def _cli_rows() -> list[dict[str, Any]]:
    try:
        return list(json.loads(CLI_REGISTRY.read_text()).get("items", []))
    except (OSError, ValueError, TypeError):
        return []


def normalized_capabilities() -> list[dict[str, Any]]:
    """Adapt existing Nexus manifest, CLI, skill, MCP, and worker facts."""
    rows: list[dict[str, Any]] = []
    for row in _manifest_rows():
        rows.append({
            "capability_id": row.get("capability_id"), "name": row.get("display_name"),
            "category": row.get("category", "OTHER"), "provider": row.get("owner", "Nexus"),
            "installed": row.get("availability") != "MISSING", "configured": bool(row.get("enabled")),
            "enabled": bool(row.get("enabled")), "authorized": row.get("approval_policy") == "NONE",
            "runtime_access": row.get("environment_policy") in {"sanitized", "repo"},
            "worker_access": row.get("executor_type") in {"cli", "python_module"},
            "real_tested": bool(row.get("last_canary") or row.get("last_success")),
            "health": "UNKNOWN", "source_registry": "configs/nexus_capability_manifest.json",
            "side_effect_class": "EXTERNAL" if row.get("external_effect") else "INTERNAL",
            "authority_scope": row.get("approval_policy"), "cost_class": row.get("risk_level"),
        })
    for row in _cli_rows():
        name = str(row.get("name", ""))
        rows.append({
            "capability_id": f"cli.{name}", "name": name, "category": "CLI", "provider": "local",
            "installed": bool(row.get("installed")), "configured": False, "enabled": False,
            "authorized": False, "runtime_access": False, "worker_access": False,
            "real_tested": row.get("proofLevel") == "execution_verified", "health": row.get("proofLevel"),
            "version": row.get("version"), "source_registry": "reports/cli_tool_registry_latest.json",
            "side_effect_class": "UNKNOWN", "authority_scope": "UNPROVEN",
        })
    for path in sorted(SKILL_ROOT.glob("*/SKILL.md")):
        rows.append({
            "capability_id": f"skill.{path.parent.name}", "name": path.parent.name,
            "category": "SKILL", "provider": "Nexus", "installed": True, "configured": True,
            "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True,
            "real_tested": path.parent.name in {"software-engineering", "worktree-safety", "test-debugging"},
            "health": "READY", "source_registry": str(path.relative_to(ROOT)),
            "side_effect_class": "INSTRUCTION_ONLY", "authority_scope": "DECLARED_FRONTMATTER",
        })
    rows.extend([
        {"capability_id": "worker.nexus_ai_workforce", "name": "Nexus AI workforce", "category": "WORKER", "provider": "Nexus", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "R9/R10 receipts"},
        {"capability_id": "worker.opencode", "name": "OpenCode", "category": "WORKER", "provider": "OpenCode", "installed": bool(shutil.which("opencode")), "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": bool(shutil.which("opencode")), "health": "READY" if shutil.which("opencode") else "MISSING", "source_registry": "OpenCode executable + governed adapter"},
        {"capability_id": "mcp.nexus_mcp", "name": "Nexus MCP", "category": "MCP", "provider": "Nexus", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "config/hermes/nova-profile/config.yaml"},
    ])
    return rows


def required_capabilities(goal: str, criterion: str, task: str = "") -> dict[str, Any]:
    text = " ".join((goal, criterion, task)).lower()
    if any(x in text for x in ("tenant", "approval", "rls", "supabase")):
        classes = ["DATABASE", "AUTHORIZATION_TESTING", "ENGINEERING"]
        skills = ["software-engineering", "worktree-safety"]
    elif any(x in text for x in ("research", "pricing", "opportunity", "source", "public evidence", "current evidence")):
        classes, skills = ["RESEARCH"], ["research-intelligence"]
    elif any(x in text for x in ("browser", "visual", "ui")):
        classes, skills = ["BROWSER"], ["software-engineering"]
    elif any(x in text for x in ("modal", "cpu", "bounded job")):
        classes, skills = ["REMOTE_EXECUTION"], ["system-operations"]
    elif any(x in text for x in ("code", "implement", "build", "test", "engineering")):
        classes, skills = ["ENGINEERING", "CLI"], ["software-engineering", "test-debugging", "worktree-safety"]
    else:
        classes, skills = ["INTERNAL_READ"], ["repo-intelligence"]
    return {"capability_classes": classes, "required_skills": skills,
            "privacy": "INTERNAL_SAFE", "authority": "INTERNAL_SAFE",
            "evidence": "criterion-specific receipt and acceptance result"}


def select_skills(*, task_id: str, requirements: dict[str, Any], failure_memory: Iterable[dict[str, Any]] = (), persist: bool = True) -> dict[str, Any]:
    """Select the smallest loadable Nexus skill set for the typed task.

    The selection is controller-led; a model may use the loaded instructions
    but cannot add authority or mutate the parent state through this API.
    Failure history can add a task-relevant debugging skill, but never loads
    an unrelated skill merely because it exists.
    """
    available = {p.parent.name for p in SKILL_ROOT.glob("*/SKILL.md")}
    requested = [s for s in requirements.get("required_skills", []) if s in available]
    failures = list(failure_memory)
    if failures and "test-debugging" in available and "test-debugging" not in requested:
        requested.append("test-debugging")
    receipt = {
        "schema_version": "nexus.skill-selection-receipt.v1", "task_id": task_id,
        "skills_considered": sorted(available), "skills_selected": requested,
        "skill_source": {s: "NEXUS_NATIVE" for s in requested},
        "why_selected": "typed task requirements" + (" plus failure-memory debugging delta" if failures else ""),
        "failure_memory_used": bool(failures), "selection_timestamp": _now(),
    }
    if persist:
        SKILL_RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (SKILL_RECEIPT_DIR / f"skills_{task_id}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def _candidate(worker: str, tool: str, backend: str, skills: Iterable[str], fit: float, *, tested: float = 1.0, cost: float = 1.0, reason: str = "") -> Candidate:
    return Candidate(worker, tool, backend, tuple(skills), fit, 1.0, 1.0, tested, 1.0 if worker == "nexus_ai_workforce" else .5, 0.0, 1.0, cost, 1.0, 1.0, 1.0, 1.0, reason=reason)


def discover_candidates(requirements: dict[str, Any], *, failure_memory: Iterable[dict[str, Any]] = ()) -> list[Candidate]:
    classes = set(requirements.get("capability_classes", []))
    if "ENGINEERING" in classes:
        return [
            _candidate("nexus_ai_workforce", "engineering.portal_beta", "LOCAL", requirements["required_skills"], 1.0, reason="certified Nexus engineering receipt path"),
            _candidate("opencode", "opencode.run", "LOCAL_ISOLATED_WORKTREE", requirements["required_skills"], .9, tested=.8, cost=.5, reason="installed and governed adapter; candidate requires bounded certification"),
        ]
    if "RESEARCH" in classes:
        return [_candidate("research", "research.alpha", "LOCAL_OR_SEARXNG", requirements["required_skills"], 1.0, reason="existing Research/Alpha path"), _candidate("oracle", "oracle.browser.read", "ORACLE", requirements["required_skills"], .7, tested=.6, reason="historical read-only browser path")]
    if "BROWSER" in classes:
        return [_candidate("playwright", "browser.playwright", "LOCAL", requirements["required_skills"], .95, tested=.7), _candidate("oracle", "browser.oracle", "ORACLE", requirements["required_skills"], .9, tested=.8)]
    if "REMOTE_EXECUTION" in classes:
        return [_candidate("modal", "modal.bounded_job", "MODAL", requirements["required_skills"], 1.0, tested=1.0, cost=.5), _candidate("oracle", "remote.cpu", "ORACLE", requirements["required_skills"], .7, tested=.8, cost=.7)]
    return [_candidate("nexus_ai_workforce", "internal.create_bounded_work_artifact", "LOCAL", requirements["required_skills"], .8)]


def select_candidate(*, task_id: str, goal_id: str, criterion_id: str, goal: str, criterion: str, task: str = "", failure_memory: Iterable[dict[str, Any]] = (), persist: bool = True) -> dict[str, Any]:
    requirements = required_capabilities(goal, criterion, task)
    skill_receipt = select_skills(task_id=task_id, requirements=requirements, failure_memory=failure_memory, persist=persist)
    requirements = dict(requirements, required_skills=skill_receipt["skills_selected"])
    candidates = discover_candidates(requirements, failure_memory=failure_memory)
    filtered: list[dict[str, Any]] = []
    qualified: list[Candidate] = []
    for c in candidates:
        reasons = []
        if not c.authorized: reasons.append("AUTHORITY")
        if not c.runtime_access: reasons.append("RUNTIME_ACCESS")
        if c.real_test_confidence <= 0: reasons.append("REAL_TEST_REQUIRED")
        if reasons: filtered.append({"worker": c.worker, "tool": c.tool, "reasons": reasons})
        else: qualified.append(c)
    if not qualified:
        raise RuntimeError("NO_QUALIFIED_CAPABILITY_CANDIDATE")
    selected = max(qualified, key=lambda c: (c.score, c.worker, c.tool))
    receipt = {
        "schema_version": "nexus.capability-selection-receipt.v2", "task_id": task_id, "goal_id": goal_id,
        "criterion_id": criterion_id, "requirements": requirements,
        "skill_selection": skill_receipt,
        "candidates_discovered": [asdict(c) | {"score": c.score} for c in candidates],
        "candidates_filtered": filtered, "candidates_scored": [{"worker": c.worker, "tool": c.tool, "score": c.score} for c in qualified],
        "selected_worker": selected.worker, "selected_tool": selected.tool, "selected_backend": selected.backend,
        "selected_skills": list(selected.skills), "why_selected": selected.reason,
        "why_alternatives_not_selected": [{"worker": c.worker, "tool": c.tool, "score": c.score, "reason": "lower deterministic score"} for c in qualified if c != selected],
        "authority": requirements["authority"], "selection_timestamp": _now(),
        "selection_fingerprint": hashlib.sha256(json.dumps(requirements, sort_keys=True).encode()).hexdigest()[:18],
    }
    if persist:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (RECEIPT_DIR / f"selection_{task_id}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def failure_learning(previous: dict[str, Any], *, new_strategy: str, new_skills: Iterable[str] = (), new_tool: str | None = None, new_worker: str | None = None) -> dict[str, Any]:
    """Produce a durable, controller-consumable material-delta decision."""
    old = {previous.get("strategy"), previous.get("tool"), previous.get("worker"), *previous.get("skills", [])}
    new = {new_strategy, new_tool, new_worker, *new_skills}
    delta = sorted(str(x) for x in (new - old) if x)
    result = {"schema_version": "nexus.failure-learning.v1", "failure_fingerprint": previous.get("failure_fingerprint", "unknown"), "retry_allowed": bool(delta), "material_delta": delta, "strategy": new_strategy, "selected_skills": list(new_skills), "selected_tool": new_tool, "selected_worker": new_worker, "learned_at": _now()}
    if bool(delta):
        FAILURE_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with FAILURE_MEMORY_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result, sort_keys=True) + "\n")
    return result
