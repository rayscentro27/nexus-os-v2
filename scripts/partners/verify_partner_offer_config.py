#!/usr/bin/env python3
"""Phase 3 — Partner offer config verification (does NOT fail on missing URLs)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    checks = lm.partner_config_checks()
    needs = [c for c in checks if c["needs_config"]]
    r = {
        "ok": True,  # missing partner URLs do NOT fail the build
        "title": "Partner Offer Config Verification", "generated_at": lm.now(), "dry_run": True,
        "checks": checks, "needs_config": [c["partner_offer_id"] for c in needs],
        "counts": {"total": len(checks), "configured": sum(1 for c in checks if c["configured"]), "needs_config": len(needs)},
        "summary": f"{len(needs)} partner(s) need config (URLs from each program). Build is not failed by missing URLs; each has a recommended next action.",
        "safety": lm.SAFETY,
    }
    md = ["## Config checks"]
    for c in checks:
        md.append(f"- {c['partner_name']}: {'configured' if c['configured'] else 'needs_config'} — {c['next_action']}")
    lm.write_report("partner_offer_config_verification_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0  # always 0 — missing config is informational


if __name__ == "__main__":
    raise SystemExit(main())
