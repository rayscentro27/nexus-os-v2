"""Creative Studio project feeder from existing drafts/assets/research only."""
from __future__ import annotations

from typing import Any

from feeders.common import (
    arr, high_risk_reason, is_public_safe, make_candidate, project_enrichment, run_candidates,
    safe_blob, score_value, table_rows, text,
)

FEEDER_ID = "creative_studio_project_feeder"
TASK_TYPE = "creative_studio_project"
PROOF_EVENT = "creative_studio_project_created"
TERMS = ("content", "campaign", "social", "copy", "copywriting", "video", "creative", "brand", "offer", "marketing")


def _from_research(row: dict[str, Any]) -> dict[str, Any] | None:
    e = project_enrichment(row)
    blob = safe_blob(e.get("destination"), e.get("category"), row.get("title"), row.get("snippet"), e.get("recommendation"))
    if not e or not any(term in blob for term in TERMS):
        return None
    if not is_public_safe(row, e):
        return None
    risks = arr(e.get("risk_triggers"))
    high = high_risk_reason(risks)
    if high:
        return None
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="creative_studio", owner_tab="creative", project_type="creative_project",
        unique_key=f"research_sources:{row.get('id')}", source_kind="research_sources", source_id=text(row.get("id")),
        source_url=text(row.get("url"), None), source_title=text(row.get("title")),
        title=f"Creative project: {text(row.get('title') or row.get('url'), 'Research source')}",
        summary=text(e.get("summary") or row.get("snippet"), "Existing research can become draft-only creative direction."),
        pros=arr(e.get("pros")) or ["Uses already-saved research.", "Draft-only creative work is safe."],
        cons=arr(e.get("cons")) or ["Publishing remains approval-gated."],
        recommendation=text(e.get("recommendation"), "Create a draft creative brief; do not publish."),
        proposed_schedule=text(e.get("proposed_schedule"), "Draft brief this week; send for approval before any public use."),
        next_action=text(e.get("next_action"), "Create an internal creative brief task."),
        score=score_value(e.get("score"), fallback=45),
        approval_required=bool(e.get("approval_required")),
        risk_triggers=risks,
    )


def _from_asset(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    title = text(row.get("title") or row.get("asset_type"), "Creative asset")
    status = "needs_review" if "publish" in safe_blob(row.get("status"), row.get("asset_type")) else "proposed"
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="creative_studio", owner_tab="creative", project_type="creative_project",
        unique_key=f"creative_assets:{row.get('id')}", source_kind="creative_assets", source_id=text(row.get("id")),
        visual_url=text(payload.get("image_url") or payload.get("preview_url"), None),
        title=f"Creative project: {title}",
        summary=text(row.get("body") or row.get("content") or row.get("hook"), "Existing creative asset ready for draft review."),
        pros=["Uses existing asset/draft.", "No social publishing is executed."],
        cons=["Compliance and final public use still require approval."],
        recommendation=text(row.get("cta") or payload.get("recommendation"), "Review asset quality and convert into a draft-only campaign task."),
        proposed_schedule="Review draft asset this week; approval required before publish/send.",
        next_action="Create a revision or approval-prep task in Creative Studio.",
        score=score_value(row.get("score"), payload.get("score"), fallback=55),
        approval_required=status == "needs_review",
        risk_triggers=["publish_send_trade_deploy"] if status == "needs_review" else [],
        status=status,
    )


def _from_social_post(row: dict[str, Any]) -> dict[str, Any]:
    title = text(row.get("title") or row.get("platform"), "Social draft")
    approval_required = True
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="creative_studio", owner_tab="creative", project_type="creative_project",
        unique_key=f"social_posts:{row.get('id')}", source_kind="social_posts", source_id=text(row.get("id")),
        title=f"Creative draft review: {title}",
        summary=text(row.get("caption") or row.get("body") or row.get("copy"), "Existing social draft needs creative review."),
        pros=["Draft already exists.", "Feeder creates review card only."],
        cons=["Publishing is explicitly gated and not executed."],
        recommendation="Review copy, compliance, and CTA; send for approval before any public post.",
        proposed_schedule="Review draft now; publish only through existing approval gates.",
        next_action="Open Creative Studio and decide whether to revise, park, or send for approval.",
        score=score_value(row.get("score"), fallback=50),
        approval_required=approval_required,
        risk_triggers=["publish_send_trade_deploy"],
        status="needs_review",
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "creative_assets", f"select=*&order=created_at.desc&limit={limit * 3}"):
        candidates.append(_from_asset(row))
    for row in table_rows(sb, "social_posts", f"select=*&order=created_at.desc&limit={limit * 2}"):
        candidates.append(_from_social_post(row))
    for row in table_rows(sb, "research_sources", f"select=*&order=created_at.desc&limit={limit * 5}"):
        c = _from_research(row)
        if c:
            candidates.append(c)
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
