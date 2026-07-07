#!/usr/bin/env python3
"""
Alpha Opinion Advisor — Outside perspective brain for Nexus OS.

Alpha gives independent opinion, critique, and strategic advice.
Not research-first. Not command-first. Not work-order-first.

Use known context first. Research only when needed or explicitly asked.
"""

import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "telegram"))


def load_conversation_context():
    """Load conversation context from disk."""
    path = os.path.join(os.path.dirname(__file__), "..", "telegram", "..", "data", "runtime", "telegram_conversation_context.json")
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def get_known_context():
    """Gather what Alpha already knows from Nexus context."""
    ctx = load_conversation_context()
    chat_ctx = ctx.get("1288928049", {})

    known = {
        "last_topic": chat_ctx.get("last_topic"),
        "last_alpha_recommendations": chat_ctx.get("last_alpha_recommendations", []),
        "last_work_order": chat_ctx.get("last_work_order_path"),
    }

    # Try to read latest operator report
    try:
        with open("reports/runtime/nexus_anytime_operator_report_latest.json") as f:
            r = json.load(f)
        known["os_score"] = r.get("system_status", {}).get("active_os_score")
        known["approvals_pending"] = r.get("approval_queue", {}).get("count", 0)
    except:
        pass

    # Try to read latest research
    try:
        with open("data/research_memory/notebooklm_scored_items_latest.json") as f:
            items = json.load(f)
        known["research_items"] = len(items)
    except:
        pass

    return known


def alpha_opinion(question, context=None):
    """
    Generate an Alpha outside opinion on a question.

    Args:
        question: Ray's question or topic
        context: Optional known context dict

    Returns:
        dict with opinion, reasoning, risks, next_move, research_needed
    """
    if context is None:
        context = get_known_context()

    question_lower = question.lower()

    # Determine topic category for opinion
    topic = _identify_topic(question_lower)

    # Build opinion based on known context
    opinion = _form_opinion(question_lower, topic, context)

    return opinion


def _identify_topic(question):
    """Identify what Ray is asking about."""
    if any(kw in question for kw in ["stripe", "payment", "billing", "checkout", "charge"]):
        return "payment_infrastructure"
    if any(kw in question for kw in ["signup", "register", "onboard", "client portal"]):
        return "client_portal"
    if any(kw in question for kw in ["landing", "public", "pages", "website", "deploy"]):
        return "public_site"
    if any(kw in question for kw in ["credit", "readiness", "fundability", "score"]):
        return "credit_readiness"
    if any(kw in question for kw in ["supabase", "database", "rls", "auth"]):
        return "infrastructure"
    if any(kw in question for kw in ["email", "resend", "notification"]):
        return "communications"
    if any(kw in question for kw in ["social", "post", "content", "marketing"]):
        return "marketing"
    if any(kw in question for kw in ["grant", "fund", "sbir", "funding"]):
        return "funding"
    if any(kw in question for kw in ["alpha", "research", "investigate"]):
        return "research"
    if any(kw in question for kw in ["hermes", "nexus", "priority", "what should"]):
        return "operations"
    return "general"


def _form_opinion(question, topic, context):
    """Form an opinion based on topic and context."""
    os_score = context.get("os_score", "?")
    approvals = context.get("approvals_pending", 0)
    last_topic = context.get("last_topic")
    recs = context.get("last_alpha_recommendations", [])

    # Build opinion based on topic
    if topic == "payment_infrastructure":
        return _opinion_payment(question, context)
    elif topic == "client_portal":
        return _opinion_client_portal(question, context)
    elif topic == "public_site":
        return _opinion_public_site(question, context)
    elif topic == "credit_readiness":
        return _opinion_credit_readiness(question, context)
    elif topic == "infrastructure":
        return _opinion_infrastructure(question, context)
    elif topic == "operations":
        return _opinion_operations(question, context)
    elif topic == "marketing":
        return _opinion_marketing(question, context)
    elif topic == "funding":
        return _opinion_funding(question, context)
    else:
        return _opinion_general(question, context)


def _opinion_payment(question, context):
    os_score = context.get("os_score", "?")
    return {
        "opinion": "I would not wire Stripe until the signup flow is live and tested. Payment infrastructure without clients reaching it is premature optimization.",
        "why": "The $97 readiness review needs a working signup before a working payment gate. GoClear's public pages are built but the funnel is not connected end-to-end.",
        "what_nexus_misses": "Stripe is ready technically, but the client-facing path does not exist yet. You need the front door before the cash register.",
        "risk": "If you wire Stripe first, you will have a payment page nobody can reach. That wastes development time and creates false confidence.",
        "better_option": "Get GoClear public pages live → test signup → then wire Stripe to the actual flow.",
        "research_needed": False,
        "next_move": "Publish GoClear public pages, verify signup works in browser, then connect Stripe.",
    }


def _opinion_client_portal(context, _):
    return {
        "opinion": "The client portal shell is built but still uses mock data. This is the right priority — clients need to see real data before you charge them.",
        "why": "A portal with fake data erodes trust. Real Supabase queries make the portal actually useful.",
        "what_nexus_misses": "The mock data is a placeholder, not a product. Replace it before showing clients.",
        "risk": "Showing clients mock data looks unfinished. Better to delay than deliver something that looks like a demo.",
        "better_option": "Wire real Supabase queries first, then add features on top of real data.",
        "research_needed": False,
        "next_move": "Replace clientPortalData with Supabase queries for the authenticated user.",
    }


