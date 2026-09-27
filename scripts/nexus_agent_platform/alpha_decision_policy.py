"""Ray-aligned Alpha disposition policy.

Alpha challenges and routes. It does not decide whether Ray ultimately accepts
an opportunity, spend, publication, customer action, or live trade.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence

DISPOSITIONS = ("QUALIFY", "TEST", "RESEARCH_MORE", "MONITOR", "REJECT", "NO_ACTION")
HARD_BLOCKER_TERMS = ("illegal", "fraud", "deception", "unsafe", "privacy exposure", "security vulnerability", "clearly disproven", "negative economics", "impossible dependency", "paid action without approval", "live trading")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _text(package: dict[str, Any], judgment: dict[str, Any]) -> str:
    return " ".join(str(package.get(key) or "") for key in ("query", "summary", "title", "analysis")) + " " + " ".join(str(judgment.get(key) or "") for key in ("reasoning_summary", "deficiencies", "contradictions"))

def hard_blockers(package: dict[str, Any], judgment: dict[str, Any]) -> list[str]:
    blob = _text(package, judgment).lower()
    return [term for term in HARD_BLOCKER_TERMS if term in blob]

def test_profile(package: dict[str, Any]) -> dict[str, Any]:
    profile = package.get("test_profile") or package.get("experiment_profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    return {
        "plausible_upside": profile.get("plausible_upside", "UNKNOWN"),
        "time_to_learn": profile.get("time_to_learn", "UNKNOWN"),
        "time_to_first_dollar": profile.get("time_to_first_dollar", "UNKNOWN"),
        "expected_cost_to_test": profile.get("expected_cost_to_test", "UNKNOWN"),
        "reversibility": profile.get("reversibility", "UNKNOWN"),
        "execution_difficulty": profile.get("execution_difficulty", "UNKNOWN"),
        "customer_demand_signal": profile.get("customer_demand_signal", "UNKNOWN"),
        "margin_potential": profile.get("margin_potential", "UNKNOWN"),
        "competitive_pressure": profile.get("competitive_pressure", "UNKNOWN"),
        "operational_load": profile.get("operational_load", "UNKNOWN"),
        "reuse_of_existing_nexus_capability": profile.get("reuse_of_existing_nexus_capability", "UNKNOWN"),
        "no_external_action": profile.get("no_external_action", package.get("external_action_allowed") is False),
    }

def _yes(value: Any) -> bool:
    return str(value).upper() in {"YES", "TRUE", "LOW", "PLAUSIBLE", "BOUNDED", "REVERSIBLE"}

def apply_policy(package: dict[str, Any], judgment: dict[str, Any]) -> dict[str, Any]:
    model_decision = str(judgment.get("decision") or "RESEARCH_MORE").upper()
    blockers = hard_blockers(package, judgment)
    profile = test_profile(package)
    evidence_for = list(judgment.get("evidence_for") or judgment.get("source_refs") or package.get("sources") or [])
    evidence_against = list(judgment.get("evidence_against") or judgment.get("contradictions") or [])
    unknowns = list(judgment.get("unknowns") or judgment.get("deficiencies") or [])
    testable = list(judgment.get("testable_unknowns") or [])
    decision = model_decision if model_decision in DISPOSITIONS else "RESEARCH_MORE"
    why = str(judgment.get("reasoning_summary") or "Alpha recorded a bounded evidence review.")
    # An explicit, low-cost reversible experiment is enough for TEST even when
    # business evidence is incomplete. Hard safety boundaries always win.
    if blockers:
        decision = "REJECT"
        why = f"Hard safety boundary: {', '.join(blockers)}. No experiment may bypass this gate."
    elif model_decision == "REJECT" and all(value == "UNKNOWN" for value in profile.values()):
        # Preserve a source-failure rejection when Alpha has no usable
        # hypothesis or test profile; this is not a universal rejection rule.
        decision = "REJECT"
    elif model_decision in {"REJECT", "RESEARCH_MORE"} and package.get("test_profile"):
        ready = (_yes(profile["plausible_upside"]) and _yes(profile["reversibility"]) and
                 _yes(profile["no_external_action"]) and str(profile["expected_cost_to_test"]).upper() in {"LOW", "ZERO", "UNKNOWN"} and
                 (_yes(profile["customer_demand_signal"]) or _yes(profile["reuse_of_existing_nexus_capability"]) or bool(evidence_for)))
        if ready:
            decision = "TEST"
            why = "Evidence is incomplete, but the proposed experiment is low-cost, reversible, bounded, and can resolve the stated uncertainty."
            testable = testable or unknowns
    elif model_decision == "PARK":
        decision = "MONITOR"
    next_owner = str(package.get("handoff_target") or package.get("department_target") or package.get("department") or "RESEARCH").upper()
    return {
        "model_decision": model_decision, "decision": decision, "why": why,
        "evidence_for": evidence_for, "evidence_against": evidence_against, "unknowns": unknowns,
        "hard_blockers": blockers, "soft_risks": list(judgment.get("soft_risks") or judgment.get("deficiencies") or []),
        "testable_unknowns": testable, "test_profile": profile, "next_owner": next_owner,
        "recommended_next_step": ("Create a bounded internal test work order; no external action." if decision == "TEST" else judgment.get("required_followup") or judgment.get("recommended_next_stage") or "Preserve the result and select the next governed step."),
        "ray_policy_rules_applied": ["hard safety gates are automatic stops", "uncertainty is not rejection", "low-cost reversible tests are eligible", "Alpha is advisory; Ray remains final business authority"],
    }

def record_ray_override(*, evaluation_id: str, decision: str, reason: str, authorized_by: str = "RAY", next_owner: str = "") -> dict[str, Any]:
    decision = str(decision).upper()
    if decision not in DISPOSITIONS:
        raise ValueError("invalid-alpha-override-decision")
    if authorized_by != "RAY":
        raise ValueError("only-ray-may-override-alpha")
    row = {"schema_version": "nexus.alpha-ray-override.v1", "override_id": persistence.new_id("alpha_override"), "evaluation_id": evaluation_id, "decision": decision, "reason": str(reason).strip(), "authorized_by": authorized_by, "next_owner": next_owner, "created_at": _now(), "external_action_performed": False}
    persistence.append_record("alpha_decision_overrides", row)
    return row
