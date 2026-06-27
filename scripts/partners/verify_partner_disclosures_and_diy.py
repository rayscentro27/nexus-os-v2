#!/usr/bin/env python3
"""Verify every partner offer has a disclosure (or is free/official) and a DIY/free option."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    offers = lm.partner_offer_dicts()
    checks = []
    failures = []
    for o in offers:
        has_disclosure = bool((o["disclosure_text"] or "").strip())
        has_diy = bool((o["diy_option_name"] or "").strip())
        # Free/official offers need no affiliate disclosure but must still show a free option.
        disclosure_ok = has_disclosure or o["is_free"]
        ok = disclosure_ok and has_diy
        if not ok:
            failures.append({"partner_offer_id": o["partner_offer_id"], "has_disclosure": has_disclosure, "has_diy": has_diy})
        checks.append({"partner_offer_id": o["partner_offer_id"], "partner_name": o["partner_name"],
                       "has_disclosure": has_disclosure, "has_diy_option": has_diy, "is_free": o["is_free"], "ok": ok})
    ok = len(failures) == 0
    r = {
        "ok": ok, "title": "Partner Disclosure + DIY Verification", "generated_at": lm.now(), "dry_run": True,
        "checks": checks, "failures": failures,
        "counts": {"total": len(checks), "passed": sum(1 for c in checks if c["ok"]), "failed": len(failures)},
        "summary": "Every partner offer has a disclosure (or is free) and a DIY/free option." if ok
        else f"{len(failures)} offer(s) missing disclosure or DIY option.",
        "safety": lm.SAFETY,
    }
    md = ["## Disclosure + DIY checks"]
    for c in checks:
        md.append(f"- {c['partner_name']}: disclosure={c['has_disclosure'] or c['is_free']} · DIY={c['has_diy_option']} · {'OK' if c['ok'] else 'FAIL'}")
    lm.write_report("partner_disclosure_diy_verification_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
