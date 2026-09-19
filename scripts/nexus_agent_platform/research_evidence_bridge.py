"""Objective-scoped Research/Alpha evidence resolution for Hermes.

This is a read-only projection over the existing governed ledgers.  It is
deliberately not a new queue or research engine: an objective is resolved
first, then every child record is selected from that parent lineage.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GOVERNED = ROOT / "data/governed"
RUNTIME_ALPHA = ROOT / "data/runtime/alpha_research"


def _rows(name: str) -> list[dict[str, Any]]:
    path = GOVERNED / f"{name}.jsonl"
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and isinstance(json.loads(line), dict)]
    except (OSError, ValueError, TypeError):
        return []


def _stamp(row: dict[str, Any]) -> str:
    return str(row.get("recorded_at") or row.get("evaluated_at") or row.get("completed_at")
               or row.get("updated_at") or row.get("created_at") or "")


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(rows, key=_stamp) if rows else None


def resolve_objective(objective_id: str) -> dict[str, Any]:
    """Return the exact current lineage; never fall back to global latest."""
    oid = str(objective_id or "").strip()
    if not oid:
        return {"status": "MISSING_OBJECTIVE", "objective_id": None,
                "missing_evidence": ["objective_id"]}

    investigations = _rows("research_v2_investigations")
    sources = _rows("research_v2_sources")
    questions = _rows("research_v2_questions")
    followups = _rows("research_v2_follow_ups")
    alpha_reviews = _rows("research_v2_alpha_reviews")
    persisted_packages = _rows("research_v2_packages")
    evaluations = _rows("alpha_evaluations")
    packages = [row for row in investigations if str(row.get("investigation_id")) == oid
                or str(row.get("objective_id")) == oid]
    objective_packages = [row for row in persisted_packages if str(row.get("objective_id")) == oid
                          or str(row.get("investigation_id")) == oid]
    alpha_for_objective = [row for row in evaluations
                           if str(row.get("investigation_id")) == oid
                           or str(row.get("research_id")) == oid
                           or str(row.get("objective_id")) == oid]
    # A package may be named by the objective's investigation record.  A
    # source's upstream run is retained as supporting context, never identity.
    lineage_package_ids = {str(row.get("research_package_id")) for row in objective_packages
                           if row.get("research_package_id")}
    lineage_package_ids |= {str(row.get("last_evidence_package_id")) for row in packages
                           if row.get("last_evidence_package_id")}
    source_ids = {str(row.get("source_id")) for row in packages if row.get("source_id")}
    scoped_sources = [row for row in sources if str(row.get("investigation_id")) == oid
                      or str(row.get("objective_id")) == oid
                      or str(row.get("upstream_run_id")) == oid
                      or str(row.get("source_id")) in source_ids]
    scoped_questions = [row for row in questions if str(row.get("objective_id")) == oid
                        or str(row.get("investigation_id")) == oid
                        or str(row.get("source_id")) in source_ids]
    scoped_followups = [row for row in followups if str(row.get("objective_id")) == oid
                        or str(row.get("investigation_id")) == oid
                        or str(row.get("parent_objective_id")) == oid]
    scoped_reviews = [row for row in alpha_reviews
                      if str(row.get("objective_id")) == oid
                      or str(row.get("investigation_id")) == oid
                      or str(row.get("research_package_id")) in lineage_package_ids]
    package_id = (str((_latest(objective_packages) or {}).get("research_package_id") or "")
                  or str((_latest(packages) or {}).get("last_evidence_package_id") or "")
                  or str(((_latest(scoped_questions) or {}).get("last_evidence_package_id")) or ""))
    if not package_id and scoped_sources:
        # Older Codex packages predated durable package persistence.  This
        # stable lineage reference is explicit reconstruction, not a claim
        # that the old transient package object still exists.
        package_id = f"reconstructed:{oid}"
    if package_id:
        lineage_package_ids.add(package_id)
    latest_alpha = _latest(alpha_for_objective)
    receipt = None
    receipt_id = str((latest_alpha or {}).get("receipt_id") or "")
    if receipt_id:
        path = RUNTIME_ALPHA / f"{receipt_id}.json"
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            receipt = {"receipt_id": receipt_id, "status": "LEDGER_ONLY"}
    latest_investigation = _latest(packages)
    latest_source = _latest(scoped_sources)
    package = {
        "research_package_id": package_id or None,
        "objective_id": oid,
        "investigation": latest_investigation,
        "source": latest_source,
        "source_ids": sorted({str(row.get("source_id")) for row in scoped_sources if row.get("source_id")}),
        "questions": sorted(scoped_questions, key=_stamp, reverse=True)[:8],
        "alpha_reviews": sorted(scoped_reviews, key=_stamp, reverse=True)[:8],
        "followups": sorted(scoped_followups, key=_stamp, reverse=True)[:8],
        "status": (latest_investigation or {}).get("status") or (latest_source or {}).get("processing_status") or "UNKNOWN",
        "latest_recorded_at": _stamp(latest_investigation or latest_source or {}),
    }
    missing = []
    if not packages and not alpha_for_objective and not scoped_sources:
        missing.append("objective_lineage")
    if not package_id and not scoped_sources:
        missing.append("latest_research_package")
    if not latest_alpha:
        missing.append("latest_alpha_receipt")
    return {
        "status": "OK" if not missing else "PARTIAL",
        "objective_id": oid,
        "research_package": package,
        "alpha_evaluation": latest_alpha,
        "alpha_receipt": receipt,
        "missing_evidence": missing,
        "current_next_action": ((latest_alpha or {}).get("recommended_next_stage")
                                 or (latest_alpha or {}).get("required_followup")
                                 or (latest_investigation or {}).get("next_action")
                                 or "No objective-linked next action recorded."),
        "historical_records_excluded": True,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
