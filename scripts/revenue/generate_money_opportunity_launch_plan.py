#!/usr/bin/env python3
"""Money opportunity launch plan (report-only; approval-gated steps, nothing launched)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import money_opportunity_model as mo  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    top = mo.ranked()[:5]
    plans = []
    for o in top:
        plans.append({
            "opportunity_id": o["opportunity_id"], "title": o["title"], "overall_score": o["overall_score"],
            "types": o["opportunity_types"], "approval_needed": o["approval_needed"],
            "internal_build_steps": [
                "Draft assets (copy/landing/social) — internal only.",
                "Score + route into Ray Review Queue.",
                "Prepare approval card with exact decision.",
            ],
            "launch_blocker": "Requires Ray approval" + (" + affiliate program approval/URL" if "affiliate_opportunity" in o["opportunity_types"] else "") + (" + payment connection" if "direct_offer" in o["opportunity_types"] or "monthly_subscription" in o["opportunity_types"] else "."),
            "ray_next_action": o["ray_next_action"],
        })
    r = {
        "ok": True, "title": "Money Opportunity Launch Plan", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "launch_plans": plans,
        "counts": {"plans": len(plans)},
        "summary": f"Prepared {len(plans)} approval-gated launch plans (top opportunities). Internal build only; nothing launched.",
        "safety": {**mo.SAFETY, "offer_launched": False, "payment_activated": False, "external_action_performed": False},
    }
    md = ["## Launch plans (top 5, approval-gated)"]
    for pl in plans:
        md.append(f"### {pl['title']} ({pl['overall_score']})")
        md.append(f"- launch blocker: {pl['launch_blocker']}")
        md.append(f"- next action: {pl['ray_next_action']}")
        md.append("")
    mo.write_report("money_opportunity_launch_plan_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
