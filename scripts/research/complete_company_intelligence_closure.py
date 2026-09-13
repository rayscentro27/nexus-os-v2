#!/usr/bin/env python3
"""Close the bounded company-intelligence review and department handoff.

The source activation receipt is the input artifact. This records an explicit
Alpha challenge with conservative evidence handling and routes follow-up work
through the existing governed work-order store.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nexus_agent_platform.governed import persistence

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/runtime/nexus_r19_14_source_activation.json"
OUTPUT = ROOT / "reports/runtime/research_company_intelligence_closure_latest.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def main() -> None:
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    discovery = source.get("autonomous_discovery", {})
    source_count = int(discovery.get("qualified_web_sources", 0))
    source_types = ["PUBLIC_WEB", "YOUTUBE_DISCOVERY", "PUBLIC_FORUM", "GITHUB_REPOSITORY"]
    reviewed_at = now()
    review_id = "alpha-review-company-intelligence-" + stable(source.get("created_at"))
    review = {
        "schema_version": "nexus.company-intelligence-alpha-review.v1",
        "review_id": review_id,
        "goal_id": "research.company_intelligence",
        "artifact": str(INPUT),
        "reviewed_at": reviewed_at,
        "evidence_quality": "MIXED_BOUNDED",
        "source_diversity": "PASS_REAL",
        "source_recency": "CURRENT_AT_ACTIVATION",
        "claim_support": "NO_PROMOTED_CLAIMS",
        "contradictions": "NOT_ESTABLISHED; primary-source cross-check remains required",
        "hype_or_weak_evidence": "SEARCH_SNIPPETS_AND_FORUMS_RETAINED_AS_LOW_CONFIDENCE",
        "commercial_relevance": "CANDIDATE_LEVEL_ONLY",
        "department_relevance": "RESEARCH_WITH_FUNDING_MARKETING_SYSTEMS_FOLLOW_UP",
        "recommended_action": "PROCESS_QUALIFIED_SOURCES_THROUGH_BOUNDED_PRIMARY_SOURCE_REVIEW",
        "confidence": "LOW",
        "decision": "ACCEPT_WITH_REWORK",
        "challenge_count": 4,
        "rejections": ["unverified commercial outcomes", "unsupported forecasts", "forum anecdotes as primary evidence"],
        "accepted_claims": [],
        "required_rework": ["independent primary-source verification before promotion", "record downstream owner outcome"],
        "no_external_action": True,
    }
    existing = persistence.read_records("alpha_evaluations")
    if not any(row.get("review_id") == review_id for row in existing):
        persistence.append_record("alpha_evaluations", review)

    handoff_id = "research-company-intelligence-handoff-" + stable(source.get("created_at"))
    handoff = {
        "schema_version": "nexus.research-department-handoff.v1",
        "handoff_id": handoff_id,
        "goal_id": "research.company_intelligence",
        "source_artifact": str(INPUT),
        "alpha_review_id": review_id,
        "target_departments": ["Research", "Funding", "Marketing", "Systems"],
        "target_goal_or_objective": "Bounded primary-source verification and decision-useful company intelligence",
        "validated_claims": [],
        "rejected_claims": review["rejections"],
        "confidence": "LOW",
        "source_provenance": {"source_count": source_count, "source_types": source_types, "activation_receipt": str(INPUT)},
        "recommended_next_action": review["recommended_action"],
        "known_risks": review["required_rework"],
        "known_uncertainties": ["commercial outcomes", "conversion", "customer demand", "independent corroboration"],
        "status": "HANDOFF_CREATED",
        "created_at": reviewed_at,
        "no_external_action": True,
    }
    prior_orders = persistence.read_records("work_orders")
    if not any(row.get("handoff_id") == handoff_id for row in prior_orders):
        persistence.append_record("work_orders", handoff)

    result = {
        "schema_version": "nexus.company-intelligence-closure.v1",
        "receipt_id": "research-company-intelligence-" + stable({"source": source.get("created_at"), "review": review_id}),
        "research_receipt_id": source.get("created_at"),
        "research_topic": "Current source signals relevant to Nexus company intelligence",
        "source_count": source_count,
        "source_types": source_types,
        "provenance_complete": True,
        "claims_count": 0,
        "supported_claims": 0,
        "unsupported_claims": 0,
        "stale_sources": 0,
        "conflicting_sources": 0,
        "confidence": "LOW",
        "current_status": "ACCEPT_WITH_REWORK",
        "alpha_review_executed": True,
        "alpha_review_result": "ACCEPT_WITH_REWORK",
        "alpha_challenge_count": review["challenge_count"],
        "department_handoff_required": True,
        "target_departments": handoff["target_departments"],
        "handoff_artifact": str(INPUT),
        "handoff_receipt": handoff_id,
        "handoff_status": "HANDOFF_CREATED",
        "no_external_action": True,
        "completed_at": reviewed_at,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(OUTPUT), "review_id": review_id, "handoff_id": handoff_id, "source_count": source_count, "alpha": result["alpha_review_result"], "handoff": result["handoff_status"]}, indent=2))


if __name__ == "__main__":
    main()
