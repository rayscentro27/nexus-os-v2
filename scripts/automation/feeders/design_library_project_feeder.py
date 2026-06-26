"""Design Library project feeder from existing assets/design references only."""
from __future__ import annotations

from typing import Any

from feeders.common import (
    arr, high_risk_reason, is_public_safe, make_candidate, project_enrichment, run_candidates,
    safe_blob, score_value, table_rows, text,
)

FEEDER_ID = "design_library_project_feeder"
TASK_TYPE = "design_library_project"
PROOF_EVENT = "design_library_project_created"
TERMS = ("design", "asset", "visual", "image", "template", "brand", "layout", "ui", "creative")


def _research(row: dict[str, Any]) -> dict[str, Any] | None:
    e = project_enrichment(row)
    blob = safe_blob(e.get("destination"), e.get("category"), row.get("title"), row.get("snippet"))
    if not e or not any(term in blob for term in TERMS) or not is_public_safe(row, e):
        return None
    risks = arr(e.get("risk_triggers"))
    if high_risk_reason(risks):
        return None
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="design_library", owner_tab="design", project_type="design_asset",
        unique_key=f"research_sources:{row.get('id')}", source_kind="research_sources", source_id=text(row.get("id")),
        source_url=text(row.get("url"), None), source_title=text(row.get("title")),
        title=f"Design reference: {text(row.get('title') or row.get('url'), 'Research source')}",
        summary=text(e.get("summary") or row.get("snippet"), "Saved research can be organized as a design reference."),
        pros=arr(e.get("pros")) or ["Reference-only use is safe.", "Can guide future layouts/assets."],
        cons=arr(e.get("cons")) or ["Do not clone external assets."],
        recommendation=text(e.get("recommendation"), "Add to Design Library as reference-only material."),
        proposed_schedule=text(e.get("proposed_schedule"), "Review this week and tag for future creative use."),
        next_action=text(e.get("next_action"), "Create a design reference card."),
        score=score_value(e.get("score"), fallback=45),
        approval_required=bool(e.get("approval_required")),
        risk_triggers=risks,
    )


def _asset(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    title = text(row.get("title") or row.get("asset_type"), "Design asset")
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="design_library", owner_tab="design", project_type="design_asset",
        unique_key=f"creative_assets:{row.get('id')}", source_kind="creative_assets", source_id=text(row.get("id")),
        visual_url=text(payload.get("image_url") or payload.get("preview_url"), None),
        title=f"Design library asset: {title}",
        summary=text(row.get("body") or row.get("content") or row.get("hook"), "Existing creative asset can be cataloged for design review."),
        pros=["Organizes existing asset metadata.", "No new image generation is performed."],
        cons=["Public use still requires approval."],
        recommendation="Catalog asset, note usage constraints, and request changes if needed.",
        proposed_schedule="Review and tag this asset this week.",
        next_action="Open Design Library and decide whether to tag, revise, or send to Creative.",
        score=score_value(row.get("score"), payload.get("score"), fallback=55),
    )


def _design_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    title = text(row.get("source_name") or row.get("feature_name") or row.get("review_title") or row.get("title"), "Design item")
    summary = text(row.get("summary") or row.get("user_goal") or row.get("recommendation"), "Existing design item needs library review.")
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="design_library", owner_tab="design", project_type="design_asset",
        unique_key=f"{table}:{row.get('id')}", source_kind=table, source_id=text(row.get("id")),
        title=f"Design library review: {title}",
        summary=summary,
        pros=["Uses existing design source data.", "Organizing/review is internal-only."],
        cons=["External inspiration remains reference-only."],
        recommendation="Review usefulness and usage constraints before sending to Creative.",
        proposed_schedule="Review this week; no public use without approval.",
        next_action="Tag, request changes, or park the design item.",
        score=score_value(row.get("usefulness_score"), row.get("overall_score"), fallback=52),
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "creative_assets", f"select=*&order=created_at.desc&limit={limit * 2}"):
        candidates.append(_asset(row))
    for table in ("design_inspiration_sources", "feature_design_packets", "ui_quality_reviews"):
        for row in table_rows(sb, table, f"select=*&order=created_at.desc&limit={limit * 2}"):
            candidates.append(_design_row(table, row))
    for row in table_rows(sb, "research_sources", f"select=*&order=created_at.desc&limit={limit * 5}"):
        c = _research(row)
        if c:
            candidates.append(c)
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
