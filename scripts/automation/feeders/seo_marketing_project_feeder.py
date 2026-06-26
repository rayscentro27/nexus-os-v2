"""SEO / Marketing feeder from existing enriched research and local growth rows."""
from __future__ import annotations

from typing import Any

from feeders.common import (
    arr, high_risk_reason, is_public_safe, make_candidate, project_enrichment, run_candidates,
    safe_blob, score_value, table_rows, text,
)

FEEDER_ID = "seo_marketing_project_feeder"
TASK_TYPE = "seo_marketing_project"
PROOF_EVENT = "seo_marketing_project_created"
TERMS = ("seo", "marketing", "content", "keyword", "funnel", "landing", "goclear", "apex", "lead", "growth")


def _research(row: dict[str, Any]) -> dict[str, Any] | None:
    e = project_enrichment(row)
    blob = safe_blob(e.get("destination"), e.get("category"), row.get("title"), row.get("snippet"), e.get("recommendation"))
    if not e or not any(term in blob for term in TERMS) or not is_public_safe(row, e):
        return None
    risks = arr(e.get("risk_triggers"))
    if high_risk_reason(risks):
        return None
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="growth", owner_tab="seo", project_type="growth_opportunity",
        unique_key=f"research_sources:{row.get('id')}", source_kind="research_sources", source_id=text(row.get("id")),
        source_url=text(row.get("url"), None), source_title=text(row.get("title")),
        title=f"Growth opportunity: {text(row.get('title') or row.get('url'), 'Research source')}",
        summary=text(e.get("summary") or row.get("snippet"), "Saved research can become a draft/report growth opportunity."),
        pros=arr(e.get("pros")) or ["Uses saved public research.", "Draft/reporting is safe."],
        cons=arr(e.get("cons")) or ["Publishing site changes, ads, email, or social posts remains approval-gated."],
        recommendation=text(e.get("recommendation"), "Create a content/SEO brief; do not publish changes."),
        proposed_schedule=text(e.get("proposed_schedule"), "Draft brief this week; publish only after approval."),
        next_action=text(e.get("next_action"), "Create an internal growth report or article draft task."),
        score=score_value(e.get("score"), fallback=45),
        approval_required=bool(e.get("approval_required")),
        risk_triggers=risks,
    )


def _seo_row(row: dict[str, Any]) -> dict[str, Any]:
    title = text(row.get("title") or row.get("keyword") or row.get("page_url"), "SEO opportunity")
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="growth", owner_tab="seo", project_type="content_opportunity",
        unique_key=f"seo_opportunities:{row.get('id')}", source_kind="seo_opportunities", source_id=text(row.get("id")),
        source_url=text(row.get("page_url"), None),
        title=f"SEO/content project: {title}",
        summary=text(row.get("reason") or row.get("summary"), "Existing SEO row can become a content/report task."),
        pros=["Uses existing SEO row.", "Creates draft/report only."],
        cons=["Publishing and ads remain approval-gated."],
        recommendation=text(row.get("recommended_action"), "Create a draft brief or growth report."),
        proposed_schedule="Review this week; create draft before scheduling any public update.",
        next_action="Create article/report task or park the opportunity.",
        score=score_value(row.get("score"), fallback=55),
    )


def _social(row: dict[str, Any]) -> dict[str, Any] | None:
    blob = safe_blob(row.get("title"), row.get("caption"), row.get("body"), row.get("platform"))
    if not any(term in blob for term in TERMS):
        return None
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="growth", owner_tab="seo", project_type="content_opportunity",
        unique_key=f"social_posts:{row.get('id')}", source_kind="social_posts", source_id=text(row.get("id")),
        title=f"Growth draft review: {text(row.get('title') or row.get('platform'), 'Social draft')}",
        summary=text(row.get("caption") or row.get("body"), "Existing social draft can inform a growth content task."),
        pros=["Draft exists already.", "Review/report only."],
        cons=["Public posting remains approval-gated."],
        recommendation="Extract a content angle or CTA test; do not post.",
        proposed_schedule="Review this week; publish only through approval gates.",
        next_action="Create growth content task or route to Creative.",
        score=score_value(row.get("score"), fallback=45),
        approval_required=True,
        risk_triggers=["publish_send_trade_deploy"],
        status="needs_review",
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "seo_opportunities", f"select=*&order=created_at.desc&limit={limit * 3}"):
        candidates.append(_seo_row(row))
    for row in table_rows(sb, "research_sources", f"select=*&order=created_at.desc&limit={limit * 5}"):
        c = _research(row)
        if c:
            candidates.append(c)
    for row in table_rows(sb, "social_posts", f"select=*&order=created_at.desc&limit={limit * 2}"):
        c = _social(row)
        if c:
            candidates.append(c)
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
