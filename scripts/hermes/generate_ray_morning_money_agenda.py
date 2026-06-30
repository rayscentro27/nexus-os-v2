#!/usr/bin/env python3
"""Ray morning money agenda + Ray/Hermes morning discussion agenda (plain language)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import money_opportunity_model as mo  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    items = mo.ranked()
    best = items[0]
    content = mo.by_type("content_opportunity")
    landing = sorted([o for o in items if o["scores"]["landing_page_potential"] >= 60], key=lambda x: x["scores"]["landing_page_potential"], reverse=True)
    affiliate = sorted(mo.needs_affiliate_approval(), key=lambda x: x["scores"]["affiliate_potential"], reverse=True)
    workflow = mo.by_type("client_workflow_improvement")
    approvals = mo.by_type("ray_review_approval_item")

    # Morning package answers
    agenda = {
        "ok": True, "title": "Ray Morning Money Agenda", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "answers": {
            "researched_overnight": f"{len(items)} opportunities across {len(mo.RESEARCH_CATEGORIES)} categories.",
            "fastest_money": mo.fastest_to_launch()["title"],
            "lowest_risk": mo.lowest_risk()["title"],
            "needs_affiliate_approval": [o["title"] for o in affiliate[:3]],
            "launch_without_affiliate": [o["title"] for o in mo.launchable_without_affiliate()[:3]],
            "first_landing_page": landing[0]["title"] if landing else "n/a",
            "first_tiktok": max(content, key=lambda x: x["scores"]["tiktok_potential"])["title"] if content else "n/a",
            "first_ig_fb": max(content, key=lambda x: x["scores"]["instagram_facebook_potential"])["title"] if content else "n/a",
            "most_important_affiliate": affiliate[0]["title"] if affiliate else "n/a",
            "client_workflow_costing_money": workflow[0]["title"] if workflow else "n/a",
            "hermes_should_discuss": "GoClear positioning: credit repair vs funding readiness.",
            "approve_first": best["ray_next_action"],
            "blocked": "Publish/send/charge/payment/connector/funding-application all blocked until approved.",
            "ready_to_build": "Landing page + TikTok + IG/FB drafts for the top opportunity.",
            "publish_after_approval_only": "All client-facing assets and offers.",
        },
        "counts": {"opportunities": len(items)},
        "summary": f"Morning agenda ready. Approve first: {best['title']}. Fastest money: {mo.fastest_to_launch()['title']}.",
        "safety": {**mo.SAFETY, "external_action_performed": False, "client_contacted": False},
    }
    md = ["## Ray morning money agenda"] + [f"- {k}: {v}" for k, v in agenda["answers"].items()]
    mo.write_report("ray_morning_money_agenda_latest", agenda, md)

    # Discussion agenda (plain language, structured)
    disc = {
        "ok": True, "title": "Ray + Hermes Morning Discussion Agenda", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "top_5_money_opportunities": [o["title"] for o in items[:5]],
        "top_3_content_ideas": [o["title"] for o in sorted(content, key=lambda x: x["scores"]["content_potential"], reverse=True)[:3]],
        "top_3_landing_page_ideas": [o["title"] for o in landing[:3]],
        "top_3_affiliate_actions": [o["ray_next_action"] for o in affiliate[:3]],
        "top_3_client_workflow_fixes": [o["title"] for o in workflow[:3]],
        "top_3_approval_decisions": [o["ray_next_action"] for o in approvals[:3]] or [best["ray_next_action"]],
        "hermes_recommendation": f"Lead with '{best['title']}'; draft assets today; approve copy; keep risky actions blocked.",
        "rays_fastest_money_move": mo.fastest_to_launch()["title"],
        "what_not_to_do_yet": "Do not publish, send, charge, connect payment, activate connectors, or apply for funding.",
        "summary": "Plain-language morning discussion agenda for Ray and Hermes.",
        "safety": {**mo.SAFETY, "external_action_performed": False},
    }
    md2 = ["## Top 5 money opportunities"] + [f"- {x}" for x in disc["top_5_money_opportunities"]]
    md2 += ["", "## Top 3 content ideas"] + [f"- {x}" for x in disc["top_3_content_ideas"]]
    md2 += ["", "## Top 3 landing page ideas"] + [f"- {x}" for x in disc["top_3_landing_page_ideas"]]
    md2 += ["", "## Top 3 affiliate actions"] + [f"- {x}" for x in disc["top_3_affiliate_actions"]]
    md2 += ["", "## Top 3 client workflow fixes"] + [f"- {x}" for x in disc["top_3_client_workflow_fixes"]]
    md2 += ["", "## Top 3 approval decisions"] + [f"- {x}" for x in disc["top_3_approval_decisions"]]
    md2 += ["", f"## Hermes recommendation", f"- {disc['hermes_recommendation']}",
            f"", f"## Ray's fastest money move", f"- {disc['rays_fastest_money_move']}",
            f"", f"## What not to do yet", f"- {disc['what_not_to_do_yet']}"]
    mo.write_report("ray_hermes_morning_discussion_agenda_latest", disc, md2)

    print(json.dumps(agenda, indent=2) if a.json else agenda["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
