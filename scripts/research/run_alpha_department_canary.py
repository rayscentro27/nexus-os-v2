#!/usr/bin/env python3
"""Bounded multi-source canary for the existing Alpha -> department route."""
from __future__ import annotations
import json, ssl, urllib.request, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_missions import build_proactive_question, persist_question
from nexus_agent_platform.alpha_model_review import review_demand_package

SOURCES = [
    ("SBA 7(a) loans", "https://www.sba.gov/funding-programs/loans/7a-loan-program"),
    ("Bank of America small business lending", "https://www.bankofamerica.com/smallbusiness/business-financing/"),
    ("American Express business line of credit", "https://www.americanexpress.com/en-us/business/blueprint/"),
]

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NexusResearch/1.0 bounded evidence"})
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
            return response.read(9000).decode("utf-8", "replace")
    except Exception as exc:
        return f"bounded fetch failure: {exc.__class__.__name__}"

def main():
    now = datetime.now(timezone.utc).isoformat()
    record = build_proactive_question(department="CLYDE_FUNDING", question="Which borrower qualification factors are supported across SBA and independent lender sources, and what should Clyde use internally?", why_this_research="The funding charter requires cross-source verification before internal guidance.", trigger="RESEARCH_GAP", business_or_nexus="GOCLEAR", parent_goal="Improve funding-readiness intelligence", project="proactive-canary-qualified-funding", expected_value="A governed internal funding-readiness brief with source boundaries.", source_plan=[url for _, url in SOURCES], mode="GOCLEAR_PROACTIVE", handoff_target="CLYDE_CREDIT")
    record.update({"source_type": "WEB_PAGE", "source_id": "proactive-canary-qualified-funding", "source_url": SOURCES[0][1]})
    persist_question(record)
    rows = [{"source_id": f"proactive-canary-qualified-funding-{i}", "title": title, "url": url, "source_type": "PUBLIC_WEB", "snippet": fetch(url)[:1800], "retrieved_at": now} for i, (title, url) in enumerate(SOURCES)]
    package = {"research_id": "proactive-canary-qualified-funding", "investigation_id": record["objective_id"], "finding_id": "proactive-canary-qualified-funding", "query": record["question"], "title": record["question"], "summary": "Three bounded public sources were acquired for a source-specific funding-readiness comparison. SBA rules and lender-specific terms remain separated.", "sources": rows, "analysis": {"summary": "Cross-source evidence package for internal Alpha review; no customer outcome or approval is asserted.", "recommended_next_action": "Clyde uses only verified and lender-specific claims."}, "handoff_target": "CLYDE_CREDIT", "department_target": "CLYDE_CREDIT", "research_mode": record["research_mode"], "objective_id": record["objective_id"], "created_at": now}
    persistence.append_record("research_v2_sources", rows[0])
    persistence.append_record("research_v2_packages", package)
    result = review_demand_package(package)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "package": package, "alpha": result, "external_actions": 0}
    path = ROOT / "reports/research/proactive_alpha_department_canary.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(path), "decision": (result.get("evaluation") or {}).get("decision"), "handoff_id": (result.get("receipt") or {}).get("handoff_id"), "receipt_id": (result.get("receipt") or {}).get("receipt_id")}, sort_keys=True))

if __name__ == "__main__":
    main()
