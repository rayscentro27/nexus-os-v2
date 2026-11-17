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
from dataclasses import dataclass, asdict, replace
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
        {"capability_id": "hermes.native.gateway.read_only", "name": "Hermes native authenticated read-only", "category": "TOOL", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": (ROOT / "reports/runtime/nexus_hermes_native_r12/native_tool_call_gateway.json").is_file(), "health": "READY" if (ROOT / "reports/runtime/nexus_hermes_native_r12/native_tool_call_gateway.json").is_file() else "UNKNOWN", "source_registry": "Oracle-side protected api.env via SSH gateway", "side_effect_class": "READ_ONLY", "authority_scope": "READ_ONLY_INTERNAL", "privacy_scope": "INTERNAL"},
        {"capability_id": "hermes.native.mcp", "name": "Hermes native MCP", "category": "MCP", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "Hermes mcp test and MCP-only live turn", "side_effect_class": "READ_ONLY", "authority_scope": "READ_ONLY_INTERNAL"},
        {"capability_id": "hermes.native.terminal", "name": "Hermes native terminal", "category": "TOOL", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "R12.6 terminal-only receipt", "side_effect_class": "BOUNDED_INTERNAL", "authority_scope": "BOUNDED_TASK_SCOPE"},
        {"capability_id": "hermes.native.file_read", "name": "Hermes native file read", "category": "TOOL", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "R12.6 file-read-only receipt", "side_effect_class": "READ_ONLY", "authority_scope": "BOUNDED_TASK_SCOPE"},
        {"capability_id": "hermes.native.execute_code", "name": "Hermes native execute code", "category": "TOOL", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "R12.6 execute-code-only receipt", "side_effect_class": "BOUNDED_INTERNAL", "authority_scope": "SANDBOXED_DETERMINISTIC"},
        {"capability_id": "hermes.native.subagent", "name": "Hermes native bounded delegation", "category": "WORKER", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "R12.6 delegation-only receipt", "side_effect_class": "READ_ONLY", "authority_scope": "BOUNDED_DELEGATION"},
        {"capability_id": "hermes.kanban.executor", "name": "Hermes governed Kanban executor", "category": "EXECUTOR", "provider": "Oracle Hermes 0.20.6", "installed": True, "configured": True, "enabled": True, "authorized": True, "runtime_access": True, "worker_access": True, "real_tested": True, "health": "READY", "source_registry": "R15.6 live dispatcher, worker, skill-receipt and reviewer receipts", "side_effect_class": "BOUNDED_INTERNAL", "authority_scope": "INTERNAL_SAFE", "execution_plane": "HERMES_KANBAN"},
    ])
    return rows


def required_capabilities(goal: str, criterion: str, task: str = "") -> dict[str, Any]:
    text = " ".join((goal, criterion, task)).lower()
    if any(x in text for x in ("system health", "operational state", "current company state")):
        classes, skills = ["INTERNAL_READ"], ["repo-intelligence"]
    elif any(x in text for x in ("tenant", "approval", "rls", "supabase")):
        classes = ["DATABASE", "AUTHORIZATION_TESTING", "ENGINEERING"]
        skills = ["software-engineering", "worktree-safety"]
    elif any(x in text for x in ("research", "pricing", "opportunity", "source", "public evidence", "current evidence")):
        classes, skills = ["RESEARCH"], ["research-intelligence"]
    elif any(x in text for x in ("image", "graphic", "logo", "thumbnail", "creative", "media", "product image", "mockup", "visual asset")):
        classes, skills = ["CREATIVE_MEDIA"], ["software-engineering"]
    elif any(x in text for x in ("dataset", "cluster", "clustering", "embedding", "large data", "data analysis")):
        classes, skills = ["REMOTE_EXECUTION"], ["system-operations"]
    elif any(x in text for x in ("modal", "bounded job")):
        classes, skills = ["REMOTE_EXECUTION"], ["system-operations"]
    # ENGINEERING checked before BROWSER: coding/build/repo intents must route to a coding runner.
    # (word-boundary-ish tokens; avoids the 'build' contains 'ui' substring collision.)
    elif any(x in text for x in ("landing page", "website", "web app", "build ", "coding", "code ", "implement",
                                 "fix a bug", "bug in", "repository", "repo ", "run tests", "engineering", "refactor", "frontend")):
        classes, skills = ["ENGINEERING", "CLI"], ["software-engineering", "test-debugging", "worktree-safety"]
    elif any(x in text for x in ("browser", "screenshot", "scrape", "web page", "user interface")):
        classes, skills = ["BROWSER"], ["software-engineering"]
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
    return Candidate(worker, tool, backend, tuple(skills), fit, 1.0, 1.0, tested, 1.0 if worker in {"nexus_ai_workforce", "hermes_orchestrator", "antigravity"} else .5, 0.0, 1.0, cost, 1.0, 1.0, 1.0, 1.0, reason=reason)


