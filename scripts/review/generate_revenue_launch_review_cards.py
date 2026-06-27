#!/usr/bin/env python3
"""Phase 6 — Ray Review launch cards (prepared only; never auto-approved/executed)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402

# (title, revenue_stream, proposed_action, exact_approval, risk, expected_value, client_impact)
CARDS = [
    ("Approve $97 Readiness Review offer", "readiness_review", "Launch the $97 readiness review at signup.", "Approve offer + price + copy.", "low", "$97 per new client (front-end).", "Client sees a paid readiness review CTA."),
    ("Approve GoClear monthly subscription tiers", "monthly_subscription", "Launch 4 subscription tiers.", "Approve tiers + monthly pricing + language.", "medium", "Recurring revenue (~$49-$197/mo).", "Client sees subscription options."),
    ("Approve SmartCredit partner offer placement", "affiliate_partner_engine", "Place SmartCredit as recommended credit source.", "Approve placement + affiliate disclosure.", "low", "Affiliate commission per signup.", "Client sees SmartCredit (with free DIY option)."),
    ("Approve online business bank recommendation placement", "affiliate_partner_engine", "Place Bluevine (primary) + Mercury/Relay backups.", "Approve placement + disclosure + DIY option.", "medium", "Referral revenue per funded account.", "Client sees bank options (with own-bank DIY)."),
    ("Approve DocuPost partner placement", "affiliate_partner_engine", "Place DocuPost as online mailing option (shell).", "Approve placement + disclosure.", "medium", "Affiliate per mailing.", "Client sees DocuPost vs USPS DIY."),
    ("Approve business setup partner categories", "affiliate_partner_engine", "Place formation/agent/address/phone/web/bookkeeping/vendor partners.", "Approve categories + disclosures + DIY options.", "low", "Affiliate per signup across categories.", "Client sees partner vs DIY per setup item."),
    ("Approve subscription pricing language", "monthly_subscription", "Use proposed pricing language across tiers.", "Approve pricing language (no-guarantee).", "low", "Supports subscription launch.", "Client sees clear pricing language."),
    ("Approve affiliate disclosure language", "affiliate_partner_engine", "Use standard affiliate/referral disclosure.", "Approve disclosure wording.", "low", "Compliance for affiliate revenue.", "Client sees disclosure on partner recs."),
    ("Approve funding readiness path language", "funding_commission_pipeline", "Use funding readiness path wording.", "Approve language (no funding guarantee).", "medium", "Supports funding pipeline.", "Funding-ready clients see next steps."),
    ("Approve post-funding growth tier language", "monthly_subscription", "Use post-funding tier wording.", "Approve post-funding tier language.", "low", "Retention after funding.", "Funded clients see growth tier."),
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    cards = [{
        "title": t, "summary": f"Ray decision: {t}.", "revenue_stream": rs, "proposed_action": pa,
        "exact_approval_needed": ea, "risk_level": risk, "expected_value": ev, "client_facing_impact": ci,
        "external_action_status": "none (prepared only)", "launch_status": "proposed",
        "recommended_ray_decision": "Approve prep / request changes / park.",
        "report_links": ["reports/manual_publish/revenue_launch_packages_latest.md", "reports/manual_publish/partner_offers_latest.md"],
        "decision_reason": "approval_gated_execution", "executed": False,
    } for (t, rs, pa, ea, risk, ev, ci) in CARDS]
    r = {
        "ok": True, "title": "Revenue Launch Review Cards", "generated_at": lm.now(), "dry_run": True,
        "cards": cards, "counts": {"cards": len(cards), "executed": 0},
        "summary": f"{len(cards)} Ray Review launch cards prepared (proposal-only). None auto-approved or executed.",
        "safety": {**lm.SAFETY, "auto_approved": False, "executed": False},
    }
    md = ["## Ray Review launch cards (prepared only)"]
    for c in cards:
        md.append(f"### {c['title']}")
        md.append(f"- revenue stream: {c['revenue_stream']} · risk: {c['risk_level']}")
        md.append(f"- exact approval: {c['exact_approval_needed']}")
        md.append(f"- expected value: {c['expected_value']}")
        md.append("")
    lm.write_report("revenue_launch_review_cards_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
