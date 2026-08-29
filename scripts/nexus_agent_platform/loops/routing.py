"""Canonical WP4 skill → worker → profile/model → executor routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .skill_resolver import resolve_skill

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "data/runtime/nexus_skill_registry.json"
WORKERS = ROOT / "data/runtime/nexus_worker_role_map.json"


def _load(path: Path, key: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"invalid {key} registry")
    return rows


def resolve_route(skill_id: str, worker_id: str, *, authority_class: str, model_policy: str | None = None, executor_id: str | None = None) -> dict[str, Any]:
    skill = next((row for row in _load(SKILLS, "skills") if row.get("skill_id") == skill_id), None)
    worker = next((row for row in _load(WORKERS, "workers") if row.get("worker_id") == worker_id), None)
    if not skill or not worker or skill_id not in worker.get("skills_allowed", []):
        raise ValueError("NO_SKILL_MATCH")
    if skill.get("authority_class") not in {authority_class, "advisory", "internal_read_only", "read_only"}:
        raise ValueError("SKILL_BLOCKED_AUTHORITY")
    if executor_id and executor_id not in worker.get("executors_allowed", []) and executor_id not in skill.get("executors_allowed", []):
        raise ValueError("SKILL_EXECUTOR_NOT_ALLOWED")
    policy = model_policy or skill.get("model_policy", "LOCAL_PRIVATE")
    if policy not in {"LOCAL_PRIVATE", "TOOL_CAPABLE", "GENERAL_REASONING", "RESEARCH", "CODE_ASSIST", "FALLBACK", "FAST_ZERO_COST"} and not any(part in {"LOCAL_PRIVATE", "TOOL_CAPABLE", "GENERAL_REASONING", "RESEARCH", "CODE_ASSIST", "FALLBACK", "FAST_ZERO_COST"} for part in str(policy).split(",")):
        raise ValueError("MODEL_POLICY_NOT_ALLOWED")
    return {"skill_id": skill_id, "worker_id": worker_id, "profile": (worker.get("profiles_allowed") or ["default"])[0], "model_policy": policy, "executor_id": executor_id, "authority_class": skill.get("authority_class")}
