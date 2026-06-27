#!/usr/bin/env python3
"""Phase 7 — Client-facing copy DRAFTS for approval (not published or sent)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402

DISCLOSURE = "Disclosure: this is a recommended partner; we may earn a commission/referral. A free/DIY option is always available."
NO_GUARANTEE = "No guarantees of approval, deletion, score increase, or funding. Educational/planning only."

# (key, headline, body, cta, affiliate, diy)
DRAFTS = [
    ("readiness_review", "Know exactly where you stand", "Get a Credit + Business Funding Readiness Review: clear scores, your top blockers, and the next steps — one simple plan.", "Start my $97 Readiness Review", False, False),
    ("tier1_credit_action_plan", "Stay on track every month", "Credit Monitoring & Action Plan: track your score, get monthly action steps, and dispute guidance in one dashboard.", "Join the Action Plan (~$49/mo)", False, False),
    ("tier2_credit_plus_business", "Build credit and your business", "Credit + Business Setup: everything in the Action Plan plus a business setup checklist and letter/document tracking.", "Upgrade to Credit + Business Setup (~$97/mo)", False, False),
    ("tier3_funding_readiness", "Get funding-ready", "Funding Readiness: bankability scoring, document tracking, and a Ray-approved funding path when you're ready.", "Move to Funding Readiness (~$197/mo)", False, False),
    ("tier4_post_funding", "Keep growing after funding", "Post-Funding Growth: business credit building, vendor accounts, and grant/funding opportunity monitoring.", "Continue with Post-Funding Growth (~$149/mo)", False, False),
    ("smartcredit", "See your score and track progress", "We recommend SmartCredit for score visibility and monitoring so we can track your progress more smoothly.", "Get SmartCredit", True, True),
    ("annualcreditreport", "Prefer the free option?", "You can pull your free official credit report at AnnualCreditReport.com. It may not include a score — you can enter one manually.", "Use the free report", False, False),
    ("online_business_bank", "Open a business bank account", "A dedicated business bank account helps with bankability and funding. We recommend Bluevine, or use your own bank.", "See bank options", True, True),
    ("business_setup_affiliate_diy", "Set up your business foundation", "For each setup item you can choose a recommended partner or a free DIY/official option — your choice.", "See setup options", True, True),
    ("docupost_usps", "Mail your letters your way", "Mail certified letters online with DocuPost, or print and send via USPS Certified Mail and upload your receipt.", "Choose mailing method", True, True),
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    drafts = []
    for (k, head, body, cta, aff, diy) in DRAFTS:
        drafts.append({
            "key": k, "headline": head, "body": body, "cta": cta,
            "affiliate_disclosure": DISCLOSURE if aff else None,
            "diy_free_option": "Included" if diy else None,
            "no_guarantee_language": NO_GUARANTEE,
            "approval_required": True, "published": False, "sent": False,
        })
    r = {
        "ok": True, "title": "Revenue Offer Copy Drafts", "generated_at": lm.now(), "dry_run": True,
        "drafts": drafts, "counts": {"drafts": len(drafts), "with_affiliate_disclosure": sum(1 for d in drafts if d["affiliate_disclosure"])},
        "summary": f"{len(drafts)} client-facing copy drafts generated for approval. Nothing published or sent.",
        "safety": {**lm.SAFETY, "published": False, "sent": False},
    }
    md = ["## Copy drafts (for approval — not published/sent)"]
    for d in drafts:
        md.append(f"### {d['key']}")
        md.append(f"- {d['headline']}")
        md.append(f"- {d['body']}")
        md.append(f"- CTA: {d['cta']}")
        if d["affiliate_disclosure"]:
            md.append(f"- {d['affiliate_disclosure']}")
        md.append(f"- {d['no_guarantee_language']}")
        md.append("")
    lm.write_report("revenue_offer_copy_drafts_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
