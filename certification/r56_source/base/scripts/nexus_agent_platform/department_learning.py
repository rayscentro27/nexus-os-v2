"""Scoped department learning on Nexus's existing shared Supabase knowledge tables.

This module deliberately reuses ``department_lessons`` and stores the richer,
typed learning contract in its existing ``result_lineage`` JSON column.  It is
not a second memory store.  A missing Supabase connection is reported instead
of silently claiming durable shared-history success.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


EXPERT_BY_DEPARTMENT = {
    "TRADING": "MERCURY_TRADING", "MERCURY_TRADING": "MERCURY_TRADING",
    "RESEARCH": "SCOUT_INTELLIGENCE", "SYSTEMS": "FORGE_SYSTEMS",
    "CREATIVE": "CREATIVE", "MARKETING": "MIRA_MARKETING",
    "FUNDING": "GRANT_FUNDING", "CLYDE": "CLYDE_CREDIT",
}
EVIDENCE_LEVELS = {"OBSERVATION", "HYPOTHESIS", "SUPPORTED_FINDING",
                   "REPLICATED_FINDING", "GENERALIZABLE_LESSON"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_learning_id(department: str, case_id: str, evidence_ref: str) -> str:
    raw = f"{department.upper()}:{case_id}:{evidence_ref}"
    return "lesson_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def normalize_learning(record: dict[str, Any]) -> dict[str, Any]:
    """Validate a reusable lesson while preventing evidence-level inflation."""
    value = dict(record)
    value["department"] = str(value.get("department") or "").upper()
    if value["department"] not in EXPERT_BY_DEPARTMENT:
        raise ValueError("Unknown department for learning history")
    level = str(value.get("evidence_level") or "OBSERVATION").upper()
    if level not in EVIDENCE_LEVELS:
        raise ValueError("Invalid evidence level")
    if int(value.get("sample_size") or 0) <= 1 and level in {"REPLICATED_FINDING", "GENERALIZABLE_LESSON"}:
        raise ValueError("Single-sample evidence cannot be promoted to a general rule")
    for field in ("case_id", "objective", "action_or_change", "result", "what_was_learned",
                  "reusable_lesson", "scope", "evidence_references"):
        if value.get(field) in (None, "", []):
            raise ValueError(f"Missing required learning field: {field}")
    value.setdefault("learning_id", stable_learning_id(
        value["department"], str(value["case_id"]), ",".join(map(str, value["evidence_references"]))))
    value.setdefault("date", _now())
    value.setdefault("last_reviewed", _now())
    value.setdefault("confidence", "LOW")
    value.setdefault("replication_count", 0)
    value.setdefault("out_of_sample_validated", False)
    value.setdefault("contradictory_evidence", [])
    value.setdefault("alternative_explanations", [])
    value.setdefault("what_changed", "")
    value.setdefault("why_it_changed", "")
    value.setdefault("root_cause", "UNDETERMINED")
    value.setdefault("what_was_not_proven", [])
    value.setdefault("what_should_be_done_differently_next_time", "")
    value.setdefault("baseline_or_prior_state", "")
    value.setdefault("source_references", [])
    value.setdefault("notebook_id", None)
    value.setdefault("next_hypothesis", "")
    value.setdefault("next_action", "")
    value["evidence_level"] = level
    return value


def lookup_department_learning(department: str, *, topic_terms: list[str] | None = None,
                               limit: int = 100) -> dict[str, Any]:
    """Read scoped prior lessons from the existing department_lessons table."""
    try:
        from social import _supabase
    except Exception as exc:  # pragma: no cover - environment-specific import
        return {"status": "UNAVAILABLE", "reason": type(exc).__name__, "records": []}
    if not _supabase.configured():
        return {"status": "UNAVAILABLE", "reason": "SUPABASE_NOT_CONFIGURED", "records": []}
    expert = EXPERT_BY_DEPARTMENT.get(str(department).upper())
    if not expert:
        return {"status": "UNAVAILABLE", "reason": "UNKNOWN_DEPARTMENT", "records": []}
    query = (f"department_lessons?expert_id=eq.{expert}&select=lesson_id,finding_id,expert_id,"
             f"success_failure,lesson,next_decision_rule,result_lineage,created_at"
             f"&order=created_at.desc&limit={max(1, min(int(limit), 250))}")
    status, body = _supabase.rest("GET", query)
    if status != 200 or not isinstance(body, list):
        return {"status": "UNAVAILABLE", "reason": f"SUPABASE_HTTP_{status}", "records": []}
    terms = [str(x).casefold() for x in (topic_terms or []) if str(x).strip()]
    records = []
    for row in body:
        lineage = row.get("result_lineage") if isinstance(row.get("result_lineage"), dict) else {}
        learning = lineage.get("learning_record") if isinstance(lineage.get("learning_record"), dict) else {}
        if not learning:
            learning = {"lesson_id": row.get("lesson_id"), "department": department,
                        "lesson": row.get("lesson"), "next_decision_rule": row.get("next_decision_rule"),
                        "scope": lineage.get("scope"), "evidence_references": lineage.get("evidence_references", [])}
        text = json.dumps(learning, ensure_ascii=False).casefold()
        if not terms or any(term in text for term in terms):
            records.append(learning)
    return {"status": "OK", "expert_id": expert, "records": records,
            "query_performed": True, "source_table": "department_lessons"}


def persist_department_learning(record: dict[str, Any]) -> dict[str, Any]:
    """Upsert one scoped lesson into the existing Supabase department history."""
    value = normalize_learning(record)
    expert = EXPERT_BY_DEPARTMENT[value["department"]]
    body = {
        "lesson_id": value["learning_id"],
        "finding_id": str(value.get("finding_id") or value["learning_id"]),
        "expert_id": expert,
        "success_failure": str(value.get("success_failure") or "LEARNED"),
        "lesson": str(value["reusable_lesson"]),
        "next_decision_rule": str(value.get("next_action") or value.get("what_should_be_done_differently_next_time") or "Review lesson scope before reusing."),
        "result_lineage": {"schema_version": "nexus.department-learning.v1", "learning_record": value,
                           "evidence_references": value.get("evidence_references", []),
                           "scope": value.get("scope"), "case_id": value.get("case_id")},
        "created_at": value["date"],
    }
    try:
        from social import _supabase
    except Exception as exc:  # pragma: no cover - environment-specific import
        return {"status": "UNAVAILABLE", "learning_id": value["learning_id"], "reason": type(exc).__name__}
    if not _supabase.configured():
        return {"status": "UNAVAILABLE", "learning_id": value["learning_id"], "reason": "SUPABASE_NOT_CONFIGURED"}
    status, response = _supabase.rest("POST", "department_lessons?on_conflict=lesson_id", body=[body],
                                     prefer="return=representation,resolution=merge-duplicates")
    if status not in {200, 201, 204}:
        return {"status": "WRITE_FAILED", "learning_id": value["learning_id"],
                "http_status": status, "error": response}
    return {"status": "WRITTEN", "learning_id": value["learning_id"], "department": value["department"],
            "expert_id": expert, "row_count": len(response) if isinstance(response, list) else 1,
            "record": value}
