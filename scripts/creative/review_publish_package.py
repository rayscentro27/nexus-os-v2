#!/usr/bin/env python3
"""Review a publish-readiness package (compliance/copy/CTA/footer/risk). No external calls.
    python3 scripts/creative/review_publish_package.py --sample
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _publish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-id"); ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    r = _publish.review_package(a.package_id, sample=a.sample or not a.package_id)
    if not r.get("ok"):
        print("blocker:", r.get("blocker")); return 1
    print(f"Review: decision={r['decision']} score={r['score']} compliance={r['compliance']} (no publish).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
