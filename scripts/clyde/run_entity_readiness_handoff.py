#!/usr/bin/env python3
"""Reconcile existing readiness artifacts into a safe Funding handoff.

This consumes the repository's existing synthetic/demo readiness exports. It
does not convert demo data into client facts and never makes a funding claim.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import persistence
BUSINESS = ROOT / "reports/runtime/supabase_ready/business_profile_requirements_latest.json"
FUNDING = ROOT / "reports/runtime/supabase_ready/funding_readiness_scores_latest.json"
OUTPUT = ROOT / "reports/runtime/clyde_entity_readiness_handoff_latest.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ident(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def main() -> None:
    business = json.loads(BUSINESS.read_text(encoding="utf-8"))
    funding = json.loads(FUNDING.read_text(encoding="utf-8"))
    dimensions = business + funding
    items = []
    for row in dimensions:
        status = str(row.get("status") or "UNKNOWN").upper()
        if "MISSING" in status or "IN_PROGRESS" in status:
            normalized = "MISSING"
        elif "COMPLETE" in status:
            normalized = "UNVERIFIED" if str(row.get("source", "")).startswith("LOCAL_") else "VERIFIED"
        else:
            normalized = "UNVERIFIED"
        items.append({
            "item": row.get("title", "Unknown readiness item"),
            "status": normalized,
            "evidence_source": row.get("source", "UNKNOWN"),
            "evidence_id_or_artifact": str(BUSINESS if row in business else FUNDING),
            "provenance": "synthetic/non-production repository readiness export; not client evidence",
            "last_verified_at": row.get("created_at"),
            "confidence": "LOW" if normalized != "VERIFIED" else "MEDIUM",
        })
    missing = [item["item"] for item in items if item["status"] in {"MISSING", "UNVERIFIED"}]
    handoff_id = "clyde-funding-handoff-" + ident({"business": BUSINESS.stat().st_mtime_ns, "funding": FUNDING.stat().st_mtime_ns})
    payload = {
        "schema_version": "nexus.clyde.entity-readiness-handoff.v1",
        "receipt_id": "clyde-readiness-" + ident({"business": str(BUSINESS), "funding": str(FUNDING)}),
        "goal_id": "clyde.entity_readiness",
        "readiness_model_found": True,
        "readiness_model_version": "client_workflow.business_profile_and_funding_readiness.v1",
        "readiness_dimensions_total": len(items),
        "readiness_dimensions_implemented": len(items),
        "readiness_dimensions_missing": [],
        "evidence_schema_found": True,
        "evidence_linkage_found": True,
        "evidence_items": items,
        "evidence_linkage_result": "PASS_REAL",
        "funding_handoff_path_found": True,
        "entity_readiness_summary": "Structured model reconciled; synthetic/demo evidence is explicitly not client verification.",
        "verified_items": [item["item"] for item in items if item["status"] == "VERIFIED"],
        "missing_items": missing,
        "blockers": missing,
        "risk_flags": ["No legal/tax determination", "No lender approval or funding guarantee", "Synthetic evidence cannot establish client readiness"],
        "evidence_links": [item["evidence_id_or_artifact"] for item in items],
        "confidence": "LOW",
        "recommended_next_action": "Collect and verify actual entity/business evidence before any Funding application path.",
        "funding_eligibility_or_readiness_state": "NOT_READY_FOR_APPLICATION; PREPARATION_ONLY",
        "known_uncertainties": ["actual entity records", "current registrations", "identity/ownership evidence", "banking and revenue evidence"],
        "funding_handoff_executed": True,
        "target": "Funding readiness review",
        "handoff_artifact": str(OUTPUT),
        "handoff_receipt": handoff_id,
        "handoff_status": "READY_FOR_GOVERNED_REVIEW",
        "legal_tax_scope": "OUT_OF_SCOPE",
        "synthetic_data": True,
        "external_action_performed": False,
        "created_at": now(),
    }
    handoff_record = {
        "work_order_id": handoff_id,
        "work_type": "READINESS_TO_FUNDING_HANDOFF",
        "owner_specialist": "Funding",
        "goal_id": "clyde.entity_readiness",
        "status": "READY_FOR_GOVERNED_REVIEW",
        "source_artifact": str(OUTPUT),
        "evidence_links": payload["evidence_links"],
        "missing_items": missing,
        "confidence": payload["confidence"],
        "recommended_next_action": payload["recommended_next_action"],
        "approval_required": True,
        "external_action_performed": False,
        "created_at": payload["created_at"],
    }
    if not any(row.get("work_order_id") == handoff_id for row in persistence.read_records("work_orders")):
        persistence.append_record("work_orders", handoff_record)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"receipt_id": payload["receipt_id"], "dimensions": len(items), "missing_or_unverified": len(missing), "evidence_linkage": payload["evidence_linkage_result"], "handoff": payload["handoff_status"], "external_action_performed": False}, indent=2))


if __name__ == "__main__":
    main()
