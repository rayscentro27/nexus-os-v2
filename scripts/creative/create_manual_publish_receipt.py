#!/usr/bin/env python3
"""Create a manual publish receipt (dry-run by default). Does NOT post anything.
    python3 scripts/creative/create_manual_publish_receipt.py --sample --dry-run
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
    ap.add_argument("--package-id"); ap.add_argument("--platform", default="facebook")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--posted-url"); ap.add_argument("--proof-notes"); ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    r = _publish.create_receipt(a.package_id, a.platform, dry_run=a.dry_run, posted_url=a.posted_url,
                                proof_notes=a.proof_notes, sample=a.sample or not a.package_id)
    if not r.get("ok"):
        print("blocker:", r.get("blocker")); return 1
    print(f"Manual receipt created: type={r['receipt_type']} (no post created by Nexus).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
