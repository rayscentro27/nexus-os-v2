"""Canonical evidence-first claim and secondary-value governance."""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

CLAIM_CLASSES = ("OBSERVED_FACT", "SUPPORTED_FACTUAL_CLAIM", "SUPPORTED_MARKETING_CLAIM", "OPINION", "HYPOTHESIS", "POSSIBLE_OUTCOME", "COMPARISON", "TEST_RESULT", "CUSTOMER_TESTIMONIAL", "FORWARD_LOOKING_STATEMENT", "UNVERIFIED_CLAIM", "PROHIBITED_GUARANTEE")
REJECTION_REASONS = ("INSUFFICIENT_EVIDENCE", "FAILED_TEST", "NOT_AUTOMATABLE", "TOO_EXPENSIVE", "LOW_COMMERCIAL_VALUE", "HIGH_RISK", "MISLEADING_CLAIM", "OVERHYPED", "COMMODITIZED", "WRONG_AUDIENCE", "POOR_NEXUS_FIT", "BETTER_ALTERNATIVE_EXISTS", "OTHER")
SECONDARY_VALUES = ("CONTENT", "EDUCATION", "COMPARISON", "AFFILIATE_ALTERNATIVE", "LEAD_GENERATION", "CUSTOMER_PAIN_SIGNAL", "PRODUCT_GAP", "MARKETING_INTELLIGENCE", "RESEARCH_INSIGHT", "ARCHIVE")
GUARANTEE = re.compile(r"\b(guaranteed?|you will|will get|always|no matter your credit|risk[- ]free)\b", re.I)
PERSONAL_ATTACK = re.compile(r"\b(scammer|fraud|fraudster|knowingly lied|criminal)\b", re.I)


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(str(value).encode()).hexdigest()[:16]}"


def classify_claim(claim_text: str, evidence_refs: list[str] | None = None, *, claim_class: str | None = None) -> dict[str, Any]:
    evidence_refs = evidence_refs or []
    if claim_class and claim_class not in CLAIM_CLASSES: raise ValueError("unsupported claim class")
    if GUARANTEE.search(claim_text): inferred = "PROHIBITED_GUARANTEE"
    elif claim_class: inferred = claim_class
    elif not evidence_refs: inferred = "UNVERIFIED_CLAIM"
    else: inferred = "SUPPORTED_MARKETING_CLAIM"
    return {"claim_id": stable_id("claim", claim_text), "claim_text": claim_text, "claim_class": inferred, "evidence_refs": evidence_refs, "scope": "bounded internal review", "limitations": [], "qualifiers": [], "risk_level": "HIGH" if inferred in {"PROHIBITED_GUARANTEE", "UNVERIFIED_CLAIM"} else "LOW", "review_status": "PENDING"}


def claim_intensity(claim: dict[str, Any]) -> dict[str, Any]:
    cls = claim["claim_class"]
    level = 5 if cls in {"PROHIBITED_GUARANTEE", "UNVERIFIED_CLAIM"} else 3 if cls in {"SUPPORTED_MARKETING_CLAIM", "POSSIBLE_OUTCOME", "COMPARISON"} else 2 if cls == "SUPPORTED_FACTUAL_CLAIM" else 1
    return {"level": level, "allowed": level <= 3, "reason": "strong framing remains allowed when evidence and limitations are preserved" if level in {2, 3} else "evidence or safety boundary requires review"}


def strongest_truthful_rewrite(text: str, *, evidence_refs: list[str] | None = None) -> str:
    if not GUARANTEE.search(text): return text
    replacements = [(r"unlimited free AI video generation", "6 AI video tools you can start using for free"), (r"guaranteed funding approval", "a clearer funding-readiness path"), (r"guaranteed funding", "funding-readiness options")]
    for pattern, replacement in replacements:
        if re.search(pattern, text, re.I): return re.sub(pattern, replacement, text, flags=re.I)
    return "What the available evidence shows about " + re.sub(GUARANTEE, "", text).strip(" .")