def discover_candidates(requirements: dict[str, Any], *, failure_memory: Iterable[dict[str, Any]] = ()) -> list[Candidate]:
    classes = set(requirements.get("capability_classes", []))
    if "INTERNAL_READ" in classes:
        tested = (ROOT / "reports/runtime/nexus_hermes_native_r12/native_tool_call_gateway.json").is_file()
        return [
            _candidate("hermes_native", "hermes.native.gateway.read_only", "ORACLE_SSH_GATEWAY", requirements["required_skills"], 1.0, tested=1.0 if tested else 0.0, reason="authenticated Oracle Hermes read-only receipt"),
            _candidate("nexus_mcp", "mcp.nexus_mcp", "LOCAL_ORACLE_BRIDGE", requirements["required_skills"], .9, tested=1.0, reason="certified Nexus MCP read path"),
        ]
    if "ENGINEERING" in classes:
        import shutil as _sh
        agy_ok = 1.0 if _sh.which("agy") else 0.0          # antigravity_cli: certified routable (Sec 30A)
        return [
            _candidate("hermes_orchestrator", "hermes.kanban.executor", "ORACLE_HERMES_KANBAN", requirements["required_skills"], 1.0, reason="live Hermes dispatcher (orchestration); heavy build Oracle-protected downstream"),
            _candidate("antigravity", "cli.antigravity_cli", "MAC_MINI_CODING", requirements["required_skills"], 1.0, tested=agy_ok, cost=.9, reason="antigravity_cli 1.5.5 Mac-local coding CLI; Sec 30A bounded build PASS"),
            _candidate("nexus_ai_workforce", "engineering.portal_beta", "LOCAL", requirements["required_skills"], .95, reason="certified Nexus engineering receipt path (non-CLI fallback)"),
            _candidate("opencode", "opencode.run", "LOCAL_ISOLATED_WORKTREE", requirements["required_skills"], .9, tested=.8, cost=.5, reason="installed and governed opencode adapter"),
            _candidate("codex", "cli.codex_cli", "MAC_MINI_CODING", requirements["required_skills"], 1.0, tested=0.0, cost=.6, reason="codex-cli installed but quota-exhausted (DEGRADED); excluded by REAL_TEST gate"),
        ]
    if "RESEARCH" in classes:
        return [_candidate("hermes_orchestrator", "hermes.kanban.executor", "ORACLE_HERMES_KANBAN", requirements["required_skills"], 1.0, reason="live Hermes dispatcher and worker receipts"), _candidate("research", "research.alpha", "LOCAL_OR_SEARXNG", requirements["required_skills"], 1.0, reason="existing Research/Alpha path"), _candidate("oracle", "oracle.browser.read", "ORACLE", requirements["required_skills"], .7, tested=.6, reason="historical read-only browser path")]
    if "CREATIVE_MEDIA" in classes:
        # Meta browser image route EXISTS but is UNPROVEN (WP8_11A) -> tested=0 -> filtered out.
        # Deterministic creative brief/direction is the currently-executable creative output.
        return [_candidate("creative_meta", "meta_ai_browser_creative", "CREATIVE_BROWSER", requirements["required_skills"], 1.0, tested=0.0, reason="Meta browser image route exists but unproven (WP8_11A); excluded until verified"),
                _candidate("creative_engine", "creative.brief_direction", "LOCAL", requirements["required_skills"], .9, tested=1.0, reason="deterministic creative brief/direction (text) READY; media RENDER needs an approved provider")]
    if "BROWSER" in classes:
        return [_candidate("playwright", "browser.playwright", "LOCAL", requirements["required_skills"], .95, tested=.7), _candidate("oracle", "browser.oracle", "ORACLE", requirements["required_skills"], .9, tested=.8)]
    if "REMOTE_EXECUTION" in classes:
        # Free/included compute preferred over metered; Oracle remote excluded downstream for heavy work.
        return [_candidate("kaggle", "kaggle.bounded_job", "KAGGLE", requirements["required_skills"], 1.0, tested=1.0, cost=1.0, reason="free bounded GPU/CPU notebook"),
                _candidate("colab", "colab.bounded_job", "COLAB", requirements["required_skills"], .95, tested=1.0, cost=.9, reason="included-subscription compute units"),
                _candidate("modal", "modal.bounded_job", "MODAL", requirements["required_skills"], 1.0, tested=1.0, cost=.5, reason="metered; approval-gated fallback"),
                _candidate("oracle", "remote.cpu", "ORACLE", requirements["required_skills"], .7, tested=.8, cost=.7, reason="Oracle remote (excluded for heavy work by protection)")]
    return [_candidate("nexus_ai_workforce", "internal.create_bounded_work_artifact", "LOCAL", requirements["required_skills"], .8)]


