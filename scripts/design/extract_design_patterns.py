#!/usr/bin/env python3
"""Deterministically register design patterns (no external fetch). Idempotent by pattern_name.
    python3 scripts/design/extract_design_patterns.py --sample
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

PATTERNS = [
    ("Trust-first social card", "social_post", "Credit/funding FB post that builds trust without hype",
     "Single headline, calm imagery, one CTA, small compliance footer.",
     {"headline":"one clear line","cta":"single","footer":"required"}, ["guarantee words","clutter"]),
    ("Premium fintech dashboard", "fintech_dashboard", "Internal/admin OS dashboard",
     "Dark navy + one accent, card grid, generous spacing, status pills, readable type.",
     {"palette":"dark navy + gold accent","layout":"card grid"}, ["rainbow colors","dense tables as primary state"]),
    ("Clean client portal", "client_portal", "GoClear client where-you-stand portal",
     "Show status first, next-best-action, education, partner offers with disclosure.",
     {"first_view":"where you stand","disclosure":"affiliate"}, ["overwhelm","guarantees"]),
    ("Conversion landing", "landing_page", "Funding readiness landing page",
     "Hero + value + proof/compliance + FAQ + secondary CTA.",
     {"hero":"benefit + CTA","compliance":"visible"}, ["fake testimonials","guaranteed outcomes"]),
    ("App UI shell", "app_ui", "App navigation shell",
     "Sidebar + topbar + content; consistent spacing tokens.", {"nav":"sidebar"}, ["inconsistent spacing"]),
    ("Mobile-first stack", "mobile_ui", "Mobile responsive layout",
     "Single column, large tap targets, sticky CTA.", {"columns":1}, ["tiny tap targets"]),
    ("Open gate / upward path", "trust_metaphor", "Credit readiness hope-not-hype metaphor",
     "Open gate + upward path imagery implying readiness, not guarantees.",
     {"metaphor":"gate+path"}, ["money rain","instant approval imagery"]),
    ("Compliance footer", "compliance_footer", "Credit/funding disclosure",
     "Small persistent footer: results vary; no guaranteed funding/approval/deletions/score increases.",
     {"text":"results vary; no guarantees"}, ["hiding disclosure","fine-print tricks"]),
]

def extract_all() -> int:
    n = 0
    for name, cat, use, desc, rules, avoid in PATTERNS:
        st, ex = get("design_pattern_registry", f"pattern_name=eq.{q(name)}&select=id&limit=1")
        if isinstance(ex, list) and ex: continue
        insert("design_pattern_registry", {"pattern_name": name, "pattern_category": cat, "use_case": use,
            "description": desc, "design_rules": rules, "avoid_rules": avoid}, prefer="return=minimal")
        n += 1
    event("monetization", "design_patterns_extracted", "success", f"Registered design patterns (+{n})", "deterministic")
    return n

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", action="store_true"); ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    n = extract_all()
    print(f"Design patterns ready (+{n} new, {len(PATTERNS)} total categories).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
