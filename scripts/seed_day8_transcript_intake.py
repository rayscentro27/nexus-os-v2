#!/usr/bin/env python3
"""Nexus OS v2 — Day 8 idempotent seed: transcript intake + orientation + candidate backlog.

Seeds improvement_candidates (AI resource / GoClear / trading / workforce), DRAFT
approved_knowledge, sample intake_events + transcript_reviews + orientation_notes, a wager and
a lesson, and a proof event. No publish/trading/Telegram/external calls.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day8_transcript_intake.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import configured, get, insert, rest, event, q  # noqa: E402

IMPROVEMENTS = [
    # GoClear / funding / credit
    ("GoClear Credit Report Discrepancy Analyzer", "credit_compliance"),
    ("Funding Stack Readiness Planner", "funding_readiness"),
    ("Credit Compliance Intake Mode", "credit_compliance"),
    ("Funding Strategy Compliance Extractor", "funding_readiness"),
    ("Claim Risk Classifier", "compliance"),
    ("GoClear Client AI Approved Knowledge Boundary", "client_agent"),
    # trading
    ("Trading Pod Tournament / Agentic Backtest Pipeline", "trading"),
    ("Options Strategy Simulator", "trading"),
    ("Paper Trading Incubation Rules", "trading"),
    ("Trading Claim Risk Classifier", "trading"),
    # AI resource
    ("Local Coding Model Benchmark Harness", "ai_resource"),
    ("Local Hardware Feasibility Checker", "ai_resource"),
    ("AI Resource / Token Usage Layer", "ai_resource"),
    ("Self-Healing Provider Scout", "ai_resource"),
    # workforce / education
    ("AI Education / Workforce Opportunity Finder", "workforce"),
    ("Senior AI Usability Score", "workforce"),
    ("Wealth Readiness Education Library", "education"),
]

KNOWLEDGE = [
    ("credit_outcomes_vary", "Credit outcomes vary", "Credit outcomes vary and are not guaranteed."),
    ("funding_depends_on_underwriting", "Funding depends on underwriting",
     "Funding approvals, amounts, and terms depend on lender underwriting, credit profile, revenue, documentation, and other factors."),
    ("goclear_no_guarantees", "GoClear cannot guarantee outcomes",
     "GoClear/Apex can help organize education, readiness, and preparation, but cannot guarantee approvals, deletions, score increases, or funding."),
    ("responsible_debt_management", "Responsible debt management",
     "Business funding should include repayment planning and responsible debt management."),
]

INTAKES = [
    "Local AI Coding Model Candidate", "5 Ways to Improve Credit Score in 30 Days",
    "Agentic AI Trading Pods", "AI Voice Receptionist for Local Business",
    "AI Credit Dispute Workflow", "Robinhood Robo Advisor Review",
    "Business Funding Stack Case Study", "Real Estate AI Listing Assistant",
    "AI Education for Adults Over 50",
]


def absent(table, col, value):
    st, rows = get(table, f"{col}=eq.{q(value)}&select=id&limit=1")
    return not (isinstance(rows, list) and rows)


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    n = {"improvements": 0, "knowledge": 0, "intakes": 0, "reviews": 0}

    for title, area in IMPROVEMENTS:
        if absent("improvement_candidates", "title", title):
            insert("improvement_candidates", {"title": title, "source_type": "transcript_intake",
                   "capability_area": area, "decision": "needs_review", "status": "captured"}, prefer="return=minimal")
            n["improvements"] += 1

    for key, title, body in KNOWLEDGE:
        rest("POST", "approved_knowledge?on_conflict=knowledge_key", body=[{
            "knowledge_key": key, "title": title, "body": body, "category": "compliance",
            "audience_type": "client", "status": "draft", "compliance_notes": "Draft — requires compliance review."}],
            prefer="resolution=merge-duplicates,return=minimal")
        n["knowledge"] += 1

    for title in INTAKES:
        if absent("intake_events", "title", title):
            insert("intake_events", {"source_type": "transcript", "title": title,
                   "raw_text": f"(seed sample) {title}", "status": "new",
                   "metadata": {"seed_key": "day8"}}, prefer="return=minimal")
            n["intakes"] += 1

    # two sample transcript_reviews + orientation notes (idempotent by title)
    samples = [
        ("Agentic AI Trading Pods", "trading_strategy", "RESEARCH_ONLY", "high",
         "Extract process not signal; require backtest + paper; block live trading."),
        ("AI Voice Receptionist for Local Business", "local_business_automation", "GO_CLEAR_TEST", "medium",
         "Extract service opportunity; draft monetization; 7-day pilot."),
    ]
    for title, cat, decision, comp, action in samples:
        if absent("transcript_reviews", "title", title):
            st, row = insert("transcript_reviews", {"title": title, "core_idea": title, "category": cat,
                   "usefulness_score": 7, "money_now_score": 5, "automation_score": 5, "risk_score": 6,
                   "compliance_risk": comp, "decision": decision, "recommended_action": action,
                   "nexus_should_do": [action], "claim_flags": []})
            rid = row[0]["id"] if isinstance(row, list) and row else None
            insert("orientation_notes", {"category": cat, "summary": title, "decision": decision,
                   "reason": action, "risk_flags": []}, prefer="return=minimal")
            if rid:
                insert("dispositions", {"subject_table": "transcript_reviews", "subject_id": rid,
                       "disposition": decision, "reason": action}, prefer="return=minimal")
            n["reviews"] += 1

    if absent("wagers", "title", "AI receptionist pilot books 5+ appointments in 7 days"):
        insert("wagers", {"title": "AI receptionist pilot books 5+ appointments in 7 days",
               "hypothesis": "A 7-day AI receptionist pilot recovers missed-call revenue for one local business.",
               "success_metric": "appointments booked via AI", "target_value": "5", "time_window": "7 days",
               "status": "open"}, prefer="return=minimal")
    if absent("nexus_lessons", "lesson", "Guarantee/loophole transcripts are rejected as hype"):
        insert("nexus_lessons", {"lesson": "Guarantee/loophole transcripts are rejected as hype",
               "category": "compliance", "confidence": 0.8}, prefer="return=minimal")

    if absent("nexus_events", "action", "day8_transcript_intake_seeded"):
        event("system", "day8_transcript_intake_seeded", "success", "Day 8 transcript intake seeded",
              f"improvements+{n['improvements']} knowledge_draft intakes+{n['intakes']} reviews+{n['reviews']}")

    print("Day 8 transcript intake seed complete (no publish/trading/Telegram/external calls).")
    print(f"  new: improvements={n['improvements']} knowledge(draft)={n['knowledge']} intakes={n['intakes']} reviews={n['reviews']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
