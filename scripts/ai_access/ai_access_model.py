"""Shared AI access model for verification/report scripts.

Mirrors src/config/nexusAIDepartmentRoles.ts, nexusAIAgentAccessPolicy.ts,
nexusClientDataSensitivityPolicy.ts, and src/lib/nexusAIAccessPolicy.ts. Deterministic, local-first.
No external calls, no DB writes.
"""
from __future__ import annotations

from datetime import datetime, timezone

INTERNET_TOOLS = {"internet", "web_browse", "youtube", "external_ai_api"}

# role -> {allowed_tools, blocked_tools}
TOOL_ACCESS = {
    "hermes_ceo_advisor": {
        "allowed": {"internet", "web_browse", "supabase_system_reports", "sanitized_client_signals", "approved_knowledge"},
        "blocked": {"client_vault_adapter", "external_ai_api"},
    },
    "researcher_ai": {
        "allowed": {"internet", "web_browse", "youtube", "supabase_system_reports", "approved_knowledge"},
        "blocked": {"client_vault_adapter", "sanitized_client_signals"},
    },
    "credit_specialist_ai": {
        "allowed": {"supabase_system_reports", "sanitized_client_signals", "client_vault_adapter", "approved_knowledge"},
        "blocked": {"internet", "web_browse", "youtube", "external_ai_api", "unapproved_research"},
    },
    "funding_specialist_ai": {
        "allowed": {"supabase_system_reports", "sanitized_client_signals", "client_vault_adapter", "approved_knowledge"},
        "blocked": {"internet", "web_browse", "youtube", "external_ai_api", "unapproved_research"},
    },
    "business_setup_specialist_ai": {
        "allowed": {"supabase_system_reports", "sanitized_client_signals", "client_vault_adapter", "approved_knowledge"},
        "blocked": {"internet", "web_browse", "youtube", "external_ai_api", "unapproved_research"},
    },
    "client_chat_ai": {
        "allowed": {"client_vault_adapter", "approved_knowledge"},
        "blocked": {"internet", "web_browse", "youtube", "external_ai_api", "supabase_system_reports", "unapproved_research"},
    },
}

# role meta
ROLE_META = {
    "hermes_ceo_advisor": {"internet": True, "vault": False, "approved_knowledge_only": False, "client_facing": "approval_gated"},
    "researcher_ai": {"internet": True, "vault": False, "approved_knowledge_only": False, "client_facing": "blocked"},
    "credit_specialist_ai": {"internet": False, "vault": True, "approved_knowledge_only": True, "client_facing": "approval_gated"},
    "funding_specialist_ai": {"internet": False, "vault": True, "approved_knowledge_only": True, "client_facing": "approval_gated"},
    "business_setup_specialist_ai": {"internet": False, "vault": True, "approved_knowledge_only": True, "client_facing": "approval_gated"},
    "client_chat_ai": {"internet": False, "vault": True, "approved_knowledge_only": True, "client_facing": "approval_gated"},
}

# data category -> {hermes_allowed, vault_only}
DATA_CATEGORIES = {
    "sanitized_signal": {"hermes_allowed": True, "vault_only": False},
    "aggregate_metric": {"hermes_allowed": True, "vault_only": False},
    "stage_count": {"hermes_allowed": True, "vault_only": False},
    "workflow_status_internal": {"hermes_allowed": True, "vault_only": False},
    "client_name": {"hermes_allowed": False, "vault_only": True},
    "client_contact": {"hermes_allowed": False, "vault_only": True},
    "address": {"hermes_allowed": False, "vault_only": True},
    "dob": {"hermes_allowed": False, "vault_only": True},
    "ssn": {"hermes_allowed": False, "vault_only": True},
    "account_number": {"hermes_allowed": False, "vault_only": True},
    "creditor_account_detail": {"hermes_allowed": False, "vault_only": True},
    "bank_statement": {"hermes_allowed": False, "vault_only": True},
    "raw_credit_report": {"hermes_allowed": False, "vault_only": True},
    "smartcredit_file": {"hermes_allowed": False, "vault_only": True},
    "credit_score_raw": {"hermes_allowed": False, "vault_only": True},
    "raw_letter": {"hermes_allowed": False, "vault_only": True},
    "funding_document": {"hermes_allowed": False, "vault_only": True},
    "client_consent_record": {"hermes_allowed": False, "vault_only": True},
    "business_profile": {"hermes_allowed": False, "vault_only": True},
    "business_setup_item": {"hermes_allowed": False, "vault_only": True},
    "workflow_task": {"hermes_allowed": False, "vault_only": True},
    "reminder_task": {"hermes_allowed": False, "vault_only": True},
    "funding_readiness": {"hermes_allowed": False, "vault_only": True},
    "proof_upload": {"hermes_allowed": False, "vault_only": True},
    "mailing_record": {"hermes_allowed": False, "vault_only": True},
    "affiliate_attribution": {"hermes_allowed": False, "vault_only": True},
}

HERMES_FORBIDDEN_FIELDS = [
    "full_client_name", "full_credit_report", "smartcredit_file", "smartcredit_import", "ssn", "dob",
    "address", "account_number", "creditor_account_detail", "bank_statement", "raw_letter",
    "private_funding_document",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def can_access_data(role: str, category: str) -> bool:
    d = DATA_CATEGORIES.get(category)
    meta = ROLE_META.get(role, {})
    if not d:
        return False
    if not d["vault_only"]:
        # Sanitized/aggregate/internal: readable if Hermes-safe or the role has system-report access.
        return bool(d["hermes_allowed"]) or bool(meta.get("vault"))
    # Private vault-only data: only roles with vault adapter access.
    return bool(meta.get("vault"))


def verify_invariants() -> list[dict]:
    v = []
    # 1. Hermes cannot access private data.
    for cat in ["raw_credit_report", "smartcredit_file", "bank_statement", "raw_letter", "ssn", "dob", "account_number"]:
        if can_access_data("hermes_ceo_advisor", cat):
            v.append({"rule": "hermes_no_raw_client_data", "role": "hermes_ceo_advisor", "detail": f"Hermes could access {cat}"})
    # 2. Internet + vault separation.
    for role, acc in TOOL_ACCESS.items():
        if (acc["allowed"] & INTERNET_TOOLS) and ("client_vault_adapter" in acc["allowed"]):
            v.append({"rule": "internet_and_vault_separation", "role": role, "detail": f"{role} has internet and vault"})
    # 3. Specialists no web tools.
    for role in ["credit_specialist_ai", "funding_specialist_ai", "business_setup_specialist_ai"]:
        if TOOL_ACCESS[role]["allowed"] & INTERNET_TOOLS:
            v.append({"rule": "specialist_supabase_only", "role": role, "detail": f"{role} has web tools"})
    # 4. Researcher no PII.
    if can_access_data("researcher_ai", "raw_credit_report") or can_access_data("researcher_ai", "ssn"):
        v.append({"rule": "researcher_no_client_pii", "role": "researcher_ai", "detail": "Researcher could access PII"})
    # 5. Client-facing gated.
    for role, meta in ROLE_META.items():
        if meta["client_facing"] not in ("blocked", "approval_gated"):
            v.append({"rule": "client_facing_gated", "role": role, "detail": f"{role} not gated"})
    # 6. Specialists + client chat approved-knowledge-only.
    for role in ["credit_specialist_ai", "funding_specialist_ai", "business_setup_specialist_ai", "client_chat_ai"]:
        if not ROLE_META[role]["approved_knowledge_only"]:
            v.append({"rule": "approved_knowledge_only", "role": role, "detail": f"{role} not approved-knowledge-only"})
    return v
