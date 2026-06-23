#!/usr/bin/env python3
"""Nexus OS v2 — deterministic transcript review + orientation.

Classifies a pasted transcript into a category, scores it, decides what Nexus should do, and
records transcript_reviews + orientation_notes + a disposition (and optional DRAFT
improvement_candidates / monetization_opportunities). No external model calls, no publishing.

    python3 scripts/intake/review_transcript.py --sample
    python3 scripts/intake/review_transcript.py --intake-event-id <uuid>
    python3 scripts/intake/review_transcript.py --title "..." --text "..."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE.parent / "compliance"))
from _supabase import configured, get, insert, event, q  # noqa: E402
import classify_claim_risk as claim  # noqa: E402

SAMPLE = ("Local businesses miss a huge number of calls and lose revenue. An AI voice receptionist "
          "can answer every call, qualify the lead, book the appointment, and text a follow-up. "
          "You can sell this to dentists, plumbers, and salons for a monthly fee.")

# (regex, category, cfg). First match wins; else 'parked_research'.
# cfg: decision, use, money, auto, risk, compliance, action, do[list], improvement, monetization,
#      trading_candidate, knowledge_draft, say
CATS = [
    (r"local (coding )?model|ollama|llama|lm studio|open-?source model|coding model",
     "ai_resource_local_model", dict(decision="SEED_AS_IMPROVEMENT_CANDIDATE", use=7, money=2, auto=6, risk=3,
        compliance="low", action="Register as candidate only; read-only benchmark first; do NOT auto-install.",
        do=["register local model candidate", "queue Local Coding Model Benchmark Harness", "read-only benchmark"],
        improvement="Local Coding Model Benchmark Harness", say="Promising local model — benchmark before adopting.")),
    (r"mac ?mini|hardware|\bram\b|\bgpu\b|\bvram\b|cpu|disk|feasib",
     "ai_resource_hardware", dict(decision="RESEARCH_ONLY", use=6, money=1, auto=5, risk=2, compliance="low",
        action="Run a local hardware feasibility check (RAM/CPU/disk/OS/Ollama/LM Studio).",
        do=["queue Local Hardware Feasibility Checker"], improvement="Local Hardware Feasibility Checker",
        say="Check feasibility before recommending any local install.")),
    (r"credit dispute|dispute (letter|workflow)|fcra|fdcpa|delete (items|accounts)|wipe (inquir|hard pull)",
     "credit_compliance_dispute", dict(decision="PARK", use=6, money=4, auto=4, risk=9, compliance="very_high",
        action="Extract workflow only. Do NOT auto-generate client-ready dispute letters or auto-send. Compliance review required.",
        do=["extract dispute workflow steps", "human/compliance review required", "no auto letters/sends"],
        improvement="GoClear Credit Report Discrepancy Analyzer", say="High-compliance area — workflow only, human review required.")),
    (r"funding stack|bank-?ready|lender|business funding|funding readiness|no doc",
     "funding_readiness", dict(decision="GO_CLEAR_TEST", use=8, money=6, auto=5, risk=6, compliance="high",
        action="Extract funding readiness framework. Flag guarantees / lender-specific / 'no docs' / inquiry-wipe / exact approval claims. Draft knowledge only.",
        do=["extract readiness framework", "flag risky claims", "draft approved_knowledge"],
        improvement="Funding Stack Readiness Planner", knowledge_draft=True, say="Useful readiness framework — strip guarantees, draft only.")),
    (r"credit score|credit education|utilization|credit report",
     "goclear_credit_education", dict(decision="GO_CLEAR_TEST", use=7, money=4, auto=4, risk=6, compliance="high",
        action="Extract safe education; rewrite into no-guarantee language; draft approved_knowledge; compliance review.",
        do=["extract safe education", "rewrite no-guarantee", "draft approved_knowledge"],
        knowledge_draft=True, say="Good education base — rewrite without guarantees, keep as draft.")),
    (r"option(s)?|covered call|cash[- ]secured put|the wheel",
     "trading_options", dict(decision="RESEARCH_ONLY", use=6, money=3, auto=4, risk=7, compliance="high",
        action="Extract option legs/risk profile if present. Education only. Block live trading.",
        do=["extract option legs/risk", "queue Options Strategy Simulator", "no live trading"],
        improvement="Options Strategy Simulator", say="Options education only — simulate, never execute live.")),
    (r"trad(e|ing)|backtest|forex|prop firm|strategy",
     "trading_strategy", dict(decision="RESEARCH_ONLY", use=6, money=3, auto=5, risk=8, compliance="high",
        action="Extract process, not signal. Create trading_strategy_candidate only if safe. Require backtest/robustness/paper/risk review. Block live trading.",
        do=["extract process not signal", "create trading_strategy_candidate (research)", "require backtest + paper", "block live trading"],
        trading_candidate=True, say="Capture the process as a research candidate — backtest before anything.")),
    (r"invest(ing|ment)|robo[- ]?advisor|index fund|wealth|retire",
     "investing_wealth", dict(decision="CONTENT_IDEA", use=5, money=2, auto=3, risk=5, compliance="medium",
        action="Education/content only. No investment advice, no product recommendation. Flag fee/performance/current-info claims.",
        do=["education/content only", "flag fee/performance claims"], say="Retention content, not advice — verify any numbers.")),
    (r"missed call|receptionist|voice (agent|assistant)|local business|book(ing)? appointment|answer(s|ing) calls",
     "local_business_automation", dict(decision="GO_CLEAR_TEST", use=8, money=8, auto=7, risk=4, compliance="medium",
        action="Extract problem/buyer/offer/pricing/vendor needs/7-day pilot/sales assets. Draft monetization opportunity. Do NOT build a vendor platform from scratch.",
        do=["extract service opportunity", "draft monetization_opportunity", "7-day pilot plan"],
        monetization="AI Missed Call Recovery System", say="Strong first-dollar service — package a 7-day pilot.")),
    (r"real estate|listing|realtor|property|fair housing",
     "real_estate_voice", dict(decision="GO_CLEAR_TEST", use=7, money=7, auto=6, risk=6, compliance="high",
        action="Create AI Listing Concierge / Lead Recovery offer candidate. Add fair-housing, property-accuracy, call-consent, privacy risks.",
        do=["draft monetization_opportunity", "flag fair-housing + consent + privacy"],
        monetization="AI Listing Concierge for Real Estate Agents", say="Good niche — watch fair-housing and consent.")),
    (r"over 50|seniors?|workforce|eligibility|government (pay|grant|benefit)|adults",
     "workforce_50plus", dict(decision="RESEARCH_ONLY", use=6, money=4, auto=4, risk=7, compliance="high",
        action="Extract audience/programs/eligibility/resources/income angle/scam risks. Current verification required. No guarantee government pays everyone.",
        do=["extract audience + programs", "mark verification required", "no gov-pays-everyone guarantee"],
        improvement="AI Education / Workforce Opportunity Finder", say="Promising audience — verify eligibility claims, no guarantees.")),
    (r"short[- ]?form|reel|tiktok|content idea|hook",
     "creative_shortform", dict(decision="CONTENT_IDEA", use=6, money=3, auto=6, risk=3, compliance="medium",
        action="Route to Creative Studio as a campaign/brief idea.", do=["seed creative brief idea"], say="Content idea — route to Creative Studio.")),
    (r"\bseo\b|niche|keyword|search console",
     "seo_niche", dict(decision="RESEARCH_ONLY", use=5, money=3, auto=5, risk=3, compliance="low",
        action="Capture as SEO/niche opportunity research.", do=["seed seo opportunity research"], say="Niche signal — log for SEO research.")),
    (r"nexus|internal|ops|roadmap|infrastructure",
     "nexus_internal_ops", dict(decision="ADD_TO_PHASE_2", use=6, money=2, auto=6, risk=2, compliance="low",
        action="Internal/ops note — add to phase 2 backlog.", do=["log internal ops note"], say="Internal note — backlog it.")),
]
DEFAULT = ("parked_research", dict(decision="PARK", use=3, money=1, auto=2, risk=4, compliance="medium",
           action="Not enough signal — park for later.", do=["park research"], say="Parked — not enough actionable signal yet."))


def categorize(text: str):
    import re
    t = (text or "").lower()
    for rx, cat, cfg in CATS:
        if re.search(rx, t):
            return cat, cfg
    return DEFAULT[0], DEFAULT[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intake-event-id")
    ap.add_argument("--title")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    text, title, intake_id = args.text, args.title, args.intake_event_id
    if args.file:
        text = Path(args.file).read_text(errors="ignore")
    if args.sample:
        text, title = SAMPLE, title or "AI Voice Receptionist for Local Business"
    if intake_id and not text:
        st, rows = get("intake_events", f"id=eq.{q(intake_id)}&select=raw_text,title&limit=1")
        if isinstance(rows, list) and rows:
            text = rows[0].get("raw_text"); title = title or rows[0].get("title")
    if not text:
        print("provide --text/--file/--sample/--intake-event-id"); return 1
    title = title or "(untitled transcript)"

    cr = claim.classify(text)
    cat, cfg = categorize(text)
    # If mostly hype with no useful workflow → reject as hype.
    if cr["risk_class"] == "misleading_or_hype" and cat in ("parked_research", "investing_wealth", "creative_shortform"):
        cfg = dict(cfg); cfg["decision"] = "REJECT"; cfg["action"] = "Mostly unrealistic claims, no useful workflow — reject as hype."
        cfg["say"] = "Reject as hype — store the lesson."
    compliance = "very_high" if cr["risk_class"] == "do_not_use_client_facing" else cfg.get("compliance", "medium")

    review = {
        "intake_event_id": intake_id, "title": title, "core_idea": (text[:300]),
        "category": cat, "usefulness_score": cfg["use"], "money_now_score": cfg["money"],
        "automation_score": cfg["auto"], "risk_score": cfg["risk"], "compliance_risk": compliance,
        "decision": cfg["decision"], "recommended_action": cfg["action"],
        "nexus_should_do": cfg["do"], "hermes_should_say": cfg.get("say"),
        "jobs_to_create": [j for j in [cfg.get("improvement") and "seed_improvement_candidate",
                                       cfg.get("monetization") and "extract_service_opportunity"] if j],
        "tables_to_update": [t for t in ["improvement_candidates" if cfg.get("improvement") else None,
                                         "monetization_opportunities" if cfg.get("monetization") else None,
                                         "approved_knowledge" if cfg.get("knowledge_draft") else None,
                                         "trading_strategy_candidates" if cfg.get("trading_candidate") else None] if t],
        "claim_flags": cr["flags"], "metadata": {"claim_risk": cr["risk_class"], "domains": cr["domains"]},
    }
    st, row = insert("transcript_reviews", review)
    review_id = row[0]["id"] if isinstance(row, list) and row else None

    insert("orientation_notes", {
        "intake_event_id": intake_id, "category": cat, "summary": title,
        "decision": cfg["decision"], "reason": cfg["action"],
        "suggested_jobs": review["jobs_to_create"], "suggested_tables": review["tables_to_update"],
        "risk_flags": cr["flags"],
    }, prefer="return=minimal")

    if review_id:
        insert("dispositions", {"subject_table": "transcript_reviews", "subject_id": review_id,
               "disposition": cfg["decision"], "reason": cfg["action"]}, prefer="return=minimal")

    # Optional DRAFT artifacts (candidate only)
    if cfg.get("improvement"):
        st, ex = get("improvement_candidates", f"title=eq.{q(cfg['improvement'])}&select=id&limit=1")
        if not (isinstance(ex, list) and ex):
            insert("improvement_candidates", {"title": cfg["improvement"], "source_type": "transcript",
                   "summary": title, "capability_area": cat, "decision": "needs_review", "status": "captured"},
                   prefer="return=minimal")
    if cfg.get("monetization"):
        st, ex = get("monetization_opportunities", f"title=eq.{q(cfg['monetization'])}&select=id&limit=1")
        if not (isinstance(ex, list) and ex):
            insert("monetization_opportunities", {"title": cfg["monetization"], "source_summary": title,
                   "money_angle": cfg["action"], "status": "captured", "decision": "needs_review"},
                   prefer="return=minimal")
    if cfg["decision"] == "REJECT":
        insert("nexus_lessons", {"source_table": "transcript_reviews", "source_id": review_id,
               "lesson": f"Rejected as hype: {title}", "category": cat, "confidence": 0.6}, prefer="return=minimal")

    event("automation", "transcript_reviewed", "success", f"Transcript reviewed: {cat} → {cfg['decision']}",
          f"compliance={compliance} flags={', '.join(cr['flags']) or 'none'}", payload={"review_id": review_id})
    print(f"Reviewed → category={cat} decision={cfg['decision']} compliance={compliance} "
          f"claim_risk={cr['risk_class']} flags={cr['flags']}")
    print(f"  recommended: {cfg['action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
