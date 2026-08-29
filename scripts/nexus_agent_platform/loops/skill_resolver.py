"""Deny-by-default Nexus SKILL.md resolution."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills/nexus"


@dataclass(frozen=True)
class SkillResolution:
    skill_id: str
    path: str
    worker_id: str
    profile: str
    model_policy: str
    executor_policy: tuple[str, ...]


def _frontmatter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter")
    values: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    raise ValueError("unterminated SKILL.md frontmatter")


def load_skill(skill_id: str, root: Path = SKILL_ROOT) -> tuple[Path, dict[str, Any]]:
    safe = re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill_id)
    if not safe:
        raise ValueError("NO_SKILL_MATCH")
    path = root / skill_id / "SKILL.md"
    if not path.is_file():
        raise ValueError("NO_SKILL_MATCH")
    return path, _frontmatter(path)


def resolve_skill(
    skill_id: str,
    *,
    authority_class: str,
    worker_id: str,
    available_workers: set[str],
    available_executors: set[str],
    root: Path = SKILL_ROOT,
) -> SkillResolution:
    path, meta = load_skill(skill_id, root)
    if worker_id not in available_workers:
        raise ValueError("SKILL_BLOCKED_AUTHORITY")
    declared_authority = meta.get("authority_class", "")
    if declared_authority not in {authority_class, "internal_read_only", "advisory"}:
        raise ValueError("SKILL_BLOCKED_AUTHORITY")
    declared = tuple(x.strip() for x in meta.get("allowed_executors", "").split(",") if x.strip())
    if declared and not set(declared).issubset(available_executors):
        raise ValueError("SKILL_EXECUTOR_NOT_ALLOWED")
    return SkillResolution(skill_id, str(path.relative_to(ROOT)), worker_id,
                           meta.get("default_profile", "default"),
                           meta.get("model_policy", "LOCAL_PRIVATE"), declared)
