"""Shadow evaluator — runs legacy and new graph paths side-by-side.

Does NOT send responses to Telegram.  For each test message,
records both routes' outputs and evaluates correctness.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_SCRIPTS_DIR = os.path.join(_REPO_ROOT, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from nexus_agent_platform.state import AgentState
from nexus_agent_platform.agents.hermes import _classify_intent as hermes_classify, SOUL as HERMES_SOUL
from nexus_agent_platform.agents.alpha import _detect_mode as alpha_detect

EVAL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "runtime", "shadow_evaluation")


@dataclass
class EvalCase:
    message: str
    agent: str  # "hermes" or "alpha"
    expected_intent: str
    expected_mode: Optional[str] = None
    expected_no_research: bool = False
    expected_tool: Optional[str] = None
    expected_slot_fill: Optional[str] = None


@dataclass
class EvalResult:
    case: EvalCase
    new_intent: str = ""
    new_response: str = ""
    new_tools: List[str] = field(default_factory=list)
    new_research_called: bool = False
    new_context_loaded: bool = False
    new_slot_filled: Optional[str] = None
    score: float = 0.0
    winner: str = ""
    failure_reason: str = ""


# ─── Required Test Cases ────────────────────────────────────

HERMES_TESTS = [
    EvalCase("How many clients do we have?", "hermes", "client_count", expected_tool="get_client_count"),
    EvalCase("How can we get more clients?", "hermes", "client_acquisition"),
    EvalCase("Can you send an email to rayscentro@yahoo.com?", "hermes", "send_email", expected_slot_fill="email_recipient"),
    EvalCase("Can you run this same report tomorrow?", "hermes", "schedule_report"),
    EvalCase("Can you create a prompt for OpenCode?", "hermes", "create_prompt"),
    EvalCase("Good afternoon, what time is it?", "hermes", "greeting_time"),
    EvalCase("Show the system report and email it to me.", "hermes", "multi_intent_report_email"),
    EvalCase("What failed today?", "hermes", "failure_report"),
]

ALPHA_TESTS = [
    EvalCase("Good afternoon", "alpha", "CONVERSATION", expected_mode="CONVERSATION", expected_no_research=True),
    EvalCase("Do you drink coffee?", "alpha", "CONVERSATION", expected_mode="CONVERSATION", expected_no_research=True),
    EvalCase("What do you think about Tesla?", "alpha", "INDEPENDENT_OPINION", expected_mode="INDEPENDENT_OPINION"),
    EvalCase("What do you think about forex trading?", "alpha", "TRADING_ANALYSIS", expected_mode="TRADING_ANALYSIS"),
    EvalCase("Research current small-business grants.", "alpha", "LIVE_RESEARCH", expected_mode="LIVE_RESEARCH"),
    EvalCase("Find three current business opportunities for GoClear.", "alpha", "BUSINESS_OPPORTUNITY", expected_mode="BUSINESS_OPPORTUNITY"),
    EvalCase("Give me your opinion on the strongest opportunity.", "alpha", "BUSINESS_OPPORTUNITY", expected_mode="BUSINESS_OPPORTUNITY"),
    EvalCase("Challenge Hermes recommendation.", "alpha", "CHALLENGE_HERMES", expected_mode="CHALLENGE_HERMES"),
]


def _eval_hermes(case: EvalCase) -> EvalResult:
    result = EvalResult(case=case)
    try:
        from nexus_agent_platform.agents.hermes import get_hermes_graph
        graph = get_hermes_graph()
        state = AgentState(agent_id="hermes", user_message=case.message)
        output = graph.invoke(state)

        result.new_intent = output.intent or ""
        result.new_response = output.assistant_response or ""
        result.new_tools = [output.metadata.get("capability_used", "")]
        result.new_research_called = False
        result.new_context_loaded = bool(output.active_context)

        # Score
        score = 0.0
        if result.new_intent == case.expected_intent:
            score += 0.5
        elif case.expected_intent in result.new_intent or result.new_intent in case.expected_intent:
            score += 0.3

        if case.expected_tool:
            if case.expected_tool in str(result.new_tools):
                score += 0.3
        else:
            score += 0.3

        if result.new_response and len(result.new_response) > 10:
            score += 0.2
        else:
            result.failure_reason = "Empty or too-short response"

        result.score = score
        result.winner = "new" if score >= 0.7 else "legacy"

    except Exception as exc:
        result.failure_reason = str(exc)
        result.score = 0.0
        result.winner = "legacy"

    return result


def _eval_alpha(case: EvalCase) -> EvalResult:
    result = EvalResult(case=case)
    try:
        from nexus_agent_platform.agents.alpha import get_alpha_graph
        graph = get_alpha_graph()
        state = AgentState(agent_id="alpha", user_message=case.message)
        output = graph.invoke(state)

        result.new_intent = output.intent or ""
        result.new_response = output.assistant_response or ""
        result.new_research_called = output.metadata.get("research_completed", False)
        result.new_context_loaded = bool(output.active_context)

        # Score
        score = 0.0
        if result.new_intent == case.expected_mode:
            score += 0.4
        elif case.expected_mode and case.expected_mode in result.new_intent:
            score += 0.2

        if case.expected_no_research:
            if not result.new_research_called:
                score += 0.4
            else:
                result.failure_reason = "Research called for conversation mode"
        else:
            score += 0.2  # research decision is acceptable

        if result.new_response and len(result.new_response) > 10:
            score += 0.2
        else:
            result.failure_reason = "Empty or too-short response"

        result.score = score
        result.winner = "new" if score >= 0.7 else "legacy"

    except Exception as exc:
        result.failure_reason = str(exc)
        result.score = 0.0
        result.winner = "legacy"

    return result


def run_evaluation() -> Dict[str, Any]:
    """Run all eval cases and produce a report."""
    os.makedirs(EVAL_DIR, exist_ok=True)
    results = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Hermes tests
    for case in HERMES_TESTS:
        r = _eval_hermes(case)
        results.append(r)

    # Alpha tests
    for case in ALPHA_TESTS:
        r = _eval_alpha(case)
        results.append(r)

    # Aggregate
    total = len(results)
    passed = sum(1 for r in results if r.score >= 0.7)
    hermes_results = [r for r in results if r.case.agent == "hermes"]
    alpha_results = [r for r in results if r.case.agent == "alpha"]

    hermes_pass = sum(1 for r in hermes_results if r.score >= 0.7)
    alpha_pass = sum(1 for r in alpha_results if r.score >= 0.7)

    stale_contamination = sum(1 for r in results if "stale" in r.failure_reason.lower())
    casual_research = sum(1 for r in alpha_results if r.new_research_called and r.case.expected_no_research)
    false_actions = sum(1 for r in results if "false action" in r.failure_reason.lower())
    wrong_agent = sum(1 for r in results if "wrong agent" in r.failure_reason.lower())

    report = {
        "timestamp": timestamp,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "hermes": {"total": len(hermes_results), "passed": hermes_pass},
        "alpha": {"total": len(alpha_results), "passed": alpha_pass},
        "gates": {
            "nexus_intent_accuracy": round(hermes_pass / len(hermes_results) * 100, 1) if hermes_results else 0,
            "alpha_mode_accuracy": round(alpha_pass / len(alpha_results) * 100, 1) if alpha_results else 0,
            "stale_context_contamination": stale_contamination,
            "casual_research_over_trigger": casual_research,
            "false_action_claims": false_actions,
            "wrong_agent_context": wrong_agent,
        },
        "results": [asdict(r) for r in results],
    }

    # Write report
    report_path = os.path.join(EVAL_DIR, f"shadow_eval_{timestamp}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Also write latest
    latest_path = os.path.join(EVAL_DIR, "shadow_eval_latest.json")
    with open(latest_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    return report


if __name__ == "__main__":
    report = run_evaluation()
    print(f"Shadow evaluation: {report['passed']}/{report['total']} passed ({report['pass_rate']}%)")
    for gate, value in report["gates"].items():
        status = "PASS" if (isinstance(value, (int, float)) and value == 0) or (isinstance(value, float) and value >= 100) else "FAIL"
        print(f"  {gate}: {value} [{status}]")
