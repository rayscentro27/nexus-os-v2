#!/usr/bin/env python3

import argparse
import json
import random
import sys
from datetime import datetime


RESPONSE_BANK = {
    "greeting": [
        "Hey Ray. I'm here and ready. What's the move?",
        "Good to see you. What are we working on?",
        "Hello. I'm locked in. What do you need?",
        "Hey. Standing by. What's on your mind?",
        "I'm here. Let's get to work.",
    ],
    "casual": [
        "I'm good. Always on. What's up?",
        "Running at full capacity. What do you need?",
        "I don't sleep, but I'm always ready. What's on your mind?",
        "All systems operational. What's next?",
        "I'm here, focused, and ready. What are we doing?",
    ],
    "emotional": [
        "I hear you. Let's work through this together. What's the priority right now?",
        "That's valid. Let me help you untangle it. What's the most urgent thing?",
        "I understand. Let's focus on what we can control. What's the next step?",
        "You're not alone in this. Let me take some weight off. What needs attention first?",
        "That sounds heavy. Let's break it down. What's the one thing that matters most right now?",
    ],
    "partner_mode": [
        "I'm your partner in this. What do you need?",
        "Always here. What are we building?",
        "Your AI advisor, ready. What's the plan?",
        "Standing by as your co-pilot. What's next?",
        "Partner mode engaged. What's the mission?",
    ],
    "nexus_topic": {
        "synthetic_customer": [
            "The synthetic customer insert is a game-changer. It lets you simulate real user behavior through your product pipeline without waiting for actual customers. Why it matters: it de-risks your UX, onboarding, and billing flows before you go live. What it unlocks: faster iteration, cheaper testing, and proof that your product works at scale. Approval gates this from going into production. Cleanup ensures no stale data leaks into live runs.",
            "Synthetic customer is your simulation layer. You inject fake but realistic user data into the system to test every touchpoint. It matters because you catch issues before real money is on the line. It unlocks parallel testing and faster shipping. Approval is the quality gate. Cleanup keeps the data pipeline clean.",
            "Think of synthetic customer as your dress rehearsal. You run the full customer journey with synthetic data to validate that everything works end-to-end. It matters because it eliminates guesswork. It unlocks confidence in your launch. Approval is the final checkpoint. Cleanup prevents data rot.",
        ],
        "research_engine": [
            "The research engine is your opportunity scanner. It crawls, aggregates, and ranks market opportunities for you. Right now it needs the approval button wired so you can act on findings directly from the UI. Once that's connected, you can go from insight to action in one click.",
            "Research engine is your AI-powered market intelligence. It finds opportunities, scores them, and surfaces the best ones. The approval workflow is the last mile: once wired, you approve or reject candidates straight from the dashboard. That closes the loop from discovery to decision.",
            "Research engine scans the market, ranks opportunities, and hands you a shortlist. The missing piece is the approval button wiring in the UI. Until that's live, you're reviewing findings manually. Once connected, it's a one-click approve-and-act workflow.",
        ],
        "monetization": [
            "For monetization, I'd rank it: 1) Research Engine subscriptions (high value, low friction), 2) Synthetic Customer as a service (unique differentiator), 3) Advisory/consulting layer on top of both. Start with the subscription model because it's the cleanest path to recurring revenue.",
            "Monetization priority: First, package the research engine as a SaaS tool. Second, offer synthetic customer testing as a premium feature. Third, build an advisory tier. The research engine has the shortest path to paying customers because it delivers immediate, quantifiable value.",
            "Here's how I'd sequence monetization: 1) Research engine subscriptions (fastest to revenue), 2) Synthetic customer testing (highest differentiation), 3) Full-stack advisory (highest margin but requires trust). Start with the subscription and layer up.",
        ],
        "stripe": [
            "Stripe is your payment backbone. It handles subscriptions, one-time payments, and invoicing. For Nexus, you want to wire it for recurring billing on the research engine and synthetic customer tiers. Make sure you set up webhooks for payment events so your system stays in sync.",
            "Stripe integration is straightforward: set up products and prices, connect the checkout session, and handle webhooks for payment confirmation, failure, and subscription lifecycle. For Nexus, focus on subscription billing first since that's your primary revenue model.",
            "Stripe handles your payments. For Nexus, I'd set up subscription plans for the research engine and synthetic customer features. Wire webhooks so your backend knows about every payment event. Keep the checkout flow clean and minimal.",
        ],
        "resend": [
            "Resend is your transactional email layer. Use it for welcome sequences, approval notifications, payment confirmations, and system alerts. It's developer-friendly and delivers well. Make sure you set up domain verification and warm up your sending reputation before going live.",
            "Resend handles your transactional emails. Wire it for: approval notifications, payment receipts, onboarding sequences, and system alerts. Verify your domain early and monitor deliverability. It's clean, fast, and API-first.",
            "Resend is your email infrastructure. Use it for all transactional messaging: approval workflows, payment confirmations, user onboarding, and alerts. Set up domain verification, create templates, and wire webhooks for delivery tracking.",
        ],
        "approval": [
            "The approval workflow is your quality gate. For the research engine, it means you review and approve opportunities before they move forward. The UI needs the approval button wired so you can act directly from the dashboard. Right now you're doing it manually, which is fine for validation but won't scale.",
            "Approval is how you control what goes live. In the research engine, you approve candidates before they become actionable. The button needs wiring in the UI. Once connected, it's a one-step gate: review, approve, done.",
            "The approval flow is your safety net. You review synthetic customers, research candidates, and published reports before they go out. The research engine needs the approve button connected in the UI. That's the last piece before the loop is closed.",
        ],
        "credit": [
            "Credit and funding: you're bootstrapping, which means every dollar counts. Focus on revenue-generating features first. The research engine subscription is your fastest path. Keep burn low, ship fast, and let paying customers fund the next phase.",
            "For credit and funding, the strategy is clear: generate revenue before you need outside money. The research engine is your cash engine. Once it's producing MRR, you have leverage for any future raise. Until then, keep costs minimal.",
            "Funding strategy: don't raise until you have traction. The research engine subscription is your proof of concept. Get paying customers, show the numbers, then decide if you need outside capital. Bootstrapping gives you control.",
        ],
        "client": [
            "Client acquisition starts with the research engine. It's the product that solves an immediate problem. Get early users, collect feedback, iterate. The synthetic customer feature is your upsell: once they see the value, they'll want the full simulation suite.",
            "For clients: lead with the research engine. It's the quickest win. Once they're in, show them the synthetic customer capability. That's your expansion play. Focus on users who have budget and a pain point the research engine solves.",
            "Client strategy: research engine first, synthetic customer second. The research engine gets them in the door. The synthetic customer keeps them there. Build case studies from early adopters and use them to close bigger deals.",
        ],
        "opportunity": [
            "Market opportunities: the research engine is identifying them, but you need to prioritize. Look for opportunities where you have an unfair advantage: deep domain knowledge, existing relationships, or technical moats. The synthetic customer feature is itself an opportunity because almost nobody else has it.",
            "Opportunities to pursue: 1) Research engine as a service (proven demand), 2) Synthetic customer testing (unique moat), 3) Advisory for companies building similar tools. The biggest opportunity is the synthetic customer because it's differentiated and hard to replicate.",
            "Your best opportunities: the research engine fills a gap in the market for automated opportunity scanning. The synthetic customer is even bigger because it lets companies test without real users. That's a massive unlock for startups and enterprises alike.",
        ],
        "marketing": [
            "Marketing strategy: content-led growth. Publish your research findings publicly to build authority. Use the synthetic customer demos as proof of concept. Target communities where your ideal users hang out. Build in public to generate organic interest.",
            "For marketing: lead with proof. Show the research engine in action. Demo the synthetic customer pipeline. Publish case studies. Content marketing plus community engagement is your play. Don't spend on ads until you have product-market fit.",
            "Marketing approach: show, don't tell. Publish research outputs. Demo synthetic customer runs. Build in public. Let the product quality speak. Target indie hackers, startup communities, and tech Twitter. Word of mouth is your best channel right now.",
        ],
        "strategy": [
            "Strategic priorities for today: 1) Ship the approval button wiring for the research engine, 2) Run a synthetic customer test to validate the pipeline, 3) Review and prioritize the research candidates queue. Keep it tight: three things, all high-impact.",
            "Today's strategy: close the loops. Wire the approval UI, run a synthetic customer test, and push one research candidate toward action. Don't spread thin. Focus on completing the circuits that unlock the next phase.",
            "Strategy right now: focus on the approval workflow and synthetic customer validation. Those two things unlock everything else. Once the approval button is wired, you can act on research findings in real time. Once the synthetic customer is validated, you have a product story.",
        ],
        "trading": [
            "On trading: I'd approach it systematically. The research engine can scan for opportunities, but execution needs discipline. Define your edge, size positions correctly, and never risk more than you can afford to lose. The research engine gives you data; your rules give you the edge.",
            "Trading strategy: use the research engine for opportunity scanning, but build your own execution framework. Set clear entry and exit rules. Risk management is everything. The research engine finds the setups; your discipline makes the money.",
            "For trading: the research engine can surface opportunities, but you need a systematic approach. Define your criteria, automate what you can, and manage risk aggressively. The edge is in the process, not the prediction.",
        ],
    },
    "opinion": [
        "Here's my take: you should monetize the research engine first. It's the fastest path to revenue, has the clearest value proposition, and doesn't require as much trust as the synthetic customer. Get that paying, then layer on the premium features.",
        "My recommendation: lead with the research engine subscription. It solves an immediate problem, is easy to explain, and has a natural upgrade path to synthetic customer features. That's your sequence: research engine first, synthetic customer second, advisory third.",
        "Opinion: the research engine is your cash cow in waiting. It delivers instant value, is easy to demo, and has a clear pricing model. Start there. The synthetic customer is your moat but needs more validation before it's ready for prime time. Prioritize accordingly.",
    ],
    "approval": [
        "To approve in the research engine: go to the Research Dashboard, find the candidate you want to approve, and click the Approve button. If the button isn't wired yet, the fallback is to update the candidate status manually in the data file. The approval gates the candidate from moving to the next stage.",
        "Approval steps: 1) Open the Research Dashboard, 2) Review the candidate details, 3) Click Approve to move it forward. If the approve button isn't connected yet, you can manually set the status to approved in the research candidates file. Either way, the approval is what triggers the next action.",
        "How to approve: navigate to the research engine dashboard, select the candidate, and hit approve. The UI button should wire to update the candidate status. If it's not connected yet, edit the candidate status directly. The approval is the gate that moves things from review to action.",
    ],
    "money": [
        "Revenue status: the research engine subscription is your primary revenue driver. Focus on getting early subscribers. The synthetic customer is your premium tier. Keep burn low and reinvest in product. Every dollar should go toward features that drive adoption.",
        "Money situation: you're bootstrapping, so cash efficiency matters. The research engine is your fastest path to revenue. Get paying users, show the numbers, and reinvest. Don't spend on marketing until the product converts organically.",
        "Financial priorities: 1) Get the research engine generating MRR, 2) Keep operating costs minimal, 3) Use revenue to fund synthetic customer development. The goal is self-sustaining growth before you even think about outside funding.",
    ],
    "blockers": [
        "I see the blocker. Let me look into it and get back to you with options.",
        "That's a real issue. Let me analyze what's causing it and propose a fix.",
        "Good catch. Let me dig into this and come back with a solution.",
        "On it. Let me assess the situation and find the best path forward.",
        "That needs attention. Let me investigate and get you an answer.",
    ],
    "summary": [
        "Here's where things stand: the research engine is functional but needs the approval button wired. The synthetic customer pipeline is ready for testing. Revenue is pre-launch. Today's priorities: wire the approval, run a synthetic test, and push a candidate to action.",
        "Status update: research engine is up, synthetic customer pipeline is built, approval workflow needs UI wiring. Revenue is pending launch. Focus areas: close the approval loop, validate synthetic customer data, and get the first paying user.",
        "Current state: research engine scanning, synthetic customer pipeline ready, approval UI incomplete, revenue model defined but not live. Next moves: wire approval, test synthetic customer, launch subscription.",
    ],
    "delegation": [
        "Got it. I'll take care of that.",
        "On it. I'll handle this.",
        "Consider it done. I'll manage this.",
        "I'll take this one. Consider it handled.",
        "Understood. I'll take care of it.",
    ],
    "question": [
        "That's a good question. Let me think through it and give you the best answer I can.",
        "Interesting question. Here's what I know.",
        "Good question. Let me break that down for you.",
        "Let me address that. Here's my understanding.",
        "That's worth exploring. Here's my take.",
    ],
    "conversation": [
        "Tell me more about that. I'm listening.",
        "Interesting. What's your thinking on it?",
        "I'm following. What's the context here?",
        "Go on. I'm engaged.",
        "I hear you. What's the next thought?",
    ],
}

