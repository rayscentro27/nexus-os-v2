"""Deterministic guard for model/rendered claims against verified evidence."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def validate_response(response: str, evidence_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return violations; this does not decide authority or mutate state."""
    text = (response or "").lower()
    facts = evidence_payload.get("evidence", [])
    unknowns = evidence_payload.get("unknowns", [])
    violations: List[str] = []

    unknown_claims = " ".join(str(item.get("claim", "")).lower() for item in unknowns)
    if unknowns and re.search(r"\b(healthy|running|approved|complete|executed|guaranteed)\b", text):
        if any(word in unknown_claims for word in ("health", "status", "result", "approval")):
            violations.append("unsupported_claim_over_unknown_evidence")

    if re.search(r"\b(approved|approval granted)\b", text):
        approval_facts = [str(item.get("value", "")).lower() for item in facts if "approval" in str(item.get("claim", "")).lower()]
        if approval_facts and not any("approved" in value for value in approval_facts):
            violations.append("approval_claim_without_approved_evidence")

    if re.search(r"\b(guarantee(?:s|d)?\s+(?:revenue|income))\b", text):
        violations.append("guaranteed_revenue_claim")

    return {"valid": not violations, "violations": violations}
