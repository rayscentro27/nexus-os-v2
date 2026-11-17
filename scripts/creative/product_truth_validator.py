"""Nexus Product Truth Validator & Governance Layer.

Enforces the doctrine:
CREATIVE INFERENCE != VERIFIED PRODUCT FACT != PROPOSED BUSINESS DECISION != UNVERIFIED CLAIM.

Mandatory pipeline:
MARKETING / CREATIVE COPY -> PRODUCT FACT VALIDATOR -> TRUTH LAYER -> APPROVED COPY.

Creative may propose claims; Creative may NOT certify its own factual claims.
No customer-facing copy may present unverified inferences or proposed business decisions
as established facts.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ClaimCategory(str, Enum):
    PRODUCT_SPEC = "PRODUCT_SPEC"
    MATERIAL = "MATERIAL"
    PERFORMANCE = "PERFORMANCE"
    PRICE = "PRICE"
    COGS = "COGS"
    SHIPPING = "SHIPPING"
    WARRANTY = "WARRANTY"
    FULFILLMENT = "FULFILLMENT"
    SUPPLIER = "SUPPLIER"
    MARKETPLACE_ELIGIBILITY = "MARKETPLACE_ELIGIBILITY"
    AVAILABILITY = "AVAILABILITY"


class ClaimStatus(str, Enum):
    VERIFIED_FACT = "VERIFIED_FACT"
    APPROVED_BUSINESS_DECISION = "APPROVED_BUSINESS_DECISION"
    PROPOSED_DECISION = "PROPOSED_DECISION"
    UNVERIFIED = "UNVERIFIED"
    DISPROVEN = "DISPROVEN"


@dataclass
class ProductClaimEntry:
    claim: str
    category: ClaimCategory
    source: str
    evidence: str
    status: ClaimStatus
    correction_guidance: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "category": self.category.value,
            "source": self.source,
            "evidence": self.evidence,
            "status": self.status.value,
            "correction_guidance": self.correction_guidance,
        }


# Canonical Register of Current Claims Evaluated for prod_stoneware_mug_14oz
MUG_FACT_REGISTER: List[ProductClaimEntry] = [
    ProductClaimEntry(
        claim="485 grams product weight",
        category=ClaimCategory.PRODUCT_SPEC,
        source="Creative Engine generation",
        evidence="None (invented specification; no physical product weighed)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Remove exact gram weight. Describe as 'substantial ceramic form' or 'grounded weight' without asserting numbers.",
    ),
    ProductClaimEntry(
        claim="14 oz liquid capacity",
        category=ClaimCategory.PRODUCT_SPEC,
        source="Creative Engine generation",
        evidence="None (no supplier specification or volume measurement)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Remove explicit fluid ounce number or label as conceptual sizing until physical specimen selected.",
    ),
    ProductClaimEntry(
        claim="Handcrafted / hand-thrown construction",
        category=ClaimCategory.MATERIAL,
        source="Creative Concept generation",
        evidence="None (no production contract with artisan potter; Printify/commercial mugs are typically slip-cast or molded)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Do not assert 'hand-thrown on a wheel'. Describe artisanal tactile aesthetics without misrepresenting manufacturing method.",
    ),
    ProductClaimEntry(
        claim="High-fire stoneware ceramic",
        category=ClaimCategory.MATERIAL,
        source="Creative Brief",
        evidence="None (no ceramic material test report or supplier spec sheet)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Describe as 'ceramic vessel' or 'stoneware-inspired finish' until clay composition is certified.",
    ),
    ProductClaimEntry(
        claim="Unglazed thermal terracotta foot ring",
        category=ClaimCategory.PRODUCT_SPEC,
        source="Meta.ai prompt direction",
        evidence="Visual depiction in AI image only; not an actual manufactured product feature",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Remove claim of physical thermal barrier. Focus on grounded visual presence.",
    ),
    ProductClaimEntry(
        claim="Coffee stays hot twice as long",
        category=ClaimCategory.PERFORMANCE,
        source="Creative Copywriter",
        evidence="None (no thermal heat retention comparative lab test against porcelain)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Remove comparative thermal multiplier. Replace with sensory copy: 'Made for slow mornings and warm hands'.",
    ),
    ProductClaimEntry(
        claim="Three-finger ergonomic pulled handle",
        category=ClaimCategory.PRODUCT_SPEC,
        source="Creative Copywriter",
        evidence="None (no ergonomic mechanical drawing or physical sample)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Describe handle comfort generally; do not specify mechanical finger-count clearance.",
    ),
    ProductClaimEntry(
        claim="Lifetime chip replacement pledge / Forever-Morning guarantee",
        category=ClaimCategory.WARRANTY,
        source="Creative Concept generation",
        evidence="None (not approved by business owner Ray; no liability underwriting or replacement logistics established)",
        status=ClaimStatus.PROPOSED_DECISION,
        correction_guidance="Remove active lifetime replacement pledge from customer copy. Keep as internal proposed policy only.",
    ),
    ProductClaimEntry(
        claim="$48.00 retail price",
        category=ClaimCategory.PRICE,
        source="Creative Brief proposal",
        evidence="Proposed pricing in campaign brief; no official price book or approval receipt from Ray",
        status=ClaimStatus.PROPOSED_DECISION,
        correction_guidance="Mark clearly as PROPOSED_RETAIL_PRICE ($48) in internal strategy; do not display as an established live price offer.",
    ),
    ProductClaimEntry(
        claim="$16.50 COGS / 65.6% gross margin",
        category=ClaimCategory.COGS,
        source="Creative Brief financial estimate",
        evidence="Estimated calculation; no actual supplier quote or wholesale invoice",
        status=ClaimStatus.PROPOSED_DECISION,
        correction_guidance="Retain in business model forecasts only; label explicitly as ESTIMATED_COGS.",
    ),
    ProductClaimEntry(
        claim="Free shipping",
        category=ClaimCategory.SHIPPING,
        source="Creative Copywriter",
        evidence="None (no carrier rates negotiated or subsidized shipping budget approved)",
        status=ClaimStatus.PROPOSED_DECISION,
        correction_guidance="Remove free shipping assertion from customer copy.",
    ),
    ProductClaimEntry(
        claim="On-demand craft pottery partner / Small-Batch Winter Firing #04 (180 units)",
        category=ClaimCategory.SUPPLIER,
        source="Creative Copywriter",
        evidence="None (fictional domestic pottery kiln narrative; no supplier contracted)",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Remove fictional small-batch kiln numbers (Batch #04, 180 units). Frame campaign around concept exploration.",
    ),
    ProductClaimEntry(
        claim="Printify readiness",
        category=ClaimCategory.MARKETPLACE_ELIGIBILITY,
        source="Manifest",
        evidence="No Printify ceramic mug SKU selected, mockups uncreated, print provider unassigned",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Downgrade status to PRODUCT_DATA_REQUIRED.",
    ),
    ProductClaimEntry(
        claim="TikTok Shop / Amazon / Walmart Marketplace readiness",
        category=ClaimCategory.MARKETPLACE_ELIGIBILITY,
        source="Manifest",
        evidence="No marketplace merchant accounts connected, approved, or catalog entries created",
        status=ClaimStatus.UNVERIFIED,
        correction_guidance="Downgrade status to ACCOUNT_INTEGRATION_REQUIRED.",
    ),
    ProductClaimEntry(
        claim="Owned Storefront readiness",
        category=ClaimCategory.MARKETPLACE_ELIGIBILITY,
        source="Landing page build",
        evidence="Local HTML template built in dist/creative/landing/index.html; no live domain, host, or payment gateway",
        status=ClaimStatus.PROPOSED_DECISION,
        correction_guidance="Downgrade status to CREATIVE_READY.",
    ),
]


class ProductTruthValidator:
    """Enforces truth boundaries on creative copy, landing pages, and commerce manifests."""

    UNVERIFIED_PATTERNS = [
        (re.compile(r"\b485\s*(?:g|grams)\b", re.I), "unverified_weight_485g"),
        (re.compile(r"\b14\s*(?:oz|ounce)\b", re.I), "unverified_capacity_14oz"),
        (re.compile(r"\b(?:twice\s+as\s+long|2x\s+longer|double\s+the\s+heat)\b", re.I), "unverified_thermal_multiplier"),
        (re.compile(r"\bhand[- ]thrown\s+(?:on\s+a\s+wheel|stoneware|in\s+kiln)\b", re.I), "unverified_hand_thrown_method"),
        (re.compile(r"\blifetime\s+chip\s+replacement\b|\bforever[- ]morning\s+promise\b", re.I), "unapproved_lifetime_warranty"),
        (re.compile(r"\bbatch\s*#?04\b|\b180\s+units\b", re.I), "fictional_batch_scarcity"),
        (re.compile(r"\bfree\s+shipping\b", re.I), "unapproved_free_shipping"),
        (re.compile(r"\bunglazed\s+terracotta\s+foot\s+(?:ring\s+)?stays\s+cool\b", re.I), "unverified_thermal_foot_claim"),
    ]

    @classmethod
    def audit_copy(cls, text: str) -> Dict[str, Any]:
        """Scans customer-facing copy for unverified facts and unapproved decisions."""
        violations = []
        for pattern, label in cls.UNVERIFIED_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append({
                    "violation": label,
                    "matched_text": match.group(0),
                    "rule": "Only verified physical evidence or approved business decisions may be published."
                })

        truth_score = round(max(0.0, 100.0 - (len(violations) * 20.0)), 1)
        passed = len(violations) == 0

        return {
            "status": "PASS" if passed else "FLAGGED_UNVERIFIED_CLAIMS",
            "truthfulness_score": truth_score,
            "violations": violations,
            "violation_count": len(violations),
        }

    @classmethod
    def get_fact_register(cls) -> List[Dict[str, Any]]:
        return [entry.to_dict() for entry in MUG_FACT_REGISTER]
