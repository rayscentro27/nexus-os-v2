"""Small governed input ledger for real build-certification nutrients.

This is an input contract over the existing governed store, not a scheduler or
research system. It records provenance and routing context so later Alpha and
department receipts can be tied to the same real source.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_input(*, input_id: str, business_or_nexus: str, department: str, source: str,
                 source_class: str, why_this_matters: str, customer_or_system_problem: str,
                 hypothesis: str, expected_value: str, testability: str,
                 evidence_strength: str, novelty: str, parent_goal: str,
                 next_owner: str, date_or_freshness: str = "CURRENT_AT_ACQUISITION",
                 duplicate: bool = False, stale: bool = False, actionable: bool = True,
                 certification_value: str = "BOUNDED_INTERNAL_LEARNING", details: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = persistence.get_record("certification_inputs", input_id, key="input_id")
    if existing:
        return {**existing, "deduplicated": True}
    row = {
        "schema_version": "nexus.certification-input.v1", "input_id": input_id,
        "business_or_nexus": business_or_nexus, "department": department, "source": source,
        "source_class": source_class, "date_or_freshness": date_or_freshness,
        "why_this_matters": why_this_matters, "customer_or_system_problem": customer_or_system_problem,
        "hypothesis": hypothesis, "expected_value": expected_value, "testability": testability,
        "evidence_strength": evidence_strength, "novelty": novelty, "parent_goal": parent_goal,
        "next_owner": next_owner, "duplicate": bool(duplicate), "stale": bool(stale),
        "actionable": bool(actionable), "certification_value": certification_value,
        "details": details or {}, "created_at": _now(), "external_action_performed": False,
    }
    return persistence.append_record("certification_inputs", row)


def input_metrics(*, since: str | None = None) -> dict[str, Any]:
    rows = persistence.read_records("certification_inputs")
    if since:
        rows = [row for row in rows if str(row.get("created_at") or "") >= since]
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest.setdefault(str(row.get("input_id") or ""), row)
    rows = list(latest.values())
    return {
        "real_inputs_acquired": len(rows),
        "unique_sources": len({str(row.get("source") or "") for row in rows if row.get("source")} ),
        "new_research_questions": len({str(row.get("hypothesis") or "") for row in rows if row.get("hypothesis")} ),
        "departments_fed": sorted({str(row.get("department") or "").upper() for row in rows if row.get("department")} ),
        "inputs_by_department": {dept: sum(1 for row in rows if str(row.get("department") or "").upper() == dept) for dept in sorted({str(row.get("department") or "").upper() for row in rows if row.get("department")})},
        "actionable_inputs": sum(1 for row in rows if row.get("actionable")),
        "testable_inputs": sum(1 for row in rows if any(token in str(row.get("testability") or "").upper() for token in ("SAFE", "CHEAP", "REVERSIBLE", "BOUNDED"))),
        "stale_inputs": sum(1 for row in rows if row.get("stale")),
        "duplicates": sum(1 for row in rows if row.get("duplicate")),
        "source_classes": sorted({str(row.get("source_class") or "UNKNOWN") for row in rows}),
    }
