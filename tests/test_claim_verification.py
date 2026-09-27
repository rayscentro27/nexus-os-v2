from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.research.claim_verification import assess_evidence, classify_claim, required_source_classes


def test_named_lender_claim_does_not_require_sba():
    claim = "Bank of America Business Advantage Term Loan typically requires 700 FICO and two years in business."
    result = assess_evidence(claim, [{"source_url": "https://business.bankofamerica.com/en/business-loans", "source_class": "OFFICIAL_LENDER"}])
    assert result["claim_type"] == "LENDER_REQUIREMENT"
    assert result["required_source_classes"] == ["OFFICIAL_LENDER"]
    assert result["sba_required"] is False
    assert result["evidence_state"] == "PUBLISHED_REQUIREMENT"


def test_approval_profile_requires_observed_and_multi_source_evidence():
    result = assess_evidence(
        "Observed business-card approval profile for applicants with recent inquiries.",
        [
            {"source_class": "OBSERVED_OUTCOME_SOURCE"},
            {"source_class": "MULTI_SOURCE_MARKET"},
        ],
    )
    assert result["claim_type"] == "CREDIT_CARD_APPROVAL_PATTERN"
    assert result["evidence_state"] == "OBSERVED_APPROVAL_PATTERN"
    assert "OFFICIAL_SBA" not in result["required_source_classes"]


def test_real_canary_evidence_stays_product_scoped():
    artifact = ROOT / "reports/research/intelligence/clyde_native/gVYmkoruPDc.lender-evidence.json"
    payload = json.loads(artifact.read_text())
    evidence = payload["evidence"]
    result = assess_evidence(
        evidence[0]["claims"]["credit"],
        [{"source_url": item["url"], "source_class": item["source_class"]} for item in evidence],
        "LENDER_REQUIREMENT",
    )
    assert result["claim_type"] == "LENDER_REQUIREMENT"
    assert result["evidence_state"] == "PUBLISHED_REQUIREMENT"
    assert result["lender_specific_must_remain_product_scoped"] is True
