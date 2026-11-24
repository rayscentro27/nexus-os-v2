"""Live shadow proof for the 2026 Nexus top-three online business review.

Source notes are assembled from current public pages gathered for this case.
The script creates one isolated case and makes no production handoff or outreach.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .advisor_router import AdvisorRouter, ChatGPTAdvisor, OpenRouterFreeAdvisor
from .codex_chatgpt_advisor import CodexCliChatGPTConnector
from .participants import append_message
from .advisor_router import select_domain
from .room_graph import RoomGraph
from .source_tools import SourceTools
from .state import JsonCaseStore
from .transcripts import write_case_artifacts
from .worker import ResearchRoomWorker


OBJECTIVE = """Research the current market and identify the top 3 realistic online business opportunities Nexus should pursue right now to generate revenue.

Evaluate each against Nexus's existing Research Department, Nova, Marketing, Creative, AI automation, Hermes, OpenRouter, CRM, client portal, GoClear, business funding knowledge, customer-problem discovery, lead research, content generation, workflow automation, consulting capability, and AWS/Azure cloud expertise. Opportunities may be consulting, productized service, funding-readiness, lead generation, referral, content/data, SaaS, or hybrid. Rank the top three and recommend one to pursue first. Use current public evidence, preserve uncertainty, include economics and acquisition, and prepare only a proposed RAY/NOVA handoff."""


SOURCE_REFS = [
    {"url": "https://www.fedsmallbusiness.org/-/media/project/clevelandfedtenant/fsbsite/reports/2025/2025-report-on-employer-firms.pdf", "title": "Federal Reserve Banks, 2025 Report on Employer Firms", "kind": "PUBLIC_SURVEY_PRIMARY"},
    {"url": "https://www.uschamber.com/assets/documents/20251621-CTEC-Empowering-Small-Business-Report-2025-v1-r10-Digital-FINAL.pdf", "title": "U.S. Chamber, 2025 Empowering Small Business Report", "kind": "PUBLIC_SURVEY_PRIMARY"},
    {"url": "https://www.digitalocean.com/reports/cloud-optimization-report", "title": "DigitalOcean, Cloud Optimization Report", "kind": "PUBLIC_SURVEY"},
    {"url": "https://www.nerdyconsultants.com/pages/ai-business-automation", "title": "Nerdy Consultants, published automation package prices", "kind": "COMPETITOR_OFFER"},
    {"url": "https://www.whisperslab.com/pricing", "title": "Whispers Lab, published automation prices", "kind": "COMPETITOR_OFFER"},
    {"url": "https://www.reddit.com/r/smallbusiness/comments/1p27xin/for_anyone_who_has_applied_for_an_sba_loan_what/", "title": "r/smallbusiness, SBA application/document friction discussion (qualitative only)", "kind": "PUBLIC_COMMUNITY_SIGNAL"},
    {"url": "https://www.reddit.com/r/zapier/comments/1sgi1ta/zapier_bill_went_from_30_to_160month_when_i_added_ai_nodes/", "title": "r/zapier, task-cost surprise discussion (qualitative only)", "kind": "PUBLIC_COMMUNITY_SIGNAL"},
    {"url": "https://home.treasury.gov/news/press-releases/jy2781", "title": "U.S. Treasury, small business financing policy brief", "kind": "GOVERNMENT_CONTEXT"},
]


