"""Consume Alpha-qualified Research handoffs for Clyde internal intelligence.

This is the existing Clyde/Funding consumer boundary for Research V2 handoffs.
It does not contact a client, make a funding decision, call a lender, or run a
second research/Alpha pipeline.  It records a durable internal review and, when
evidence is incomplete, uses the existing ``research_requests`` return path.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.intelligence_fabric import build_research_request, persist_research_request  # noqa: E402

CONSUMER = "clyde_credit_research_handoff_consumer_v1"
TARGET = "CLYDE_CREDIT"
HANDOFF_STATES = {
    "HANDOFF_CREATED",
    "WAITING_FOR_CONSUMER",
    "IN_REVIEW",
    "RESEARCH_MORE",
    "QUALIFIED_INTERNAL",
    "NO_ACTION",
    "HUMAN_APPROVAL_REQUIRED",
    "FAILED_RETRYABLE",
    "FAILED_TERMINAL",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _latest(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    matches = [row for row in persistence.read_records(key) if row.get("handoff_id") == value]
    return matches[-1] if matches else None


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _sba_evidence(root: Path) -> list[dict[str, Any]]:
    artifact = root / "reports/runtime/research_artifacts/web/cert-sba-funding.document.json"
    raw = root / "reports/runtime/research_artifacts/web/cert-sba-funding.normalized.txt"
    document = _read_json(artifact, {})
    url = str(document.get("source_url") or "")
    if "sba.gov" not in url or not raw.exists():
        return []
    return [{
        "source_id": document.get("source_id") or "cert-sba-funding",
        "source_url": url,
        "artifact": str(artifact.relative_to(root)),
        "normalized_text": str(raw.relative_to(root)),
        "source_class": "OFFICIAL_GOVERNMENT",
        "retrieved_at": document.get("retrieved_at"),
    }]


def _independent_lender_evidence(root: Path) -> list[dict[str, Any]]:
    """Return only independent lender artifacts, never treat SBA as a lender."""
    candidates: list[dict[str, Any]] = []
    directory = root / "reports/runtime/research_artifacts/web"
    for path in directory.glob("*.document.json"):
        document = _read_json(path, {})
        url = str(document.get("source_url") or "")
        hostname = (urlparse(url).hostname or "").lower()
        if hostname and hostname != "sba.gov" and not hostname.endswith(".sba.gov") and any(token in hostname for token in ("bank", "lender", "capital", "funding")):
            candidates.append({"source_id": document.get("source_id"), "source_url": url, "artifact": str(path.relative_to(root))})
    return candidates


def build_internal_result(handoff: dict[str, Any], alpha: dict[str, Any], analysis: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    sba = _sba_evidence(root)
    lenders = _independent_lender_evidence(root)
    missing = []
    if not lenders:
        missing.append("independent lender evidence for fees, APR-equivalent costs, collateral, guarantees, and early repayment terms")
    return {
        "schema_version": "nexus.clyde.research-intelligence.v1",
        "consumer": CONSUMER,
        "target_department": TARGET,
        "handoff_id": handoff["handoff_id"],
        "alpha_receipt_id": handoff.get("alpha_receipt_id"),
        "finding_id": handoff.get("finding_id"),
        "investigation_id": alpha.get("investigation_id") or handoff.get("finding_id"),
        "need_id": handoff.get("need_id"),
        "source_lineage": {
            "youtube_video_id": "gVYmkoruPDc",
            "transcript": "reports/research/intelligence/youtube/gVYmkoruPDc.transcript.txt",
            "ai_analysis": "reports/research/intelligence/youtube/gVYmkoruPDc.ai-analysis.json",
            "alpha_receipt": "reports/research/intelligence/alpha_native_canary/alpha_receipt_ff30fd24f38f4e34b0d9b092dae94572.json",
        },
        "verified": {
            "official_sba_evidence": sba,
            "official_evidence_summary": "Existing SBA.gov material covers SBA-backed 7(a), 504, and microloan program context and points to Lender Match.",
            "alpha_decision": alpha.get("decision"),
        },
        "unverified": [
            "Transcript credit-score ranges and 10-to-90-day timeline claims",
            "Product-specific fees, APR-equivalent costs, collateral, guarantees, and early-repayment terms",
            "Clear Value Lending product availability and commercial claims",
        ],
        "source_claim_vs_nexus_interpretation": {
            "source_claim": "The video presents financing options and qualification factors; it is commercially interested and contains claims Alpha marked for verification.",
            "nexus_interpretation": "Use this only as internal funding-readiness education research. Do not present lender-specific thresholds or timelines as client facts.",
        },
        "funding_readiness_implications": [
            "A borrower profile should be segmented by credit, revenue/cash flow, business history, funding amount, collateral, and guarantees.",
            "Product comparison should separate official program facts from lender-variable pricing and underwriting terms.",
            "GoClear education can focus on evidence preparation and comparison questions, not approval prediction.",
        ],
        "lender_evidence_found": bool(lenders),
        "missing_verification": missing,
        "decision": "RESEARCH_MORE" if missing else "QUALIFIED_INTERNAL",
        "final_internal_state": "RESEARCH_MORE" if missing else "QUALIFIED_INTERNAL",
        "external_action_allowed": False,
        "consequential_action_performed": False,
        "human_approval_required": False,
        "created_at": _now(),
    }


def process_handoff(handoff_id: str, *, root: Path = ROOT, force: bool = False) -> dict[str, Any]:
    handoff = _latest([], "research_v2_handoffs", handoff_id)
    if not handoff:
        raise ValueError(f"handoff-not-found:{handoff_id}")
    if handoff.get("target_department") != TARGET:
        raise ValueError("handoff-target-is-not-clyde-credit")
    if not force and handoff.get("result_artifact") and handoff.get("consumer") == CONSUMER:
        return {"status": "DEDUPLICATED", "handoff_id": handoff_id, "result_artifact": handoff["result_artifact"]}

    alpha = next((row for row in persistence.read_records("alpha_evaluations") if row.get("receipt_id") == handoff.get("alpha_receipt_id")), {})
    analysis = _read_json(root / "reports/research/intelligence/youtube/gVYmkoruPDc.ai-analysis.json", {})
    started = {**handoff, "status": "IN_REVIEW", "department_handoff_status": "IN_REVIEW", "consumer": CONSUMER, "consumed_at": _now()}
    persistence.append_record("research_v2_handoffs", started)

    result = build_internal_result(started, alpha, analysis, root=root)
    output = root / "reports/research/intelligence/clyde_native/gVYmkoruPDc.clyde-internal.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    request = None
    if result["decision"] == "RESEARCH_MORE":
        request = build_research_request(
            department=TARGET,
            objective_id=str(handoff.get("investigation_id") or handoff.get("finding_id")),
            question="What independent lender evidence verifies the financing claims identified in the Alpha-qualified ClearValue Tax item?",
            knowledge_gap="Independent lender evidence is missing for fees, APR-equivalent costs, collateral, guarantees, and early repayment terms.",
            reason_needed="Clyde internal review cannot safely convert lender-variable claims into useful guidance without cross-source verification.",
            desired_evidence=["at least one independent lender or lender-market source", "fees and APR-equivalent costs", "collateral and guarantees", "early repayment terms"],
            risk_consequence="CLIENT_FINANCIAL_CLAIM_RISK",
            freshness_requirement="CURRENT",
            priority="P2_REVENUE",
            next_action="Acquire bounded lender evidence, then return to Clyde for re-review.",
        )
        existing = next((row for row in persistence.read_records("research_requests") if row.get("request_id") == request["request_id"]), None)
        request = existing or persist_research_request(request)
        result["research_return_request_id"] = request["request_id"]

    result["research_return_created"] = bool(request)
    result["research_return_path"] = "research_requests -> Research -> Alpha -> CLYDE_CREDIT" if request else None
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final = {
        **started,
        "status": result["final_internal_state"],
        "department_handoff_status": result["final_internal_state"],
        "consumer": CONSUMER,
        "consumed_at": started["consumed_at"],
        "result_artifact": str(output.relative_to(root)),
        "next_action": result["research_return_path"] or "Use the bounded internal intelligence artifact.",
        "research_return_request_id": result.get("research_return_request_id"),
        "external_action_allowed": False,
        "consequential_action_performed": False,
    }
    persistence.append_record("research_v2_handoffs", final)
    return {"status": result["final_internal_state"], "handoff_id": handoff_id, "result_artifact": str(output.relative_to(root)), "research_return_request_id": result.get("research_return_request_id"), "external_action_performed": False}


if __name__ == "__main__":
    handoff = sys.argv[1] if len(sys.argv) > 1 else "research_handoff_237bb7a35e454ce7a186baac8832fbdd"
    print(json.dumps(process_handoff(handoff, force="--reprocess" in sys.argv[2:]), indent=2, sort_keys=True))
