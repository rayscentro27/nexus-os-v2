#!/usr/bin/env python3
"""Create a manual publish-readiness package from a winning design variant.
NO real publishing, no Facebook/Instagram API, no external model calls.
    python3 scripts/creative/create_publish_readiness_package.py --sample
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
    ap.add_argument("--design-variant-id"); ap.add_argument("--comparison-id")
    ap.add_argument("--platform", default="facebook"); ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2
    r = _publish.build_package(design_variant_id=a.design_variant_id, comparison_id=a.comparison_id,
                               platform=a.platform, sample=a.sample or not (a.design_variant_id or a.comparison_id))
    if not r.get("ok"):
        print("blocker:", r.get("blocker")); return 1
    print(f"Publish package {'exists' if r.get('existed') else 'created'} (id {r['package_id']}). "
          f"compliance={r.get('compliance_status')} approval={r.get('approval_id') and 'pending'} · NO real publish.")
    print(f"  risk_flags={r.get('risk_flags')} footer={r.get('footer')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
