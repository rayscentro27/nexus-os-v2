#!/usr/bin/env python3
"""Create feature_design_packets (deterministic). Idempotent by feature_name.
    python3 scripts/design/create_feature_design_packet.py --sample
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, insert, event, q  # noqa: E402

FOOTER = "Results vary. No guaranteed funding, approval, deletions, or score increases."
PACKETS = [
    ("GoClear Client Portal", "client_portal", "Client instantly sees where they stand and what to fix next",
     ["readiness score","top blockers","next best action","education","partner offers + disclosure"],
     {"layout":"clean client portal"}, {"tone":"supportive, plain language"}, {"palette":"calm + one accent"},
     ["no guaranteed approvals/deletions/score increases","affiliate disclosure required"]),
    ("Nexus Command Center", "admin_dashboard", "Ray runs Nexus and sees status at a glance",
     ["awareness panel","jobs","approvals","money actions"], {"layout":"premium dark fintech"},
     {"tone":"operator, direct"}, {"palette":"dark navy + gold"}, ["no fake data"]),
    ("Facebook Credit Readiness Post", "social_post", "Drive funding-readiness reviews without hype",
     ["headline","subline","CTA","compliance footer"], {"layout":"trust-first social card"},
     {"tone":"hopeful, realistic"}, {"metaphor":"open gate + path"}, [FOOTER]),
    ("Funding Readiness Landing Page", "landing_page", "Convert visitors into readiness reviews",
     ["hero","value","proof/compliance","FAQ","secondary CTA"], {"layout":"conversion landing"},
     {"tone":"clear, credible"}, {"palette":"premium financial"}, ["no guaranteed funding","visible disclosure"]),
]

def create_all() -> int:
    n = 0
    for name, surface, goal, sections, comp_g, copy_g, vis_g, rules in PACKETS:
        st, ex = get("feature_design_packets", f"feature_name=eq.{q(name)}&select=id&limit=1")
        if isinstance(ex, list) and ex: continue
        insert("feature_design_packets", {"feature_name": name, "target_surface": surface, "user_goal": goal,
            "required_sections": sections, "component_guidance": comp_g, "copy_guidance": copy_g,
            "visual_guidance": vis_g, "compliance_rules": rules, "status": "draft"}, prefer="return=minimal")
        n += 1
    event("monetization", "feature_design_packets_created", "success", f"Feature design packets (+{n})", "deterministic")
    return n

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", action="store_true"); ap.add_argument("--feature"); ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    n = create_all()
    print(f"Feature design packets ready (+{n} new, {len(PACKETS)} total).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
