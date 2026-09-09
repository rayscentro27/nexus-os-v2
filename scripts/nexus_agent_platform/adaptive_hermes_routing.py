"""Evidence-driven Hermes model routing for bounded Nexus tasks."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
FAILURE_PATH = ROOT / "reports/runtime/nexus_hermes_model_failures_r15_9.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    profile: str
    auth_available: bool
    tool_use_supported: bool
    structured_output_supported: bool
    health: str = "UNKNOWN"
    recent_latency_seconds: float | None = None
    cost_class: str = "UNKNOWN"
    rate_limit_state: str = "UNKNOWN"
    last_real_success: str | None = None


def load_failures() -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in FAILURE_PATH.read_text().splitlines() if line.strip()]
    except (OSError, ValueError, TypeError):
        return []


def route_fingerprint(route: ModelRoute, task_class: str) -> str:
    return hashlib.sha256(json.dumps({"provider": route.provider, "model": route.model, "task_class": task_class}, sort_keys=True).encode()).hexdigest()[:20]


def score_route(route: ModelRoute, task_class: str, failures: Iterable[dict[str, Any]] = ()) -> float:
    if not route.auth_available or route.health not in {"PASS", "READY", "HEALTHY"}:
        return -100.0
    score = 5.0 + (2.0 if route.tool_use_supported else 0) + (2.0 if route.structured_output_supported else 0)
    if route.recent_latency_seconds is not None:
        score += max(0.0, 3.0 - route.recent_latency_seconds / 30.0)
    fp = route_fingerprint(route, task_class)
    score -= 2.0 * sum(1 for row in failures if row.get("fingerprint") == fp)
    return round(score, 4)


def choose_route(routes: Iterable[ModelRoute], task_class: str, failures: Iterable[dict[str, Any]] = ()) -> tuple[ModelRoute | None, list[dict[str, Any]]]:
    failures = list(failures)
    ranked = sorted(({"route": asdict(route), "score": score_route(route, task_class, failures)} for route in routes), key=lambda row: (row["score"], row["route"]["provider"], row["route"]["model"]), reverse=True)
    eligible = [row for row in ranked if row["score"] >= 0]
    return (next((r for r in routes if asdict(r) == eligible[0]["route"]), None) if eligible else None), ranked


def record_failure(route: ModelRoute, task_class: str, failure_class: str, latency_seconds: float | None, material_delta: bool) -> dict[str, Any]:
    row = {"schema_version": "nexus.hermes.model-failure.v1", "fingerprint": route_fingerprint(route, task_class), "provider": route.provider, "model": route.model, "task_class": task_class, "profile": route.profile, "failure_class": failure_class, "latency_seconds": latency_seconds, "material_delta": material_delta, "recorded_at": _now()}
    FAILURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def validate_criterion_evidence(value: Any, goal_id: str, criterion_id: str, task_id: str) -> dict[str, Any]:
    """Reject completion-like prose; accept only criterion-shaped evidence."""
    if isinstance(value, str):
        return {"valid": False, "reason": "PASS_WITHOUT_MATERIAL_DELTA", "goal_id": goal_id, "criterion_id": criterion_id, "task_id": task_id}
    if not isinstance(value, dict):
        return {"valid": False, "reason": "STRUCTURED_RESULT_REQUIRED", "goal_id": goal_id, "criterion_id": criterion_id, "task_id": task_id}
    required = {"goal_id", "criterion_id", "task_id", "action_performed", "evidence_items", "expected", "observed", "delta_remaining", "recommended_criterion_state"}
    missing = sorted(required - set(value))
    valid = not missing and value.get("goal_id") == goal_id and value.get("criterion_id") == criterion_id and bool(value.get("evidence_items"))
    return {"valid": valid, "reason": "VALID" if valid else "STRUCTURED_EVIDENCE_INVALID", "missing": missing, "goal_id": goal_id, "criterion_id": criterion_id, "task_id": task_id}
