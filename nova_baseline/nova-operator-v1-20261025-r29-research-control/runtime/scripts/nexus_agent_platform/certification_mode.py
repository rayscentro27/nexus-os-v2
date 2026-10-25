"""Canonical operating-mode and safe internal certification contract.

This module is intentionally policy-only.  It does not select work, create a
second queue, or authorize governed external actions.  It gives existing Alpha
and department adapters a shared answer to one question: can this uncertain
item be exercised safely for internal learning?
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence

OPERATING_MODES = ("BUILD_CERTIFICATION", "NORMAL_PRODUCTION")
CERTIFICATION_DISPOSITION = "CERTIFICATION_TEST"
_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "nexus_operating_mode.json"
_HARD_TERMS = (
    "illegal", "fraud", "deception", "prohibited", "live trading",
    "customer financial application", "customer outreach", "public publishing",
    "paid advertising", "purchase", "inventory", "funds movement",
    "sensitive customer data", "security vulnerability", "access-control bypass",
    "captcha bypass", "account creation", "paid subscription", "destructive production",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_mode() -> str:
    requested = str(os.environ.get("NEXUS_OPERATING_MODE") or "").strip().upper()
    if not requested:
        try:
            requested = str(json.loads(_CONFIG.read_text(encoding="utf-8")).get("mode") or "").upper()
        except (OSError, ValueError, TypeError):
            requested = "NORMAL_PRODUCTION"
    return requested if requested in OPERATING_MODES else "NORMAL_PRODUCTION"


def is_build_certification_mode() -> bool:
    return current_mode() == "BUILD_CERTIFICATION"


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().upper()
    if text in {"YES", "TRUE", "Y", "LOW", "ZERO", "NONE", "BOUNDED", "REVERSIBLE"}:
        return True
    if text in {"NO", "FALSE", "N", "HIGH", "BLOCKED", "PROHIBITED", "UNKNOWN", ""}:
        return False if text not in {"UNKNOWN", ""} else None
    return None


def _profile(package: dict[str, Any]) -> dict[str, Any]:
    value = package.get("certification_test_profile") or package.get("test_profile") or package.get("experiment_profile") or {}
    return value if isinstance(value, dict) else {}


def testability_review(package: dict[str, Any], judgment: dict[str, Any], blockers: list[str] | None = None) -> dict[str, Any]:
    """Return an explicit testability review; unknown is never silently safe."""
    profile = _profile(package)
    blob = " ".join(str(package.get(key) or "") for key in ("query", "summary", "title", "analysis"))
    blob += " " + " ".join(str(judgment.get(key) or "") for key in ("reasoning_summary", "deficiencies", "hard_blockers"))
    lower = blob.lower()
    inferred_hard = [term for term in _HARD_TERMS if term in lower]
    hard = list(dict.fromkeys([*(blockers or []), *inferred_hard]))
    values = {
        "can_this_be_tested_safely": _bool(profile.get("can_this_be_tested_safely")),
        "can_this_be_tested_cheaply": _bool(profile.get("can_this_be_tested_cheaply")),
        "can_this_be_tested_reversibly": _bool(profile.get("can_this_be_tested_reversibly", profile.get("reversibility"))),
        "can_this_teach_nexus_something": _bool(profile.get("can_this_teach_nexus_something", profile.get("learning_value"))),
        # A caller-supplied false cannot erase a detected policy blocker.
        "hard_blocker_present": bool(hard) or bool(_bool(profile.get("hard_blocker_present"))),
    }
    candidate = all(values[key] is True for key in values if key != "hard_blocker_present") and not values["hard_blocker_present"]
    why = str(profile.get("why_certification_test_not_used") or "").strip()
    if not candidate and not why:
        missing = [key for key in values if key != "hard_blocker_present" and values[key] is not True]
        why = "Hard safety boundary present." if values["hard_blocker_present"] else ("Explicit testability evidence missing: " + ", ".join(missing))
    return {**values, "hard_blockers": hard, "certification_test_candidate": candidate, "why_certification_test_not_used": why}


def choose_disposition(model_decision: str, review: dict[str, Any]) -> str:
    decision = str(model_decision or "RESEARCH_MORE").upper()
    if review.get("hard_blocker_present"):
        return "REJECT"
    if is_build_certification_mode() and decision in {"REJECT", "RESEARCH_MORE", "MONITOR", "NO_ACTION"} and review.get("certification_test_candidate"):
        return CERTIFICATION_DISPOSITION
    return decision


def create_experiment(*, department: str, source_finding: str, alpha_decision: str, hypothesis: str,
                      parent_goal: str | None = None, parent_project: str | None = None,
                      why_test_anyway: str = "", expected_result: str = "", test_method: str = "",
                      safety_boundary: str = "internal only; no external action", cost_boundary: str = "zero or pre-approved internal resources",
                      reversibility: str = "reversible", inputs: list[Any] | None = None,
                      variants: list[Any] | None = None, next_test: str = "", next_owner: str = "",
                      completion_state: str = "CREATED", experiment_id: str | None = None) -> dict[str, Any]:
    experiment_id = experiment_id or persistence.new_id("experiment")
    existing = persistence.get_record("certification_experiments", experiment_id, key="experiment_id")
    if existing:
        return {**existing, "deduplicated": True}
    row = {
        "schema_version": "nexus.certification-experiment.v1", "experiment_id": experiment_id,
        "parent_goal": parent_goal, "parent_project": parent_project, "department": department,
        "source_finding": source_finding, "alpha_decision": alpha_decision, "hypothesis": hypothesis,
        "why_test_anyway": why_test_anyway, "expected_result": expected_result, "actual_result": None,
        "test_method": test_method, "safety_boundary": safety_boundary, "cost_boundary": cost_boundary,
        "reversibility": reversibility, "inputs": inputs or [], "variants": variants or [], "metrics": {},
        "what_worked": [], "what_failed": [], "lesson": None, "policy_or_strategy_change": None,
        "next_test": next_test, "next_owner": next_owner, "completion_state": completion_state,
        "external_action_performed": False, "created_at": _now(), "updated_at": _now(),
    }
    return persistence.append_record("certification_experiments", row)


def update_experiment(experiment_id: str, **changes: Any) -> dict[str, Any]:
    current = persistence.get_record("certification_experiments", experiment_id, key="experiment_id")
    if not current:
        raise ValueError("experiment_not_found")
    row = {**current, **changes, "experiment_id": experiment_id, "updated_at": _now(), "external_action_performed": False}
    return persistence.append_record("certification_experiments", row)


def certification_metrics(*, since: str | None = None) -> dict[str, Any]:
    rows = persistence.read_records("certification_experiments")
    if since:
        rows = [row for row in rows if str(row.get("created_at") or row.get("updated_at") or "") >= since]
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest.setdefault(str(row.get("experiment_id") or ""), row)
    values = list(latest.values())
    state = lambda *names: sum(1 for row in values if str(row.get("completion_state") or "").upper() in names)
    return {
        "certification_tests_created": len(values), "certification_tests_started": state("IN_PROGRESS", "COMPLETED", "CERTIFICATION_PASS", "PASS_REAL", "PASS_REAL_BOUNDED", "EXPERIMENT_FAILED"), "certification_tests_claimed": state("CLAIMED", "IN_PROGRESS", "COMPLETED", "CERTIFICATION_PASS", "PASS_REAL", "PASS_REAL_BOUNDED", "EXPERIMENT_FAILED"),
        "certification_tests_completed": state("COMPLETED", "CERTIFICATION_PASS", "PASS_REAL", "PASS_REAL_BOUNDED"),
        "certification_tests_failed": state("EXPERIMENT_FAILED"), "certification_tests_blocked": state("BLOCKED_EXTERNAL", "BLOCKED_HUMAN", "INSUFFICIENT_INPUT"),
        "rejects_overridden_to_certification_test": sum(1 for row in values if str(row.get("alpha_decision") or "").upper() == "REJECT"),
        "research_more_overridden_to_certification_test": sum(1 for row in values if str(row.get("alpha_decision") or "").upper() == "RESEARCH_MORE"),
        "department_certification_activity": {d: sum(1 for row in values if str(row.get("department") or "").upper() == d) for d in sorted({str(row.get("department") or "").upper() for row in values if row.get("department")})},
        "experiment_lessons_created": sum(1 for row in values if row.get("lesson")),
        "lessons_applied": sum(1 for row in values if row.get("lesson") and row.get("policy_or_strategy_change")),
        "next_tests_created": sum(1 for row in values if row.get("next_test")),
        "experiments_with_no_lesson": sum(1 for row in values if not row.get("lesson")),
        "trading_variants_tested": sum(len(row.get("variants") or []) for row in values if str(row.get("department") or "").upper() == "TRADING"),
        "creative_variants_created": sum(len(row.get("variants") or []) for row in values if str(row.get("department") or "").upper() == "CREATIVE"),
        "clyde_internal_matches": sum(1 for row in values if str(row.get("department") or "").upper() in {"CLYDE", "CLYDE/FUNDING", "FUNDING"}),
        "systems_isolated_tests": sum(1 for row in values if str(row.get("department") or "").upper() == "SYSTEMS" and "ISOLATED" in str(row.get("test_method") or "").upper()),
        "revenue_internal_validations": sum(1 for row in values if "REVENUE" in str(row.get("department") or "").upper()),
    }
