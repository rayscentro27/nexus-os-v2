#!/usr/bin/env python3
"""Nexus OS v2 — Day 10 idempotent seed: a manual publish-readiness package from the Day 9
GoClear credit-readiness design winner. Creates package + review + approval + dry-run receipt
+ Markdown export. NO real publishing, no external calls.

    # macOS SSL: SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_day10_publish_readiness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "social"))
sys.path.insert(0, str(HERE / "creative"))
from _supabase import configured, event  # noqa: E402
import _publish  # noqa: E402


def main() -> int:
    if not configured():
        print("SETUP NEEDED: Supabase env required (not printed)."); return 2

    pkg = _publish.build_package(sample=True)
    if not pkg.get("ok"):
        print("BLOCKER:", pkg.get("blocker")); return 1
    rev = _publish.review_package(pkg["package_id"])
    rec = _publish.create_receipt(pkg["package_id"], "facebook", dry_run=True)
    exp = _publish.export_markdown(pkg["package_id"], "/tmp/nexus_publish_package.md")

    if not (_publish.get("nexus_events", "action=eq.day10_publish_readiness_seeded&select=id&limit=1")[1] or []):
        event("monetization", "day10_publish_readiness_seeded", "success", "Day 10 publish readiness seeded",
              f"package compliance={pkg.get('compliance_status')} review={rev.get('decision')} "
              f"receipt={rec.get('receipt_type')} export={exp.get('output')}")

    print("Day 10 publish readiness seed complete (no real publish, no API calls).")
    print(f"  package_id={pkg['package_id']} compliance={pkg.get('compliance_status')} "
          f"approval={'pending' if pkg.get('approval_id') else '—'}")
    print(f"  review={rev.get('decision')} ({rev.get('score')}) · receipt={rec.get('receipt_type')} · export={exp.get('output')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