_response_counters = {}


def _get_next_response(intent: str, topic: str = None) -> str:
    key = topic if topic and intent == "nexus_topic" else intent
    pool = RESPONSE_BANK.get(intent, RESPONSE_BANK.get("conversation", []))

    if isinstance(pool, dict):
        pool = pool.get(topic, ["I'm here. What's the focus?"])

    if key not in _response_counters:
        _response_counters[key] = 0

    idx = _response_counters[key] % len(pool)
    _response_counters[key] += 1

    return pool[idx]


def generate_response(message: str, specialist: str = None) -> dict:
    from classify_hermes_intent import classify_intent

    classification = classify_intent(message)
    intent = classification["intent"]
    topic = classification["topic"]

    text = _get_next_response(intent, topic)

    queued = intent in ("blockers", "delegation")

    context = {
        "specialist": specialist or classification.get("suggested_specialist", "general"),
        "original_message": message,
        "classification": classification,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    return {
        "intent": intent,
        "specialist": context["specialist"],
        "text": text,
        "queued": queued,
        "context": context,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Hermes advisor response")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--message", "-m", required=True, help="User message")
    parser.add_argument("--specialist", "-s", default=None, help="Specialist override")
    args = parser.parse_args()

    result = generate_response(args.message, args.specialist)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Intent: {result['intent']}")
        print(f"Specialist: {result['specialist']}")
        print(f"Response: {result['text']}")
        print(f"Queued: {result['queued']}")


if __name__ == "__main__":
    main()
