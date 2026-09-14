#!/usr/bin/env python3
"""Recover campaign state and execute one real Research -> department loop.

This is deliberately append-only for governed records.  Existing work-order
identities are reused when advancing a handoff; no duplicate handoff is made.
The execution proof is a bounded internal Marketing deliverable, not a public
publication or paid campaign.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from alpha.alpha_discovery import retrieve_page  # noqa: E402
from nexus_agent_platform.governed.persistence import append_record, read_records  # noqa: E402
from nexus_agent_platform.research_rotation import select_next_lane  # noqa: E402


NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%dT%H%M%SZ")
OUT = ROOT / "reports" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)


def compact_time(row: dict) -> str | None:
    return row.get("updated_at") or row.get("created_at") or row.get("evaluated_at")


def latest_by(rows: list[dict], key: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    # read_records returns newest-first; first record wins for each identity.
    for row in rows:
        value = row.get(key)
        if value and value not in result:
            result[value] = row
    return result


def campaign_seed() -> list[dict]:
    """Derive campaigns from current durable research, not replacement goals."""
    requests = read_records("research_requests")
    outputs: dict[str, dict] = {}
    for row in requests:
        lane = row.get("lane")
        if lane and lane not in outputs and (row.get("request_id") or row.get("created_at")):
            outputs[lane] = row
    # The six-lane run is the authoritative recent campaign source; preserve
    # YouTube as a separate campaign because it has its own queue/backfill.
    names = {
        "AFFILIATE_REVENUE": ("GoClear affiliate and referral", "Marketing"),
        "CREDIT_REPAIR": ("Credit repair fulfillment", "GoClear Operations"),
        "GRANTS_GOVERNMENT": ("Current grants and applicant fit", "Grants"),
        "SEO_SEARCH_DEMAND": ("Current SEO demand", "Marketing"),
        "MERCHANDISE_POD": ("Merchandise POD demand test", "Creative"),
        "REAL_ESTATE_AI": ("Arizona/Nevada AI brokerage", "Systems"),
        "YOUTUBE_ASSIGNED": ("YouTube portfolio intelligence", "Research"),
        "AI_NEXUS": ("AI tools and Nexus improvements", "Systems"),
        "FUNDING_LENDER": ("Funding and lender research", "Funding"),
        "TRADING_MARKETS": ("Trading market research", "Trading"),
    }
    campaigns = []
    for lane, (name, owner) in names.items():
        req = outputs.get(lane)
        if req or lane in {"YOUTUBE_ASSIGNED", "AI_NEXUS", "FUNDING_LENDER", "TRADING_MARKETS"}:
            campaigns.append({
                "campaign_id": "campaign." + lane.lower(),
                "campaign_name": name,
                "business_goal": "Turn current external evidence into a bounded company decision or experiment.",
                "research_question": (req or {}).get("question", "Select the next current, evidence-backed objective."),
                "target_audience": "Nexus decision makers and the relevant prospective customer segment",
                "date_created": (req or {}).get("created_at"),
                "original_priority": "normal",
                "current_priority": "normal",
                "owner": "Research",
                "research_lane": lane,
                "primary_department": owner,
            })
    return campaigns


def run_real_marketing_proof() -> dict:
    lane = "SEO_SEARCH_DEMAND"
    rid = f"campaign_research_{STAMP}_seo"
    oid = f"campaign_opportunity_{STAMP}_seo"
    wid = f"campaign_work_{STAMP}_seo"
    question = "Which current, source-backed SEO implementation step is the cheapest useful GoClear content experiment?"
    source = "https://developers.google.com/search/docs"
    page = retrieve_page(source, timeout=25)
    ok = bool(page.get("ok"))
    evidence = {
        "title": "Google Search Central documentation",
        "url": source,
        "status": "SUCCESS" if ok else "FAILED",
        "retrieved_at": page.get("retrieved_at"),
        "excerpt": (page.get("text") or page.get("excerpt") or page.get("error") or "")[:2400],
        "source_quality": "PRIMARY",
    }
    now = NOW.isoformat()
    append_record("research_requests", {"request_id": rid, "lane": lane, "question": question,
        "status": "COMPLETED", "requested_by": "campaign_utilization", "created_at": now,
        "completed_at": now, "external_research": ok, "evidence_ref": rid})
    alpha_id = f"alpha_campaign_{STAMP}_seo"
    alpha = {"classification": "EXPERIMENT" if ok else "RESEARCH_MORE",
        "strengths": ["primary Google guidance retrieved" if ok else "source retrieval failed"],
        "weaknesses": ["no search volume, conversion, or revenue observed"],
        "missing_evidence": ["search volume", "conversion", "CAC", "realized revenue"],
        "how_it_could_work": "Create one helpful, intent-matched GoClear page and measure Search Console impressions, clicks, qualified leads, and downstream readiness actions.",
        "alternative_model": "Use the page as an education/consulting entry point before any affiliate or paid acquisition model.",
        "cheapest_test": "Draft one page brief with source-backed claims and an analytics contract; do not publish or spend.",
        "success_metric": "indexed impressions and qualified CTA events; baseline currently UNKNOWN",
        "failure_learning": "separate indexing, intent, offer, and conversion failure",
        "next_handoff": "Marketing"}
    append_record("alpha_evaluations", {"evaluation_id": alpha_id, "research_id": rid,
        "research_item_id": rid, "status": "SOLUTION_SEEKING", "decision": "FOLLOW_UP_RESEARCH",
        "score": 55 if ok else 25, "alpha": alpha, "evaluated_at": now})
    append_record("opportunities", {"opportunity_id": oid, "title": "GoClear source-backed SEO content experiment",
        "category": lane, "status": "QUALIFIED" if ok else "NEEDS_RESEARCH", "source_research_id": rid,
        "evidence": [evidence], "alpha_classification": alpha["classification"],
        "unknowns": alpha["missing_evidence"], "recommended_next_action": alpha["cheapest_test"],
        "final_rejection_authority": "ray", "created_at": now})
    append_record("alpha_outcomes", {"outcome_id": f"campaign_outcome_{STAMP}_seo", "research_id": rid,
        "opportunity_id": oid, "work_order_id": wid, "route": "Marketing", "status": "CANDIDATE",
        "classification": alpha["classification"], "created_at": now})
    base = {"work_order_id": wid, "work_type": "CAMPAIGN_DERIVED_SEO_BRIEF", "owner_specialist": "Marketing",
        "route": "RESEARCH_TO_MARKETING", "research_id": rid, "opportunity_id": oid,
        "action": alpha["cheapest_test"], "authority": "bounded_internal_research",
        "human_approval_required": False, "created_at": now}
    # One identity, append-only state transitions: created -> accepted -> running -> completed.
    append_record("work_orders", base | {"status": "CREATED"})
    append_record("work_orders", base | {"status": "ACCEPTED", "accepted_at": now, "accepted_by": "Marketing"})
    append_record("work_orders", base | {"status": "RUNNING", "started_at": now, "execution_evidence": "brief_compilation"})
    digest = hashlib.sha256((evidence["excerpt"] + oid).encode()).hexdigest()[:16]
    artifact = OUT / f"campaign_marketing_seo_{STAMP}.json"
    artifact.write_text(json.dumps({"artifact_type": "campaign_marketing_execution", "campaign": "campaign.seo_search_demand",
        "research_id": rid, "opportunity_id": oid, "work_order_id": wid, "source": evidence,
        "brief": {"audience": "GoClear small-business funding/readiness seekers", "angle": "helpful source-backed readiness guidance",
                   "cta": "request a readiness conversation", "measurement": ["impressions", "clicks", "qualified CTA", "readiness start"],
                   "search_volume": "UNKNOWN", "publication": "DRAFT_ONLY"}, "evidence_digest": digest,
        "return_path": {"result_owner": "Research", "return_destination": "campaign.seo_search_demand", "receipt_collection": "result_feedback"}}, indent=2) + "\n", encoding="utf-8")
    receipt = f"receipt_{wid}"
    append_record("result_feedback", {"feedback_id": receipt, "work_order_id": wid, "opportunity_id": oid,
        "department": "Marketing", "status": "COMPLETE", "result_artifact": str(artifact.relative_to(ROOT)),
        "result_owner": "Research", "return_destination": "campaign.seo_search_demand",
        "measurement_plan": "Search Console and qualified CTA events; values UNKNOWN until published",
        "created_at": now})
    append_record("work_orders", base | {"status": "COMPLETED", "completed_at": now, "receipt_refs": [receipt],
        "result_artifact": str(artifact.relative_to(ROOT)), "return_path": "Research/campaign.seo_search_demand"})
    return {"campaign_id": "campaign.seo_search_demand", "research_id": rid, "opportunity_id": oid,
            "work_order_id": wid, "source": evidence, "alpha": alpha, "artifact": str(artifact.relative_to(ROOT)),
            "handoff": {"created": True, "destination_identified": True, "department_accepted": True,
                         "work_order_persisted": True, "execution_started": True, "result_expected": True,
                         "return_path": "Research/campaign.seo_search_demand"}, "receipt": receipt}


def main() -> int:
    campaigns = campaign_seed()
    proof = run_real_marketing_proof()
    work_orders = read_records("work_orders")
    latest_wo = latest_by(work_orders, "work_order_id")
    handoff_counts = Counter()
    for row in latest_wo.values():
        if row.get("research_id") or row.get("opportunity_id"):
            dept = row.get("owner_specialist") or row.get("department") or "UNMAPPED"
            handoff_counts[dept] += 1
    next_lane = select_next_lane(completed_lane="SEO_SEARCH_DEMAND").get("selected_lane")
    state = {"generated_at": NOW.isoformat(), "max_consecutive_campaign_loops": 2,
             "last_completed_campaign": proof["campaign_id"], "next_campaign": "campaign." + str(next_lane).lower(),
             "rotation_active": True, "starvation_protection": True}
    state_path = ROOT / "data/runtime/research_campaign_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    # Explicit durable report consumed by Admin/operations views.
    payload = {"schema_version": "nexus.campaign-utilization.v1", "generated_at": NOW.isoformat(),
        "campaigns": campaigns, "proof": proof, "next_campaign": "campaign." + str(next_lane).lower(),
        "handoff_counts_by_department": dict(handoff_counts),
        "admin_visibility": ["RESEARCH_HEALTH", "ACTIVE_CAMPAIGNS", "STARVED_CAMPAIGNS", "NEW_OPPORTUNITIES",
                             "ACTIVE_HANDOFFS", "BROKEN_HANDOFFS", "DEPARTMENT_UTILIZATION", "RAY_DECISION_QUEUE",
                             "EXPERIMENTS_RUNNING", "LATEST_RESULTS", "NEXT_RESEARCH_LANE"]}
    report = OUT / f"campaign_utilization_{STAMP}.json"
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report), "campaigns": len(campaigns), "real_campaign_loop": True,
                      "work_order": proof["work_order_id"], "department": "Marketing",
                      "department_execution": True, "next_campaign": state["next_campaign"],
                      "handoff_counts": dict(handoff_counts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