def filter_candidates(candidates: Iterable[Candidate], requirements: dict[str, Any]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    """Apply deterministic readiness, authority, privacy, and health gates."""
    qualified, rejected = [], []
    for c in candidates:
        reasons = []
        if not c.authorized: reasons.append("AUTHORITY")
        if not c.runtime_access: reasons.append("RUNTIME_ACCESS")
        if c.worker_access <= 0: reasons.append("WORKER_ACCESS")
        if c.health <= 0: reasons.append("UNHEALTHY")
        if c.real_test_confidence <= 0: reasons.append("REAL_TEST_REQUIRED")
        if c.privacy_fit <= 0: reasons.append("PRIVACY")
        if reasons: rejected.append({"worker": c.worker, "tool": c.tool, "reasons": reasons})
        else: qualified.append(c)
    return qualified, rejected


def _apply_failure_memory(candidates: Iterable[Candidate], failure_memory: Iterable[dict[str, Any]]) -> list[Candidate]:
    """Apply task-scoped failure penalties without globally blacklisting tools."""
    history = list(failure_memory)
    result = []
    for c in candidates:
        relevant = [h for h in history if h.get("worker") == c.worker or h.get("tool") == c.tool]
        if relevant:
            result.append(replace(c, past_failure=-min(1.0, .25 * len(relevant)), failure_compatibility=-min(1.0, .2 * len(relevant))))
        else:
            result.append(c)
    return result


def select_candidate(*, task_id: str, goal_id: str, criterion_id: str, goal: str, criterion: str, task: str = "", failure_memory: Iterable[dict[str, Any]] = (), persist: bool = True) -> dict[str, Any]:
    requirements = required_capabilities(goal, criterion, task)
    skill_receipt = select_skills(task_id=task_id, requirements=requirements, failure_memory=failure_memory, persist=persist)
    requirements = dict(requirements, required_skills=skill_receipt["skills_selected"])
    candidates = _apply_failure_memory(discover_candidates(requirements, failure_memory=failure_memory), failure_memory)
    qualified, filtered = filter_candidates(candidates, requirements)
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


# Dispatch map: selected tool -> EXISTING governed runner category (no new executor built).
_TOOL_RUNNER = {
    "hermes.kanban.executor": ("HERMES_KANBAN", "hermes_kanban_executor"),
    "cli.antigravity_cli": ("CODING_CLI", "coding_worker_supervisor"),
    "cli.codex_cli": ("CODING_CLI", "coding_worker_supervisor"),
    "opencode.run": ("CODING_CLI", "coding_worker_supervisor"),
    "engineering.portal_beta": ("SCRIPT_ENGINE", "department_engine"),
    "research.alpha": ("RESEARCH", "research_r16_engine"),
    "mcp.nexus_mcp": ("MCP", "hermes_native_mcp"),
    "hermes.native.gateway.read_only": ("MCP", "hermes_native_gateway"),
    "hermes.native.mcp": ("MCP", "hermes_native_mcp"),
    "browser.playwright": ("BROWSER", "playwright_governed"),
    "browser.oracle": ("BROWSER", "oracle_browser_readonly"),
    "meta_ai_browser_creative": ("BROWSER", "creative_meta_surface"),
    "creative.brief_direction": ("SCRIPT_ENGINE", "creative_engine"),
    "modal.bounded_job": ("REMOTE", "remote_worker"),
    "kaggle.bounded_job": ("REMOTE", "remote_worker"),
    "colab.bounded_job": ("REMOTE", "remote_worker"),
    "remote.cpu": ("REMOTE", "remote_worker"),
    "internal.create_bounded_work_artifact": ("SCRIPT_ENGINE", "department_engine"),
}
_ORACLE_BACKENDS = {"ORACLE", "ORACLE_HERMES_KANBAN", "ORACLE_SSH_GATEWAY"}
_HEAVY_CLASSES = {"ENGINEERING", "BROWSER", "REMOTE_EXECUTION", "RESEARCH"}
_PAID_TOOLS = {"modal.bounded_job"}


def _reselect_non_oracle(selection: dict[str, Any]):
    """Oracle protection: for heavy work, drop Oracle-backed candidates and re-pick the best."""
    discovered = selection.get("candidates_discovered") or []
    non_oracle = [c for c in discovered if c.get("backend") not in _ORACLE_BACKENDS
                  and c.get("real_test_confidence", 0) > 0 and c.get("authorized", True)]
    if not non_oracle:
        return None
    best = max(non_oracle, key=lambda c: c.get("score", 0))
    return best


def execute_selected_candidate(selection: dict[str, Any], task_spec: dict[str, Any]) -> dict[str, Any]:
    """Resolve the selected capability to its EXISTING governed runner and return a
    normalized EXECUTION_RECEIPT. Consults resource/worker routers + execution-truth,
    enforces Oracle protection + cost/approval governance. Does NOT build a new executor
    and does NOT auto-run heavy/destructive work (the governed runner performs it when
    task_spec['execute'] is True and the method is safe). Preserves hermes.kanban behavior."""
    tool = selection.get("selected_tool")
    classes = set((selection.get("requirements") or {}).get("capability_classes", []))
    heavy = bool(classes & _HEAVY_CLASSES)
    reroute = None
    # --- Oracle protection: heavy work never lands on an Oracle backend ---
    sel_backend = next((c.get("backend") for c in (selection.get("candidates_discovered") or [])
                        if c.get("tool") == tool), None)
    if heavy and sel_backend in _ORACLE_BACKENDS:
        alt = _reselect_non_oracle(selection)
        if alt:
            reroute = {"from": tool, "from_backend": sel_backend, "to": alt["tool"], "to_backend": alt.get("backend"),
                       "reason": "ORACLE_PROTECTION_HEAVY_WORK"}
            tool = alt["tool"]; sel_backend = alt.get("backend")
        else:
            return _receipt(selection, task_spec, tool, "WAITING_FOR_RAY_APPROVAL", runner=None,
                            approval_reason="No non-Oracle execution route for heavy work; wait/approval required.",
                            reroute={"blocked": "ONLY_ORACLE_AVAILABLE_FOR_HEAVY_WORK"})
    category, runner = _TOOL_RUNNER.get(tool, ("UNKNOWN", None))
    # --- execution-truth routability gate (registered != routable) ---
    truth = _execution_truth_routable(tool)
    if truth is False:
        return _receipt(selection, task_spec, tool, "NOT_ROUTABLE", runner=runner, category=category,
                        approval_reason="Execution method registered but not routable per execution-truth (unverified/unhealthy).",
                        reroute=reroute)
    # --- cost / approval governance ---
    approved_spend = float(task_spec.get("approved_spend", 0) or 0)
    if tool in _PAID_TOOLS and approved_spend <= 0:
        return _receipt(selection, task_spec, tool, "WAITING_FOR_RAY_APPROVAL", runner=runner, category=category,
                        approval_reason=f"{tool} is PAID_METERED; no approved budget -> approval required.", reroute=reroute)
    # --- preserve existing broker-native Hermes execution ---
    if tool == "hermes.kanban.executor" and not heavy:
        from nexus_agent_platform.hermes_kanban_executor import execute_with_hermes_kanban
        result = execute_with_hermes_kanban({**task_spec,
            "skills": task_spec.get("skills") or selection.get("selected_skills", []),
            "profile": task_spec.get("profile") or "nexus_research_test"})
        return _receipt(selection, task_spec, tool, result.get("status", "COMPLETED"), runner="hermes_kanban_executor",
                        category="HERMES_KANBAN", runner_result=result, reroute=reroute)
    # --- coding worker supervisor governed execution when requested ---
    if task_spec.get("execute") and runner == "coding_worker_supervisor":
        from nexus_agent_platform import coding_worker_supervisor as CWS
        task_id = str(task_spec.get("task_id") or "task_coding")
        prompt = str(task_spec.get("prompt") or task_spec.get("goal") or "Build a simple responsive test landing page. Do not deploy.")
        allowed_paths = tuple(task_spec.get("allowed_paths") or ("tmp/nova_coding_jobs/",))
        checkpoint_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        coding_task = CWS.CodingTask(
            task_id=task_id, objective_id=task_id, prompt=prompt,
            allowed_paths=allowed_paths,
            protected_paths=("scripts/", "services/", "configs/", "data/", "src/"),
            acceptance=("artifact exists",), checkpoint_sha=checkpoint_sha,
        )
        worker_id = "antigravity" if "antigravity" in str(tool) else "opencode"
        runner_res = CWS.execute_coding_task(coding_task, worker_id=worker_id, timeout=int(task_spec.get("timeout") or 90))
        st = "COMPLETED" if runner_res.get("status") == "PASS" else "FAILED"
        return _receipt(selection, task_spec, tool, st, runner=runner, category=category,
                        runner_result=runner_res, reroute=reroute, note="Executed by coding_worker_supervisor.")
    # --- all other categories: hand to the EXISTING governed runner (resolve + route) ---
    return _receipt(selection, task_spec, tool, "ROUTED_TO_RUNNER", runner=runner, category=category, reroute=reroute,
                    note="Handed to the existing governed runner; the runner performs the work and returns its own receipt.")


def _execution_truth_routable(tool: str):
    """Best-effort execution-truth consult; None if the layer is unavailable (not a hard fail)."""
    mapping = {"cli.antigravity_cli": "antigravity_cli", "cli.codex_cli": "codex_cli", "opencode.run": "opencode_cli",
               "mcp.nexus_mcp": "nexus_mcp", "modal.bounded_job": "modal", "research.alpha": "deterministic_scripts",
               "meta_ai_browser_creative": "meta_ai_browser_creative"}
    eid = mapping.get(tool)
    if not eid:
        return None
    try:
        import sys as _sys
        _rd = str(ROOT / "scripts")
        if _rd not in _sys.path: _sys.path.insert(0, _rd)
        from resource_directory import execution_truth as _ET
        return _ET.routable(eid)
    except Exception:
        return None


_CATEGORY_WORKLOAD = {"CODING_CLI": "coding", "REMOTE": "data_processing", "BROWSER": "media_generation",
                      "RESEARCH": "research", "MCP": "reasoning", "SCRIPT_ENGINE": "reasoning",
                      "HERMES_KANBAN": "control"}


def _consult_routers(category, selection):
    """Best-effort consult of the Section-28 resource + worker routers (cross-check / enrichment)."""
    try:
        import sys as _sys
        _rd = str(ROOT / "scripts")
        if _rd not in _sys.path: _sys.path.insert(0, _rd)
        from resource_directory import router as _RR
        workload = _CATEGORY_WORKLOAD.get(category, "reasoning")
        rt = _RR.route_task(f"broker:{category}", workload=workload)
        wr = _RR.route_worker([workload])
        return {"resource_router_candidates": [r["environment_id"] for r in rt.get("ranked", []) if r.get("eligible")][:4],
                "resource_router_selected": (rt.get("selected") or {}).get("environment_id"),
                "worker_router_candidates": [w["worker_id"] for w in wr.get("registered_workers_ranked", [])][:3]}
    except Exception:
        return {"resource_router_candidates": "UNKNOWN", "worker_router_candidates": "UNKNOWN"}


def _receipt(selection, task_spec, tool, status, *, runner=None, category=None, runner_result=None,
             approval_reason=None, reroute=None, note=None) -> dict[str, Any]:
    """Normalized EXECUTION_RECEIPT (spec 1A). Unknown values stay UNKNOWN; never fabricated."""
    routers = _consult_routers(category, selection)
    return {
        "schema_version": "nexus.execution-receipt.v1",
        "execution_receipt_id": "exec_" + hashlib.sha256(
            f"{task_spec.get('task_id')}:{tool}:{status}".encode()).hexdigest()[:18],
        "task_id": task_spec.get("task_id", "UNKNOWN"), "parent_work_id": task_spec.get("parent_work_id", "UNKNOWN"),
        "venture_id": task_spec.get("venture_id", "UNKNOWN"), "department": task_spec.get("department", "UNKNOWN"),
        "selected_capability": (selection.get("requirements") or {}).get("capability_classes", "UNKNOWN"),
        "selected_tool": tool, "execution_method": category or "UNKNOWN", "executor_runner": runner or "UNKNOWN",
        "environment": task_spec.get("environment", "UNKNOWN"), "worker": selection.get("selected_worker", "UNKNOWN"),
        "provider": task_spec.get("provider", "UNKNOWN"), "model": task_spec.get("model", "UNKNOWN"),
        "start_time": task_spec.get("start_time", "UNKNOWN"), "end_time": task_spec.get("end_time", "UNKNOWN"),
        "status": status, "artifacts": (runner_result or {}).get("artifacts", []) if runner_result else [],
        "files_changed": (runner_result or {}).get("files_changed", "UNKNOWN") if runner_result else "UNKNOWN",
        "usage_reference": task_spec.get("ai_usage_ref", "UNKNOWN"), "cost_class": task_spec.get("cost_class", "UNKNOWN"),
        "cost_if_known": task_spec.get("cost_if_known", "UNKNOWN"),
        "approval_state": ("WAITING_FOR_RAY_APPROVAL" if status == "WAITING_FOR_RAY_APPROVAL" else "AUTONOMOUS_OK"),
        "approval_reason": approval_reason, "error": None, "retry_state": "NONE",
        "oracle_reroute": reroute, "note": note,
        "resource_router": routers.get("resource_router_candidates"),
        "resource_router_selected": routers.get("resource_router_selected"),
        "worker_router": routers.get("worker_router_candidates"),
        "next_action": ("REQUEST_RAY_APPROVAL" if status == "WAITING_FOR_RAY_APPROVAL" else
                        "INVOKE_RUNNER" if status == "ROUTED_TO_RUNNER" else "CONTINUE"),
    }


def select_and_execute(*, task_id: str, goal_id: str, criterion_id: str, goal: str, criterion: str, task: str, task_spec: dict[str, Any], failure_memory: Iterable[dict[str, Any]] = (), persist: bool = True) -> dict[str, Any]:
    """Normal Nexus broker entrypoint: requirements → selection → execution."""
    selection = select_candidate(task_id=task_id, goal_id=goal_id, criterion_id=criterion_id, goal=goal, criterion=criterion, task=task, failure_memory=failure_memory, persist=persist)
    execution = execute_selected_candidate(selection, {**task_spec, "goal_id": goal_id, "criterion_id": criterion_id, "task_id": task_id, "task_requirements": selection["requirements"]})
    return {"selection": selection, "execution": execution, "verifier_required": True, "criterion_completion_claimed": False}


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