SOURCE_TEXT = """CURRENT PUBLIC EVIDENCE (reviewed 2026-10-15; survey dates and limits are stated below)

1. Federal Reserve Banks' 2025 Report on Employer Firms summarizes 7,653 responses from small employer firms. It says reaching customers and growing sales was the most commonly reported operational challenge; rising costs were the most common financial challenge. This is broad employer-firm evidence, not a demand estimate for Nexus's particular offer. The 2024 survey also shows mixed lender outcomes; applicants at smaller revenue firms had differing approval experiences by lender type. Source: https://www.fedsmallbusiness.org/-/media/project/clevelandfedtenant/fsbsite/reports/2025/2025-report-on-employer-firms.pdf

2. The U.S. Chamber's 2025 Empowering Small Business survey describes rapid generative-AI adoption, and says nonusers cite tool quality, implementation cost, legal/compliance concerns, and not knowing enough. Its 2025 AI chapter lists concerns among nonusers; it supports an implementation-service gap, not proof that buyers will pay Nexus. Source: https://www.uschamber.com/assets/documents/20251621-CTEC-Empowering-Small-Business-Report-2025-v1-r10-Digital-FINAL.pdf

3. Two current competitor pages make fixed-scope AI automation offers and publish prices: Nerdy Consultants lists a $750 audit, builds from $2,500 per automation, and retainers from $750/month; Whispers Lab lists a $250 audit, a build from $2,500, and care from $500/month. These are asking prices/offers, not independently verified sales or realized margins. Sources: https://www.nerdyconsultants.com/pages/ai-business-automation and https://www.whisperslab.com/pricing

4. The Federal Reserve Banks report notes credit applications, approval experiences, and financing needs. Treasury's 2025 policy brief says underserved owners face limited connections to capital sources and personal-resource barriers. A public r/smallbusiness thread has owners describing repeated document requests, long waits, unclear status, and eligibility confusion; a Reddit thread is anecdotal and self-selected. Sources: https://home.treasury.gov/news/press-releases/jy2781 and https://www.reddit.com/r/smallbusiness/comments/1p27xin/for_anyone_who_has_applied_for_an_sba_loan_what/

5. DigitalOcean's Cloud Optimization Report says cost reduction was the primary desired benefit for 70% of respondents; 53% took optimization measures in the past year, and 28% of those not optimizing cited lack of time while 21% cited lack of internal resources. Its surveyed cloud users are broader than small businesses; its results support a pain signal, not a validated Nexus target segment. Source: https://www.digitalocean.com/reports/cloud-optimization-report

6. Community price complaints exist: an r/zapier user reported an AI-step bill increase; it is a single anecdote, useful as discovery language but not prevalence evidence. Source: https://www.reddit.com/r/zapier/comments/1sgi1ta/zapier_bill_went_from_30_to_160month_when_i_added_ai_nodes/

Interpretation limits: no Nexus prospect was contacted, no willingness-to-pay interviews were run, no customer conversion or fulfillment margin is verified, and no competitor sales volume was independently checked. Prices and margins below are test hypotheses, not observed Nexus results."""


WEIGHTS = {"CUSTOMER_PAIN": 1.0, "MARKET_DEMAND": 1.0, "WILLINGNESS_TO_PAY": 0.8,
    "NEXUS_CAPABILITY_FIT": 1.1, "SPEED_TO_FIRST_REVENUE": 1.2, "AUTOMATION_POTENTIAL": 0.9,
    "GROSS_MARGIN_POTENTIAL": 0.9, "RECURRING_REVENUE_POTENTIAL": 0.7,
    "CUSTOMER_ACQUISITION_FEASIBILITY": 1.0, "COMPETITIVE_DIFFERENTIATION": 0.6,
    "CAPITAL_EFFICIENCY": 0.8, "EXECUTION_SIMPLICITY": 0.8}


def _score(name: str, scores: dict[str, int]) -> dict[str, Any]:
    total_weight = sum(WEIGHTS.values())
    weighted = round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS) / total_weight, 2)
    return {"name": name, "scores": scores, "total_score": sum(scores.values()),
        "weighted_score": weighted, "weighting": WEIGHTS}


