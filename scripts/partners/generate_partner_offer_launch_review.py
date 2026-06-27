#!/usr/bin/env python3
"""Phase 1 — Partner offer launch review (reviews previous monetization sprint output)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_model as lm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
PRIOR = [
    "nexus_night_run_readiness", "hermes_executive_brief", "nexus_revenue_streams",
    "goclear_subscription_market_research", "online_business_bank_affiliate_research",
    "client_workflow_monetization", "business_setup_banking_monetization",
    "docupost_usps_mailing_monetization", "client_reminder_revenue_risk",
    "nexus_approval_needed", "nexus_blocked_high_risk",
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    reviewed = [{"report": n, "present": (ROOT / "reports" / "manual_publish" / f"{n}_latest.md").exists()} for n in PRIOR]
    r = {
        "ok": True, "title": "Partner Offer Launch Review", "generated_at": lm.now(), "dry_run": True,
        "reviewed_reports": reviewed,
        "revenue_streams_existing": [s["name"] for s in lm.REVENUE_STREAMS],
        "pricing_recommendations_existing": [f"{o[1]}: ${o[2]}/{o[4]}" for o in lm.GOCLEAR_OFFERS],
        "partners_researched": [o["partner_name"] for o in lm.partner_offer_dicts()],
        "still_missing_before_launch": [
            "Partner affiliate/referral URLs (needs_config).",
            "Ray approval of offers, pricing language, and disclosures.",
            "Payment/billing connection (contract-only for now).",
        ],
        "needs_ray_approval": [
            "Each GoClear offer + subscription tier pricing/language.",
            "Each non-free partner placement + affiliate disclosure.",
            "Funding readiness path language.",
        ],
        "blocked_by_policy": [
            "Charging clients / activating payment links / activating subscriptions.",
            "Activating partner connectors; SmartCredit login/scrape; DocuPost sending.",
            "Live Client Vault / 2nd Supabase / external AI on client data.",
        ],
        "counts": {"reviewed": len(reviewed), "present": sum(1 for x in reviewed if x["present"]),
                   "partners": len(lm.PARTNER_OFFERS), "offers": len(lm.GOCLEAR_OFFERS)},
        "summary": "Reviewed prior monetization reports; revenue streams + pricing + partners exist. Missing before launch: partner URLs, Ray approvals, and payment connection. All blocked actions remain blocked.",
        "safety": lm.SAFETY,
    }
    md = ["## Reviewed reports"] + [f"- {'OK' if x['present'] else 'MISSING'} {x['report']}" for x in reviewed]
    md += ["", "## Revenue streams (existing)"] + [f"- {x}" for x in r["revenue_streams_existing"]]
    md += ["", "## Pricing recommendations (existing)"] + [f"- {x}" for x in r["pricing_recommendations_existing"]]
    md += ["", "## Partners researched"] + [f"- {x}" for x in r["partners_researched"]]
    md += ["", "## Still missing before launch"] + [f"- {x}" for x in r["still_missing_before_launch"]]
    md += ["", "## Needs Ray approval"] + [f"- {x}" for x in r["needs_ray_approval"]]
    md += ["", "## Blocked by policy"] + [f"- {x}" for x in r["blocked_by_policy"]]
    lm.write_report("partner_offer_launch_review_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
