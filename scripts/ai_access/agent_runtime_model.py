"""Shared model for the AI Agent Runtime verification/report.

Mirrors src/lib/nexusAgentRuntime.ts (VAULT_METHOD_SPECS + guard logic) on top of ai_access_model.
Deterministic, local-first. Simulates the runtime guard to prove enforcement + audit logging without
executing TS. No external calls, no DB writes.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ai_access"))
import ai_access_model as m  # noqa: E402

# method -> (tool, data_category, audit_category, client_scoped)
VAULT_METHOD_SPECS = {
    "listClientProfiles": ("client_vault_adapter", "client_name", "client_profile", False),
    "getCreditReport": ("client_vault_adapter", "raw_credit_report", "raw_credit_report", True),
    "getCreditScoreSnapshots": ("client_vault_adapter", "credit_score_raw", "credit_score", True),
    "getBusinessProfile": ("client_vault_adapter", "business_profile", "business_profile", True),
    "listBusinessSetupItems": ("client_vault_adapter", "business_setup_item", "business_setup_item", True),
    "listProofUploads": ("client_vault_adapter", "proof_upload", "proof_upload", True),
    "listLetterPackets": ("client_vault_adapter", "raw_letter", "raw_letter", True),
    "listMailingRecords": ("client_vault_adapter", "mailing_record", "mailing_record", True),
    "listWorkflowTasks": ("client_vault_adapter", "workflow_task", "workflow_task", True),
    "listReminderTasks": ("client_vault_adapter", "reminder_task", "reminder_task", True),
    "getFundingReadiness": ("client_vault_adapter", "funding_readiness", "funding_readiness", True),
    "listAffiliateAttribution": ("client_vault_adapter", "affiliate_attribution", "affiliate_attribution", True),
    "listConsentEvents": ("client_vault_adapter", "client_consent_record", "consent_event", True),
    "exportSanitizedSignals": ("sanitized_client_signals", "sanitized_signal", "sanitized_signal", False),
}


def can_use_tool(role: str, tool: str) -> bool:
    acc = m.TOOL_ACCESS.get(role, {"allowed": set(), "blocked": set()})
    if tool in acc["blocked"]:
        return False
    return tool in acc["allowed"]


def simulate(role: str, method: str, client_id: str, allowed_client_id: str | None = None) -> dict:
    """Mirror of NexusAgentRuntime.guard(): returns the access decision + audit event."""
    tool, data_cat, audit_cat, client_scoped = VAULT_METHOD_SPECS[method]
    denied_reason = None
    if not can_use_tool(role, tool):
        denied_reason = f"{role} blocked from tool {tool}."
    elif not m.can_access_data(role, data_cat):
        denied_reason = f"{role} has no access to {data_cat}."
    elif client_scoped and role == "client_chat_ai" and (allowed_client_id is None or allowed_client_id != client_id):
        denied_reason = f"Client Chat AI scoped to {allowed_client_id}; cannot read {client_id}."
    allowed = denied_reason is None
    audit = {
        "agent_role": role,
        "client_id": client_id,
        "access_type": audit_cat if allowed else "denied",
        "data_category": audit_cat,
        "allowed": allowed,
        "denied_reason": denied_reason,
    }
    return {"allowed": allowed, "data_returned": allowed, "denied_reason": denied_reason, "audit": audit}


ROLES = list(m.ROLE_META.keys())
METHODS = list(VAULT_METHOD_SPECS.keys())
PRIVATE_METHODS = [k for k, v in VAULT_METHOD_SPECS.items() if v[1] != "sanitized_signal"]
