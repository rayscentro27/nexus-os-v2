"""Business attention adapter for the certified Active Operator.

Reads canonical Opportunity, Revenue Truth, Growth, and governance state. It
does not duplicate source records, schedule work, call the web, or execute
external actions.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.growth_operations import growth_portfolio, list_growth_experiments
from nexus_agent_platform.opportunities.engine import opportunity_portfolio
from nexus_agent_platform.creative.studio import creative_portfolio

BUSINESS_ATTENTION_SCHEMA = "nexus.business-attention.v1"
BUSINESS_PRIORITY_POLICY = "nexus.business-priority.v1"
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()[:24]


def _finding(*, source_system: str, source_record_id: str, category: str, priority: str, summary: str, reason: str, truth_class: str, freshness: str, recommended_action: str, action_class: str, approval_required: bool, evidence_refs: Optional[List[str]] = None, state: Any = None) -> Dict[str, Any]:
    dedupe_key = f"business_operator:{source_system}:{source_record_id}:{category}:v1"
    return {
        "schema_version": BUSINESS_ATTENTION_SCHEMA,
        "finding_id": f"{dedupe_key}:{_fingerprint(state if state is not None else reason)}",
        "business_id": "goclear",
        "source_system": source_system,
        "source_record_id": source_record_id,
        "category": category,
        "priority": priority,
        "summary": summary,
        "reason": reason,
        "truth_class": truth_class,
        "freshness": freshness,
        "recommended_action": recommended_action,
        "action_class": action_class,
        "approval_required": approval_required,
        "evidence_refs": list(evidence_refs or []),
        "dedupe_key": dedupe_key,
        "material_fingerprint": _fingerprint(state if state is not None else reason),
        "created_at": _now(),
        "external_action_performed": False,
    }


def discover_business_attention() -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    sources: Dict[str, str] = {}
    errors: List[str] = []
    try:
        portfolio = opportunity_portfolio()
        sources["opportunity_engine"] = "CONNECTED"
        for row in portfolio.get("rankings", {}).get("needs_ray", [])[:10]:
            findings.append(_finding(source_system="opportunity_engine", source_record_id=row.get("opportunity_id", "unknown"), category="opportunity_review", priority="P2", summary=f"Opportunity needs Ray review: {row.get('title', 'untitled')}", reason=f"canonical opportunity status is {row.get('status')}; score={(row.get('scores') or {}).get('overall_score', 'UNKNOWN')}", truth_class="EVIDENCE_BACKED", freshness=(row.get("freshness") or {}).get("status", "UNKNOWN"), recommended_action="opportunity.review", action_class="APPROVAL_REQUIRED", approval_required=True, evidence_refs=row.get("evidence_refs", []), state={"status": row.get("status"), "score": (row.get("scores") or {}).get("overall_score")}))
        for row in portfolio.get("rankings", {}).get("needs_research", [])[:10]:
            findings.append(_finding(source_system="opportunity_engine", source_record_id=row.get("opportunity_id", "unknown"), category="opportunity_research", priority="P4", summary=f"Opportunity needs research: {row.get('title', 'untitled')}", reason="canonical opportunity lacks sufficient current evidence", truth_class="UNKNOWN", freshness=(row.get("freshness") or {}).get("status", "UNKNOWN"), recommended_action="research_refresh.request", action_class="APPROVAL_REQUIRED", approval_required=True, evidence_refs=row.get("evidence_refs", []), state={"status": row.get("status"), "research_needed": row.get("research_needed")}))
    except Exception as exc:
        sources["opportunity_engine"] = "UNAVAILABLE"
        errors.append(f"opportunity_engine:{type(exc).__name__}")

    try:
        snapshot = persistence.latest_record("revenue_snapshots")
        sources["revenue_hub"] = "CONNECTED" if snapshot else "NOT_CONNECTED"
        if snapshot and snapshot.get("revenue_truth") == "NOT_CONNECTED":
            findings.append(_finding(source_system="revenue_hub", source_record_id="revenue_measurement_connection", category="revenue_measurement_connection_gap", priority="P3", summary="Revenue truth source is not connected", reason="actual revenue and funnel observations are UNKNOWN/NOT_CONNECTED; UNKNOWN is not zero", truth_class="UNKNOWN", freshness=(snapshot or {}).get("freshness", "UNKNOWN"), recommended_action="measurement_gap.report", action_class="AUTO_EXECUTE_INTERNAL_SAFE", approval_required=False, state={"source_status": "NOT_CONNECTED", "snapshot_id": (snapshot or {}).get("snapshot_id")}))
    except Exception as exc:
        sources["revenue_hub"] = "UNAVAILABLE"
        errors.append(f"revenue_hub:{type(exc).__name__}")

    try:
        portfolio = growth_portfolio()
        rows = list_growth_experiments()
        sources["growth_operations"] = "CONNECTED"
        ray_rows = [row for row in rows if row.get("status") == "NEEDS_RAY_REVIEW"]
        for row in ray_rows[:10]:
            review_action = "opportunity.review" if row.get("source_opportunity_id") else "business_attention.review"
            item = _finding(source_system="growth_operations", source_record_id=row.get("growth_id", "unknown"), category="growth_review", priority="P2", summary=f"Growth experiment needs Ray review: {row.get('title', 'untitled')}", reason="growth experiment is evidence-backed but public work remains approval-gated", truth_class="EVIDENCE_BACKED", freshness=(row.get("freshness") or {}).get("status", "UNKNOWN"), recommended_action=review_action, action_class="APPROVAL_REQUIRED", approval_required=True, evidence_refs=row.get("evidence_refs", []), state={"status": row.get("status"), "fingerprint": row.get("fingerprint"), "source_opportunity_id": row.get("source_opportunity_id")})
            item["source_opportunity_id"] = row.get("source_opportunity_id")
            findings.append(item)
        if portfolio.get("counts", {}).get("NEEDS_RESEARCH"):
            findings.append(_finding(source_system="growth_operations", source_record_id="growth_research_queue", category="growth_research", priority="P4", summary="Growth research queue needs attention", reason="one or more growth experiments lack current evidence", truth_class="UNKNOWN", freshness="UNKNOWN", recommended_action="research_refresh.request", action_class="APPROVAL_REQUIRED", approval_required=True, state=portfolio.get("counts")))
        if portfolio.get("counts", {}).get("MEASUREMENT_PENDING"):
            findings.append(_finding(source_system="growth_operations", source_record_id="growth_measurement_connection", category="growth_measurement_gap", priority="P3", summary="Growth measurement is pending", reason="Search Console/Analytics are not connected; outcome remains UNKNOWN", truth_class="UNKNOWN", freshness="UNKNOWN", recommended_action="measurement_gap.report", action_class="AUTO_EXECUTE_INTERNAL_SAFE", approval_required=False, state={"measurement_pending": portfolio.get("counts", {}).get("MEASUREMENT_PENDING")}))
    except Exception as exc:
        sources["growth_operations"] = "UNAVAILABLE"
        errors.append(f"growth_operations:{type(exc).__name__}")

    try:
        creative = creative_portfolio()
        sources["creative_studio"] = "CONNECTED"
        for row in [item for item in persistence.read_records("creative_assets") if item.get("status") == "REVIEW_REQUIRED"][:10]:
            findings.append(_finding(source_system="creative_studio", source_record_id=row.get("asset_id", "unknown"), category="creative_review", priority="P2", summary=f"Creative asset needs Ray review: {row.get('asset_type', 'asset')}", reason="internal asset is ready for review; public distribution remains blocked", truth_class="INTERNAL_DRAFT", freshness="CURRENT", recommended_action="business_attention.review", action_class="APPROVAL_REQUIRED", approval_required=True, evidence_refs=row.get("evidence_refs", []), state={"status": row.get("status"), "input_fingerprint": row.get("input_fingerprint")}))
    except Exception as exc:
        sources["creative_studio"] = "UNAVAILABLE"
        errors.append(f"creative_studio:{type(exc).__name__}")

    findings.sort(key=lambda item: (PRIORITY_RANK[item["priority"]], item["finding_id"]))
    return {"schema_version": BUSINESS_ATTENTION_SCHEMA, "priority_policy": BUSINESS_PRIORITY_POLICY, "generated_at": _now(), "findings": findings, "sources": sources, "errors": errors, "top_priority": findings[0] if findings else None, "external_action_performed": False}


def write_business_priority_brief(result: Dict[str, Any], path: Path) -> str:
    lines = ["# GoClear Business Active Operator Brief", "", f"Generated: {result.get('generated_at')}", "", "## Business Health", "", "Business attention is derived from canonical read models. Unknown revenue or measurement is not treated as zero.", "", "## Top Priorities", ""]
    if not result.get("findings"):
        lines.append("- No business attention required.")
    for item in result.get("findings", [])[:10]:
        lines.append(f"- **{item['priority']}** {item['summary']} — {item['reason']} Next: `{item['recommended_action']}`; approval: `{item['approval_required']}`.")
    lines.extend(["", "## Sources", ""])
    lines.extend([f"- {key}: {value}" for key, value in result.get("sources", {}).items()])
    lines.extend(["", "## Safety", "", "- Internal analysis/report only.", "- external_action_performed=false", "- No publishing, messaging, financial mutation, funding submission, trading, or arbitrary shell."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def answer_business_question(question: str, *, heartbeat: Optional[Dict[str, Any]] = None, latest_receipt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Hermes-facing read helper; priority is computed by this canonical adapter."""
    text = str(question or "").lower()
    heartbeat = heartbeat or {}
    if "away" in text or "did nexus" in text:
        receipt = latest_receipt or {}
        return {"type": "away_mode", "operator_run_id": receipt.get("operator_run_id") or heartbeat.get("operator_run_id"), "safe_actions": receipt.get("business_safe_actions_executed", []), "work_orders": receipt.get("business_work_orders_created", []), "duplicates_suppressed": receipt.get("business_duplicates_suppressed", heartbeat.get("business_duplicates_suppressed", 0)), "source": "Active Operator receipt", "external_action_performed": False}
    priorities = heartbeat.get("business_priorities") or []
    if "approval" in text or "ray" in text:
        priorities = [row for row in priorities if row.get("approval_required")]
    return {"type": "today_priorities", "priorities": priorities[:5], "needs_ray": sum(1 for row in priorities if row.get("approval_required")), "source": "Active Operator heartbeat", "external_action_performed": False}
