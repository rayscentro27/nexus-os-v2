"""Natural-language front brain for Research Room execution modes.

This classifies the root objective only. It does not fan out department jobs;
the completed Research strategy may propose those handoffs later.
"""
from __future__ import annotations

import re
from typing import Any


def route_research_intent(text: str) -> dict[str, Any] | None:
    value = " ".join(str(text or "").split()).strip()
    folded = value.casefold()
    if not value:
        return None

    # Claims are evaluated first so business language inside a claim does not
    # turn a verification request into opportunity discovery.
    if re.search(r"\b(?:is this (?:claim|true)|is (?:that|it) true|can you really|review what .{0,35} saying|verify (?:this|whether)|claim verification)\b", folded):
        mode = "CLAIM_VERIFICATION_MODE"
    elif re.search(r"\b(?:forex|trading strategy|paper[- ]trad\w*|backtest|trading indicator|market idea)\b", folded):
        mode = "TRADING_STRATEGY_MODE"
    elif re.search(r"\b(?:business opportunit\w*|online business|businesses? (?:should|could|can) nexus|make money|making money|monetiz\w*|revenue from|start (?:a|an|this) business)\b", folded) or (
        re.search(r"\b(?:business|venture|opportunity)\b", folded) and re.search(r"\b(?:find|identify|start|pursue|automate|build|sell|revenue|money)\b", folded)
    ):
        mode = "BUSINESS_OPPORTUNITY_MODE"
    elif re.search(r"\b(?:can this (?:\w+\s+){0,3}help nexus|improve nova|add this tool|what can nexus copy|review .{0,40}(?:github|opencode|project|tool)|should nexus (?:use|adopt|add)|technology review)\b", folded):
        mode = "NEXUS_ENHANCEMENT_MODE"
    elif re.search(r"\b(?:deep research|comprehensive research|major architecture decision|high.value investigation)\b", folded):
        mode = "DEEP_RESEARCH_MODE"
    else:
        return None

    contexts = []
    if re.search(r"\b(?:nova|automate|automation|workflow)\b", folded):
        contexts.append("NOVA_AUTOMATION")
    if re.search(r"\b(?:build|implement|first|next step|what .* need to build)\b", folded):
        contexts.append("IMPLEMENTATION_PLAN")
    if re.search(r"\b(?:nexus|we|our)\b", folded):
        contexts.append("NEXUS_FIT")
    expected = {
        "BUSINESS_OPPORTUNITY_MODE": "business strategy + Nova automation plan + implementation blueprint",
        "TRADING_STRATEGY_MODE": "testable strategy + bounded paper-test plan + Trading handoff",
        "NEXUS_ENHANCEMENT_MODE": "Nexus implementation blueprint + smallest safe test",
        "CLAIM_VERIFICATION_MODE": "verified claim + Nexus action plan",
        "DEEP_RESEARCH_MODE": "deep analysis + execution plan",
    }[mode]
    return {"objective": value, "primary_mode": mode, "secondary_context": contexts,
        "research_required": True, "expected_output": expected,
        "possible_downstream_departments": [], "dispatch_path": "NOVA_TO_RESEARCH_ROOM",
        "alpha_assignment_required": False, "downstream_actions_before_strategy": False}
