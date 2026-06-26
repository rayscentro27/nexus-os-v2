"""GoClear Revenue Hub feeder.

Reads existing safe Nexus rows/reports and creates internal revenue metric project cards.
No payment processor calls, affiliate API calls, emails, publish, deploy, or external AI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import make_candidate, project_enrichment, run_candidates, score_value, table_rows, text

FEEDER_ID = "goclear_revenue_hub_feeder"
TASK_TYPE = "goclear_revenue_metric_project"
PROOF_EVENT = "goclear_revenue_hub_metrics_updated"
ROOT = Path(__file__).resolve().parent.parent.parent.parent

TERMS = (
    "goclear", "apex", "funding", "credit", "readiness", "business credit",
    "$97", "$297", "$497", "affiliate", "referral", "nav", "beehiiv", "pictory",
    "seo/content", "revenue hub", "readiness review",
)
EXCLUDED_TASK_TYPES = {
    TASK_TYPE,
    "integration_status_project",
    "event_ledger_project",
    "agent_job_project",
    "command_center_summary",
}


def blob(*values: Any) -> str:
    return " ".join(text(v) for v in values if text(v)).lower()


def relevant_row(row: dict[str, Any]) -> bool:
    if text(row.get("task_type")) in EXCLUDED_TASK_TYPES:
        return False
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if payload.get("department") in ("integrations", "events_feed", "agent_jobs", "command_center"):
        return False
    enrichment = project_enrichment(row)
    body = blob(
        row.get("task_type"), row.get("result_summary"), row.get("summary"),
        payload.get("title"), payload.get("summary"), payload.get("recommendation"),
        payload.get("source_title"), enrichment.get("summary"), enrichment.get("recommendation"),
        enrichment.get("destination"), enrichment.get("category"),
    )
    return any(term in body for term in TERMS)


def metric_payload(row: dict[str, Any], source_kind: str) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    enrichment = project_enrichment(row)
    score = score_value(payload.get("score"), enrichment.get("score"), fallback=55)
    title = text(payload.get("title") or payload.get("source_title") or row.get("task_type"), "GoClear revenue signal")
    estimated = 97
    body = blob(title, payload.get("summary"), enrichment.get("summary"), enrichment.get("recommendation"), row.get("result_summary"))
    if "upgrade" in body or "$297" in body or "$497" in body:
        estimated = 297
    if "affiliate" in body or "nav" in body or "partner" in body:
        estimated += 150
    if "seo" in body or "lead" in body:
        estimated += 97
    return {
        "title": f"GoClear revenue signal: {title}"[:140],
        "summary": text(enrichment.get("summary") or payload.get("summary") or row.get("result_summary"), "Existing Nexus output suggests a GoClear/Apex revenue-pipeline signal."),
        "recommendation": "Review this as a GoClear Revenue Hub metric candidate; do not charge, email, publish, or change offers from this feeder.",
        "score": score,
        "estimated": int(estimated * max(0.25, min(1.5, score / 70))),
        "source_id": text(row.get("id")),
        "source_kind": source_kind,
        "source_url": text(payload.get("source_url"), "") or None,
    }


def report_candidates(limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted((ROOT / "reports" / "manual_publish").glob("*goclear*"))[: limit * 2]:
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        title = path.stem.replace("_", " ")
        candidates.append(make_candidate(
            feeder_id=FEEDER_ID,
            task_type=TASK_TYPE,
            proof_event_type=PROOF_EVENT,
            department="opportunity_lab",
            owner_tab="goclear",
            project_type="revenue_metric",
            unique_key=f"manual_report:{path.relative_to(ROOT)}",
            source_kind="manual_publish_report",
            source_id=str(path.relative_to(ROOT)),
            title=f"GoClear report metric: {title}"[:140],
            summary=f"Safe local report available for GoClear Revenue Hub review: {path.relative_to(ROOT)}",
            pros=["Uses an existing local Nexus report.", "No payment processor or affiliate API call required."],
            cons=["Revenue values may be estimated until live connectors are configured."],
            recommendation="Review the report and decide which revenue metric source should be connected next.",
            proposed_schedule="Manual review in next daily digest; scheduler remains disabled.",
            next_action="Open the report and classify the metric as lead, purchase, referral, or content signal.",
            score=60,
            data_sources=["reports/manual_publish"],
            metadata_extra={
                "metrics": {"estimated_revenue_potential": 97, "actual_revenue": None},
                "affiliate_stats": {},
                "pipeline_stage": "source_detected",
            },
        ))
    return candidates


def task_candidates(sb, limit: int) -> list[dict[str, Any]]:
    rows = table_rows(sb, "task_requests", f"select=*&order=created_at.desc&limit={limit * 8}")
    candidates = []
    for row in rows:
        if not relevant_row(row):
            continue
        metric = metric_payload(row, "task_requests")
        candidates.append(make_candidate(
            feeder_id=FEEDER_ID,
            task_type=TASK_TYPE,
            proof_event_type=PROOF_EVENT,
            department="opportunity_lab",
            owner_tab="goclear",
            project_type="revenue_metric",
            unique_key=f"task_requests:{metric['source_id']}",
            source_kind="task_requests",
            source_id=metric["source_id"],
            source_url=metric["source_url"],
            title=metric["title"],
            summary=metric["summary"],
            pros=["Existing Nexus task/request already points at GoClear, funding, credit, lead, or affiliate work."],
            cons=["Actual revenue remains connector-dependent until payment/referral sources are safely connected."],
            recommendation=metric["recommendation"],
            proposed_schedule="Review in the next manual daily digest; no scheduler is active.",
            next_action="Classify the signal and decide whether it belongs in leads, $97 purchases, upgrades, referrals, or content leads.",
            score=metric["score"],
            data_sources=["task_requests"],
            metadata_extra={
                "metrics": {
                    "readiness_review_leads": 1,
                    "estimated_revenue_potential": metric["estimated"],
                    "actual_revenue": None,
                },
                "affiliate_stats": {
                    "clicks": None,
                    "conversions": None,
                    "estimated_commission": None,
                    "actual_commission": None,
                },
                "pipeline_stage": "source_detected",
            },
        ))
    return candidates


def research_candidates(sb, limit: int) -> list[dict[str, Any]]:
    rows = table_rows(sb, "research_sources", f"select=*&order=created_at.desc&limit={limit * 8}")
    candidates = []
    for row in rows:
        enrichment = project_enrichment(row)
        body = blob(row.get("title"), row.get("url"), enrichment.get("summary"), enrichment.get("destination"), enrichment.get("category"))
        if not any(term in body for term in TERMS):
            continue
        score = score_value(enrichment.get("score"), fallback=45)
        candidates.append(make_candidate(
            feeder_id=FEEDER_ID,
            task_type=TASK_TYPE,
            proof_event_type=PROOF_EVENT,
            department="opportunity_lab",
            owner_tab="goclear",
            project_type="revenue_metric",
            unique_key=f"research_sources:{row.get('id')}",
            source_kind="research_sources",
            source_id=text(row.get("id")),
            source_url=text(row.get("url"), "") or None,
            source_title=text(row.get("title"), "GoClear research source"),
            title=f"GoClear research metric: {text(row.get('title'), 'Research source')}"[:140],
            summary=text(enrichment.get("summary") or row.get("snippet"), "Research source may inform GoClear/Apex revenue pipeline."),
            pros=["Uses existing saved research metadata.", "No capture or external enrichment required."],
            cons=["Revenue impact is estimated until a real lead/purchase/referral source is connected."],
            recommendation="Review as a GoClear/Apex revenue or affiliate metric candidate.",
            proposed_schedule="Manual digest review; scheduler remains disabled.",
            next_action="Map to lead, $97 review, upgrade, referral, SEO/content lead, or park.",
            score=score,
            data_sources=["research_sources"],
            metadata_extra={
                "metrics": {"estimated_revenue_potential": max(25, int(97 * score / 70)), "actual_revenue": None},
                "affiliate_stats": {},
                "pipeline_stage": "source_detected",
            },
        ))
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    candidates = []
    candidates.extend(task_candidates(sb, limit))
    candidates.extend(research_candidates(sb, limit))
    candidates.extend(report_candidates(limit))
    return run_candidates(
        sb,
        feeder_id=FEEDER_ID,
        task_type=TASK_TYPE,
        proof_event_type=PROOF_EVENT,
        dry_run=dry_run,
        limit=limit,
        candidates=candidates,
    )
