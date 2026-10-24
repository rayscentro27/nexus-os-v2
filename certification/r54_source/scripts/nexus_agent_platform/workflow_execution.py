"""Execution-class declarations for Nexus workflows.

The class describes the current job/step's execution mode; a workflow may
contain deterministic and reasoning steps beneath one specialized department
job. LLM calls must declare LIGHT_REASONING or STRONG_REASONING at the call
site and are recorded separately by the canonical model router.
"""
from __future__ import annotations

from typing import Any

EXECUTION_CLASSES = {
    "DETERMINISTIC", "LIGHT_REASONING", "STRONG_REASONING", "SPECIALIZED_EXECUTOR"
}

STEP_CLASSES = {
    **{name: "DETERMINISTIC" for name in (
        "job_lookup", "receipt_lookup", "artifact_lookup", "receipt_verification",
        "job_creation", "department_handoff", "workflow_state_transition",
        "resource_state_lookup", "provider_health_lookup", "openrouter_quota_lookup",
        "free_tier_availability_lookup", "queue_transition", "job_claim_lease",
        "checkpoint_save", "receipt_persistence", "completion_event_creation",
        "telegram_acknowledgment", "telegram_completion_delivery", "google_calendar_read",
        "google_gmail_read", "google_drive_read", "nexus_state_read", "durable_job_list",
        "known_mcp_action", "finance_arithmetic", "systems_health_collection",
    )},
    **{name: "LIGHT_REASONING" for name in (
        "ambiguous_intent", "simple_context_reference", "short_summary",
        "simple_classification", "small_tool_selection_ambiguity",
    )},
    **{name: "STRONG_REASONING" for name in (
        "alpha_evaluation", "complex_research_synthesis", "strategic_prioritization",
        "multi_department_planning", "marketing_strategy", "opportunity_evaluation",
        "contradictory_evidence_resolution", "decision_support",
    )},
    **{name: "SPECIALIZED_EXECUTOR" for name in (
        "notebooklm", "browser_automation", "backtest", "trading_executor",
        "finance_calculation_engine", "image_generation", "video_generation",
        "code_executor", "opencode", "codex", "systems_diagnostics",
        "google_tools", "remote_worker", "local_worker",
    )},
}


def classify_step(step: str) -> str:
    """Return a declared execution class; unknown step names fail closed."""
    try:
        return STEP_CLASSES[str(step).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"UNDECLARED_WORKFLOW_STEP:{step}") from exc

_JOB_CLASSES = {
    "NOVA_TELEGRAM_OWNER_TURN": "LIGHT_REASONING",
    "NOVA_RESEARCH_RESULT_NOTICE": "DETERMINISTIC",
    "NOVA_SYSTEMS_RESULT_NOTICE": "DETERMINISTIC",
    "NOVA_ALPHA_RESULT_NOTICE": "DETERMINISTIC",
    "NOVA_ALPHA_ASSIGNMENT_NOTICE": "DETERMINISTIC",
    "NOTEBOOKLM_DISCOVERY": "SPECIALIZED_EXECUTOR",
    "TRADING_BACKTEST": "SPECIALIZED_EXECUTOR",
    "TRADING_TOURNAMENT_UPDATE": "SPECIALIZED_EXECUTOR",
    "PAPER_TRADING_DEPLOY": "SPECIALIZED_EXECUTOR",
    "SYSTEMS_HEALTH_CHECK": "DETERMINISTIC",
    "FINANCE_CALCULATION": "DETERMINISTIC",
    "MARKETING_STRATEGY": "STRONG_REASONING",
    "MARKETING_CAMPAIGN_BUILD": "STRONG_REASONING",
    "CREATIVE_BRIEF_BUILD": "STRONG_REASONING",
    "CREATIVE_ASSET_GENERATE": "SPECIALIZED_EXECUTOR",
    "CREATIVE_ASSET_REVISE": "SPECIALIZED_EXECUTOR",
    "LANDING_PAGE_BUILD": "SPECIALIZED_EXECUTOR",
    "LANDING_PAGE_VERIFY": "DETERMINISTIC",
    "NEEDLE_RESEARCH_READINESS_VERIFY": "LIGHT_REASONING",
    "NEEDLE_RESEARCH_TARGETED_REPAIR": "SPECIALIZED_EXECUTOR",
    "RESEARCH_RUNTIME_INSPECT": "DETERMINISTIC",
}


