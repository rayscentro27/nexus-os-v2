#!/usr/bin/env python3
"""Best money opportunity creative package (draft-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import money_opportunity_model as mo  # noqa: E402

NO_GUARANTEE = "Educational/planning only. No guarantee of approval, deletion, score increase, or funding."


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    best = mo.best_overall()
    pkg = {
        "ok": True, "title": "Best Money Opportunity Creative Package", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True, "external_action_performed": False,
        "client_contacted": False, "money_spent": False, "client_charged": False,
        "opportunity": {"id": best["opportunity_id"], "title": best["title"], "overall_score": best["overall_score"]},
        "landing_page_concept": "A focused readiness check that tells a business owner exactly what to fix before applying for funding.",
        "landing_page_headline": "Before You Apply for Business Funding, Check These 3 Things",
        "cta": "Start your $97 Credit + Business Funding Readiness Review",
        "tiktok_video_hook": "Most business owners get denied for the same 3 reasons — here's how to check yours first.",
        "tiktok_script": (
            "Hook: 'Applying for business funding without checking these 3 things? Big mistake.'\n"
            "1) Personal credit + utilization. 2) Business foundation (LLC, EIN, business bank account). "
            "3) Funding readiness score.\n"
            "CTA: 'Get a readiness review before you apply — link in bio.' " + NO_GUARANTEE
        ),
        "instagram_facebook_caption": (
            "Before you apply for business funding, check these 3 things: your credit + utilization, your business "
            "foundation (LLC/EIN/business bank account), and your funding readiness. Get a readiness review first. " + NO_GUARANTEE
        ),
        "creative_background_prompt": "Clean modern fintech hero: calm navy gradient, a checklist with 3 glowing checkmarks, subtle dollar/▲ growth motif, professional and trustworthy (no logos, no people's faces).",
        "ray_review_approval_card": {
            "title": "Approve best-opportunity creative package: " + best["title"],
            "exact_approval_needed": "Approve landing page concept + headline + CTA + TikTok script + IG/FB caption.",
            "risk_level": "low", "external_action_status": "none (draft only)", "launch_status": "proposed",
            "recommended_ray_decision": "Approve copy / request changes / park.",
            "report_links": ["reports/manual_publish/best_money_opportunity_creative_package_latest.md"],
        },
        "hermes_recommendation": (
            f"Lead with '{best['title']}'. It scores highest because it turns research into a clear, low-risk "
            "front-end offer that funds the relationship and feeds the subscription + funding pipeline. "
            "Build the landing page + TikTok first (draft), then approve copy. Keep payment + posting blocked until you approve."
        ),
        "summary": f"Drafted a full creative package for the best opportunity: {best['title']} ({best['overall_score']}). Draft-only.",
        "safety": {**mo.SAFETY, "publish_status": "draft_only", "external_action_performed": False},
    }
    md = [f"## Best opportunity: {best['title']} ({best['overall_score']})",
          f"- Landing headline: {pkg['landing_page_headline']}",
          f"- CTA: {pkg['cta']}",
          f"- TikTok hook: {pkg['tiktok_video_hook']}",
          "", "### TikTok script", pkg["tiktok_script"],
          "", "### IG/FB caption", pkg["instagram_facebook_caption"],
          "", "### Creative background prompt", pkg["creative_background_prompt"],
          "", "### Ray Review approval card", f"- {pkg['ray_review_approval_card']['exact_approval_needed']}",
          "", "### Hermes recommendation", pkg["hermes_recommendation"]]
    mo.write_report("best_money_opportunity_creative_package_latest", pkg, md)
    print(json.dumps(pkg, indent=2) if a.json else pkg["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
