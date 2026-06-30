#!/usr/bin/env python3

import argparse
import json
import re
import sys


def classify_intent(message: str) -> dict:
    msg = message.lower().strip()

    # Greeting patterns
    greeting_patterns = [
        r'\b(hello|hi|hey|sup|yo|greetings|good morning|good evening|good afternoon|what\'s up)\b',
        r'^(hi|hey|yo|sup)\b',
    ]
    for pat in greeting_patterns:
        if re.search(pat, msg):
            return {
                "intent": "greeting",
                "topic": "general",
                "confidence": 0.9,
                "suggested_specialist": "general",
            }

    # Partner / Hermes direct address
    partner_patterns = [
        r'\b(hermes|buddy|partner|assistant|advisor)\b',
        r'^(hey you|listen|buddy)\b',
    ]
    for pat in partner_patterns:
        if re.search(pat, msg):
            return {
                "intent": "partner_mode",
                "topic": "hermes_direct",
                "confidence": 0.85,
                "suggested_specialist": "general",
            }

    # Nexus-specific topics
    nexus_patterns = {
        r'\b(synthetic\s*customer|customer\s*insert)\b': "synthetic_customer",
        r'\b(research\s*engine|research\s*dashboard|research\s*panel)\b': "research_engine",
        r'\b(monetiz|revenue\s*model|pricing\s*strategy)\b': "monetization",
        r'\b(stripe|payment\s*gateway|checkout)\b': "stripe",
        r'\b(resend|email\s*service|transactional\s*email)\b': "resend",
        r'\b(approval|approve|approve\s*button|wiring)\b': "approval",
        r'\b(credit|funding|investor|raise)\b': "credit",
        r'\b(client|customer|user\s*onboard)\b': "client",
        r'\b(opportunity|opportunities|market\s*gap)\b': "opportunity",
        r'\b(marketing|growth|acquisition|funnel)\b': "marketing",
        r'\b(strategy|strategic|priorities|roadmap|plan)\b': "strategy",
        r'\b(trading|trade|market|stock|crypto|forex)\b': "trading",
    }
    for pat, topic in nexus_patterns.items():
        if re.search(pat, msg):
            return {
                "intent": "nexus_topic",
                "topic": topic,
                "confidence": 0.88,
                "suggested_specialist": "business",
            }

    # Opinion request
    opinion_patterns = [
        r'\b(what\s*(do\s*you|\'s?\s*your)\s*(think|opinion|take|view|advice))\b',
        r'\b(your\s*(thoughts|opinion|take|view|recommendation))\b',
        r'\b(should\s*i|should\s*we|what\s*should)\b',
        r'\b(rank|ranking|best\s*option|which\s*one)\b',
    ]
    for pat in opinion_patterns:
        if re.search(pat, msg):
            return {
                "intent": "opinion",
                "topic": "general",
                "confidence": 0.8,
                "suggested_specialist": "business",
            }

    # Approval request
    approval_patterns = [
        r'\b(approve|approval|how\s*do\s*i\s*approve)\b',
        r'\b(give\s*(me\s*)?(the\s*)?(go\s*ahead|green|okay))\b',
        r'\b(sign\s*off|signoff)\b',
    ]
    for pat in approval_patterns:
        if re.search(pat, msg):
            return {
                "intent": "approval",
                "topic": "approval_workflow",
                "confidence": 0.85,
                "suggested_specialist": "operations",
            }

    # Money / funding
    money_patterns = [
        r'\b(money|revenue|funding|investor|runway|burn|cash|capital|raise)\b',
        r'\b(how\s*much\s*(do\s*we|is|are))\b',
        r'\b(financial|finance|budget)\b',
    ]
    for pat in money_patterns:
        if re.search(pat, msg):
            return {
                "intent": "money",
                "topic": "financial",
                "confidence": 0.8,
                "suggested_specialist": "business",
            }

    # Blockers
    blocker_patterns = [
        r'\b(block|blocker|blocked|stuck|issue|problem|error|bug|fail|broken|stalling)\b',
        r'\b(how\s*(do|can)\s*i\s*(fix|resolve|unblock|debug))\b',
        r'\b(not\s*working|doesn\'?t\s*work|can\'?t)\b',
    ]
    for pat in blocker_patterns:
        if re.search(pat, msg):
            return {
                "intent": "blockers",
                "topic": "technical",
                "confidence": 0.82,
                "suggested_specialist": "technical",
            }

    # Summary request
    summary_patterns = [
        r'\b(summary|summarize|recap|catch\s*me\s*up|what\'?s?\s*happening|status|update|where\s*(are|do)\s*we)\b',
        r'\b(what\s*did\s*we\s*(do|accomplish))\b',
        r'\b(progress|standup|stand-up)\b',
    ]
    for pat in summary_patterns:
        if re.search(pat, msg):
            return {
                "intent": "summary",
                "topic": "status",
                "confidence": 0.85,
                "suggested_specialist": "general",
            }

    # Delegation
    delegation_patterns = [
        r'\b(delegate|assign|hand\s*off|take\s*care\s*of|handle\s*this|do\s*this)\b',
        r'\b(you\s*(handle|take|deal|manage))\b',
    ]
    for pat in delegation_patterns:
        if re.search(pat, msg):
            return {
                "intent": "delegation",
                "topic": "task",
                "confidence": 0.8,
                "suggested_specialist": "general",
            }

    # Sleep / idle
    sleep_patterns = [
        r'\b(did\s*you\s*sleep|are\s*you\s*(tired|awake|sleeping))\b',
        r'\b(how\s*(are|do)\s*you\s*(feeling|doing))\b',
    ]
    for pat in sleep_patterns:
        if re.search(pat, msg):
            return {
                "intent": "casual",
                "topic": "wellbeing",
                "confidence": 0.75,
                "suggested_specialist": "general",
            }

    # Casual conversation
    casual_patterns = [
        r'\b(thanks|thank\s*you|cheers|nice|cool|awesome|great|good|lol|haha|yeah|yep|nah)\b',
        r'^(ok|okay|sure|fine|yup|nope|nah)\s*[.!?]*$',
        r'\b(tell\s*me\s*a\s*joke|funny|bored|random)\b',
    ]
    for pat in casual_patterns:
        if re.search(pat, msg):
            return {
                "intent": "casual",
                "topic": "conversation",
                "confidence": 0.7,
                "suggested_specialist": "general",
            }

    # Emotional / venting
    emotional_patterns = [
        r'\b(frustrat|angry|annoyed|stressed|overwhelm|tired|exhausted|burnout|anxious|worried|sad)\b',
        r'\b(i\s*(feel|\'m)\s*(bad|terrible|awful|horrible))\b',
        r'\b(this\s*sucks|hate|despise)\b',
    ]
    for pat in emotional_patterns:
        if re.search(pat, msg):
            return {
                "intent": "emotional",
                "topic": "emotional",
                "confidence": 0.78,
                "suggested_specialist": "general",
            }

    # Question (general)
    question_patterns = [
        r'\?$',
        r'^(what|how|why|when|where|who|which|can|could|would|should|do|does|is|are|will)\b',
        r'\b(explain|describe|tell\s*me)\b',
    ]
    for pat in question_patterns:
        if re.search(pat, msg):
            return {
                "intent": "question",
                "topic": "general",
                "confidence": 0.6,
                "suggested_specialist": "general",
            }

    # Default: conversation
    return {
        "intent": "conversation",
        "topic": "general",
        "confidence": 0.5,
        "suggested_specialist": "general",
    }


def main():
    parser = argparse.ArgumentParser(description="Classify Hermes intent")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--message", "-m", required=True, help="User message")
    args = parser.parse_args()

    result = classify_intent(args.message)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Intent: {result['intent']}")
        print(f"Topic: {result['topic']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Suggested Specialist: {result['suggested_specialist']}")


if __name__ == "__main__":
    main()
