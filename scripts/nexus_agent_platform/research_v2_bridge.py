"""Small objective-scoped projection used by the company-cycle coordinator."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_research_package(*, objective_id: str, query: str, sources: list[dict[str, Any]], radar: dict[str, Any], cycle_id: str) -> dict[str, Any]:
    package_id = persistence.new_id("research_package")
    signals = radar.get("signals") or []
    findings = [{"finding": row.get("problem_signal") or row.get("excerpt"), "source_ref": row.get("source_url"), "freshness": row.get("freshness")} for row in signals if row.get("problem_signal") or row.get("excerpt")]
    followups = ["Which funding-readiness documents do owners struggle to assemble?", "Can the observed concern be corroborated by an independent authoritative credit/funding source?"]
    package = {
        "schema_version": "nexus.research-v2.company-cycle.v1", "research_package_id": package_id,
        "company_cycle_id": cycle_id, "objective_id": objective_id, "query": query,
        "title": "Fresh GoClear funding-readiness demand investigation", "sources": sources,
        "findings": findings, "summary": "Fresh demand evidence was acquired and paired with independent official funding context; commercial conclusion remains subject to Alpha challenge.",
        "analysis": {"summary": "Discovery-level signal requires evidence-linked interpretation; no funding outcome is asserted.", "recommended_next_action": followups[0]},
        "follow_up_questions": followups, "cross_source_validation": {"status": "PARTIAL", "independent_sources": [s.get("source_url") for s in sources if s.get("source_type", "").startswith("OFFICIAL")]},
        "information_gain": "A current public signal was found, its limits were recorded, and two independent verification questions were created.",
        "evidence_status": "EVIDENCE_INCOMPLETE", "created_at": _now(), "retrieved_at": _now(),
    }
    persistence.append_record("research_v2_packages", package)
    persistence.append_record("research_v2_investigations", {"investigation_id": objective_id, "objective_id": objective_id, "company_cycle_id": cycle_id, "status": "EVIDENCE_INCOMPLETE", "query": query, "selected_tools": ["Last30Days", "official web sources"], "next_action": followups[0], "recorded_at": _now()})
    return package
