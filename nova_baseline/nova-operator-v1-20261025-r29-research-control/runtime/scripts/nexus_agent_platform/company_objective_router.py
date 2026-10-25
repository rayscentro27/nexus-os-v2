"""Company-level objective planning over the canonical Nexus routes.

This is intentionally a planning/router layer: it chooses governed specialists,
orders handoffs, and records approval boundaries. It does not publish, spend,
submit financial applications, or place live trades.
"""
from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from typing import Any

from .department_router import classify_intent, resolve


def _contains(text: str, *terms: str) -> bool:
    value = text.lower()
    return any(term in value for term in terms)


def build_root_objective(text: str, *, conversation_message_id: str | int | None = None,
                         submitted_by: str = "RAY", submitted_at: str | None = None) -> dict[str, Any]:
    """Group an entire direct message as one root; headings are requirements."""
    clean = text.strip()
    stable = f"{conversation_message_id or ''}:{clean}".encode("utf-8")
    objective_id = "root_" + hashlib.sha256(stable).hexdigest()[:20]
    requirements: list[dict[str, str]] = []
    current = "General requirements"
    body: list[str] = []
    for raw in clean.splitlines():
        line = raw.strip().strip("#").strip()
        if not line:
            continue
        heading = re.match(r"^(?:\d+[.)]\s*)?([A-Z][A-Z _/&-]{2,})$", line)
        if heading:
            if body:
                requirements.append({"section": current, "text": " ".join(body)[:1000]})
                body = []
            current = heading.group(1).title()
        else:
            body.append(line)
    if body:
        requirements.append({"section": current, "text": " ".join(body)[:1000]})
    return {
        "objective_id": objective_id,
        "objective_source": "RAY",
        "objective_source_type": "DIRECT_MESSAGE",
        "submitted_by": submitted_by,
        "submitted_at": submitted_at or datetime.now(timezone.utc).isoformat(),
        "conversation_message_id": conversation_message_id,
        "explicit_intent": True,
        "parent_objective_id": None,
        "requirements": requirements or [{"section": "General requirements", "text": clean[:1000]}],
    }


def route_company_objective(text: str, *, conversation_message_id: str | int | None = None) -> dict[str, Any]:
    """Resolve only the owners required by the requested work and evidence."""
    clean = re.sub(r"\s+", " ", text.strip())[:500]
    root_objective = build_root_objective(text, conversation_message_id=conversation_message_id)
    intent = classify_intent(clean)
    base = resolve(clean)
    lower = clean.lower()
    requested: list[tuple[str, str, str, str]] = []
    rules = (
        (r"\b(research|discover|verify|source evidence|trend evidence|competitor evidence|audience evidence)\b", "RESEARCH_ALPHA", "ALPHA", "resolve_evidence_question", "read_only"),
        (r"\b(business opportunity|business idea|affiliate opportunity|revenue model|customer need|commercial viability|opportunity)\b", "ATLAS_OPPORTUNITY", "OPPORTUNITY_ENGINE", "evaluate_commercial_candidate", "internal_review"),
        (r"\b(economic|economics|commission|payout|break-even|unit economics|acquisition cost)\b", "FINANCE", "FINANCE", "evaluate_evidenced_economics", "internal_review"),
        (r"\b(claim|disclosure|compliance|guaranteed|eligibility wording)\b", "COMPLIANCE", "COMPLIANCE_ENGINE", "review_or_repair_supported_claims", "internal_review"),
        (r"\b(campaign|positioning|audience segmentation|channel strategy|funnel|content plan|marketing)\b", "MARKETING_CREATIVE", "GROWTH", "prepare_campaign_strategy", "draft_only"),
        (r"\b(asset production|produce asset|image|video|creative asset|typography|visual execution)\b", "MARKETING_CREATIVE", "CREATIVE", "produce_or_revise_requested_asset", "draft_only"),
        (r"\b(trading|trading strategy|trading indicator|entry signal|exit signal|backtest)\b", "TRADING", "TRADING_ENGINE", "develop_or_test_trading_candidate", "paper_only"),
        (r"\b(technology|capability|experiment|benchmark|prototype)\b", "LABS", "LABS", "run_bounded_capability_experiment", "internal_experiment"),
        (r"\b(incident|restore|production health|operational capability)\b", "SYSTEMS", "SYSTEMS", "restore_and_verify_safe_capability", "internal_reversible"),
    )
    seen: set[tuple[str, str]] = set()
    for pattern, owner, specialist, action, authority in rules:
        if re.search(pattern, lower):
            key=(owner,action)
            if key not in seen:
                requested.append((owner,specialist,action,authority)); seen.add(key)
    if not requested:
        requested=[(base.get("department","GOVERNANCE_REVIEW"),base.get("specialist","NOVA"),base.get("action","clarify_or_queue_unresolved_objective"),base.get("authority","human_review"))]
    steps=[{"order":i,"owner":owner,"specialist":specialist,"action":action,"authority":authority} for i,(owner,specialist,action,authority) in enumerate(requested,1)]
    approvals=["Ray approval before Creative generation, external publication, paid traffic, financial execution, client submission, or irreversible action."]
    return {
        "schema_version":"nexus.company-objective-plan.v1",
        "objective":clean,
        "root_objective":root_objective,
        "intent_class":intent,
        "canonical_route":{"department":steps[0]["owner"],"basis":"WORK_REQUIRED_AND_DEPARTMENT_MISSION"},
        "steps":steps,
        "handoff_order":[step["owner"] for step in steps],
        "routing_basis":{"work_required":clean,"current_goal_considered":True,"handoff_evidence_considered":"when supplied by downstream handoff contract","fixed_chain":False},
        "approval_boundaries":approvals,
        "continuation":"Parent objective remains open until every required decision has evidence and a receipt or a governed blocker.",
        "outcome_integrity":"Plans and test results are not business outcomes; unknown metrics remain UNKNOWN.",
    }
