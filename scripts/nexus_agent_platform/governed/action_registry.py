"""Canonical governed action registry and bounded risk model.

Only LOW-risk actions may execute. MODERATE/HIGH may be recommended but never
executed in this sprint. PROHIBITED never executes. No dynamic action names, no
generated shell commands. Every executable action must be explicitly registered.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Risk:
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    PROHIBITED = "prohibited"


# Execution ranks: only LOW is executable.
EXECUTABLE_RISKS = frozenset({Risk.LOW})
ALL_RISKS = frozenset({Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.PROHIBITED})

# Actions exposed as governable by Nova this sprint. Kept deliberately tiny.
# PROHIBITED and HIGH classes exist as documented non-executable categories, not
# as registered executor actions.
ACTION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "opportunity.review": {
        "action_id": "opportunity.review",
        "name": "Review Governed Opportunity",
        "description": "Record Ray's explicit review decision for one bounded opportunity.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "record_opportunity_review",
        "input_schema": {"type": "object", "properties": {"opportunity_id": {"type": "string"}}, "required": ["opportunity_id"]},
        "result_schema": {"type": "object", "properties": {"opportunity_id": {"type": "string"}, "decision": {"type": "string"}}},
        "timeout_seconds": 60,
        "idempotency_supported": True,
        "telemetry_process_id": "opportunity_review",
        "enabled": True,
    },
    "system_health.run": {
        "action_id": "system_health.run",
        "name": "Run System Health Check",
        "description": "Run a fresh composite Nexus system health check and record its result.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "run_system_health_action",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "result_schema": {
            "type": "object",
            "properties": {
                "overall_status": {"type": "string"},
                "active_services": {"type": "integer"},
                "sources_checked": {"type": "array"},
            },
        },
        "timeout_seconds": 120,
        "idempotency_supported": True,
        "telemetry_process_id": "system_health",
        "enabled": True,
    },
    "repo_intelligence.scan": {
        "action_id": "repo_intelligence.scan",
        "name": "Run Repo Intelligence Scan",
        "description": "Run a bounded repo intelligence scan (AI agent runtime report) and record its result.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "run_repo_intelligence_action",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "result_schema": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "counts": {"type": "object"},
            },
        },
        "timeout_seconds": 180,
        "idempotency_supported": True,
        "telemetry_process_id": "repo_intelligence",
        "enabled": True,
    },
    "nexus_study.refresh": {
        "action_id": "nexus_study.refresh",
        "name": "Refresh Bounded Nexus Study",
        "description": "Run a bounded one-pass Nexus study refresh and write fresh study artifacts.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "run_nexus_study_refresh_action",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "result_schema": {
            "type": "object",
            "properties": {
                "domains": {"type": "integer"},
                "artifacts": {"type": "array"},
            },
        },
        "timeout_seconds": 300,
        "idempotency_supported": True,
        "telemetry_process_id": "nexus_study",
        "enabled": True,
    },
    "runtime_report.generate": {
        "action_id": "runtime_report.generate",
        "name": "Generate Runtime Report",
        "description": "Generate a bounded internal runtime report artifact.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "run_runtime_report_action",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "result_schema": {
            "type": "object",
            "properties": {},
        },
        "timeout_seconds": 120,
        "idempotency_supported": True,
        "telemetry_process_id": "runtime_report",
        "enabled": True,
    },
    "business_attention.review": {
        "action_id": "business_attention.review",
        "name": "Review Business Attention",
        "description": "Review one bounded GoClear business-attention finding; no external action.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "record_business_attention_review",
        "input_schema": {"type": "object", "properties": {"finding_id": {"type": "string"}}, "required": ["finding_id"]},
        "result_schema": {"type": "object", "properties": {"finding_id": {"type": "string"}, "decision": {"type": "string"}}},
        "timeout_seconds": 60,
        "idempotency_supported": True,
        "telemetry_process_id": "business_attention_review",
        "enabled": True,
    },
    "engineering.repair.voice": {
        "action_id": "engineering.repair.voice",
        "name": "Bounded Voice Engineering Repair",
        "description": "Run the explicitly approved VOICE-001 repair in an isolated coding worker; deployment remains separately gated.",
        "risk_level": Risk.LOW,
        "approval_required": True,
        "executor": "run_voice_engineering_repair",
        "input_schema": {
            "type": "object",
            "properties": {"repair_id": {"type": "string"}, "run_id": {"type": "string"}},
            "required": ["repair_id", "run_id"],
        },
        "result_schema": {"type": "object", "properties": {"state": {"type": "string"}}},
        "timeout_seconds": 900,
        "idempotency_supported": True,
        "telemetry_process_id": "voice_engineering_repair",
        "enabled": True,
    },
}

# Documented, non-executable classes (for honest recommendation labelling).
# These exist so Nova can say "I can recommend this but cannot execute it yet."
KNOWN_NON_EXECUTABLE_RECOMMENDATIONS: List[Dict[str, Any]] = [
    {"action_id": "stripe.live_activation", "name": "Activate Stripe live checkout", "risk_level": Risk.HIGH},
    {"action_id": "git.commit_push", "name": "Commit and push repository changes", "risk_level": Risk.HIGH},
    {"action_id": "deploy.netlify", "name": "Deploy to production", "risk_level": Risk.HIGH},
    {"action_id": "client.sends", "name": "Send client communications", "risk_level": Risk.HIGH},
    {"action_id": "financial.transactions", "name": "Financial transactions", "risk_level": Risk.PROHIBITED},
    {"action_id": "credit.report_mutation", "name": "Credit report or bureau mutation", "risk_level": Risk.PROHIBITED},
    {"action_id": "shell.arbitrary", "name": "Arbitrary shell commands", "risk_level": Risk.PROHIBITED},
    {"action_id": "code.schema_migration", "name": "Database schema migration", "risk_level": Risk.HIGH},
]


def get_action(action_id: str) -> Optional[Dict[str, Any]]:
    return ACTION_REGISTRY.get(action_id)


def action_exists(action_id: str) -> bool:
    return action_id in ACTION_REGISTRY


def is_action_enabled(action_id: str) -> bool:
    action = get_action(action_id)
    return bool(action and action.get("enabled"))


def is_action_executable(action_id: str) -> bool:
    action = get_action(action_id)
    if not action:
        return False
    if not action.get("enabled"):
        return False
    return action.get("risk_level") in EXECUTABLE_RISKS


def risk_rank(level: Optional[str]) -> int:
    order = {Risk.LOW: 0, Risk.MODERATE: 1, Risk.HIGH: 2, Risk.PROHIBITED: 3}
    return order.get(level or "", 10)


def list_actions() -> List[Dict[str, Any]]:
    return [
        {k: v for k, v in action.items() if k != "result_schema"}
        for action in ACTION_REGISTRY.values()
    ]


def list_available_actions() -> List[Dict[str, Any]]:
    """Actions visible to Nova — includes non-executable documented classes so
    recommendations are honest about what is unavailable."""
    available = [a for a in list_actions()]
    available.extend(KNOWN_NON_EXECUTABLE_RECOMMENDATIONS)
    return available


def validate_action_id(action_id: str) -> bool:
    """No dynamic action names, no arbitrary path/function names from the model."""
    if not isinstance(action_id, str):
        return False
    if action_id not in ACTION_REGISTRY:
        return False
    return True
