#!/usr/bin/env python3

import argparse
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify_hermes_intent import classify_intent
from generate_hermes_advisor_response import generate_response
from load_hermes_context import load_context
from search_hermes_context import search_context


def handle_message(message: str) -> dict:
    classification = classify_intent(message)
    intent = classification["intent"]
    topic = classification["topic"]

    context_data = load_context()
    search_result = search_context(message)

    response = generate_response(message)

    enriched_text = response["text"]

    if search_result.get("confidence", 0) > 0.6 and search_result.get("suggested_answer"):
        enriched_text = search_result["suggested_answer"]

    return {
        "intent": intent,
        "specialist": response["specialist"],
        "text": enriched_text,
        "queued": response["queued"],
        "context": {
            "topic": topic,
            "confidence": classification["confidence"],
            "search_confidence": search_result.get("confidence", 0),
            "sources": search_result.get("sources", []),
            "matches": search_result.get("matches", []),
            "hemes_context": context_data,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Handle Hermes advisor message")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--message", "-m", required=True, help="User message")
    args = parser.parse_args()

    try:
        result = handle_message(args.message)
    except Exception as e:
        result = {
            "intent": "conversation",
            "specialist": "general",
            "text": "I hit an issue processing that. Can you rephrase?",
            "queued": False,
            "context": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Intent: {result['intent']}")
        print(f"Specialist: {result['specialist']}")
        print(f"Response: {result['text']}")
        print(f"Queued: {result['queued']}")
        print(f"Timestamp: {result['timestamp']}")


if __name__ == "__main__":
    main()
