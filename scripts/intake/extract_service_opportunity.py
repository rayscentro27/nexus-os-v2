#!/usr/bin/env python3
"""Nexus OS v2 — extract a productized service opportunity from a transcript/idea (deterministic).

Builds a structured service package (problem/buyer/offer/pricing/7-day test/sales assets) and
creates a DRAFT monetization_opportunities row. No external calls, no vendor build, no publishing.

    python3 scripts/intake/extract_service_opportunity.py --sample
    python3 scripts/intake/extract_service_opportunity.py --text "..." --name "..."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

SAMPLE = ("Local businesses miss calls and lose booked revenue. An AI voice receptionist answers "
          "every call, qualifies the lead, books the appointment, and texts a follow-up.")


def extract(text: str, name: str | None) -> dict:
    t = (text or "").lower()
    buyer = ("real estate agents" if "real estate" in t or "listing" in t else
             "local service businesses (dentists, plumbers, salons)" if "local" in t or "receptionist" in t or "missed call" in t else
             "small business owners")
    return {
        "name": name or "AI Missed Call Recovery System",
        "problem": "Missed calls and slow follow-up lose booked revenue.",
        "target_buyer": buyer,
        "urgent_pain": "Every missed call is a lost customer; nights/weekends are uncovered.",
        "offer": "Done-for-you AI voice receptionist: answers, qualifies, books, and texts follow-up.",
        "pricing_model": "Setup fee + monthly retainer (per location).",
        "setup_requirements": "Phone number/forwarding, booking link, business hours, FAQ script.",
        "tools_vendors": "Voice agent platform (vendor, not built from scratch), calendar, SMS.",
        "risk_compliance": "Call-consent/recording disclosure, privacy, accuracy of info, fair-housing if real estate.",
        "seven_day_test": "Day1 scope+script · Day2-3 configure on one client number · Day4-5 live test calls · Day6 measure booked calls · Day7 decide.",
        "sales_assets": ["1-page offer", "demo call recording", "before/after missed-call stat", "DM script"],
        "first_20_prospects": "20 local businesses with poor call answer rates / no after-hours coverage.",
        "demo_first_angle": "Record a live demo answering their own business line, then send it.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--name")
    ap.add_argument("--review-id")
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    text = args.text
    if args.file:
        text = Path(args.file).read_text(errors="ignore")
    if args.review_id and not text:
        st, rows = get("transcript_reviews", f"id=eq.{q(args.review_id)}&select=core_idea,title&limit=1")
        if isinstance(rows, list) and rows:
            text = rows[0]["core_idea"]; args.name = args.name or rows[0]["title"]
    if args.sample:
        text = SAMPLE
    if not text:
        print("provide --text/--file/--sample/--review-id"); return 1

    pkg = extract(text, args.name)
    st, ex = get("monetization_opportunities", f"title=eq.{q(pkg['name'])}&select=id&limit=1")
    if isinstance(ex, list) and ex:
        print(f"opportunity '{pkg['name']}' already exists (draft) — skip.")
    else:
        insert("monetization_opportunities", {
            "title": pkg["name"], "source_summary": pkg["problem"], "money_angle": pkg["offer"],
            "status": "captured", "decision": "needs_review", "smallest_test": pkg["seven_day_test"],
            "metadata": {"service_package": pkg, "draft": True},
        }, prefer="return=minimal")
        print(f"Draft monetization opportunity created: {pkg['name']}")
    event("monetization", "service_opportunity_extracted", "success",
          f"Service opportunity: {pkg['name']}", f"buyer: {pkg['target_buyer']}")
    print(f"  buyer: {pkg['target_buyer']} · offer: {pkg['offer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
