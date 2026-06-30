#!/usr/bin/env python3
"""Test Hermes business answers for quality and variety.

Tests these messages through the Python Hermes handler:
  1. "what color is the sky" → must get a normal answer (not Nexus-related)
  2. "tell me about the synthetic customer insert" → must explain what it is
  3. "how do i approve anything in the research engine" → must give UI steps
  4. "what strategy do you have today" → must give strategic priorities
  5. "did you sleep" → must answer naturally
  6. "give me your opinion on what we should monetize first" → must give ranked recommendation
  7. Two different messages must NOT get identical responses

Returns JSON with: test_results, all_passed, response_samples
"""
import argparse
import json
import sys
from pathlib import Path

HERMES_DIR = Path(__file__).resolve().parents[1] / "hermes"
sys.path.insert(0, str(HERMES_DIR))

try:
    from hermes_context_common import advisor_response
except ImportError:
    # Fallback: define a minimal advisor_response if the module is unavailable
    def advisor_response(message, ctx=None):
        return {"intent": "unknown", "response": "Module unavailable", "mode": "fallback", "external_action_performed": False}


TEST_CASES = [
    {
        "id": "sky_color",
        "message": "what color is the sky",
        "check": "not_nexus_related",
        "validator": lambda resp: not any(w in resp.lower() for w in ["nexus", "hermes", "approval", "scheduler", "ray review"]),
        "description": "Must give a normal answer, not Nexus-related",
    },
    {
        "id": "synthetic_customer_insert",
        "message": "tell me about the synthetic customer insert",
        "check": "explains_synthetic_customer",
        "validator": lambda resp: any(w in resp.lower() for w in ["synthetic", "customer", "fake", "test", "insert", "dashboard"]),
        "description": "Must explain what the synthetic customer insert is",
    },
    {
        "id": "research_engine_approval",
        "message": "how do i approve anything in the research engine",
        "check": "gives_ui_steps",
        "validator": lambda resp: any(w in resp.lower() for w in ["approve", "review", "card", "queue", "click", "button", "select", "ray"]),
        "description": "Must give UI steps for approval",
    },
    {
        "id": "strategy_today",
        "message": "what strategy do you have today",
        "check": "gives_strategic_priorities",
        "validator": lambda resp: any(w in resp.lower() for w in ["priority", "today", "focus", "first", "step", "plan", "money", "revenue", "path"]),
        "description": "Must give strategic priorities",
    },
    {
        "id": "did_you_sleep",
        "message": "did you sleep",
        "check": "answers_naturally",
        "validator": lambda resp: any(w in resp.lower() for w in ["sleep", "awake", "always", "ready", "never", "monitor", "watch"]),
        "description": "Must answer naturally about not sleeping",
    },
    {
        "id": "monetize_first",
        "message": "give me your opinion on what we should monetize first",
        "check": "gives_ranked_recommendation",
        "validator": lambda resp: any(w in resp.lower() for w in ["first", "start", "top", "best", "priority", "recommend", "readiness", "$97", "offer", "path"]),
        "description": "Must give a ranked recommendation on monetization",
    },
]

UNIQUENESS_PAIRS = [
    ("what color is the sky", "did you sleep"),
    ("what strategy do you have today", "give me your opinion on what we should monetize first"),
    ("tell me about the synthetic customer insert", "how do i approve anything in the research engine"),
]


def run_tests():
    test_results = []
    response_samples = {}
    all_passed = True

    for tc in TEST_CASES:
        result = advisor_response(tc["message"])
        response = result.get("response", "")
        response_samples[tc["id"]] = response

        passed = tc["validator"](response)
        test_results.append({
            "test_id": tc["id"],
            "message": tc["message"],
            "check": tc["check"],
            "description": tc["description"],
            "passed": passed,
            "response_preview": response[:200] + ("..." if len(response) > 200 else ""),
            "intent": result.get("intent", "unknown"),
        })
        if not passed:
            all_passed = False

    # Test 7: Uniqueness check
    for msg_a, msg_b in UNIQUENESS_PAIRS:
        resp_a = advisor_response(msg_a).get("response", "")
        resp_b = advisor_response(msg_b).get("response", "")
        unique = resp_a != resp_b
        test_results.append({
            "test_id": f"uniqueness_{msg_a[:10]}_{msg_b[:10]}",
            "message": f"'{msg_a}' vs '{msg_b}'",
            "check": "responses_not_identical",
            "description": "Two different messages must NOT get identical responses",
            "passed": unique,
            "response_a_preview": resp_a[:100],
            "response_b_preview": resp_b[:100],
        })
        if not unique:
            all_passed = False

    payload = {
        "ok": all_passed,
        "status": "hermes_business_answer_test_passed" if all_passed else "hermes_business_answer_test_failed",
        "test_results": test_results,
        "tests_passed": sum(1 for t in test_results if t["passed"]),
        "tests_failed": sum(1 for t in test_results if not t["passed"]),
        "all_passed": all_passed,
        "response_samples": response_samples,
        "external_action_performed": False,
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Test Hermes business answers")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    payload = run_tests()

    if args.json:
        print(json.dumps(payload, indent=2))

    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
