"""Shared launch model for partner-offers / pricing / launch-package / review-card generators.

Mirrors the TS source-of-truth configs (partnerOffers.ts, goclearSubscriptionOffers.ts,
goclearPricingValidation.ts, goclearPaymentOfferContract.ts, nexusRevenueStreams.ts). Reuses the
night-run report writer. Deterministic, internal/report-only. No charge/send/contact/activation.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402,F401

NO_GUARANTEE = "Educational/planning only. No guarantee of approval, deletion, score increase, or funding."

# partner_offer_id, category, partner_name, revenue_type, target_stage, diy_option, risk, is_free
PARTNER_OFFERS = [
    ("smartcredit", "credit_monitoring", "SmartCredit", "affiliate", "credit_report_source_needed", "AnnualCreditReport.com (free)", "low", False),
    ("annualcreditreport", "credit_report_free", "AnnualCreditReport.com", "free_official", "credit_report_source_needed", "Self-request (free)", "low", True),
    ("bluevine", "online_business_bank_account", "Bluevine", "referral", "business_setup_in_progress", "Client's own bank/credit union", "medium", False),
    ("mercury", "online_business_bank_account", "Mercury", "referral", "business_setup_in_progress", "Client's own bank/credit union", "medium", False),
    ("relay", "online_business_bank_account", "Relay", "referral", "business_setup_in_progress", "Client's own bank/credit union", "medium", False),
    ("docupost", "online_mailing", "DocuPost", "affiliate", "mailing_needed", "USPS Certified Mail (DIY)", "medium", False),
    ("business_formation", "business_formation", "Formation partner (placeholder)", "affiliate", "business_setup_needed", "State SoS + IRS.gov (free EIN)", "low", False),
    ("registered_agent", "registered_agent", "Registered agent partner (placeholder)", "affiliate", "business_setup_needed", "Act as your own agent", "low", False),
    ("business_address", "business_address", "Virtual address partner (placeholder)", "affiliate", "business_setup_needed", "Existing commercial address", "low", False),
    ("business_phone", "business_phone", "VoIP partner (placeholder)", "affiliate", "business_setup_needed", "Any business line", "low", False),
    ("website_domain_email", "website_domain_email", "Website/domain partner (placeholder)", "affiliate", "business_setup_needed", "Self-built site + domain email", "low", False),
    ("bookkeeping", "bookkeeping_accounting", "Bookkeeping partner (placeholder)", "affiliate", "business_analysis_ready", "DIY spreadsheet", "low", False),
    ("vendor_credit", "vendor_credit_accounts", "Vendor credit partner (placeholder)", "affiliate", "business_analysis_ready", "Net-30 vendors (DIY)", "low", False),
    ("funding_readiness_service", "funding_readiness_services", "Funding readiness service", "service_fee", "funding_readiness_pending", "Internal funding readiness checklist", "medium", False),
]


def partner_offer_dicts() -> list[dict]:
    out = []
    for (pid, cat, name, rev, stage, diy, risk, is_free) in PARTNER_OFFERS:
        out.append({
            "partner_offer_id": pid, "category": cat, "partner_name": name,
            "affiliate_url": None, "referral_url": None, "application_url": None,
            "diy_option_name": diy,
            "disclosure_text": "Free official option — no affiliate relationship." if is_free
            else "Recommended partner; we may earn a commission/referral if you sign up. Optional — a free/DIY option is always available.",
            "client_trigger": f"Client needs {cat.replace('_', ' ')}.",
            "target_client_stage": stage, "revenue_type": rev,
            "estimated_revenue": "$0 (no affiliate)" if is_free else "$ per signup (validate)",
            "approval_required": not is_free, "activation_status": "proposed",
            "configuration_status": "configured" if is_free else "needs_config",
            "risk_level": risk, "compliance_notes": NO_GUARANTEE,
            "last_validated_at": None, "next_validation_due_at": None, "is_free": is_free,
        })
    return out


def partner_config_checks() -> list[dict]:
    checks = []
    for o in partner_offer_dicts():
        missing = []
        if not o["is_free"]:
            if not (o["affiliate_url"] or o["referral_url"] or o["application_url"]):
                missing.append("affiliate/referral/application URL")
        configured = len(missing) == 0
        checks.append({
            "partner_offer_id": o["partner_offer_id"], "partner_name": o["partner_name"], "category": o["category"],
            "configured": configured, "missing": missing, "needs_config": not configured,
            "next_action": "Validate live terms, then request Ray approval to activate." if configured
            else f"Add {' + '.join(missing)} from the partner program, then re-validate.",
            "approval_required": o["approval_required"], "activation_status": o["activation_status"],
        })
    return checks


# offer_id, name, price, range, cycle, client_stage, trigger, upgrade, downgrade
GOCLEAR_OFFERS = [
    ("readiness_review", "GoClear/Apex Credit + Business Funding Readiness Review", 97, [97, 97], "one_time",
     "profile_created", "New signup / profile created.", "credit_action_plan", None),
    ("credit_action_plan", "Credit Monitoring & Action Plan", 49, [39, 69], "monthly",
     "credit_analysis_ready", "Client needs credit guidance + score/report tracking.", "credit_plus_business_setup", None),
    ("credit_plus_business_setup", "Credit + Business Setup", 97, [79, 129], "monthly",
     "business_setup_needed", "Client needs credit repair plus business foundation.", "funding_readiness", "credit_action_plan"),
    ("funding_readiness", "Funding Readiness", 197, [149, 297], "monthly",
     "funding_readiness_pending", "Client is preparing for funding.", "post_funding_growth", "credit_plus_business_setup"),
    ("post_funding_growth", "Post-Funding Growth", 149, [99, 249], "monthly",
     "funding_ready", "Funded client maintaining/growing business credit.", None, "funding_readiness"),
]

# market bands for validation: (offer_id -> (low, high, label))
PRICING_BANDS = {
    "readiness_review": (97, 199, "Business funding readiness/coaching"),
    "credit_action_plan": (19, 149, "Credit repair (DIY/service)"),
    "credit_plus_business_setup": (49, 199, "Business credit builder subscription"),
    "funding_readiness": (97, 497, "Business funding readiness/coaching"),
    "post_funding_growth": (97, 497, "Business funding readiness/coaching"),
}


def pricing_validations() -> list[dict]:
    out = []
    for (oid, name, price, rng, cycle, *_rest) in GOCLEAR_OFFERS:
        low, high, label = PRICING_BANDS[oid]
        if cycle == "one_time":
            out.append({"offer_id": oid, "offer_name": name, "price": price, "billing_cycle": cycle,
                        "within_market_band": True, "reference_band": f"{label} (${low}-${high})",
                        "verdict": "one_time", "note": "$97 readiness review is a common front-end price point; validate locally."})
            continue
        in_range = low <= price <= high
        verdict = "in_range" if in_range else ("below_range" if price < low else "above_range")
        out.append({"offer_id": oid, "offer_name": name, "price": price, "billing_cycle": cycle,
                    "within_market_band": in_range, "reference_band": f"{label} (${low}-${high})", "verdict": verdict,
                    "note": "Price sits within the market band." if in_range else
                    ("Below band — room to raise after validation." if verdict == "below_range" else "Above band — confirm value justifies premium.")})
    return out


def payment_offers() -> list[dict]:
    return [{
        "offer_id": oid, "offer_name": name, "price": price, "billing_cycle": cycle,
        "stripe_product_id_placeholder": f"prod_PLACEHOLDER_{oid}",
        "stripe_price_id_placeholder": f"price_PLACEHOLDER_{oid}",
        "payment_link_placeholder": f"https://PLACEHOLDER.invalid/pay/{oid}",
        "activation_status": "not_connected", "approval_required": True,
    } for (oid, name, price, _rng, cycle, *_rest) in GOCLEAR_OFFERS]


REVENUE_STREAMS = [
    {"stream_id": "readiness_review", "name": "GoClear/Apex $97 Readiness Review"},
    {"stream_id": "monthly_subscription", "name": "GoClear Monthly Subscription"},
    {"stream_id": "affiliate_partner_engine", "name": "Affiliate + Partner Recommendations"},
    {"stream_id": "funding_commission_pipeline", "name": "Funding Commission Pipeline"},
]