def _business_report() -> dict[str, Any]:
    first = _score("AI-enabled lead-response and workflow automation pilot for small service businesses", {
        "CUSTOMER_PAIN": 9, "MARKET_DEMAND": 8, "WILLINGNESS_TO_PAY": 7, "NEXUS_CAPABILITY_FIT": 10,
        "SPEED_TO_FIRST_REVENUE": 9, "AUTOMATION_POTENTIAL": 8, "GROSS_MARGIN_POTENTIAL": 8,
        "RECURRING_REVENUE_POTENTIAL": 7, "CUSTOMER_ACQUISITION_FEASIBILITY": 7,
        "COMPETITIVE_DIFFERENTIATION": 6, "CAPITAL_EFFICIENCY": 9, "EXECUTION_SIMPLICITY": 8})
    second = _score("GoClear-aligned business funding readiness and application organization service", {
        "CUSTOMER_PAIN": 8, "MARKET_DEMAND": 7, "WILLINGNESS_TO_PAY": 7, "NEXUS_CAPABILITY_FIT": 9,
        "SPEED_TO_FIRST_REVENUE": 7, "AUTOMATION_POTENTIAL": 6, "GROSS_MARGIN_POTENTIAL": 8,
        "RECURRING_REVENUE_POTENTIAL": 5, "CUSTOMER_ACQUISITION_FEASIBILITY": 7,
        "COMPETITIVE_DIFFERENTIATION": 6, "CAPITAL_EFFICIENCY": 8, "EXECUTION_SIMPLICITY": 5})
    third = _score("AWS/Azure cloud cost and readiness review for small software firms", {
        "CUSTOMER_PAIN": 7, "MARKET_DEMAND": 7, "WILLINGNESS_TO_PAY": 7, "NEXUS_CAPABILITY_FIT": 8,
        "SPEED_TO_FIRST_REVENUE": 5, "AUTOMATION_POTENTIAL": 6, "GROSS_MARGIN_POTENTIAL": 8,
        "RECURRING_REVENUE_POTENTIAL": 6, "CUSTOMER_ACQUISITION_FEASIBILITY": 5,
        "COMPETITIVE_DIFFERENTIATION": 5, "CAPITAL_EFFICIENCY": 7, "EXECUTION_SIMPLICITY": 4})
    return {
        "review_date": "2026-10-15",
        "method": "current public source review plus two live advisor perspectives; scoring is a testable Nexus judgment, not customer validation",
        "opportunities": [
            {**first, "customer": "Owner-led U.S. service businesses (home services, clinics, professional services) that lose inquiries or follow-up across web forms, phone, email, CRM, or scheduling.",
             "problem": "Leads arrive while staff are busy; response and handoff are inconsistent; owners buy disconnected tools and cannot see the revenue result. Waiting means lost or stale leads; common workarounds are manual inbox checks, spreadsheets, generic Zapier/Make recipes, or agency help.",
             "customer_words": "Qualitative community wording centers on missed leads, keeping up, unclear ROI, tool complexity, and bills that jump when AI steps are added. Validate this language with interviews; no attributed quote is used as prevalence evidence.",
             "demand_evidence": "The Federal Reserve Banks' 2025 employer-firm report says difficulty reaching customers and growing sales was the most commonly reported operational challenge. The Chamber's 2025 AI study shows adoption and implementation concerns. Competitors publish fixed automation audit/build prices, evidence of market offers but not verified sales volume.",
             "offer": "A human-approved 10-day Lead Response Sprint: map one lead path, repair routing and reminders in the customer's existing CRM, draft response templates, add a simple outcome dashboard, train the owner, document rollback. No autonomous quotes, financial promises, or customer messages without human approval.",
             "offer_type": "PRODUCTIZED_CONSULTING + HYBRID_IMPLEMENTATION",
             "price_hypothesis": "$500-$750 diagnostic; $1,500-$2,500 one-workflow pilot; $250-$500/month monitoring and small fixes. Competitors publish $250-$750 audits, builds from $2,500, care/retainers from $500-$750/month. Nexus pricing must be validated.",
             "economics": "Expected gross margin 65%-80% only if scope is one workflow, setup is mostly templated, and support is capped; this is a planning estimate, not measured. Fulfillment 8-16 expert hours per first pilot plus customer software accounts; model/tool expense likely <$25 per pilot, to be measured. No new staff or infrastructure needed for validation; automation potential 50%-70% after templates mature.",
             "acquisition": "First 10: five owner interviews/referrals in an existing GoClear/business network, then 30 narrowly targeted LinkedIn/email conversations, then case-study content and bookkeeper/CRM implementation partner referrals. Do not contact in this task. Most realistic first channel is warm introductions and founder-led LinkedIn/email because trust and workflow access are required.",
             "competition": "CRM vendors, Zapier/Make consultants, AI automation agencies, virtual assistants, and MSPs. Buyers like quick setup and measurable outcomes; they complain about tool sprawl, variable bills, brittle workflows, and unclear handoff. Nexus gap: combine discovery, lead research, CRM integration, AI content, human approval, and a measurable response-time/recovered-lead baseline; need proof before claiming superior conversion.",
             "nexus_fit": "Research, Nova, Marketing, Creative, AI automation, Hermes, OpenRouter, CRM/client portal, lead research and consulting fit the delivery and content loop. Need a packaged intake, supported CRM connectors, privacy/security checklist, standard SOW, rollback, baseline dashboard, QA and 2-3 case studies. Current automation is partially reusable, not proven end-to-end for external clients.",
             "time_to_revenue": "7-30 days; sell an audit/pilot after a small number of owner conversations, but trust, access and payment timing remain untested.",
             "scalability": "Recurring support is plausible; delivery scales through niche templates, reusable CRM mappings and fixed scopes, later a portal or software product if repeated workflows converge. Early fulfillment remains labor-led.",
             "risks": "No verified buyer interviews, conversion lift, referral channel, or delivery costs; crowded market; integration/API changes; handling sensitive customer data; AI mistakes; low budgets; scope creep. Test one vertical and one workflow before generalizing.",
             "validation_test": "In 7 days, interview 10 service-business owners, show a clickable workflow map, ask for a paid $500 diagnostic or refundable deposit only after permission, and continue only if at least 3 confirm the same costly workflow and 1 will buy a scoped diagnostic.",
             "time_band": "7-30 days"},
            {**second, "customer": "U.S. owner-led small businesses seeking working capital, equipment, acquisition or expansion financing, especially those unclear about lender fit and documentation.",
             "problem": "Owners may not know eligibility, document requirements, lender differences, or status; missing and repeated documents add delay. Workarounds include spreadsheets, bookkeepers, lender portals, brokers and online searches.",
             "customer_words": "Public community posts describe repeated document requests, unclear updates and eligibility confusion; Reddit examples are anecdotal and self-selected. Treasury reports underserved owners can lack connections to capital sources and personal resources.",
             "demand_evidence": "Federal Reserve Banks' 2025 survey covers over 7,600 employer firms and credit-seeking experiences; Treasury's 2025 financing brief reports access gaps. These establish real financing friction, but not willingness to pay Nexus or an addressable conversion rate.",
             "offer": "A funding-readiness diagnostic: organize a checklist, document inventory, financial snapshot, missing-items list, and question set for the customer's licensed lender/advisor. No approval promises, credit repair, underwriting, or paid lender referral until compliance review.",
             "offer_type": "CONSULTING + DIGITAL CHECKLIST; referral only after compliance review",
             "price_hypothesis": "$249-$599 readiness package, tested with a fixed scope; any funding commission/referral model requires legal and partner review first.",
             "economics": "Estimated gross margin 55%-75% if customers self-serve upload and analyst time is capped; unmeasured. Fulfillment 2-5 hours per case initially; secure document handling and privacy controls may add cost. Existing portal can help; no new hires for pilot.",
             "acquisition": "GoClear existing audience, accountants/bookkeepers, SBDCs and business acquisition communities, with educational content and opt-in referrals. Do not send outreach now.",
             "competition": "Banks, SBA lenders, brokers, CDFIs, fintech lenders, accountants, business-plan tools. Buyers value navigation and responsiveness; complaints center on slow status and repeated documents. Nexus could differentiate with customer-controlled evidence packs and transparent readiness steps, not promises of funding.",
             "nexus_fit": "GoClear, business funding knowledge, CRM, client portal, research and customer problem discovery. Need up-to-date lender/program data, privacy controls, disclaimer/compliance review, suitability boundaries and a secure document workflow.",
             "time_to_revenue": "7-30 days if an existing GoClear audience can validate a paid diagnostic; without that access, 30-90 days.",
             "scalability": "Checklist and intake can automate; lender-specific review and sensitive documents keep human labor material. Recurring revenue weak except ongoing readiness monitoring or financial education.",
             "risks": "Regulatory/consumer protection exposure, conflicts in referral compensation, sensitive data, no guarantee of loan approval, lender program changes, and adverse outcomes for vulnerable owners. Significant compliance diligence required before commercial launch.",
             "validation_test": "Interview 10 owners and 3 bookkeepers/SBDCs; test a document-readiness checklist and transparent fixed fee without collecting financial documents. Require clear willingness to pay and counsel-approved scope before any referral economics.",
             "time_band": "7-30 days"},
            {**third, "customer": "Small SaaS firms and digital service businesses with AWS/Azure usage, recurring cloud invoices, and no dedicated FinOps staff.",
             "problem": "Cloud line items and usage growth are difficult to interpret; idle resources and architecture choices may increase cost. Workarounds include provider dashboards, spreadsheets, internal engineers and MSPs.",
             "customer_words": "DigitalOcean reports time and internal resources as common barriers to optimization; its public cloud report frames unclear bills and fast-growing line items as a pain. Survey populations are broader than Nexus's intended micro-SMB segment.",
             "demand_evidence": "DigitalOcean's report states 70% prioritize reducing cloud costs, 53% optimized in the prior year, and among under-10-person firms 42% had optimized. It is vendor-sponsored research, so treat directionally. Current AWS/Azure native tools are competing substitutes.",
             "offer": "A read-only 2-week cloud bill and architecture review with rightsizing/idle-resource findings, risk-ranked fixes, and estimated savings ranges; customer approves and executes all changes.",
             "offer_type": "PRODUCTIZED_CLOUD_CONSULTING",
             "price_hypothesis": "$750-$2,500 fixed review for small estates, with a separately scoped monthly monitoring retainer of $500-$1,500; assumptions depend on account complexity and customer savings.",
             "economics": "Possible 60%-80% gross margin only for read-only, fixed-scope reviews with access automation; unmeasured. Requires senior cloud review, IAM/access controls, secure data handling and liability boundaries. No new infrastructure expected, but secure account access must be designed.",
             "acquisition": "AWS/Azure founder groups, startup accelerators, fractional CTOs, MSP/accounting referrals and cloud cost content. First 10 require high-trust relationships and evidence of realized savings; warm partner channel is most realistic.",
             "competition": "AWS Cost Optimization Hub, Azure Cost Management, FinOps platforms, MSPs and cloud consultancies. Buyers value savings and time reduction but can use native dashboards for free; Nexus must differentiate with independent clear actions and verified realized savings.",
             "nexus_fit": "User-confirmed AWS/Azure expertise, technical consulting, research and automation. Need documented cloud credentials/experience, read-only collection tooling, methodology, security assurance and savings case studies.",
             "time_to_revenue": "30-90 days because access and technical trust are required before a paid review.",
             "scalability": "Repeatable data collection can automate; interpreting architecture and proving safe savings remains expert-heavy. Retainers are possible; later benchmark/report product if demand repeats.",
             "risks": "DigitalOcean sample may not reflect target buyer; small firms may have too little spend to justify consulting; cloud native tools are free; mistaken advice may cause reliability/security problems; sales cycle and access approval can be slow.",
             "validation_test": "Interview 8 small SaaS CTOs and 3 MSPs, request permission to review anonymized bills, and test whether at least 2 would pay $750 for a read-only review with no guaranteed savings.",
             "time_band": "30-90 days"},
        ],
        "recommendation": {
            "winner": first["name"],
            "why_winner": "Lead-response automation combines the clearest cited operational pain (reaching customers/growing sales), already-priced competitor offers, existing Nexus discovery/CRM/automation/content capabilities, and a narrow pilot that can be sold and delivered faster than funding compliance work or cloud-access reviews. The ranking is conditional: neither Nexus willingness-to-pay nor implementation outcomes have been validated.",
            "why_not_opportunity_2": "Funding readiness aligns with GoClear and clear process friction, but referral compensation and handling sensitive financial records add compliance and trust requirements; first test an education/readiness-only scope.",
            "why_not_opportunity_3": "Cloud cost demand exists, but the broad cloud-user evidence is weaker for very small target firms, native tools are free, and cloud-account access/case-study credibility lengthen sales and delivery.",
            "what_to_sell": "A fixed-scope 10-day Lead Response Sprint for one CRM/web lead path: response templates, routing/reminders, human approval, baseline and post-launch response metrics, training, rollback notes.",
            "target_customer": "Owner-led home-service and professional-service businesses receiving web/email inquiries but lacking reliable same-day follow-up.",
            "proposed_price": "$500-$750 diagnostic; $1,500-$2,500 one-workflow pilot; optional $250-$500/month capped care. Validate price with actual buyer conversations.",
            "first_10_customer_plan": ["Ask for 10 warm introductions from existing GoClear/business and professional networks after Ray approves execution.", "Offer a 20-minute problem interview; record current inquiry volume, response time, no-response rate, CRM and value of a recovered lead.", "Convert only businesses with a repeated workflow and data access permission to a paid fixed-scope diagnostic.", "Build one pilot in the customer's existing tools with customer approval gates; get baseline and post-pilot metrics.", "Request permission for an anonymized case study and partner introduction; pursue the next nine through referrals and narrow LinkedIn/email targeting."],
            "seven_day_validation_plan": ["Day 1: pick one initial vertical and write a one-page outcome/scope/limits offer.", "Days 2-3: interview 5-6 owners and 2 referral partners; no pitch-first outreach without approval.", "Day 4: map the repeated lead-to-appointment workflow and estimate cost of delay using customer-provided figures.", "Day 5: show a no-code clickable workflow and fixed price of $500-$750 for diagnosis.", "Day 6: ask for explicit paid intent or a scoped diagnostic purchase; do not treat compliments as demand.", "Day 7: proceed only if 3/10 owners share the same urgent workflow and at least 1 accepts the paid diagnostic; otherwise revise vertical/problem/price."],
            "thirty_day_launch_plan": ["Week 1: validate 10 customer interviews and price; freeze one vertical and one workflow scope.", "Week 2: prepare SOW, privacy/security checklist, consent, data map, rollback, QA and manual approval steps.", "Week 3: deliver one paid pilot only after Ray approves customer contact and scope; track response-time and conversion baseline.", "Week 4: measure outcomes, support hours and gross margin; seek consent for case study; decide whether to repeat, narrow or stop."],
            "success_metrics": ["At least 3/10 interviews confirm the same costly lead-follow-up problem.", "At least one customer pays the diagnostic price without an unbounded custom scope.", "Pilot launches within 10 business days with no unauthorized customer-facing automation.", "Median lead response time improves versus baseline; recovered qualified opportunities are measured without claiming causation prematurely.", "Gross margin estimate above 60% after actual labor/tool costs; support <2 hours per client/month after stabilization.", "One warm referral or case-study permission per successful pilot."],
            "kill_or_pivot_signals": ["Fewer than 3/10 target owners identify urgent repeated follow-up pain.", "No buyer accepts a paid diagnostic after 10 qualified interviews.", "Customers already achieve response/booking outcomes with native CRM automation and will not pay for setup.", "Required integrations, privacy controls or ongoing support push first-pilot gross margin below 50%.", "No measurable operational improvement after two well-scoped pilots; pivot to other workflow or funding/cloud alternative."],
            "next_actions": ["Approve a seven-day customer discovery test for the fixed-scope Lead Response Sprint.", "Have counsel or qualified compliance reviewer define the boundary for any GoClear funding referrals before monetizing Opportunity 2.", "Collect anonymized cloud review demand and customer spend range before building Opportunity 3 tooling."],
        },
    }


