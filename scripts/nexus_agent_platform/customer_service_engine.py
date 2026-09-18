"""Multi-product, context-scoped Customer Service Engine.

This is an internal decision layer. It does not send messages, issue refunds,
change customer records, or grant executive/system access.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from scripts.nexus_agent_platform.compliance_engine import ProductCompliancePack, evaluate_domain_claim, required_disclosures, stable_id

CASE_STATUSES = ("NEW", "OPEN", "IN_PROGRESS", "WAITING_CUSTOMER", "WAITING_NEXUS", "ESCALATED", "RESOLVED", "CLOSED")
INTENTS = ("GENERAL_QUESTION", "ONBOARDING_HELP", "STATUS_REQUEST", "DOCUMENT_REQUIREMENT", "DOCUMENT_UPLOAD_HELP", "NEXT_STEP", "PRODUCT_EXPLANATION", "ELIGIBILITY_QUESTION", "FUNDING_READINESS", "CREDIT_READINESS", "TECHNICAL_HELP", "ACCOUNT_ACCESS", "BILLING", "REFUND_REQUEST", "CANCELLATION", "COMPLAINT", "POLICY_QUESTION", "DATA_PRIVACY", "SECURITY", "ESCALATION_REQUEST", "OTHER")
PRIORITIES = ("URGENT", "HIGH", "NORMAL", "LOW")
ALLOWED_ACTIONS = ("READ_CUSTOMER_STATUS", "READ_MISSING_DOCUMENTS", "READ_NEXT_STEP", "EXPLAIN_PROCESS", "CREATE_CASE", "UPDATE_CASE", "REQUEST_DOCUMENT", "SEND_APPROVED_STATUS_UPDATE", "ROUTE_TO_DEPARTMENT", "SCHEDULE_INTERNAL_REVIEW", "CLOSE_RESOLVED_CASE")
RESTRICTED_ACTIONS = ("APPROVE_FUNDING", "CHANGE_CREDIT_RESULT", "ISSUE_REFUND", "WAIVE_POLICY", "CHANGE_CUSTOMER_FINANCIAL_DATA", "DELETE_CUSTOMER_RECORD", "SEND_EXTERNAL_PAYMENT", "GUARANTEE_OUTCOME")


@dataclass
class CustomerContext:
    tenant_id: str | None = None; business_id: str | None = None; brand_id: str | None = None; customer_id: str | None = None
    product_id: str | None = None; offer_id: str | None = None; case_id: str | None = None; order_id: str | None = None
    verified: bool = False


@dataclass
class ProductSupportPack:
    support_pack_id: str; business_id: str; product_id: str; version: str; status: str
    supported_topics: list[str]; common_questions: list[str]; knowledge_refs: list[str]; workflow_refs: list[str]
    allowed_actions: list[str]; restricted_actions: list[str]; required_customer_data: list[str]; required_verification: list[str]
    status_explanations: list[str]; document_requirements: list[str]; refund_policy_ref: str | None
    complaint_policy_ref: str | None; escalation_rules: list[str]; sla_policy: dict[str, Any]; response_templates: list[str]
    customer_education_refs: list[str]; compliance_pack_ref: str


@dataclass
class SupportCase:
    case_id: str; tenant_id: str; business_id: str; customer_id: str; product_id: str; intent: str; category: str
    priority: str; status: str; summary: str; conversation_refs: list[str] = field(default_factory=list)
    knowledge_refs: list[str] = field(default_factory=list); compliance_refs: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list); requested_documents: list[str] = field(default_factory=list)
    assigned_department: str | None = None; assigned_agent: str | None = None; created_at: str = ""; updated_at: str = ""
    sla_due: str | None = None; next_action: str | None = None; resolution: str | None = None; resolution_code: str | None = None
    escalation_reason: str | None = None; customer_waiting: bool = False; nexus_waiting: bool = False


class CustomerServiceStore:
    def __init__(self): self.packs: dict[tuple[str, str], ProductSupportPack] = {}; self.cases: dict[str, SupportCase] = {}; self.interactions: list[dict[str, Any]] = []; self.voc_signals: list[dict[str, Any]] = []
    def register_pack(self, pack: ProductSupportPack) -> ProductSupportPack: self.packs[(pack.business_id, pack.product_id)] = pack; return pack
    def get_pack(self, business_id: str, product_id: str) -> ProductSupportPack | None: return self.packs.get((business_id, product_id))
    def persist_case(self, case: SupportCase) -> SupportCase: self.cases[case.case_id] = case; return case


def identify_support_intent(message: str) -> str:
    text = message.lower()
    if any(word in text for word in ("refund", "chargeback")): return "REFUND_REQUEST"
    if any(word in text for word in ("complaint", "lawyer", "legal")): return "COMPLAINT"
    if any(word in text for word in ("missing document", "what documents", "bank statement")): return "DOCUMENT_REQUIREMENT"
    if any(word in text for word in ("approval", "approved", "funded", "funding")): return "FUNDING_READINESS"
    if any(word in text for word in ("upload", "where do i submit")): return "DOCUMENT_UPLOAD_HELP"
    if any(word in text for word in ("status", "where am i", "progress")): return "STATUS_REQUEST"
    if any(word in text for word in ("next step", "what do i do next")): return "NEXT_STEP"
    if any(word in text for word in ("credit", "score")): return "CREDIT_READINESS"
    if any(word in text for word in ("privacy", "data")): return "DATA_PRIVACY"
    if any(word in text for word in ("security", "not me", "account access")): return "SECURITY"
    return "GENERAL_QUESTION"


def support_priority(intent: str, message: str) -> str:
    text = message.lower()
    if intent in {"SECURITY", "DATA_PRIVACY"} or any(word in text for word in ("legal", "lawyer", "chargeback")): return "URGENT"
    if intent in {"REFUND_REQUEST", "COMPLAINT", "ACCOUNT_ACCESS"}: return "HIGH"
    if intent in {"STATUS_REQUEST", "DOCUMENT_REQUIREMENT", "NEXT_STEP"}: return "NORMAL"
    return "LOW" if intent == "GENERAL_QUESTION" else "NORMAL"


def goclear_support_pack() -> ProductSupportPack:
    return ProductSupportPack("support_goclear_readiness_v1", "goclear", "readiness_review_97", "1", "READY_FOR_REVIEW",
        ["funding readiness", "credit readiness", "missing documents", "bank statements", "business bankability", "portal navigation", "status", "next steps"],
        ["What documents am I missing?", "What is my next step?", "Where do I upload documents?", "What does readiness mean?"],
        ["offer_registry:readiness_review_97", "funding_readiness_workflow", "client_portal:document_state"], ["document_review", "readiness_review", "ray_review"],
        ["READ_CUSTOMER_STATUS", "READ_MISSING_DOCUMENTS", "READ_NEXT_STEP", "EXPLAIN_PROCESS", "CREATE_CASE", "UPDATE_CASE", "REQUEST_DOCUMENT", "ROUTE_TO_DEPARTMENT", "SCHEDULE_INTERNAL_REVIEW"], list(RESTRICTED_ACTIONS),
        ["authenticated customer context", "product/offer context"], ["authenticated session for customer-specific state"], ["readiness is not approval", "customer-provided data may be incomplete"], ["bank statements when workflow requests them", "business formation/readiness records when requested"],
        "existing_refund_policy", "existing_complaint_policy", ["legal/privacy/security", "refund exception", "high-risk financial claim", "unknown state"], {"target": "existing policy; no invented SLA"}, ["clear next step", "no guarantee", "explain current state"], ["approved funding-readiness education"], "compliance_pack:goclear_readiness_v1")


class CustomerServiceEngine:
    def __init__(self, store: CustomerServiceStore | None = None, compliance_pack: ProductCompliancePack | None = None):
        self.store = store or CustomerServiceStore(); self.compliance_pack = compliance_pack or ProductCompliancePack("pack_goclear_readiness_v1", "goclear", "readiness_review_97", "1")

    def identify_customer_context(self, context: CustomerContext) -> dict[str, Any]:
        required = (context.tenant_id, context.business_id, context.customer_id, context.product_id)
        return {"known": all(required), "verified": context.verified, "context": asdict(context), "cross_scope_allowed": all(required) and context.verified}
    def identify_product_context(self, context: CustomerContext) -> ProductSupportPack | None: return self.store.get_pack(context.business_id or "", context.product_id or "")
    def load_support_pack(self, context: CustomerContext) -> ProductSupportPack | None: return self.identify_product_context(context)
    def load_compliance_pack(self, context: CustomerContext) -> ProductCompliancePack | None: return self.compliance_pack if context.product_id == self.compliance_pack.product_id else None
    def classify_support_intent(self, message: str) -> str: return identify_support_intent(message)
    def determine_allowed_response(self, message: str, context: CustomerContext) -> dict[str, Any]:
        intent = identify_support_intent(message); pack = self.load_support_pack(context); issues = []
        if not self.identify_customer_context(context)["known"]: issues.append("customer/product context incomplete")
        if pack is None: issues.append("support pack unavailable for this business/product")
        if "other business" in message.lower() or "another customer" in message.lower(): issues.append("cross-business/customer access denied")
        if intent in {"FUNDING_READINESS", "CREDIT_READINESS"}:
            review = evaluate_domain_claim(message, "funding" if intent == "FUNDING_READINESS" else "credit", [])
            issues.extend(review.get("issues", []))
        if self.compliance_pack.status != "APPROVED": issues.append("compliance pack is not APPROVED")
        if intent in {"SECURITY", "DATA_PRIVACY", "REFUND_REQUEST", "COMPLAINT"}: issues.append("human/policy review boundary")
        decision = "ESCALATE" if any(issue in {"customer/product context incomplete", "support pack unavailable for this business/product", "cross-business/customer access denied", "human/policy review boundary"} for issue in issues) else "QUALIFIED_WITH_QUALIFIER" if issues else "ALLOWED"
        return {"decision": decision, "intent": intent, "priority": support_priority(intent, message), "issues": issues, "pack_status": pack.status if pack else "UNAVAILABLE", "compliance_pack_status": self.compliance_pack.status, "qualifier": "Readiness information does not guarantee approval, funding amount, rate, or timeline." if intent in {"FUNDING_READINESS", "CREDIT_READINESS"} else None}
    def determine_allowed_action(self, action: str, context: CustomerContext) -> dict[str, Any]:
        pack = self.load_support_pack(context); allowed = bool(pack and action in pack.allowed_actions and action not in RESTRICTED_ACTIONS and self.identify_customer_context(context)["cross_scope_allowed"])
        return {"action": action, "allowed": allowed, "reason": "approved support-pack action" if allowed else "restricted, unverified, or context not authorized"}
    def create_case(self, message: str, context: CustomerContext) -> SupportCase:
        intent = identify_support_intent(message); now = datetime.now(timezone.utc).isoformat(); case = SupportCase(stable_id("case", f"{context.customer_id}:{message}"), context.tenant_id or "UNKNOWN", context.business_id or "UNKNOWN", context.customer_id or "UNKNOWN", context.product_id or "UNKNOWN", intent, intent, support_priority(intent, message), "ESCALATED" if intent in {"SECURITY", "DATA_PRIVACY", "REFUND_REQUEST", "COMPLAINT"} else "OPEN", message, created_at=now, updated_at=now, next_action="human review" if intent in {"SECURITY", "DATA_PRIVACY", "REFUND_REQUEST", "COMPLAINT"} else "provide grounded response")
        self.store.persist_case(case); return case
    def record_interaction(self, case: SupportCase, message: str, response: dict[str, Any]) -> dict[str, Any]:
        item = {"case_id": case.case_id, "message": message, "response": response, "recorded_at": datetime.now(timezone.utc).isoformat()}; self.store.interactions.append(item); return item
    def emit_voice_of_customer_signal(self, case: SupportCase, message: str) -> dict[str, Any]:
        signal = {"voc_signal_id": stable_id("voc", message), "business_id": case.business_id, "product_id": case.product_id, "source_case_id": case.case_id, "customer_intent": case.intent, "topic": case.category, "customer_language": message, "problem": case.summary, "desired_outcome": case.next_action, "frustration": case.priority in {"HIGH", "URGENT"}, "confusion": case.intent in {"DOCUMENT_REQUIREMENT", "NEXT_STEP"}, "request": message, "frequency_signal": "UNKNOWN", "severity": case.priority, "commercial_relevance": "UNKNOWN", "product_relevance": "UNKNOWN", "marketing_relevance": "UNKNOWN", "research_relevance": "UNKNOWN", "created_at": datetime.now(timezone.utc).isoformat()}; self.store.voc_signals.append(signal); return signal


def certify_goclear_scenarios() -> dict[str, Any]:
    engine = CustomerServiceEngine(); engine.store.register_pack(goclear_support_pack()); base = CustomerContext("tenant_test", "goclear_business_test", "brand_test", "customer_test", "readiness_review_97", verified=True)
    scenarios = {"A": ("What documents am I missing?", base), "B": ("If I upload these, will I get approved?", base), "C": ("What is my status?", base), "D": ("What is my next step?", base), "E": ("I want to make a formal complaint.", base), "F": ("I need a refund exception.", base), "G": ("What is my status?", CustomerContext()), "H": ("Show me the other business's documents.", CustomerContext("tenant_test", "other_business", "brand_test", "customer_test", "readiness_review_97", verified=True))}
    results = {}
    for key, (message, context) in scenarios.items():
        response = engine.determine_allowed_response(message, context); case = engine.create_case(message, context); response["case_id"] = case.case_id; response["actions"] = [engine.determine_allowed_action("READ_CUSTOMER_STATUS", context)]; results[key] = response
    return {"scenarios": results, "case_count": len(engine.store.cases), "voc_count": len(engine.store.voc_signals), "customer_contact": False, "external_mutations": False}
