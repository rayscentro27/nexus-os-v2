#!/usr/bin/env python3
"""Run four bounded, read-only proactive Research -> Alpha canaries.

The existing Alpha model-review bridge is used; this script only creates
durable mission/question and evidence records and never publishes, spends,
trades, or contacts anyone.
"""
from __future__ import annotations

import json
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_missions import build_proactive_question, persist_question
from nexus_agent_platform.alpha_model_review import review_demand_package

CANARIES = [
    ("SYSTEMS", "What are Needle and Jev, and do their public evidence and compatibility constraints justify an isolated Nexus benchmark?", "https://github.com/search?q=needle+jev&type=repositories", "systems-capability"),
    ("TRADING", "What bounded strategy or tool candidate appears in TradingView Editor's Picks that Trading should paper-test next?", "https://www.tradingview.com/scripts/editors-picks/", "trading-candidate"),
    ("CLYDE_FUNDING", "What current public funding-readiness problem should GoClear investigate next, and what evidence is needed before client education?", "https://www.sba.gov/business-guide/plan-your-business/market-research-competitive-analysis", "goclear-funding"),
    ("REVENUE_OPPORTUNITY_DISCOVERY", "What low-cost public opportunity could plausibly contribute to verified net revenue, and what economics and fulfillment evidence is missing?", "https://www.shopify.com/affiliates", "revenue-opportunity"),
]

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "NexusResearch/1.0 (bounded public evidence)"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
            return response.read(12000).decode("utf-8", "replace")
    except Exception as exc:
        return f"Public fetch bounded failure: {exc.__class__.__name__}. The source URL remains an unresolved evidence reference."

def main() -> int:
    results = []
    for department, question, url, slug in CANARIES:
        now = datetime.now(timezone.utc).isoformat()
        target = "CLYDE_CREDIT" if department == "CLYDE_FUNDING" else department
        record = build_proactive_question(department=department, question=question,
            why_this_research=f"Standing {department} mission requires a bounded current evidence check.",
            trigger="DEPARTMENT_MISSION" if department != "REVENUE_OPPORTUNITY_DISCOVERY" else "REVENUE_OPPORTUNITY",
            business_or_nexus="GOCLEAR" if department == "CLYDE_FUNDING" else "NEXUS",
            parent_goal="Verified $1,000/month net revenue" if department == "REVENUE_OPPORTUNITY_DISCOVERY" else "Advance the department mission",
            project=f"proactive-canary-{slug}", expected_value="A source-backed internal decision or a precise next question.",
            source_plan=[url], requested_by="nexus_research", mode="GOCLEAR_PROACTIVE" if department == "CLYDE_FUNDING" else "NEXUS_DEPARTMENTAL_PROACTIVE",
            handoff_target=target)
        record.update({"source_type": "WEB_PAGE", "source_id": f"proactive-canary-{slug}", "source_url": url})
        persist_question(record)
        raw = fetch(url)
        source_id = f"proactive-canary-{slug}"
        source = {"source_id": source_id, "title": question, "url": url, "source_type": "PUBLIC_WEB", "snippet": raw[:1800], "retrieved_at": now}
        persistence.append_record("research_v2_sources", source)
        package = {"research_id": source_id, "investigation_id": record["objective_id"], "finding_id": source_id,
                   "query": question, "title": question, "summary": raw[:5000], "sources": [source],
                   "analysis": {"summary": "Bounded public-source canary; evidence is not a guarantee.", "recommended_next_action": "Alpha selects qualify, research-more, reject, or park."},
                   "handoff_target": target, "department_target": target, "research_mode": record["research_mode"],
                   "objective_id": record["objective_id"], "created_at": now}
        persistence.append_record("research_v2_packages", package)
        alpha = review_demand_package(package)
        results.append({"department": department, "question_id": record["request_id"], "source_url": url, "alpha": alpha, "no_external_action": True})
    out = ROOT / "reports/research/proactive_canaries_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "canaries": results, "external_actions": 0}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(out), "canaries": [{"department": x["department"], "decision": (x["alpha"].get("evaluation") or {}).get("decision"), "handoff": (x["alpha"].get("receipt") or {}).get("handoff_id")} for x in results]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