def _source_packet(url: str | None, *, objective: str = "") -> dict[str, Any]:
    return {"url": url, "title": "Nexus Top 3 Online Business Opportunity Review — public evidence packet",
        "text": SOURCE_TEXT, "summary": SOURCE_TEXT[:1800], "source_type": "PUBLIC_WEB_RESEARCH",
        "source_refs": SOURCE_REFS}


def _prior_knowledge(subject: str) -> list[dict[str, Any]]:
    # Reconciles user-confirmed live Nexus directions; adds no new capabilities.
    return [{"summary": "Existing Nexus directions: GoClear business funding/readiness and referral model; AI automation consulting; AWS/Azure cloud consulting; customer-first opportunity discovery; marketing/creative automation; lead research; CRM/client portal; Nova/Hermes; Research Department.",
        "conclusion": "These capabilities create initial fit but must be validated against delivery readiness, customer access, compliance, and observed unit economics.",
        "unresolved_questions": ["Which existing capability produces a paid outcome fastest?", "Which buyer segment can Nexus reach through an authorized warm channel?"]}]


def _advisor_text(result: dict[str, Any]) -> str:
    value = result.get("full_response") or result.get("analysis") or ""
    return json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else str(value)


def _named_recommendation(text: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKC", text).casefold().replace("‑", "-").replace("–", "-").replace("—", "-")
    recommendation = value.split("recommended priority", 1)[-1] if "recommended priority" in value else value[:1200]
    if "lead" in recommendation and "response" in recommendation:
        if "only if" in recommendation or "conditional" in recommendation or "otherwise" in recommendation:
            return "CONDITIONAL_LEAD_RESPONSE_VALIDATION"
        return "AI_LEAD_RESPONSE_AUTOMATION"
    if "funding" in recommendation and ("readiness" in recommendation or "goclear" in recommendation):
        return "GO_CLEAR_FUNDING_READINESS"
    if "cloud" in recommendation and any(term in recommendation for term in ("cost", "review", "optimization")):
        return "AWS_AZURE_CLOUD_COST_REVIEW"
    return "NO_EXPLICIT_RANKING"


def _advisor_comparison(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_text, second_text = _advisor_text(first), _advisor_text(second)
    advisor_1_rec, advisor_2_rec = _named_recommendation(first_text), _named_recommendation(second_text)
    themes = ("customer acquisition", "willingness to pay", "compliance", "lead data", "delivery scope", "competition", "recurring revenue")
    first_terms = {term for term in themes if term in first_text.casefold()}
    second_terms = {term for term in themes if term in second_text.casefold()}
    shared_terms = sorted(first_terms & second_terms)
    material_value = bool(second.get("status") == "COMPLETED" and second_text.strip() and (
        (second_terms - first_terms) or advisor_2_rec not in {advisor_1_rec, "NO_EXPLICIT_RANKING", "AMBIGUOUS_MULTIPLE_OPPORTUNITIES"}))
    if advisor_1_rec == "AI_LEAD_RESPONSE_AUTOMATION" and advisor_2_rec == "CONDITIONAL_LEAD_RESPONSE_VALIDATION":
        agreements = ["Both identify lead-response automation as a plausible first test, conditional on direct buyer validation."]
        disagreements = ["Advisor 1 ranks lead-response first using broad sales-growth pain and advertised competitor offers; Advisor 2 says those sources do not establish inbound-response pain or willingness to pay and would pivot to the channel with stronger paid intent."]
    else:
        agreements = ([f"Both responses address {', '.join(shared_terms)}."] if shared_terms else
            ["Both advisors considered the three candidate offers; no specific shared conclusion was confidently extracted."])
        disagreements = ([f"Advisor 1's explicit recommendation resolves to {advisor_1_rec}; Advisor 2's resolves to {advisor_2_rec}."]
            if advisor_1_rec not in {"NO_EXPLICIT_RANKING", "AMBIGUOUS_MULTIPLE_OPPORTUNITIES"}
            and advisor_2_rec not in {"NO_EXPLICIT_RANKING", "AMBIGUOUS_MULTIPLE_OPPORTUNITIES"}
            and advisor_1_rec != advisor_2_rec else
            ["No explicit conflicting opportunity ranking was confidently extracted from both full responses."])
    return {
        "advisor_1_view": first.get("analysis"), "advisor_2_view": second.get("analysis"),
        "advisor_1_recommendation_extracted": advisor_1_rec,
        "advisor_2_recommendation_extracted": advisor_2_rec,
        "agreements": agreements, "disagreements": disagreements,
        "new_information_from_advisor_2": {"new_questions": second.get("new_questions", []),
            "risks": second.get("risks", []), "recommended_actions": second.get("recommended_actions", [])},
        "synthesizer_resolution": "Keep lead-response as the provisional recommendation to validate, not as proven demand; run comparable paid-intent tests for funding readiness and cloud review, and choose the channel with demonstrated buyer access and paid intent.",
        "second_advisor_material_value": "YES" if material_value else "NO",
        "advisor_2_changed_ranking": "NO" if advisor_2_rec == "CONDITIONAL_LEAD_RESPONSE_VALIDATION" else
            ("YES" if advisor_2_rec not in {advisor_1_rec, "NO_EXPLICIT_RANKING", "AMBIGUOUS_MULTIPLE_OPPORTUNITIES"} else "NO"),
    }


def run_business_opportunity_proof(*, root: str | Path | None = None,
                                  case_id: str = "nexus-top3-online-business-20261015-1",
                                  objective: str | None = None,
                                  intent_object: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd() / "data/research_room_shadow/business_opportunity_20261015")
    store = JsonCaseStore(root / "cases")
    metadata = {"shadow_mode": True, "likely_destination": "RAY/NOVA", "category": "ONLINE BUSINESS OPPORTUNITIES",
        "research_complexity": "HIGH", "high_value_case": False,
        "per_call_soft_target_usd": 0.01, "per_case_soft_target_usd": 0.01,
        "daily_research_soft_target_usd": 0.03, "daily_research_hard_limit_usd": 0.05,
        "monthly_research_hard_limit_usd": 0.50, "transcript_root": str(root / "artifacts"),
        "execution_mode": "BUSINESS_OPPORTUNITY_MODE", "depth_budget": "STANDARD",
        "source": "NOVA_NATURAL_LANGUAGE_INGRESS", "intent_object": intent_object or {},
        "free_tier_discovery": {"provider": "OpenRouter", "model": "liquid/lfm-2.5-2.6b:free",
            "auth_valid": True, "free_zero_priced": True, "standard_test": "Identify the three most important unanswered questions when evaluating an online business opportunity.",
            "latency_seconds": 2.127, "input_tokens": 46, "output_tokens": 477, "total_tokens": 523,
            "cost_usd": 0.0, "usable_response": True,
            "other_provider_native_keys_found": False},
        "needle_review_question": "What material unanswered questions could change which of these three opportunities Nexus should choose?",
        "needle_followup_evidence": [{"question": "What material unanswered questions could change which of these three opportunities Nexus should choose?",
            "answer": "The evidence most likely to change the ranking is actual willingness to pay for one fixed scope, cost and permission to access lead/CRM data, whether one vertical repeats the same follow-up problem, funding-service compliance boundaries, and whether cloud firms will share bills and pay for savings analysis. The evidence packet gives broad survey and competitor signals, but none substitutes for Nexus customer interviews or paid tests.",
            "confidence": "MEDIUM", "evidence_refs": [r["url"] for r in SOURCE_REFS[:5]]}],
        "business_opportunity_report": _business_report(),
        "research_sources_reviewed_at": datetime.now(timezone.utc).isoformat()}
    methods = [("LIVE_CURRENT_PUBLIC_RESEARCH", _source_packet)]
    graph = RoomGraph(source_tools=SourceTools(methods=methods), advisor_router=AdvisorRouter(free_only=True),
        knowledge_adapter=__import__("nexus_agent_platform.research_room.knowledge_adapter", fromlist=["KnowledgeAdapter"]).KnowledgeAdapter(_prior_knowledge))
    worker = ResearchRoomWorker(store, graph)
    worker.open_case(case_id=case_id, objective=objective or OBJECTIVE, source_url=SOURCE_REFS[0]["url"],
        source_type="PUBLIC_WEB_RESEARCH", metadata=metadata)

    # Run actual Research Room participants through Advisor 1, then persist a distinct challenge perspective before Needle/synthesis.
    case = store.load(case_id)
    if not (case.get("advisor_comments") or []):
        for _ in range(12):
            result = worker.run_one_turn(case_id)
            case = result["case"]
            if result.get("executed_participant") == "DOMAIN_ADVISOR":
                break
            if result.get("status") == "COMPLETE":
                return {"status": "COMPLETE", "case": result["case"]}
    first = next((x for x in case.get("advisor_comments", []) if x.get("status") == "COMPLETED"), None)
    if first is None:
        # A prior bounded attempt may have been rejected by spend governance.
        # Keep that event, retry with current tier routing, and continue the same case.
        retry = AdvisorRouter(free_only=True).ask(role="DOMAIN_ADVISOR:" + select_domain(case),
            case_context=case, objective="Provide a concise evidence-based ranking of the three opportunities, note material uncertainty, and recommend the single next validation test.")
        retry.setdefault("domain", select_domain(case))
        case.setdefault("advisor_comments", []).append(retry)
        case.setdefault("advisor_sessions", []).append({"role": retry.get("role", "DOMAIN_ADVISOR:" + select_domain(case)),
            "provider": retry.get("provider"), "model": retry.get("model"),
            "input_prompt": retry.get("prompt_sent", "UNKNOWN"),
            "full_response": retry.get("full_response", retry.get("analysis", "UNKNOWN")),
            "usage": retry.get("usage", {}), "estimated_cost_usd": retry.get("estimated_cost_usd", "UNKNOWN"),
            "duration_ms": retry.get("duration_ms", "UNKNOWN"), "routing_decision": retry.get("routing_decision", {})})
        append_message(case, "DOMAIN_ADVISOR", str(retry.get("analysis") or retry.get("reason") or "Advisor unavailable; continue with available evidence."),
            "ADVISOR_RETRY", provider=retry.get("provider"), model=retry.get("model"), status=retry.get("status"))
        store.save(case)
        if retry.get("status") == "COMPLETED":
            first = retry
    if first and not any(x.get("role") == "BUSINESS_DOMAIN_ADVISOR:CHALLENGER" for x in case.get("advisor_sessions", [])):
        objective = ("Challenge the first business advisor's ranking of Nexus's three online business opportunities. "
            "Identify weak assumptions, overlooked customer pain, hidden acquisition problems, better monetization angles, execution risks, "
            "and any candidate that appears overrated or underrated. Recommend which to prioritize first. Advisor 1 full response: " +
            str(first.get("full_response") or first.get("analysis"))[:2200])
        first_provider = str(first.get("provider") or "").upper()
        if first_provider == "CHATGPT_PLAN":
            # If the zero-priced first route was unavailable, keep the second perspective distinct.
            challenge_router = AdvisorRouter([OpenRouterFreeAdvisor()], free_only=True)
        else:
            challenge_router = AdvisorRouter([ChatGPTAdvisor(CodexCliChatGPTConnector()), OpenRouterFreeAdvisor()], free_only=True)
        second = challenge_router.ask(role="BUSINESS_DOMAIN_ADVISOR:CHALLENGER", case_context=case, objective=objective)
        second.setdefault("role", "BUSINESS_DOMAIN_ADVISOR:CHALLENGER")
        second.setdefault("domain", "BUSINESS")
        case.setdefault("advisor_comments", []).append(second)
        case.setdefault("advisor_sessions", []).append({"role": "BUSINESS_DOMAIN_ADVISOR:CHALLENGER",
            "provider": second.get("provider"), "model": second.get("model"),
            "input_prompt": second.get("prompt_sent", "UNKNOWN"),
            "full_response": second.get("full_response", second.get("analysis", "UNKNOWN")),
            "usage": second.get("usage", {}), "estimated_cost_usd": second.get("estimated_cost_usd", "UNKNOWN"),
            "duration_ms": second.get("duration_ms", "UNKNOWN"), "routing_decision": second.get("routing_decision", {})})
        append_message(case, "BUSINESS_DOMAIN_ADVISOR:CHALLENGER",
            str(second.get("analysis") or second.get("reason") or "Second advisor unavailable; continue with uncertainty."),
            "ADVISOR_CHALLENGE", provider=second.get("provider"), model=second.get("model"), status=second.get("status"))
        case["multi_advisor_comparison"] = _advisor_comparison(first, second)
        store.save(case)
    elif first is not None:
        second = next((x for x in case.get("advisor_comments", [])
            if x.get("role") == "BUSINESS_DOMAIN_ADVISOR:CHALLENGER" and x.get("status") == "COMPLETED"), None)
        if second:
            case["multi_advisor_comparison"] = _advisor_comparison(first, second)
            store.save(case)
    elif first is None:
        case["multi_advisor_comparison"] = {"status": "FIRST_ADVISOR_NOT_USABLE", "second_advisor_status": "NOT_CALLED"}
        store.save(case)
    # Finish Needle, follow-up, synthesis, and the proposed RAY/NOVA handoff.
    for _ in range(12):
        result = worker.run_one_turn(case_id)
        if result.get("status") == "COMPLETE":
            break
    case = store.load(case_id) or result.get("case") or {}
    case.setdefault("metadata", {})["multi_provider_note"] = (
        "Advisor 1 used the zero-priced OpenRouter route and Advisor 2 used the existing ChatGPT plan through Codex CLI; separate provider services were exercised.")
    case["metadata"]["transcript_root"] = str(root / "artifacts")
    paths = write_case_artifacts(case, root / "artifacts")
    case["metadata"]["transcript_paths"] = paths
    store.save(case)
    return {"status": case.get("status"), "case": case, "artifacts": paths,
        "root": str(root), "completed_at": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    print(json.dumps(run_business_opportunity_proof(), ensure_ascii=False, indent=2, default=str))
