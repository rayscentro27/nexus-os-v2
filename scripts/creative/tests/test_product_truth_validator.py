"""Tests for Nexus Product Truth Validator & Governance Layer."""
from __future__ import annotations

import pytest
from scripts.creative.product_truth_validator import (
    ClaimCategory,
    ClaimStatus,
    ProductTruthValidator,
    MUG_FACT_REGISTER,
)


def test_fact_register_structure():
    reg = ProductTruthValidator.get_fact_register()
    assert len(reg) >= 10
    for entry in reg:
        assert "claim" in entry
        assert "category" in entry
        assert "source" in entry
        assert "evidence" in entry
        assert "status" in entry
        assert entry["status"] in ("VERIFIED_FACT", "APPROVED_BUSINESS_DECISION", "PROPOSED_DECISION", "UNVERIFIED", "DISPROVEN")


def test_audit_flags_unverified_claims():
    bad_copy = (
        "This 485 grams mug holds 14 oz and is hand-thrown in kiln Batch #04 (180 units). "
        "It keeps coffee hot twice as long with our unglazed terracotta foot stays cool feature! "
        "Order now with free shipping and our lifetime chip replacement pledge!"
    )
    result = ProductTruthValidator.audit_copy(bad_copy)
    assert result["status"] == "FLAGGED_UNVERIFIED_CLAIMS"
    assert result["violation_count"] >= 5
    assert result["truthfulness_score"] < 50.0


def test_audit_passes_honest_poetic_copy():
    clean_copy = (
        "The 6:12 AM Quiet Ritual. "
        "The only fifteen minutes that belong entirely to you. "
        "Before the house wakes up, before the holiday rush takes over: a substantial ceramic mug "
        "designed for solitary morning quiet. "
        "Made for slow winter mornings and warm hands."
    )
    result = ProductTruthValidator.audit_copy(clean_copy)
    assert result["status"] == "PASS"
    assert result["violation_count"] == 0
    assert result["truthfulness_score"] == 100.0
