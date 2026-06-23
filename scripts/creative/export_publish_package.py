#!/usr/bin/env python3
"""Export a publish-readiness package to Markdown. Does NOT post anything.
    python3 scripts/creative/export_publish_package.py --sample
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
    ap.add_argument("--output", default="/tmp/nexus_publish_package.md")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    r = _publish.export_markdown(a.package_id, a.output, sample=a.sample or not a.package_id)
    if not r.get("ok"):
        print("blocker:", r.get("blocker")); return 1
    print(f"Exported publish package -> {r['output']} (no post created).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
