#!/usr/bin/env python3
"""Create a creative_design_briefs row. Deterministic, no external calls.
    python3 scripts/creative/create_design_brief.py --sample
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _design
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    for f in ("title","platform","audience","offer","tone","visual-metaphor","image-concept"):
        ap.add_argument("--"+f)
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    if a.sample or not a.title:
        b = _design.get_or_create_sample_brief()
        print(f"Sample design brief ready: {b.get('title')} (id {b.get('id')})"); return 0
    bid = _design.create_brief({"title": a.title, "platform": a.platform or "facebook",
        "audience": a.audience or "general", "offer": a.offer, "tone": a.tone,
        "visual_metaphor": getattr(a,"visual_metaphor"), "image_concept": getattr(a,"image_concept"),
        "compliance_rules": ["no guarantees"], "required_text": {"footer": _design.FOOTER}, "status": "draft"})
    print(f"Design brief created: {bid}"); return 0

if __name__ == "__main__":
    raise SystemExit(main())
