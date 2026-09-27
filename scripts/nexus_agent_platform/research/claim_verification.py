"""Claim-specific verification doctrine for funding intelligence.

The Research -> Alpha -> Clyde path remains the single pipeline.  This module
only supplies deterministic classification and source-class routing so an
official source is authoritative for the claims it actually governs.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

CLAIM_TYPES = {
    "SBA_PROGRAM_RULE", "LENDER_REQUIREMENT", "ISSUER_PRODUCT_TERM",
    "CREDIT_UNION_MEMBERSHIP_RULE", "CREDIT_CARD_APPROVAL_PATTERN",
    "BUREAU_PULL_PATTERN", "BUSINESS_BUREAU_REPORTING", "PERSONAL_GUARANTEE_RULE",
    "CREDIT_LIMIT_PATTERN", "APPLICATION_VELOCITY_PATTERN", "RELATIONSHIP_BANKING_PATTERN",
    "MARKET_PATTERN", "REGULATORY_RULE", "CUSTOMER_NEED", "PRACTITIONER_STRATEGY", "OTHER",
}

SOURCE_CLASS_ROUTING: dict[str, tuple[str, ...]] = {
    "SBA_PROGRAM_RULE": ("OFFICIAL_SBA", "OFFICIAL_REGULATORY"),
    "LENDER_REQUIREMENT": ("OFFICIAL_LENDER",),
    "ISSUER_PRODUCT_TERM": ("OFFICIAL_ISSUER",),
    "CREDIT_UNION_MEMBERSHIP_RULE": ("OFFICIAL_CREDIT_UNION",),
    "CREDIT_CARD_APPROVAL_PATTERN": ("OBSERVED_OUTCOME_SOURCE", "MULTI_SOURCE_MARKET"),
    "BUREAU_PULL_PATTERN": ("OBSERVED_OUTCOME_SOURCE", "ISSUER_DISCLOSURE", "MULTI_SOURCE_MARKET"),
    "BUSINESS_BUREAU_REPORTING": ("ISSUER_DISCLOSURE", "BUSINESS_BUREAU_EVIDENCE", "OBSERVED_OUTCOME_SOURCE"),
    "PERSONAL_GUARANTEE_RULE": ("OFFICIAL_LENDER", "OFFICIAL_ISSUER"),
    "CREDIT_LIMIT_PATTERN": ("OBSERVED_OUTCOME_SOURCE", "MULTI_SOURCE_MARKET"),
    "APPLICATION_VELOCITY_PATTERN": ("OBSERVED_OUTCOME_SOURCE", "MULTI_SOURCE_MARKET"),
    "RELATIONSHIP_BANKING_PATTERN": ("OFFICIAL_INSTITUTION", "OBSERVED_OUTCOME_SOURCE"),
    "MARKET_PATTERN": ("MULTI_SOURCE_MARKET",),
    "REGULATORY_RULE": ("OFFICIAL_REGULATORY",),
    "CUSTOMER_NEED": ("CUSTOMER_RESEARCH", "MULTI_SOURCE_MARKET"),
    "PRACTITIONER_STRATEGY": ("MULTI_SOURCE_MARKET", "PRACTITIONER_SOURCE"),
    "OTHER": ("MULTI_SOURCE_MARKET",),
}

EVIDENCE_STATES = {
    "PUBLISHED_REQUIREMENT", "OFFICIAL_PROGRAM_RULE", "OFFICIAL_PRODUCT_TERM",
    "OBSERVED_APPROVAL_PATTERN", "MULTI_SOURCE_MARKET_EVIDENCE", "ANECDOTAL_SIGNAL",
    "NEXUS_INFERENCE", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED", "STALE",
}


def classify_claim(claim: str, explicit_type: str | None = None) -> str:
    """Classify a claim conservatively; caller-supplied canonical type wins."""
    if explicit_type and explicit_type.upper() in CLAIM_TYPES:
        return explicit_type.upper()
    text = str(claim or "").lower()
    if any(token in text for token in ("sba", "7(a)", "504 loan", "microloan")):
        return "SBA_PROGRAM_RULE"
    if any(token in text for token in ("credit union", "membership eligibility")):
        return "CREDIT_UNION_MEMBERSHIP_RULE"
    if any(token in text for token in ("bureau pull", "hard pull", "soft pull")):
        return "BUREAU_PULL_PATTERN"
    if any(token in text for token in ("approval profile", "approval pattern", "often approved", "approval rate")):
        return "CREDIT_CARD_APPROVAL_PATTERN"
    if any(token in text for token in ("credit limit", "application velocity", "business bureau", "reports to experian")):
        return "CREDIT_LIMIT_PATTERN" if "limit" in text else "BUSINESS_BUREAU_REPORTING"
    if any(token in text for token in ("personal guarantee", "collateral", "fico", "revenue", "time in business", "prepayment", "apr", "origination fee")):
        return "LENDER_REQUIREMENT"
    if any(token in text for token in ("regulation", "regulatory", "consumer financial protection")):
        return "REGULATORY_RULE"
    return "OTHER"


def required_source_classes(claim_type: str) -> tuple[str, ...]:
    return SOURCE_CLASS_ROUTING.get(str(claim_type or "OTHER").upper(), SOURCE_CLASS_ROUTING["OTHER"])


def source_class_from_reference(reference: str, declared: str | None = None) -> str:
    if declared:
        return declared.upper()
    host = (urlparse(str(reference or "")).hostname or "").lower()
    if host == "sba.gov" or host.endswith(".sba.gov"):
        return "OFFICIAL_SBA"
    if any(token in host for token in ("bank", "americanexpress", "chase", "ondeck", "capitalone", "lending")):
        return "OFFICIAL_LENDER"
    return "UNCLASSIFIED_SOURCE"


def assess_evidence(claim: str, evidence: list[dict[str, Any]], explicit_type: str | None = None) -> dict[str, Any]:
    claim_type = classify_claim(claim, explicit_type)
    required = required_source_classes(claim_type)
    classes = {source_class_from_reference(item.get("source_url") or item.get("source"), item.get("source_class")) for item in evidence}
    matched = [item for item in required if item in classes]
    if matched and len(matched) == len(required):
        state = "OBSERVED_APPROVAL_PATTERN" if claim_type in {"CREDIT_CARD_APPROVAL_PATTERN", "CREDIT_LIMIT_PATTERN", "APPLICATION_VELOCITY_PATTERN"} else ("MULTI_SOURCE_MARKET_EVIDENCE" if "MULTI_SOURCE_MARKET" in required else "PUBLISHED_REQUIREMENT")
    elif matched:
        state = "PARTIALLY_VERIFIED"
    else:
        state = "UNVERIFIED"
    return {
        "claim_type": claim_type,
        "required_source_classes": list(required),
        "observed_source_classes": sorted(classes),
        "matched_source_classes": matched,
        "evidence_state": state,
        "sba_required": "OFFICIAL_SBA" in required,
        "sba_absence_invalidates": claim_type == "SBA_PROGRAM_RULE",
        "lender_specific_must_remain_product_scoped": claim_type in {"LENDER_REQUIREMENT", "ISSUER_PRODUCT_TERM", "PERSONAL_GUARANTEE_RULE"},
    }
