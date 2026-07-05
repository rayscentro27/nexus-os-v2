#!/usr/bin/env python3
"""NotebookLM Normalization Shim — converts legacy export format to unified scoring fields."""
import json
import os
import sys
from datetime import datetime, timezone

UNIFIED_FIELDS = [
    "source_id", "source_type", "title", "source_path_or_url", "captured_at",
    "summary", "monetization_score", "implementation_effort", "urgency",
    "confidence", "risk_level", "relevance_to_nexus", "recommended_route",
    "current_decision", "next_action", "citations_or_receipts", "status"
]

ROUTES = ["hermes", "alpha", "creative", "research", "client_portal",
          "funding_credit", "operations", "stripe_payments", "telegram", "scheduler_recovery"]

def classify_route(title, summary):
    t = (title + " " + summary).lower()
    if any(w in t for w in ["credit", "funding", "loan", "bank"]): return "funding_credit"
    if any(w in t for w in ["stripe", "payment", "billing", "subscription"]): return "stripe_payments"
    if any(w in t for w in ["client", "portal", "customer"]): return "client_portal"
    if any(w in t for w in ["trading", "market", "stock"]): return "alpha"
    if any(w in t for w in ["content", "creative", "video", "youtube"]): return "creative"
    if any(w in t for w in ["telegram", "bot", "message"]): return "telegram"
    if any(w in t for w in ["research", "analysis", "study"]): return "research"
    if any(w in t for w in ["hermes", "advisor", "recommend"]): return "hermes"
    return "operations"

def score_item(item):
    score = 50
    title = item.get("title", "")
    summary = item.get("summary", "")
    t = (title + " " + summary).lower()
    if any(w in t for w in ["revenue", "money", "income", "profit"]): score += 15
    if any(w in t for w in ["credit", "funding", "loan"]): score += 10
    if any(w in t for w in ["automation", "system", "process"]): score += 5
    if any(w in t for w in ["urgent", "critical", "immediate"]): score += 10
    if any(w in t for w in ["low risk", "safe", "proven"]): score += 5
    return min(score, 100)

def normalize_export(export_path):
    with open(export_path) as f:
        data = json.load(f)
    
    items = []
    opportunities = data.get("top_opportunities", [])
    for i, opp in enumerate(opportunities):
        title = opp.get("title", opp.get("name", f"Item {i+1}"))
        summary = opp.get("description", opp.get("summary", ""))
        score = score_item(opp)
        route = classify_route(title, summary)
        
        item = {
            "source_id": f"notebooklm_{i+1}",
            "source_type": "notebooklm_export",
            "title": title,
            "source_path_or_url": export_path,
            "captured_at": data.get("generated_at", datetime.now(timezone.utc).isoformat()),
            "summary": summary,
            "monetization_score": score,
            "implementation_effort": "medium",
            "urgency": "high" if score >= 80 else "medium" if score >= 60 else "low",
            "confidence": 0.7,
            "risk_level": "low" if score < 60 else "medium",
            "relevance_to_nexus": score / 100,
            "recommended_route": route,
            "current_decision": "auto_approved" if score < 80 else "ray_review_required",
            "next_action": f"Route to {route}" if score < 80 else "Submit for Ray Review",
            "citations_or_receipts": [],
            "status": "scored"
        }
        items.append(item)
    
    return items

def main():
    export_dir = "data/exports/notebooklm/research_bundles"
    output_dir = "data/research_memory"
    os.makedirs(output_dir, exist_ok=True)
    
    sources = []
    all_scored = []
    
    for fname in os.listdir(export_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(export_dir, fname)
            try:
                items = normalize_export(fpath)
                all_scored.extend(items)
                sources.append({"file": fname, "items": len(items)})
                print(f"Normalized {fname}: {len(items)} items")
            except Exception as e:
                print(f"Error processing {fname}: {e}")
    
    # Write outputs
    with open(os.path.join(output_dir, "notebooklm_sources_latest.json"), "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "sources": sources}, f, indent=2)
    
    with open(os.path.join(output_dir, "notebooklm_scored_items_latest.json"), "w") as f:
        json.dump(all_scored, f, indent=2)
    
    with open("reports/research/nexus_notebooklm_alpha_intake_latest.json", "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "intake_type": "notebooklm_normalized",
            "items": all_scored,
            "route_counts": {r: sum(1 for i in all_scored if i["recommended_route"] == r) for r in ROUTES}
        }, f, indent=2)
    
    print(f"\nTotal normalized: {len(all_scored)} items")
    print(f"Routes: {json.dumps({r: sum(1 for i in all_scored if i['recommended_route'] == r) for r in ROUTES}, indent=2)}")

if __name__ == "__main__":
    main()
