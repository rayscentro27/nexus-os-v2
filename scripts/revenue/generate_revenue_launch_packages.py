#!/usr/bin/env python3
"""Phase 5 — Package the 4 revenue streams into launch packages (report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    tiers = [{"name": o[1], "price": o[2], "cycle": o[4]} for o in lm.GOCLEAR_OFFERS if o[4] == "monthly"]
    packages = [
        {
            "stream": "GoClear/Apex $97 Readiness Review", "offer": "$97 one-time readiness review",
            "target_client": "New signup", "deliverables": ["credit + business readiness scores", "top blockers", "next actions", "Ray-approved plan"],
            "cta_draft": "Start your Credit + Business Funding Readiness Review.",
            "required_approval": "Ray approves offer + price + copy.", "launch_blocker": "No payment connection (contract-only).",
            "next_action": "Approve offer, then wire payment later behind approval.",
        },
        {
            "stream": "GoClear Monthly Subscription", "offer": "4 tiers", "tiers": tiers,
            "pricing_recommendation": "core ~$97/mo; entry ~$49; funding readiness ~$197; post-funding ~$149",
            "what_client_receives": ["monitoring", "monthly action plans", "business setup tracking", "funding readiness tracking"],
            "retention_logic": "Ongoing tracking after credit wins; path to funding.",
            "upgrade_after_credit_repair": "credit_action_plan -> credit_plus_business_setup",
            "upgrade_after_funding": "funding_readiness -> post_funding_growth",
            "required_approval": "Ray approves tiers + pricing language.", "launch_blocker": "No billing connection.",
            "next_action": "Approve tiers, then connect billing later behind approval.",
        },
        {
            "stream": "Affiliate + Partner Recommendations",
            "partners": [o["partner_name"] for o in lm.partner_offer_dicts() if not o["is_free"]],
            "free_options": [o["diy_option_name"] for o in lm.partner_offer_dicts()],
            "disclosures": "Affiliate/referral disclosed; DIY/free option always shown.",
            "required_approval": "Ray approves partner placements + disclosure language.",
            "missing_configuration": [c["partner_offer_id"] for c in lm.partner_config_checks() if c["needs_config"]],
            "next_action": "Add partner URLs, validate terms, then approve placements.",
        },
        {
            "stream": "Funding Commission Pipeline", "readiness_trigger": "Client reaches funding-ready.",
            "funding_path_recommendation": "Ray-approved funding path (no auto-apply, no auto-contact lenders).",
            "ray_review_requirement": "Required before any funding routing.", "automatic_applications": False,
            "commission_opportunity_tracking": True, "post_funding_tier_offer": "Post-Funding Growth (~$149/mo)",
            "next_action": "Track funding-ready clients; route only after Ray approval.",
        },
    ]
    r = {
        "ok": True, "title": "Revenue Launch Packages", "generated_at": lm.now(), "dry_run": True,
        "packages": packages, "status": "approval_ready_only",
        "counts": {"packages": len(packages)},
        "summary": "4 revenue streams packaged as approval-ready launch packages. Nothing launched, charged, or activated.",
        "safety": {**lm.SAFETY, "streams_launched": False, "payment_activated": False},
    }
    md = ["## Launch packages"]
    for pk in packages:
        md.append(f"### {pk['stream']}")
        md.append(f"- required approval: {pk.get('required_approval', 'Ray review')}")
        md.append(f"- next action: {pk['next_action']}")
        md.append("")
    lm.write_report("revenue_launch_packages_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
