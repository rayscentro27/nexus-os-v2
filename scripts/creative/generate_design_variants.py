#!/usr/bin/env python3
"""Generate compliance-safe design variants for a brief (deterministic; no image/model API)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _design
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, get, q  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief-id"); ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    brief = _design.get_or_create_sample_brief() if (a.sample or not a.brief_id) else \
        (get("creative_design_briefs", f"id=eq.{q(a.brief_id)}&select=*&limit=1")[1] or [None])[0]
    if not brief:
        print("brief not found"); return 1
    ids = _design.generate_variants(brief)
    print(f"Variants ready for '{brief.get('title')}': {len(ids)} (routes: {', '.join(_design.ROUTES)})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