def _opinion_public_site(context, _):
    return {
        "opinion": "The GoClear pages are built and polished. The only blocker is the stale Netlify deploy. This should be live already.",
        "why": "The pages exist, the code is correct, the only issue is deployment. This is a quick win that unblocks everything downstream.",
        "what_nexus_misses": "Nothing. This is ready to ship.",
        "risk": "Every day these pages are not live is a day clients cannot find GoClear.",
        "better_option": "Redeploy Netlify now. The alpha-url-review fix already cleared the deploy blocker.",
        "research_needed": False,
        "next_move": "Trigger Netlify deploy and verify pages are live.",
    }


def _opinion_credit_readiness(context, _):
    return {
        "opinion": "The Credit Readiness Checklist is the right lead magnet. It is faster, cheaper, and more directly connected to the $97 readiness review than paid ads.",
        "why": "A free checklist captures emails, builds trust, and qualifies leads before they reach the paid offering.",
        "what_nexus_misses": "The checklist needs to exist as a real asset. If it is just a concept, it is not doing any work.",
        "risk": "If the checklist is generic or unclear, it will not convert. It needs to be specific to GoClear's audience.",
        "better_option": "Create a concrete 1-page checklist, connect it to email capture, then drive traffic to it.",
        "research_needed": False,
        "next_move": "Draft the checklist content and connect it to a signup form.",
    }


def _opinion_infrastructure(context, _):
    return {
        "opinion": "Supabase is working and the migration is applied. RLS is in place. The infrastructure is solid enough to build on.",
        "why": "The foundation is there. The next step is connecting the frontend to real queries, not adding more infrastructure.",
        "what_nexus_misses": "Infrastructure is not the bottleneck. Frontend wiring is.",
        "risk": "Over-engineering the backend when the frontend still uses mock data wastes time.",
        "better_option": "Focus on frontend-to-Supabase wiring. The database layer is ready.",
        "research_needed": False,
        "next_move": "Wire client portal to real Supabase queries.",
    }


def _opinion_operations(context, _):
    os_score = context.get("os_score", "?")
    approvals = context.get("approvals_pending", 0)
    return {
        "opinion": f"Nexus is running at {os_score}/100 with {approvals} pending approvals. The system is healthy. The gap is not operations — it is the client-facing funnel.",
        "why": "Operations are solid. Launchd jobs are loaded, Telegram is polling, reports are generated. What is missing is clients reaching the product.",
        "what_nexus_misses": "The internal machine works. The external funnel needs attention.",
        "risk": "Continuing to polish internals when the front door is closed delays revenue.",
        "better_option": "Shift focus from internal operations to client-facing funnel: public pages, signup, Stripe.",
        "research_needed": False,
        "next_move": "Focus on GoClear public pages → signup → Stripe wiring.",
    }


def _opinion_marketing(context, _):
    return {
        "opinion": "Marketing without a working funnel is wasted effort. Get the funnel live first, then drive traffic to it.",
        "why": "Social posts and ads need somewhere to send people. The signup and readiness review pages are that destination.",
        "what_nexus_misses": "Marketing channels are ready but the destination is not live.",
        "risk": "Driving traffic to a non-working page wastes money and damages brand.",
        "better_option": "Publish pages → verify signup → then start marketing.",
        "research_needed": False,
        "next_move": "Publish GoClear public pages before any marketing spend.",
    }


def _opinion_funding(context, _):
    return {
        "opinion": "Grants are worth exploring but not as the primary path. The $97 readiness review is faster revenue. Grants are longer-term and more competitive.",
        "why": "SBIR/STTR grants take months and require specific technical alignment. The readiness review can generate revenue this week.",
        "what_nexus_misses": "Grants are a secondary revenue stream, not the primary one. Do not let grant research distract from the core offering.",
        "risk": "Spending weeks on grant applications when the core product is not live delays revenue significantly.",
        "better_option": "Launch the core offering first, then explore grants as a parallel long-term play.",
        "research_needed": False,
        "next_move": "Focus on getting the readiness review live and generating revenue.",
    }


def _opinion_general(question, context):
    os_score = context.get("os_score", "?")
    return {
        "opinion": f"That is a reasonable question. Based on what I know about Nexus (running at {os_score}/100), here is my outside perspective.",
        "why": "I look at this from outside the operations. What matters is whether this moves the needle for GoClear's core business.",
        "what_nexus_misses": "I do not have full context on this specific topic. I can research it if you want current evidence.",
        "risk": "Without more specifics, I cannot assess the risk accurately.",
        "better_option": "Give me more context about what you are trying to achieve, and I can give a more targeted opinion.",
        "research_needed": True,
        "next_move": "Tell me more about what you are trying to decide, or say 'alpha research <topic>' for a full investigation.",
    }


def format_alpha_opinion(opinion):
    """Format an Alpha opinion for Telegram display."""
    lines = [
        "Alpha Opinion:",
        "",
        opinion["opinion"],
        "",
        f"Why: {opinion['why']}",
        "",
    ]

    if opinion.get("what_nexus_misses"):
        lines.append(f"What Nexus may be missing: {opinion['what_nexus_misses']}")
        lines.append("")

    if opinion.get("risk"):
        lines.append(f"Risk: {opinion['risk']}")
        lines.append("")

    if opinion.get("better_option"):
        lines.append(f"Better option: {opinion['better_option']}")
        lines.append("")

    lines.append(f"Next move: {opinion['next_move']}")

    if opinion.get("research_needed"):
        lines.append("")
        lines.append("Research needed? Yes — say 'alpha research <topic>' for a full investigation.")

    return "\n".join(lines)
