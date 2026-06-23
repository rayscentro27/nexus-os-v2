#!/usr/bin/env python3
"""Pick the best compliance-safe variant; create a comparison (approval required)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _design
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief-id"); ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    bid = _design.get_or_create_sample_brief()["id"] if (a.sample or not a.brief_id) else a.brief_id
    res = _design.compare_variants(bid)
    print(f"{res['summary']} · next_action={res['next_action']} · approval required before publish.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
