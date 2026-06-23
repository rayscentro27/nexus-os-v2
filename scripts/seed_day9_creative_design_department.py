#!/usr/bin/env python3
"""Nexus OS v2 — Day 9 idempotent seed: Creative Design Department + Design Inspiration Registry.

Registers inspiration sources (REFERENCE ONLY — no clone/import/dependency), extracts design
patterns, builds the sample credit-readiness FB design (brief → variants → scores → comparison),
creates feature design packets, and a UI quality review. No external image/model calls.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day9_creative_design_department.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "social"))
sys.path.insert(0, str(HERE / "design"))
sys.path.insert(0, str(HERE / "creative"))
from _supabase import configured, get, event  # noqa: E402
import register_design_inspiration as insp  # noqa: E402
import extract_design_patterns as patt  # noqa: E402
import create_feature_design_packet as packets  # noqa: E402
import review_ui_quality as uiq  # noqa: E402
import _design  # noqa: E402

INSPIRATIONS = [
    ("reference", "AionUi-style design reference", "app_ui",
     "Agentic UI layout inspiration. REFERENCE ONLY — do not clone or import the repo."),
    ("design_output", "Claude Design credit readiness post reference", "social_post",
     "Premium credit-readiness post layout direction from a Claude design output."),
    ("image", "Open gate / upward path credit readiness metaphor", "trust_metaphor",
     "Pathway + open gate metaphor for credit readiness without guarantees."),
    ("reference", "Modern fintech dashboard style", "fintech_dashboard",
     "Dark, card-based, generous spacing, one accent color."),
    ("reference", "Clean client portal style", "client_portal",
     "Where-you-stand-first client portal with next-best-action."),
    ("reference", "Short-form social creative style", "social_post",
     "Hook-first short-form creative direction."),
    ("reference", "Premium dark navy + gold financial brand style", "brand",
     "Premium financial brand palette: dark navy base + gold accent."),
    ("pattern", "Trust-building compliance footer pattern", "compliance_footer",
     "Persistent results-vary / no-guarantees disclosure footer."),
]


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    insp_n = 0
    for stype, name, cat, summary in INSPIRATIONS:
        before = get("design_inspiration_sources", f"source_name=eq.{name.replace(' ', '%20')}&select=id&limit=1")[1]
        insp.register(stype, name, cat, summary)
        if not (isinstance(before, list) and before):
            insp_n += 1

    pat_n = patt.extract_all()

    brief = _design.get_or_create_sample_brief()
    var_ids = _design.generate_variants(brief)
    _design.score_variants(brief["id"])
    cmp_res = _design.compare_variants(brief["id"])

    pkt_n = packets.create_all()
    uiq.review("Nexus Command Center — UI quality review", "dashboard")

    if not (get("nexus_events", "action=eq.day9_creative_design_seeded&select=id&limit=1")[1] or []):
        event("monetization", "day9_creative_design_seeded", "success", "Day 9 creative design dept seeded",
              f"inspirations+{insp_n} patterns+{pat_n} variants={len(var_ids)} packets+{pkt_n} · {cmp_res['summary']}")

    print("Day 9 creative design department seed complete (no external image/model calls, no publish).")
    print(f"  inspirations(+{insp_n}) patterns(+{pat_n}) sample_variants={len(var_ids)} feature_packets(+{pkt_n})")
    print(f"  {cmp_res['summary']} · next_action={cmp_res['next_action']} (approval required before publish)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
