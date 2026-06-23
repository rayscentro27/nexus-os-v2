#!/usr/bin/env python3
"""Score design variants deterministically (compliance via classify_claim_risk)."""
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
    res = _design.score_variants(bid)
    for r in res: print(f"  {r['route']}: overall {r['overall']} compliance {r['compliance']}")
    print(f"Scored {len(res)} variants." if res else "All variants already scored.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