def classify_job(job_type: str, department: str = "", payload: dict[str, Any] | None = None) -> str:
    """Return the declared execution class for a durable job, failing closed."""
    payload = payload if isinstance(payload, dict) else {}
    declared = str(payload.get("execution_class") or "").upper()
    if declared:
        if declared not in EXECUTION_CLASSES:
            raise ValueError(f"INVALID_EXECUTION_CLASS:{declared}")
        return declared
    kind = str(job_type or "").upper()
    if kind in _JOB_CLASSES:
        return _JOB_CLASSES[kind]
    if kind == "NEXUS_DEPARTMENT_QUERY":
        dept = str(department or "").upper()
        return {
            "ALPHA": "STRONG_REASONING",
            "RESEARCH": "SPECIALIZED_EXECUTOR",
            "MARKETING": "STRONG_REASONING",
            "CREATIVE": "SPECIALIZED_EXECUTOR",
            "FINANCE": "DETERMINISTIC",
            "SYSTEMS": "DETERMINISTIC",
            "TRADING": "SPECIALIZED_EXECUTOR",
        }.get(dept, "SPECIALIZED_EXECUTOR")
    if kind in {"RESEARCH_GAP_VERIFY", "RESEARCH_RUNTIME_INSPECT", "RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY"}:
        return "SPECIALIZED_EXECUTOR"
    if kind.startswith("NOVA_") and ("NOTICE" in kind or "ACK" in kind or "DELIVERY" in kind):
        return "DETERMINISTIC"
    if kind.startswith(("FINANCE_", "SYSTEMS_", "RESOURCE_", "DURABLE_", "JOB_", "RECEIPT_")):
        return "DETERMINISTIC"
    # Registered department handlers and provider adapters are themselves
    # specialized execution boundaries unless a workflow declares otherwise.
    return "SPECIALIZED_EXECUTOR"


def job_execution_record(job_type: str, department: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    execution_class = classify_job(job_type, department, payload)
    return {
        "execution_class": execution_class,
        "model_call_required": execution_class in {"LIGHT_REASONING", "STRONG_REASONING"},
        "executor": str(department or "NEXUS").upper(),
        "workflow_controlled": True,
        "step_reason": (payload or {}).get("step_reason") if isinstance(payload, dict) else None,
    }


def nova_execution_plan(semantic: dict[str, Any]) -> dict[str, Any]:
    """Declare Nova's deterministic front-door steps and delegated executor."""
    intent = str((semantic or {}).get("intent") or "UNKNOWN_OR_AMBIGUOUS").upper()
    deterministic_reads = {"CAPABILITY_QUERY", "LIVE_STATE_QUERY", "LIST_JOBS", "PRIOR_WORK_QUERY",
                           "STATUS_OF_EXISTING_TASK", "FOLLOWUP_QUERY"}
    direct_commands = {"DEPARTMENT_ASSIGNMENT", "RESEARCH_REQUEST", "CROSS_DEPARTMENT_CONTINUATION",
                       "RESEARCH_ROOM_REQUEST", "NEW_OWNER_OBJECTIVE", "MODIFY_EXISTING_OBJECTIVE", "CONTINUE_EXISTING_WORK",
                       "GOOGLE_ACTION", "BROWSER_ACTION", "FILE_OR_DOCUMENT_ACTION"}
    if intent in deterministic_reads:
        return {"intent": intent, "execution_class": "DETERMINISTIC", "model_call_required": False,
            "steps": ["semantic_route", "known_capability_read", "format_result", "telegram_send"],
            "executor_class": "SPECIALIZED_EXECUTOR"}
    if intent in direct_commands:
        if intent == "RESEARCH_ROOM_REQUEST":
            return {"intent": intent, "execution_class": "SPECIALIZED_EXECUTOR", "model_call_required": True,
                "steps": ["semantic_route", "research_room_shadow_intake", "final_strategist", "proposed_handoffs", "telegram_send"],
                "executor_class": "SPECIALIZED_EXECUTOR", "governance_before_research": False}
        return {"intent": intent, "execution_class": "DETERMINISTIC", "model_call_required": False,
            "steps": ["semantic_route", "durable_job_or_objective_write", "acknowledgment_send"],
            "executor_class": "SPECIALIZED_EXECUTOR"}
    return {"intent": intent, "execution_class": "LIGHT_REASONING", "model_call_required": True,
        "steps": ["natural_language_interpretation", "capability_selection", "governed_executor", "format_result", "telegram_send"],
        "executor_class": "SPECIALIZED_EXECUTOR"}
