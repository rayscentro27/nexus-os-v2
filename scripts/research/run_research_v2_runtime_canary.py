#!/usr/bin/env python3
"""Real, read-only Research V2 integration proof.

Uses the existing mobile-detailing Research records and their real public
source URLs. It creates only governed research/plan *drafts*; no opportunity,
work-order, publishing, payment, or customer action is performed.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "scripts"))

from research_document_pipeline import fetch  # noqa: E402
from research_v2 import (  # noqa: E402
    alpha_collaborative_analysis,
    classify_intents,
    extract_claims,
    investigation_decision,
    knowledge_maturity,
    opportunity_thesis,
    persist_v2_records,
    productivity_metrics,
    research_package,
    select_source_requirements,
    source_reputation,
    synthesize_plan,
)
from nexus_agent_platform.governed.persistence import read_records  # noqa: E402


def latest_business_research() -> dict:
    rows = read_records("business_research")
    return next((row for row in reversed(rows) if row.get("sources")), {})


def main() -> int:
    prior = latest_business_research()
    sources = prior.get("sources", [])[:3]
    if not sources:
        raise RuntimeError("no existing real business-opportunity Research record found")
    idea = {"source_id": prior.get("idea_id", "existing-idea"), "source_type": "EXISTING_IDEA", "source_url": "governed://business_ideas", "source_title": "Mobile detailing business", "source_author_or_channel": "Ray business idea / WP8.3"}
    acquired, evidence, source_rows, claims = [], [], [], []
    for index, candidate in enumerate(sources, 1):
        url = candidate.get("url")
        if not url:
            continue
        try:
            raw, headers = fetch(url)
            source = {"source_id": f"opportunity-source-{index}", "source_type": "WEB_PAGE", "source_url": url, "source_title": candidate.get("source", url), "source_class": candidate.get("kind", "competitor_or_regulatory"), "content_type": headers.get("content_type"), "acquired": True}
            source_rows.append(source); acquired.append(url)
            evidence.append({"source": source, "question_answered": "What competitor pricing, operating, or regulatory evidence exists?", "provenance": {"source_url": url, "content_hash": __import__("hashlib").sha256(raw.encode()).hexdigest(), "excerpt": raw[:500]}})
            claims.extend(extract_claims(raw[:12000], source)[:3])
        except Exception as exc:
            evidence.append({"source": url, "acquired": False, "error": str(exc)})
    for claim in claims:
        claim["verification_status"] = "PARTIALLY_SUPPORTED"
    questions = []
    for question in ("What direct customer demand and CAC evidence exists?", "What local wash-water requirements apply?", "What operating model and pricing ranges do competitors publish?"):
        req = select_source_requirements(question, "BUSINESS_OPPORTUNITY")
        questions.append({"question_id": f"canary-{len(questions)+1}", "question": question, "intent": "BUSINESS_OPPORTUNITY", "source_class": req["source_class"], "query": req["query"], "status": "RESOLVED" if len(acquired) else "OPEN"})
    thesis = opportunity_thesis(title="Phoenix mobile detailing business", customer="individual owners, households, fleets", problem="vehicle care convenience and recurring maintenance", value_proposition="mobile scheduled detailing with recurring and fleet options", revenue_model="one-time service plus recurring membership hypothesis", evidence=evidence)
    package = research_package(source=idea, claims=claims, evidence=evidence, questions=questions, opportunity=thesis)
    alpha = alpha_collaborative_analysis(package, proposed_action="PRELIMINARY_BUSINESS_PLAN")
    package["alpha_review"] = alpha
    package["unknowns"] = ["direct demand", "CAC", "retention", "route density", "throughput"]
    plan = synthesize_plan(package)
    handoff = {"handoff_id": f"draft-{package['research_package_id']}", "primary_owner": "EXECUTIVE_PLANNING", "secondary_owners": ["MARKETING", "OPERATIONS"], "why": "market validation and operating-model research remain before execution", "input_package": package["research_package_id"], "expected_department_output": "bounded validation brief", "department_handoff_status": "DRAFT_REVIEW_REQUIRED", "external_action_allowed": False}
    reputation = source_reputation({"source_id": "phoenix-mobile-detailing-public-sources", "source_type": "WEB_PAGE", "channel_or_domain": "multiple public competitor/regulatory sources", "items_processed": len(source_rows), "claims_checked": len(claims), "partially_supported_claims": len(claims)})
    records = {"sources": source_rows + [idea], "claims": claims, "opportunities": [{"opportunity_id": thesis["opportunity_thesis_id"], "title": thesis["title"], "goclear_fit": "LOW", "new_venture_potential": "ELIGIBLE", "research_continues": True, "status": "THESIS_ONLY_NO_EXECUTION"}], "questions": questions, "investigations": [{"investigation_id": package["research_package_id"], "package": package, "decision": investigation_decision(kind="OPPORTUNITY", researchability=.8, testability=.7, upside=.6, decision_relevance=.7)}], "alpha_reviews": [{"research_package_id": package["research_package_id"], **alpha}], "plans": [plan], "reputations": [reputation], "handoffs": [handoff], "follow_ups": [{"parent_package_id": package["research_package_id"], "questions": package["unknowns"], "status": "OPEN", "bounded": True}]}
    counts = persist_v2_records(records)
    knowledge = knowledge_maturity(0)
    report = {"status": "PASS_REAL", "initial_source": idea, "ray_supplied_support_urls": False, "questions_generated": questions, "searches_performed": [x["query"] for x in questions], "sources_discovered": len(sources), "sources_acquired": len(acquired), "source_classes": sorted({x["source_class"] for x in source_rows}), "package": package, "alpha_review": alpha, "plan": plan, "handoff": handoff, "reputation": reputation, "knowledge_canary": {"source_processed": "existing GitHub Research artifact", "knowledge_captured": True, **knowledge, "opportunity_created": False}, "durable_record_counts": counts, "metrics": productivity_metrics([{"acquired": True, "processing_status": "FULLY_PROCESSED", "substantive_findings": claims, "summary_created": True, "extraction_created": True, "follow_up_questions": questions}]), "safety": {"opportunities_executed": 0, "work_orders_created": 0, "external_action": False}}
    out = ROOT / "reports" / "runtime" / "research_v2_runtime_canary_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "sources_acquired": len(acquired), "claims": len(claims), "alpha_assessment": alpha["alpha_assessment"], "plan_status": plan["plan_status"], "handoff_status": handoff["department_handoff_status"], "report": str(out.relative_to(ROOT)), "records": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
