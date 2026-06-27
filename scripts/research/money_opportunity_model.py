"""Shared model for the overnight money-opportunity research engine.

Deterministic, local-first, internal/report-only. Curated research items (NOT scraped) covering
credit/funding/business-setup/affiliate/content/landing/social opportunities, each scored and
classified. Reuses the night-run report writer. No publish/send/charge/spend/contact/external AI.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402,F401

# Score fields (0-100; cost_to_launch + risk_level are "lower is better" for ranking).
SCORE_FIELDS = [
    "revenue_potential", "speed_to_launch", "cost_to_launch", "risk_level", "client_value",
    "affiliate_potential", "subscription_potential", "funding_commission_potential",
    "content_potential", "landing_page_potential", "tiktok_potential",
    "instagram_facebook_potential", "hermes_discussion_value",
]

OPPORTUNITY_TYPES = [
    "direct_offer", "monthly_subscription", "affiliate_opportunity", "client_workflow_improvement",
    "content_opportunity", "landing_page_opportunity", "hermes_discussion_topic", "ray_review_approval_item",
]


def _o(oid, title, source_category, types, approval_needed, ray_next_action, scores):
    s = {k: 0 for k in SCORE_FIELDS}
    s.update(scores)
    return {
        "opportunity_id": oid, "title": title, "source_category": source_category,
        "opportunity_types": types, "approval_needed": approval_needed,
        "ray_next_action": ray_next_action, "scores": s,
    }


# Curated overnight research items (internal estimates to validate; not scraped).
OPPORTUNITIES = [
    _o("readiness_review_97", "$97 Credit + Business Funding Readiness Review", "direct offer / funding readiness",
       ["direct_offer", "ray_review_approval_item"], True, "Approve the $97 readiness review offer + copy.",
       {"revenue_potential": 85, "speed_to_launch": 80, "cost_to_launch": 15, "risk_level": 20, "client_value": 85,
        "affiliate_potential": 10, "subscription_potential": 60, "funding_commission_potential": 40,
        "content_potential": 70, "landing_page_potential": 85, "tiktok_potential": 70,
        "instagram_facebook_potential": 70, "hermes_discussion_value": 80}),
    _o("core_subscription", "Credit + Business Setup subscription (~$97/mo)", "subscription upsell",
       ["monthly_subscription", "ray_review_approval_item"], True, "Approve core subscription tier pricing/language.",
       {"revenue_potential": 90, "speed_to_launch": 55, "cost_to_launch": 25, "risk_level": 30, "client_value": 80,
        "affiliate_potential": 20, "subscription_potential": 95, "funding_commission_potential": 50,
        "content_potential": 55, "landing_page_potential": 70, "tiktok_potential": 50,
        "instagram_facebook_potential": 55, "hermes_discussion_value": 75}),
    _o("smartcredit_affiliate", "SmartCredit content + affiliate angle", "SmartCredit affiliate",
       ["affiliate_opportunity", "content_opportunity"], True, "Approve SmartCredit placement + disclosure; apply to program.",
       {"revenue_potential": 70, "speed_to_launch": 60, "cost_to_launch": 10, "risk_level": 25, "client_value": 75,
        "affiliate_potential": 90, "subscription_potential": 40, "funding_commission_potential": 10,
        "content_potential": 80, "landing_page_potential": 60, "tiktok_potential": 80,
        "instagram_facebook_potential": 75, "hermes_discussion_value": 60}),
    _o("online_bank_affiliate", "Online business banking (Bluevine) angle", "online business banking affiliate",
       ["affiliate_opportunity", "content_opportunity", "client_workflow_improvement"], True,
       "Approve online-bank placement; validate referral terms.",
       {"revenue_potential": 75, "speed_to_launch": 45, "cost_to_launch": 10, "risk_level": 35, "client_value": 80,
        "affiliate_potential": 85, "subscription_potential": 30, "funding_commission_potential": 60,
        "content_potential": 70, "landing_page_potential": 65, "tiktok_potential": 65,
        "instagram_facebook_potential": 65, "hermes_discussion_value": 65}),
    _o("funding_readiness_landing", "Landing page: 'Before You Apply for Business Funding, Check These 3 Things'",
       "landing page angle", ["landing_page_opportunity", "content_opportunity", "direct_offer"], True,
       "Approve landing page concept + copy.",
       {"revenue_potential": 80, "speed_to_launch": 70, "cost_to_launch": 20, "risk_level": 20, "client_value": 85,
        "affiliate_potential": 40, "subscription_potential": 55, "funding_commission_potential": 55,
        "content_potential": 85, "landing_page_potential": 95, "tiktok_potential": 75,
        "instagram_facebook_potential": 75, "hermes_discussion_value": 80}),
    _o("tiktok_not_funding_ready", "TikTok hook: 'Why your business isn't funding-ready yet'", "TikTok hook",
       ["content_opportunity"], True, "Approve TikTok script before recording.",
       {"revenue_potential": 55, "speed_to_launch": 85, "cost_to_launch": 10, "risk_level": 20, "client_value": 70,
        "affiliate_potential": 35, "subscription_potential": 40, "funding_commission_potential": 30,
        "content_potential": 90, "landing_page_potential": 50, "tiktok_potential": 95,
        "instagram_facebook_potential": 70, "hermes_discussion_value": 60}),
    _o("stuck_no_bank", "Client workflow fix: clients stuck without a business bank account", "client pain point",
       ["client_workflow_improvement", "affiliate_opportunity"], False, "No approval to detect/fix internally; gate any client contact.",
       {"revenue_potential": 65, "speed_to_launch": 80, "cost_to_launch": 5, "risk_level": 15, "client_value": 90,
        "affiliate_potential": 70, "subscription_potential": 45, "funding_commission_potential": 65,
        "content_potential": 50, "landing_page_potential": 45, "tiktok_potential": 45,
        "instagram_facebook_potential": 45, "hermes_discussion_value": 70}),
    _o("stuck_no_ein", "Client workflow fix: clients stuck without an EIN", "client pain point",
       ["client_workflow_improvement"], False, "Internal nudge/checklist; gate any client contact.",
       {"revenue_potential": 45, "speed_to_launch": 80, "cost_to_launch": 5, "risk_level": 10, "client_value": 80,
        "affiliate_potential": 40, "subscription_potential": 40, "funding_commission_potential": 35,
        "content_potential": 45, "landing_page_potential": 35, "tiktok_potential": 40,
        "instagram_facebook_potential": 40, "hermes_discussion_value": 55}),
    _o("docupost_education", "DocuPost vs USPS certified mail education", "mailing education / affiliate",
       ["content_opportunity", "affiliate_opportunity"], True, "Approve DocuPost placement + disclosure.",
       {"revenue_potential": 50, "speed_to_launch": 65, "cost_to_launch": 10, "risk_level": 25, "client_value": 65,
        "affiliate_potential": 60, "subscription_potential": 25, "funding_commission_potential": 10,
        "content_potential": 70, "landing_page_potential": 50, "tiktok_potential": 55,
        "instagram_facebook_potential": 55, "hermes_discussion_value": 50}),
    _o("acr_free_education", "AnnualCreditReport.com free-option education", "free option education",
       ["content_opportunity"], True, "Approve free-option education copy (no affiliate).",
       {"revenue_potential": 35, "speed_to_launch": 80, "cost_to_launch": 5, "risk_level": 10, "client_value": 75,
        "affiliate_potential": 5, "subscription_potential": 35, "funding_commission_potential": 10,
        "content_potential": 75, "landing_page_potential": 45, "tiktok_potential": 65,
        "instagram_facebook_potential": 65, "hermes_discussion_value": 55}),
    _o("funding_commission_pipeline", "Funding readiness -> commission pipeline", "funding commission",
       ["direct_offer", "client_workflow_improvement", "ray_review_approval_item"], True,
       "Approve funding path language; no auto-apply.",
       {"revenue_potential": 95, "speed_to_launch": 40, "cost_to_launch": 20, "risk_level": 45, "client_value": 85,
        "affiliate_potential": 30, "subscription_potential": 50, "funding_commission_potential": 95,
        "content_potential": 55, "landing_page_potential": 60, "tiktok_potential": 50,
        "instagram_facebook_potential": 50, "hermes_discussion_value": 85}),
    _o("post_funding_tier", "Post-funding growth subscription tier", "post-funding retention",
       ["monthly_subscription"], True, "Approve post-funding tier language.",
       {"revenue_potential": 70, "speed_to_launch": 45, "cost_to_launch": 20, "risk_level": 25, "client_value": 75,
        "affiliate_potential": 35, "subscription_potential": 85, "funding_commission_potential": 40,
        "content_potential": 50, "landing_page_potential": 55, "tiktok_potential": 45,
        "instagram_facebook_potential": 45, "hermes_discussion_value": 65}),
    _o("funding_path_banks", "Funding-path bank angles (BofA, Chase, credit unions, community banks)", "funding-path banks",
       ["content_opportunity", "affiliate_opportunity"], True, "Approve education angle; validate any referral terms.",
       {"revenue_potential": 60, "speed_to_launch": 55, "cost_to_launch": 10, "risk_level": 35, "client_value": 75,
        "affiliate_potential": 55, "subscription_potential": 35, "funding_commission_potential": 60,
        "content_potential": 75, "landing_page_potential": 60, "tiktok_potential": 65,
        "instagram_facebook_potential": 65, "hermes_discussion_value": 70}),
    _o("business_setup_bundle", "Business setup bundle (LLC/EIN/address/phone/domain/DUNS/vendor)", "business setup",
       ["affiliate_opportunity", "content_opportunity", "client_workflow_improvement"], True,
       "Approve setup partner categories + disclosures.",
       {"revenue_potential": 80, "speed_to_launch": 50, "cost_to_launch": 15, "risk_level": 30, "client_value": 85,
        "affiliate_potential": 85, "subscription_potential": 60, "funding_commission_potential": 55,
        "content_potential": 70, "landing_page_potential": 65, "tiktok_potential": 60,
        "instagram_facebook_potential": 60, "hermes_discussion_value": 75}),
    _o("positioning_topic", "Positioning: credit repair vs funding readiness", "Hermes discussion",
       ["hermes_discussion_topic"], False, "Decide GoClear positioning with Hermes.",
       {"revenue_potential": 50, "speed_to_launch": 90, "cost_to_launch": 0, "risk_level": 10, "client_value": 70,
        "affiliate_potential": 20, "subscription_potential": 55, "funding_commission_potential": 45,
        "content_potential": 60, "landing_page_potential": 50, "tiktok_potential": 45,
        "instagram_facebook_potential": 45, "hermes_discussion_value": 95}),
]

RESEARCH_CATEGORIES = sorted({o["source_category"] for o in OPPORTUNITIES})


def overall_score(o: dict) -> int:
    """Composite rank score. Rewards revenue/speed/value; penalizes cost + risk."""
    s = o["scores"]
    positive = (s["revenue_potential"] * 1.6 + s["speed_to_launch"] * 1.1 + s["client_value"] * 1.0
                + s["affiliate_potential"] * 0.6 + s["subscription_potential"] * 0.7
                + s["funding_commission_potential"] * 0.7 + s["content_potential"] * 0.5
                + s["landing_page_potential"] * 0.4 + s["hermes_discussion_value"] * 0.4)
    penalty = s["cost_to_launch"] * 0.8 + s["risk_level"] * 1.0
    raw = (positive - penalty) / 8.0
    return max(0, min(100, round(raw)))


def ranked() -> list[dict]:
    items = [{**o, "overall_score": overall_score(o)} for o in OPPORTUNITIES]
    items.sort(key=lambda x: x["overall_score"], reverse=True)
    return items


def fastest_to_launch() -> dict:
    return max(OPPORTUNITIES, key=lambda o: o["scores"]["speed_to_launch"] - o["scores"]["risk_level"])


def lowest_risk() -> dict:
    return min(OPPORTUNITIES, key=lambda o: o["scores"]["risk_level"])


def best_overall() -> dict:
    return ranked()[0]


def needs_affiliate_approval() -> list[dict]:
    return [o for o in OPPORTUNITIES if "affiliate_opportunity" in o["opportunity_types"]]


def launchable_without_affiliate() -> list[dict]:
    return [o for o in OPPORTUNITIES if "affiliate_opportunity" not in o["opportunity_types"]]


def by_type(t: str) -> list[dict]:
    return [o for o in OPPORTUNITIES if t in o["opportunity_types"]]
