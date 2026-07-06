#!/usr/bin/env python3
"""
Hermes Research Advisor — Turns web search results into Ray-friendly advisory answers.

Produces:
1. Direct answer
2. Key findings
3. Sources
4. Score (if opportunity-related)
5. Why it matters for Nexus/GoClear
6. Risks/caveats
7. Recommended next step
8. Approval/work-order option

Usage:
  python3 scripts/hermes/hermes_research_advisor.py --query "best credit monitoring tools"
  python3 scripts/hermes/hermes_research_advisor.py --query "low-cost affiliate programs" --json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermes_web_search import web_search, url_review


def _score_opportunity(title, snippet, topic):
    """Score a search result as a business opportunity."""
    text = f"{title} {snippet}".lower()
    topic_words = topic.lower().split()

    speed = 5
    cost = 5
    fit_goclear = 5
    fit_nexus = 5
    ease = 5
    proof = 5
    risk = 0

    # Speed signals
    if any(kw in text for kw in ["quick", "fast", "instant", "same day", "today", "24h"]):
        speed = 8
    elif any(kw in text for kw in ["long", "months", "complex", "build"]):
        speed = 3

    # Cost signals
    if any(kw in text for kw in ["free", "no cost", "low-cost", "cheap", "$0"]):
        cost = 9
    elif any(kw in text for kw in ["paid", "subscription", "$99", "$199", "premium"]):
        cost = 4

    # Fit for GoClear (credit readiness business)
    goclear_kw = ["credit", "readiness", "funding", "business", "small business", "entrepreneur",
                   "bankability", "financial", "assessment", "score"]
    if any(kw in text for kw in goclear_kw):
        fit_goclear = 8

    # Fit for Nexus (tech platform)
    nexus_kw = ["api", "platform", "saas", "automation", "tool", "software", "integration",
                "dashboard", "portal", "online"]
    if any(kw in text for kw in nexus_kw):
        fit_nexus = 7

    # Ease signals
    if any(kw in text for kw in ["easy", "simple", "no-code", "plug", "one-click"]):
        ease = 8
    elif any(kw in text for kw in ["complex", "custom", "develop", "engineer"]):
        ease = 3

    # Proof/source quality
    if any(kw in text for kw in ["case study", "review", "rated", "testimonials", "proven"]):
        proof = 8
    elif any(kw in text for kw in ["trustpilot", "g2", "capterra", "reddit"]):
        proof = 7

    # Risk adjustment
    if any(kw in text for kw in ["scam", "risky", "warning", "avoid", "controversial"]):
        risk = -2
    if any(kw in text for kw in ["guaranteed", "100%", "no risk"]):
        risk = -1  # too-good-to-be-true

    overall = round((speed + cost + fit_goclear + fit_nexus + ease + proof + risk) / 6, 1)
    overall = max(0, min(10, overall))

    return {
        "overall_score": overall,
        "score_breakdown": {
            "speed_to_money": speed,
            "cost_to_try": cost,
            "fit_for_goclear": fit_goclear,
            "fit_for_nexus": fit_nexus,
            "ease_of_execution": ease,
            "proof_source_quality": proof,
            "risk_adjustment": risk,
        },
        "reason_score_not_higher": _reason_lower(speed, cost, fit_goclear, fit_nexus, ease, proof, risk),
        "what_would_make_it_higher": _improvement_suggestions(speed, cost, fit_goclear, fit_nexus, ease, proof),
    }


def _reason_lower(speed, cost, fit_g, fit_n, ease, proof, risk):
    reasons = []
    vals = {"speed": speed, "cost": cost, "fit_goclear": fit_g, "fit_nexus": fit_n, "ease": ease, "proof": proof}
    low = sorted(vals.items(), key=lambda x: x[1])[:2]
    for name, val in low:
        if val <= 5:
            reasons.append(f"{name} is weak ({val}/10)")
    if risk < 0:
        reasons.append(f"risk adjustment: {risk}")
    return reasons or ["generally moderate across dimensions"]


def _improvement_suggestions(speed, cost, fit_g, fit_n, ease, proof):
    suggestions = []
    if speed <= 5:
        suggestions.append("Find a faster path to first revenue")
    if cost <= 5:
        suggestions.append("Look for lower-cost or free alternatives")
    if fit_g <= 5:
        suggestions.append("Verify alignment with GoClear credit readiness audience")
    if fit_n <= 5:
        suggestions.append("Assess integration potential with Nexus platform")
    if ease <= 5:
        suggestions.append("Simplify implementation or find no-code options")
    if proof <= 5:
        suggestions.append("Seek more case studies or user reviews")
    return suggestions or ["Solid opportunity — execute and gather proof"]


def build_advisory_answer(query, search_result=None):
    """
    Build a complete Hermes research advisory answer.
    Returns a dict with all advisory fields.
    """
    if search_result is None:
        search_result = web_search(query)

    now = datetime.now(timezone.utc).isoformat()

    # Build findings from results
    findings = []
    scores = []
    for r in search_result.get("results", [])[:5]:
        score = _score_opportunity(r["title"], r["snippet"], query)
        findings.append({
            "title": r["title"],
            "url": r["url"],
            "snippet": r["snippet"][:300],
            "score": score["overall_score"],
        })
        scores.append(score)

    # Aggregate score
    avg_score = round(sum(s["overall_score"] for s in scores) / len(scores), 1) if scores else 0

    # Determine if Ray approval is needed
    needs_approval = False
    approval_reason = None
    if any(kw in query.lower() for kw in ["charge", "submit", "dispute", "grant", "apply", "trade", "publish"]):
        needs_approval = True
        approval_reason = "Query involves external action that requires Ray approval"

    # Build direct answer
    answer_parts = []
    if search_result["status"] == "ok" and findings:
        answer_parts.append(f"Here's what I found on: {query[:80]}")
        answer_parts.append("")
        for i, f in enumerate(findings[:3], 1):
            answer_parts.append(f"{i}. {f['title'][:80]}")
            answer_parts.append(f"   {f['snippet'][:150]}")
            answer_parts.append(f"   Score: {f['score']}/10")
            answer_parts.append("")
        answer_parts.append(f"Overall opportunity score: {avg_score}/10")
    elif search_result["status"] == "not_configured":
        answer_parts.append("Web search is not configured yet.")
        answer_parts.append("")
        answer_parts.append("To enable live web search, add one of these env vars:")
        for note in search_result.get("notes", []):
            if "missing" in note.lower() or "not set" in note.lower():
                answer_parts.append(f"  - {note}")
        answer_parts.append("")
        answer_parts.append("I can still help with internal context and Alpha research.")
    else:
        answer_parts.append(f"Search returned no results for: {query[:80]}")
        answer_parts.append("Try rephrasing or being more specific.")

    # Why it matters
    why_matters = []
    if avg_score >= 7:
        why_matters.append("High-potential opportunity — worth exploring quickly")
    elif avg_score >= 5:
        why_matters.append("Moderate opportunity — validate before investing time")
    else:
        why_matters.append("Lower-priority opportunity — may not be the best use of time right now")

    if any(kw in query.lower() for kw in ["credit", "readiness", "funding"]):
        why_matters.append("Directly relevant to GoClear's credit readiness core offering")
    if any(kw in query.lower() for kw in ["saas", "platform", "tool", "api"]):
        why_matters.append("Could enhance Nexus platform capabilities")

    # Risks
    risks = []
    if search_result["status"] == "not_configured":
        risks.append("No live web verification — findings are based on internal context only")
    if avg_score < 5:
        risks.append("Low opportunity score — may not justify time investment")
    if not findings:
        risks.append("No concrete sources found")

    # Next step
    next_step = ""
    if search_result["status"] == "ok" and findings:
        if avg_score >= 7:
            next_step = f"Strong candidate. Say 'turn this into a work order' to create an approval-gated plan."
        elif avg_score >= 5:
            next_step = "Worth a deeper look. Say 'research deeper' for more details or 'turn this into a work order'."
        else:
            next_step = "Consider whether this aligns with current priorities. Say 'what should we do next?' for Hermes guidance."
    elif search_result["status"] == "not_configured":
        next_step = "Configure a search provider (see docs/hermes_internet_search_setup.md) to enable live research."
    else:
        next_step = "Try a different search query or ask Hermes for internal context."

    return {
        "query": query,
        "checked_at": now,
        "provider": search_result.get("provider", "none"),
        "search_status": search_result.get("status", "unknown"),
        "answer": "\n".join(answer_parts),
        "findings": findings,
        "sources": [{"title": f["title"], "url": f["url"]} for f in findings],
        "opportunity_score": {
            "overall": avg_score,
            "breakdown": scores[0]["score_breakdown"] if scores else {},
            "reason_not_higher": scores[0]["reason_score_not_higher"] if scores else [],
            "improvements": scores[0]["what_would_make_it_higher"] if scores else [],
        },
        "why_it_matters": why_matters,
        "risks": risks,
        "next_step": next_step,
        "needs_ray_approval": needs_approval,
        "approval_reason": approval_reason,
    }


def main():
    parser = argparse.ArgumentParser(description="Hermes Research Advisor")
    parser.add_argument("--query", "-q", required=True, help="Research query")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        result = build_advisory_answer(args.query)
    except Exception as e:
        result = {
            "query": args.query,
            "error": str(e),
            "answer": "I hit an issue researching that. Can you rephrase?",
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result.get("answer", "No answer generated."))


if __name__ == "__main__":
    main()
