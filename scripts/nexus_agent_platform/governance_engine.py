"""Canonical Nexus governance decisions.

This is a policy/receipt layer, not an executor.  Existing department
executors, approval records, the compliance engine, and Resource Governor
remain the owners of their respective work.  Governance only answers whether
an attempted action is within the actor's authority and what must happen next.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from .governed import persistence


SUBJECTS = {
    "RAY", "CEO_NEXUS", "NOVA", "RESEARCH", "ALPHA", "MARKETING",
    "COMPLIANCE", "CREATIVE", "CUSTOMER_SERVICE", "SOCIAL_DISTRIBUTION",
    "FUNDING_CLYDE", "CREDIT", "SYSTEMS", "TRADING", "RESOURCE_GOVERNOR",
    "TEMPORARY_WORKER", "HUMAN_SPECIALIST", "EXTERNAL_VENDOR",
}
ACTION_CLASSES = {
    "READ_INTERNAL_STATE", "READ_CUSTOMER_STATE", "RESEARCH_PUBLIC_INFORMATION",
    "CREATE_INTERNAL_ARTIFACT", "MODIFY_INTERNAL_ARTIFACT", "CREATE_WORK_ORDER",
    "ROUTE_WORK", "RUN_LOCAL_COMPUTE", "RUN_EXTERNAL_FREE_COMPUTE",
    "RUN_PAID_COMPUTE", "ACCESS_CUSTOMER_PII", "CONTACT_CUSTOMER", "SEND_EMAIL",
    "SEND_SMS", "SEND_SOCIAL_DM", "PUBLISH_SOCIAL", "PUBLISH_WEB",
    "CREATE_EXTERNAL_ACCOUNT", "MODIFY_EXTERNAL_ACCOUNT", "SPEND_MONEY",
    "COMMIT_CONTRACT", "ISSUE_REFUND", "CHANGE_PRICING", "APPROVE_FUNDING",
    "MAKE_CREDIT_DECISION", "EXECUTE_TRADE", "DELETE_CUSTOMER_DATA",
    "MODIFY_SECURITY_POLICY", "ACCESS_SECRET", "OVERRIDE_COMPLIANCE", "OTHER",
}
TIERS = {"TIER_0_AUTONOMOUS", "TIER_1_AUTONOMOUS_WITH_RECEIPT", "TIER_2_POLICY_GATED", "TIER_3_HUMAN_APPROVAL", "TIER_4_PROHIBITED"}
DATA_CLASSES = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "CUSTOMER_PII", "FINANCIAL_SENSITIVE", "CREDENTIAL_SECRET", "REGULATED", "BUSINESS_RESTRICTED"}
RETRY_CATEGORIES = {"RETRYABLE_INTERNAL", "RETRYABLE_EXTERNAL", "REROUTABLE", "WAIT_FOR_DEPENDENCY", "HUMAN_REQUIRED", "PERMANENT_FAILURE", "POLICY_BLOCKED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(str(value).encode()).hexdigest()[:16]}"


@dataclass(frozen=True)
class AuthoritySubject:
    subject_id: str
    subject_type: str
    role: str
    authority_scope: tuple[str, ...] = ()
    data_scopes: tuple[str, ...] = ("PUBLIC", "INTERNAL")

    def __post_init__(self) -> None:
        if self.subject_type not in SUBJECTS:
            raise ValueError(f"unknown authority subject: {self.subject_type}")


@dataclass
class GovernanceStore:
    decisions: list[dict[str, Any]] = field(default_factory=list)
    overrides: list[dict[str, Any]] = field(default_factory=list)
    exceptions: list[dict[str, Any]] = field(default_factory=list)


DEPARTMENT_AUTHORITY: dict[str, dict[str, Any]] = {
    "RESEARCH": {"allow": {"RESEARCH_PUBLIC_INFORMATION", "READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT", "CREATE_WORK_ORDER", "ROUTE_WORK"}},
    "ALPHA": {"allow": {"READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT", "ROUTE_WORK"}},
    "MARKETING": {"allow": {"READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT", "MODIFY_INTERNAL_ARTIFACT", "CREATE_WORK_ORDER", "ROUTE_WORK"}},
    "COMPLIANCE": {"allow": {"READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT", "ROUTE_WORK"}},
    "CREATIVE": {"allow": {"READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT", "MODIFY_INTERNAL_ARTIFACT", "RUN_LOCAL_COMPUTE", "RUN_EXTERNAL_FREE_COMPUTE"}},
    "CUSTOMER_SERVICE": {"allow": {"READ_INTERNAL_STATE", "READ_CUSTOMER_STATE", "CREATE_INTERNAL_ARTIFACT", "CREATE_WORK_ORDER"}},
    "SOCIAL_DISTRIBUTION": {"allow": {"READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT"}},
    "RESOURCE_GOVERNOR": {"allow": {"READ_INTERNAL_STATE", "RUN_LOCAL_COMPUTE", "RUN_EXTERNAL_FREE_COMPUTE"}},
    "SYSTEMS": {"allow": {"READ_INTERNAL_STATE", "CREATE_INTERNAL_ARTIFACT", "MODIFY_INTERNAL_ARTIFACT", "CREATE_WORK_ORDER", "ROUTE_WORK", "RUN_LOCAL_COMPUTE"}},
    "TEMPORARY_WORKER": {"allow": {"CREATE_INTERNAL_ARTIFACT", "RUN_LOCAL_COMPUTE", "RUN_EXTERNAL_FREE_COMPUTE"}},
}


class GovernanceEngine:
    """Deterministic authority decisions with explainable, durable receipts."""

    def __init__(self, store: GovernanceStore | None = None, *, persist: bool = True) -> None:
        self.store = store or GovernanceStore()
        self.persist = persist

    def evaluate_authority(self, subject: str | AuthoritySubject, action: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        actor = subject.subject_type if isinstance(subject, AuthoritySubject) else str(subject)
        context = context or {}
        action = action.upper()
        if actor not in SUBJECTS or action not in ACTION_CLASSES:
            return self._decision(actor, action, "BLOCK", "TIER_4_PROHIBITED", "unknown subject or action class", context)
        if context.get("cross_business") or context.get("cross_tenant") or context.get("cross_brand"):
            return self._decision(actor, action, "BLOCK", "TIER_4_PROHIBITED", "cross-business/tenant/brand boundary", context)
        if context.get("gpu_required") and context.get("gpu_capability_verified") is not True:
            return self._decision(actor, action, "BLOCK", "TIER_2_POLICY_GATED", "GPU capability is not verified", context)
        if action in {"EXECUTE_TRADE", "COMMIT_CONTRACT", "MODIFY_SECURITY_POLICY", "DELETE_CUSTOMER_DATA", "ACCESS_SECRET"}:
            return self._decision(actor, action, "HUMAN_APPROVAL_REQUIRED", "TIER_3_HUMAN_APPROVAL", "Ray-reserved or sensitive action", context)
        if action in {"PUBLISH_SOCIAL", "PUBLISH_WEB", "SEND_EMAIL", "SEND_SMS", "SEND_SOCIAL_DM", "CREATE_EXTERNAL_ACCOUNT", "MODIFY_EXTERNAL_ACCOUNT", "SPEND_MONEY", "RUN_PAID_COMPUTE", "ISSUE_REFUND", "CHANGE_PRICING", "APPROVE_FUNDING", "MAKE_CREDIT_DECISION"}:
            return self._decision(actor, action, "HUMAN_APPROVAL_REQUIRED", "TIER_3_HUMAN_APPROVAL", "external, financial, or customer-impacting action", context)
        if action == "ACCESS_CUSTOMER_PII" and actor not in {"RAY", "CEO_NEXUS", "CUSTOMER_SERVICE", "FUNDING_CLYDE", "CREDIT"}:
            return self._decision(actor, action, "BLOCK", "TIER_4_PROHIBITED", "subject lacks customer-data scope", context)
        if action == "READ_CUSTOMER_STATE" and not context.get("customer_verified", False):
            return self._decision(actor, action, "BLOCK", "TIER_2_POLICY_GATED", "customer-specific state requires authenticated verification", context)
        if actor == "TEMPORARY_WORKER" and context.get("data_class") in {"CUSTOMER_PII", "FINANCIAL_SENSITIVE", "CREDENTIAL_SECRET", "REGULATED"}:
            return self._decision(actor, action, "BLOCK", "TIER_4_PROHIBITED", "temporary workers receive no sensitive customer data", context)
        allowed = DEPARTMENT_AUTHORITY.get(actor, {}).get("allow", set())
        if actor not in {"RAY", "CEO_NEXUS", "NOVA"} and action not in allowed:
            return self._decision(actor, action, "HUMAN_APPROVAL_REQUIRED", "TIER_3_HUMAN_APPROVAL", "outside department authority", context)
        tier = "TIER_1_AUTONOMOUS_WITH_RECEIPT" if action in {"CREATE_WORK_ORDER", "ROUTE_WORK", "CREATE_INTERNAL_ARTIFACT", "MODIFY_INTERNAL_ARTIFACT", "RUN_LOCAL_COMPUTE", "RUN_EXTERNAL_FREE_COMPUTE"} else "TIER_0_AUTONOMOUS"
        return self._decision(actor, action, "ALLOW", tier, "bounded internal action within subject authority", context)

    def _decision(self, actor: str, action: str, decision: str, tier: str, reason: str, context: dict[str, Any]) -> dict[str, Any]:
        record = {"governance_receipt_id": _id("gov", f"{actor}:{action}:{context}"), "subject": actor, "action": action, "business_id": context.get("business_id"), "authority_tier": tier, "risk": context.get("risk", "LOW"), "policy_refs": context.get("policy_refs", ["nexus.governance.v1"]), "decision": decision, "required_approvals": ["RAY"] if tier == "TIER_3_HUMAN_APPROVAL" else [], "evidence": context.get("evidence", []), "reason": reason, "timestamp": _now(), "next_action": context.get("next_action", "CONTINUE_UNRELATED_WORK")}
        self.store.decisions.append(record)
        if self.persist:
            try:
                persistence.emit_audit_event({"event_type": "GOVERNANCE_DECISION", **record})
            except Exception:
                pass
        return record

    def evaluate_risk(self, action: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        if action in {"SPEND_MONEY", "RUN_PAID_COMPUTE", "PUBLISH_SOCIAL", "EXECUTE_TRADE"}: return "HIGH"
        if context.get("data_class") in {"CUSTOMER_PII", "FINANCIAL_SENSITIVE", "CREDENTIAL_SECRET", "REGULATED"}: return "HIGH"
        return str(context.get("risk", "LOW"))

    def evaluate_required_approval(self, action: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"required": self.evaluate_authority("NOVA", action, context).get("authority_tier") == "TIER_3_HUMAN_APPROVAL", "approver": "RAY"}

    def evaluate_spend_authority(self, *, cost: Any = "UNKNOWN", provider: str = "UNKNOWN", context: dict[str, Any] | None = None) -> dict[str, Any]:
        if cost in (0, "0", "FREE", "FREE_QUOTA") and context and context.get("approved_free_resource"):
            return {"decision": "ALLOW", "reason": "approved free resource within quota/data policy"}
        return {"decision": "REQUIRES_HUMAN_APPROVAL", "reason": f"cost={cost} provider={provider}; unknown cost is not free"}

    def evaluate_data_access(self, subject: str, data_class: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if data_class not in DATA_CLASSES: return {"decision": "BLOCK", "reason": "unknown data class"}
        return self.evaluate_authority(subject, "ACCESS_CUSTOMER_PII" if data_class in {"CUSTOMER_PII", "FINANCIAL_SENSITIVE"} else "READ_INTERNAL_STATE", {**(context or {}), "data_class": data_class})

    def evaluate_external_action(self, action: str, context: dict[str, Any] | None = None) -> dict[str, Any]: return self.evaluate_authority("NOVA", action, context)
    def evaluate_customer_contact(self, context: dict[str, Any] | None = None) -> dict[str, Any]: return self.evaluate_external_action("CONTACT_CUSTOMER", context)
    def evaluate_publication(self, context: dict[str, Any] | None = None) -> dict[str, Any]: return self.evaluate_external_action("PUBLISH_SOCIAL", context)
    def evaluate_retry(self, category: str, *, bounded: bool = True) -> dict[str, Any]: return {"allowed": category in RETRY_CATEGORIES and bounded and category not in {"HUMAN_REQUIRED", "PERMANENT_FAILURE", "POLICY_BLOCKED"}, "category": category, "bounded": bounded}
    def evaluate_reroute(self, *, from_capability: str, to_capability: str, reason: str) -> dict[str, Any]: return {"allowed": bool(from_capability and to_capability), "from": from_capability, "to": to_capability, "reason": reason, "receipt_id": _id("reroute", f"{from_capability}:{to_capability}:{reason}")}
    def evaluate_escalation(self, reason: str, *, unrelated_work_continues: bool = True) -> dict[str, Any]: return {"required": reason in {"human authorization", "security", "legal", "privacy", "refund exception", "policy override"}, "reason": reason, "unrelated_work_continues": unrelated_work_continues}
    def record_decision(self, decision: dict[str, Any]) -> dict[str, Any]: self.store.decisions.append(decision); return decision
    def record_override(self, *, policy: str, reason: str, authorized_by: str, scope: dict[str, Any], expires_at: str) -> dict[str, Any]:
        if authorized_by != "RAY": raise ValueError("only Ray may create governance overrides")
        value = {"override_id": _id("override", f"{policy}:{scope}:{expires_at}"), "policy": policy, "reason": reason, "authorized_by": authorized_by, "scope": scope, "expires_at": expires_at, "created_at": _now()}
        self.store.overrides.append(value); return value
    def record_exception(self, reason: str, scope: dict[str, Any]) -> dict[str, Any]:
        value = {"exception_id": _id("exception", f"{reason}:{scope}"), "reason": reason, "scope": scope, "created_at": _now()}; self.store.exceptions.append(value); return value
    def explain_decision(self, decision: dict[str, Any]) -> str: return f"{decision.get('decision')}: {decision.get('reason')} (tier={decision.get('authority_tier')})"

    def govern_crj_failure(self, record: dict[str, Any]) -> dict[str, Any]:
        missing = not record.get("source_url") and "unknown url type" in str(record.get("error", ""))
        if missing:
            decision = self._decision("CEO_NEXUS", "ROUTE_WORK", "ALLOW", "TIER_1_AUTONOMOUS_WITH_RECEIPT", "missing source URL is a bounded internal repair/reroute; no source is invented", {"evidence": [record.get("objective_id", "crj-goclear-capability-research-v1")], "next_action": "REPAIR_OR_REROUTE_RESEARCH_OBJECTIVE"})
            decision.update({"self_repair_action": "inspect objective, remove empty source dispatch, reroute through existing multi-source Research acquisition", "ray_required": False, "objective_status_after": "FAILED_RETRYABLE_PENDING_GOVERNED_REPAIR"})
            return decision
        return {"decision": "RESEARCH_MORE", "ray_required": False, "objective_status_after": record.get("status", "UNKNOWN")}


def governance_contracts() -> dict[str, Any]:
    return {"subjects": sorted(SUBJECTS), "action_classes": sorted(ACTION_CLASSES), "tiers": sorted(TIERS), "data_classes": sorted(DATA_CLASSES), "retry_categories": sorted(RETRY_CATEGORIES), "auto_spend_allowed": False, "resource_governor_mode": "SHADOW", "publication_default": "APPROVAL_REQUIRED", "customer_contact_default": "HUMAN_OR_APPROVED_SUPPORT_CONTEXT"}
