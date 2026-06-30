#!/usr/bin/env python3
"""Hermes money opportunity brief (plain language, sanitized signals only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import money_opportunity_model as mo  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    best = mo.best_overall()
    fastest = mo.fastest_to_launch()
    lowest = mo.lowest_risk()
    r = {
        "ok": True, "title": "Hermes Money Opportunity Brief", "generated_at": mo.now(), "dry_run": True,
        "uses_raw_client_data": False, "uses_sanitized_signals_only": True,
        "publish_status": "draft_only", "approval_required": True,
        "why_it_matters": f"'{best['title']}' is the strongest move: it turns overnight research into a clear, low-risk offer that funds the relationship.",
        "how_it_makes_money": "Front-end readiness review -> monthly subscription -> affiliate placements -> funding commission. Each step compounds.",
        "what_to_create": "A landing page + a TikTok + an IG/FB post (all draft) for the top opportunity.",
        "what_can_be_done_today": "Draft + score + prepare approval cards internally. Decide GoClear positioning.",
        "what_needs_ray_approval": "Offer + pricing + copy + partner placements + funding-path language.",
        "what_could_go_wrong": "Over-promising outcomes (compliance), or launching before payment/affiliate config is ready.",
        "what_should_stay_blocked": "Publishing, sending, charging, payment links, partner connectors, funding applications.",
        "connects_to_goclear_apex": "The readiness review is the GoClear/Apex front door.",
        "connects_to_subscriptions": "Readiness clients roll into the ~$97/mo core tier and beyond.",
        "connects_to_affiliate_revenue": "SmartCredit + online banking + setup partners monetize the same tasks.",
        "connects_to_funding_commissions": "Funding-ready clients feed the commission pipeline (Ray-approved, no auto-apply).",
        "fastest_money_move": f"{fastest['title']} (fastest to launch).",
        "lowest_risk_move": f"{lowest['title']} (lowest risk).",
        "counts": {"opportunities": len(mo.OPPORTUNITIES)},
        "summary": f"Hermes brief: lead with '{best['title']}'; fastest is '{fastest['title']}'; lowest risk is '{lowest['title']}'. Draft-only; keep risky actions blocked.",
        "safety": {**mo.SAFETY, "raw_client_data_used": False, "external_action_performed": False},
    }
    md = ["## Hermes money opportunity brief (plain language)",
          f"- Why it matters: {r['why_it_matters']}",
          f"- How it makes money: {r['how_it_makes_money']}",
          f"- Create: {r['what_to_create']}",
          f"- Today: {r['what_can_be_done_today']}",
          f"- Needs Ray approval: {r['what_needs_ray_approval']}",
          f"- Could go wrong: {r['what_could_go_wrong']}",
          f"- Stay blocked: {r['what_should_stay_blocked']}",
          f"- Fastest money: {r['fastest_money_move']}",
          f"- Lowest risk: {r['lowest_risk_move']}"]
    mo.write_report("hermes_money_opportunity_brief_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
