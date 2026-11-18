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

    # Deep research intent takes precedence over generic research mentions.
    if re.search(
        r"\b(?:research\s+(?:(?:\w+|this|it)\s+){0,3}deeply|deep research|validate the market|"
        r"perform competitive research|verify pricing|conduct full business research|"
        r"perform deep investigation|comprehensive research|major architecture decision|"
        r"high.value investigation)\b",
        folded,
    ):
        mode = "DEEP_RESEARCH_MODE"
    elif re.search(
        r"\b(?:create (?:a )?(?:new )?research room|open (?:a )?(?:new )?research room|research room|"
        r"add (?:a )?source|ask alpha|have alpha (?:review|research|investigate|look at|help|tell me)|"
        r"research (?:this|it|that|\w+) in a room|discuss this source|"
        r"score (?:this )?room|compare research rooms|research this idea)\b",
        folded,
    ):
        mode = "RESEARCH_ROOM_MODE"
    # Claims are evaluated next so business language inside a claim does not
    # turn a verification request into opportunity discovery.
    elif re.search(r"\b(?:is this (?:claim|true)|is (?:that|it) true|can you really|review what .{0,35} saying|verify (?:this|whether)|claim verification)\b", folded):
        mode = "CLAIM_VERIFICATION_MODE"
    elif re.search(r"\b(?:forex|trading strategy|paper[- ]trad\w*|backtest|trading indicator|market idea)\b", folded):
        mode = "TRADING_STRATEGY_MODE"
    elif re.search(r"\b(?:business opportunit\w*|online business|businesses? (?:should|could|can) nexus|make money|making money|monetiz\w*|revenue from|start (?:a|an|this) business)\b", folded) or (
        re.search(r"\b(?:business|venture|opportunity)\b", folded) and re.search(r"\b(?:find|identify|start|pursue|automate|build|sell|revenue|money)\b", folded)
    ):
        mode = "BUSINESS_OPPORTUNITY_MODE"
    elif re.search(r"\b(?:can this (?:\w+\s+){0,3}help nexus|improve nova|add this tool|what can nexus copy|review .{0,40}(?:github|opencode|project|tool)|should nexus (?:use|adopt|add)|technology review)\b", folded):
        mode = "NEXUS_ENHANCEMENT_MODE"
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
        "RESEARCH_ROOM_MODE": "Research Room creation + source attachment + Alpha conversation + preliminary score",
    }[mode]
    return {"objective": value, "primary_mode": mode, "secondary_context": contexts,
        "research_required": True, "expected_output": expected,
        "possible_downstream_departments": [], "dispatch_path": "NOVA_TO_RESEARCH_ROOM",
        "alpha_assignment_required": False, "downstream_actions_before_strategy": False}