def evaluate_headline(headline: str, body: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    claim = classify_claim(headline, evidence_refs)
    issues = []
    if claim["claim_class"] == "PROHIBITED_GUARANTEE": issues.append("headline implies an outcome the evidence does not establish")
    if headline and body and any(word.lower() in headline.lower() for word in ("guaranteed", "always", "no matter")): issues.append("headline/body consistency requires revision")
    decision = "REVISE" if issues else "APPROVED_WITH_QUALIFIERS" if claim["risk_level"] == "HIGH" else "APPROVED"
    return {"decision": decision, "claim": claim, "issues": issues, "strongest_supported_alternative": strongest_truthful_rewrite(headline, evidence_refs=evidence_refs), "checks": ["literal truth", "reasonable viewer interpretation", "material omissions", "qualification placement", "headline/body consistency", "thumbnail/CTA consistency"]}


def evaluate_domain_claim(text: str, domain: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    result = classify_claim(text, evidence_refs)
    issues = []
    if domain in {"funding", "credit"} and re.search(r"\b(approval|score increase|deletion|rate|amount|timeline)\b", text, re.I) and not evidence_refs: issues.append("material financial/credit claim lacks scoped evidence")
    if domain == "trading" and PERSONAL_ATTACK.search(text): issues.append("personal attack is not an evidence claim")
    if domain == "trading" and re.search(r"\b(win rate|profit|return|backtest)\b", text, re.I) and len(evidence_refs or []) < 2: issues.append("trading performance requires reproducible methodology and evidence")
    if issues: result["claim_class"] = "UNVERIFIED_CLAIM"
    result.update({"domain": domain, "decision": "BLOCK" if PERSONAL_ATTACK.search(text) else "RESEARCH_MORE" if issues and any("evidence" in issue or "methodology" in issue for issue in issues) else "BLOCK" if issues else "APPROVED_WITH_QUALIFIERS", "issues": issues, "required_evidence": ["source", "scope", "limitations"] if issues else []})
    return result


def required_disclosures(*, affiliate: bool = False, testimonial: bool = False, comparison: bool = False, financial: bool = False) -> list[str]:
    result = []
    if affiliate: result.append("Disclose affiliate/referral compensation clearly near the recommendation.")
    if testimonial: result.append("Use only authorized, authentic testimonials and avoid implying typicality without support.")
    if comparison: result.append("State test date, criteria, scope, and limitations.")
    if financial: result.append("Distinguish possible outcomes from approval, revenue, rate, amount, or timeline guarantees.")
    return result


def secondary_value_review(*, alpha_decision_id: str, original_use: str, rejection_reason: str, evidence_refs: list[str], commercial_relevance: str = "UNKNOWN") -> dict[str, Any]:
    if rejection_reason not in REJECTION_REASONS: raise ValueError("unsupported rejection reason")
    route = "COMPARISON" if rejection_reason in {"FAILED_TEST", "BETTER_ALTERNATIVE_EXISTS"} else "EDUCATION" if rejection_reason in {"INSUFFICIENT_EVIDENCE", "OVERHYPED", "HIGH_RISK"} else "CUSTOMER_PAIN_SIGNAL" if rejection_reason == "WRONG_AUDIENCE" else "RESEARCH_INSIGHT"
    return {"alpha_decision_id": alpha_decision_id, "original_use": original_use, "rejection_reason": rejection_reason, "secondary_value": route, "secondary_route": route, "content_value": route in {"CONTENT", "EDUCATION", "COMPARISON"}, "customer_pain_signal": route == "CUSTOMER_PAIN_SIGNAL", "alternative_solution_available": rejection_reason == "BETTER_ALTERNATIVE_EXISTS", "commercial_relevance": commercial_relevance, "evidence_refs": evidence_refs, "compliance_requirements": required_disclosures(comparison=route == "COMPARISON")}


def rejection_monetization(**kwargs: Any) -> dict[str, Any]: return secondary_value_review(**kwargs)


@dataclass
class ProductCompliancePack:
    compliance_pack_id: str
    business_id: str
    product_id: str
    version: str
    status: str = "DRAFT"
    allowed_claim_classes: list[str] = field(default_factory=lambda: ["OBSERVED_FACT", "SUPPORTED_FACTUAL_CLAIM", "SUPPORTED_MARKETING_CLAIM", "POSSIBLE_OUTCOME"])
    prohibited_claims: list[str] = field(default_factory=lambda: ["guaranteed approval", "guaranteed funding", "guaranteed revenue", "fabricated testimonials"])
    required_evidence: list[str] = field(default_factory=list)
    required_disclosures: list[str] = field(default_factory=list)
    required_qualifiers: list[str] = field(default_factory=list)
    human_escalation_rules: list[str] = field(default_factory=lambda: ["material financial claim", "testimonial authorization ambiguity", "privacy/security exception"])
    marketing_rules: list[str] = field(default_factory=lambda: ["drafts only", "no publication without approval"])
    creative_rules: list[str] = field(default_factory=lambda: ["preserve claim constraints", "no fabricated proof"])


def compliance_receipt(subject_type: str, subject_id: str, claims: list[dict[str, Any]], decision: str, *, evidence_refs: list[str] | None = None, issues: list[str] | None = None, disclosures: list[str] | None = None) -> dict[str, Any]:
    return {"compliance_receipt_id": stable_id("compliance_receipt", f"{subject_type}:{subject_id}:{decision}"), "subject_type": subject_type, "subject_id": subject_id, "claims_reviewed": [claim.get("claim_id") for claim in claims], "decision": decision, "evidence_refs": evidence_refs or [], "issues": issues or [], "required_changes": [strongest_truthful_rewrite(claim["claim_text"]) for claim in claims if claim.get("claim_class") == "PROHIBITED_GUARANTEE"], "disclosures": disclosures or [], "escalation": decision in {"HUMAN_REVIEW", "BLOCK"}, "reviewed_at": datetime.now(timezone.utc).isoformat()}


def automation_value(*, api: bool = False, cli: bool = False, mcp: bool = False, headless: bool = False, self_hosted: bool = False, commercial_use: str = "UNKNOWN", rate_limits: str = "UNKNOWN", output_retrieval: bool = False) -> dict[str, Any]:
    dimensions = {"api": api, "cli": cli, "mcp": mcp, "headless": headless, "self_hosted": self_hosted, "commercial_use": commercial_use, "rate_limits": rate_limits, "output_retrieval": output_retrieval}
    return {"dimensions": dimensions, "operational_value": "HIGH" if sum(value is True for value in dimensions.values()) >= 4 else "LOW", "product_quality_separate": True}
