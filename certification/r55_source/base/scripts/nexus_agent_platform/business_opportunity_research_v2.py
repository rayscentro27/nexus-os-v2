"""Adaptive, evidence-led Business Opportunity Research on existing Nexus stores.

This module adds an intake/context/director layer over the canonical Research
queue and NotebookLM contracts. It does not create a scheduler, queue,
NotebookLM client, model router, or downstream business-plan executor.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_DIR = ROOT / "data/runtime/business_opportunity_context"
CONTEXT_PATH = CONTEXT_DIR / "opportunities.json"

ENTRY_TYPES = {"SOURCE_LED", "VENDOR_LED", "OBJECTIVE_LED", "TREND_SIGNAL_LED",
               "RELATED_BUT_UNCLASSIFIED"}
SOURCE_ROLES = {"BUSINESS_MODEL", "PRODUCT_DISCOVERY", "MARKET_INTELLIGENCE",
    "PRICING_INTELLIGENCE", "CUSTOMER_INTELLIGENCE", "COMPETITOR_INTELLIGENCE",
    "MARKETING_INTELLIGENCE", "SUPPLIER_INTELLIGENCE", "PLATFORM_INTELLIGENCE",
    "STRATEGY", "OTHER"}
RELATIONSHIPS = {"MATCH_EXISTING_OPPORTUNITY", "NEW_OPPORTUNITY", "RELATED_BUT_DISTINCT",
                 "RELATED_BUT_UNCLASSIFIED"}
MONETIZATION_PATHS = {"SELL_PRODUCT", "PROVIDE_SERVICE", "AFFILIATE", "REFERRAL",
    "WHITE_LABEL", "CONSULTING", "EDUCATION", "DIGITAL_PRODUCT", "LEAD_GENERATION",
    "CONTENT_BUSINESS", "SOFTWARE", "MARKETPLACE", "MERCH_FAST_LAUNCH", "AFFILIATE_OFFER",
    "CONTENT_OPPORTUNITY", "FULL_BUSINESS", "ARCHIVE", "OTHER"}
MATERIAL_TOPICS = {"viability", "customer", "problem", "offer", "product", "market",
    "niche", "pricing", "startup_cost", "operating_cost", "unit_economics", "sourcing",
    "fulfillment", "delivery_time", "monetization", "customer_acquisition", "affiliate",
    "reseller", "white_label", "cheaper_entry", "risk", "next_department_action"}
TREND_SIGNAL_CLASSES = {"GOOGLE_SEARCH_TREND", "YOUTUBE_VIDEO_TREND", "YOUTUBE_TOPIC_TREND",
    "TIKTOK_FORMAT_TREND", "PRODUCT_TREND", "COMMUNITY_TREND", "CUSTOMER_COMPLAINT_TREND", "TECHNOLOGY_TREND"}
EVIDENCE_STATES = {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED",
                   "HISTORICAL", "ENTITY_MISMATCH"}

_STOP = {"the", "and", "for", "with", "from", "that", "this", "business", "idea",
         "opportunity", "research", "what", "how", "into", "your", "their", "about"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable(prefix: str, payload: Any, size: int = 18) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:size]}"


def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", str(text or "").lower())
            if len(x) > 2 and x not in _STOP}


def classify_entry_type(*, objective: str = "", source_url: str = "", source_type: str = "",
                        vendor_name: str = "", trend_signal: Mapping[str, Any] | None = None,
                        explicit: str | None = None) -> str:
    if explicit:
        value = explicit.strip().upper()
        if value not in ENTRY_TYPES:
            raise ValueError("unsupported_opportunity_entry_type")
        return value
    if trend_signal or str((trend_signal or {}).get("signal_class") or "").upper() in TREND_SIGNAL_CLASSES:
        return "TREND_SIGNAL_LED"
    if vendor_name.strip() or any(term in (source_url + " " + objective).lower()
                                  for term in ("vendor", "supplier", "saas product", "white-label", "livestorebuild")):
        return "VENDOR_LED"
    kind = str(source_type or "").upper()
    host = urlsplit(source_url).netloc.lower()
    if kind in {"YOUTUBE_VIDEO", "VIDEO", "PODCAST", "ARTICLE", "PDF", "SOCIAL_POST"} or host:
        return "SOURCE_LED"
    if objective.strip():
        return "OBJECTIVE_LED"
    return "RELATED_BUT_UNCLASSIFIED"


def classify_source_role(*, title: str = "", description: str = "", url: str = "") -> str:
    text = f"{title} {description} {url}".lower()
    rules = [
        ("SUPPLIER_INTELLIGENCE", ("supplier", "manufacturer", "wholesale", "dropship", "moq", "fulfillment")),
        ("PRICING_INTELLIGENCE", ("pricing", "price", "cost", "fee", "commission", "subscription")),
        ("CUSTOMER_INTELLIGENCE", ("customer", "complaint", "review", "pain point", "willingness to pay")),
        ("COMPETITOR_INTELLIGENCE", ("competitor", "alternative", "versus", " vs ", "comparison")),
        ("PLATFORM_INTELLIGENCE", ("platform", "policy", "marketplace", "shopify", "tiktok shop", "youtube policy")),
        ("MARKETING_INTELLIGENCE", ("marketing", "ads", "seo", "conversion", "acquisition", "funnel")),
        ("PRODUCT_DISCOVERY", ("product", "product ideas", "boring products", "product discovery")),
        ("STRATEGY", ("strategy", "how to start", "business model", "playbook")),
        ("BUSINESS_MODEL", ("business model", "start a business", "agency", "subscription business", "side hustle")),
        ("MARKET_INTELLIGENCE", ("market size", "market trend", "industry report", "demand")),
    ]
    for role, terms in rules:
        if any(term in text for term in terms):
            return role
    return "OTHER"


def classify_vendor_claim(text: str, *, identity_match: bool = True,
                          contradicted: bool = False, historical: bool = False,
                          official_support: bool = False) -> str:
    if not identity_match:
        return "ENTITY_MISMATCH"
    if contradicted:
        return "CONTRADICTED"
    if historical:
        return "HISTORICAL"
    if official_support and text.strip():
        return "VERIFIED"
    return "PARTIALLY_VERIFIED" if text.strip() else "UNVERIFIED"


def _context_store() -> dict[str, Any]:
    try:
        data = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"schema_version": "nexus.opportunity-context.v2", "opportunities": []}
    except (OSError, ValueError, TypeError):
        return {"schema_version": "nexus.opportunity-context.v2", "opportunities": []}


def save_opportunity_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Atomically upsert detailed active context locally, by opportunity_id."""
    row = dict(context)
    if not row.get("opportunity_id"):
        raise ValueError("opportunity_id_required")
    row.setdefault("updated_at", _now())
    store = _context_store()
    rows = list(store.get("opportunities") or [])
    for index, old in enumerate(rows):
        if old.get("opportunity_id") == row["opportunity_id"]:
            rows[index] = {**old, **row, "created_at": old.get("created_at") or row.get("created_at") or _now()}
            break
    else:
        row.setdefault("created_at", _now())
        rows.append(row)
    store.update({"schema_version": "nexus.opportunity-context.v2", "updated_at": _now(), "opportunities": rows})
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONTEXT_PATH.with_suffix(f".json.{__import__('os').getpid()}.tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(CONTEXT_PATH)
    return row


def load_opportunity_contexts() -> list[dict[str, Any]]:
    return [dict(row) for row in _context_store().get("opportunities", []) if isinstance(row, dict)]


def match_existing_opportunity(subject: str, contexts: list[Mapping[str, Any]] | None = None,
                               *, threshold: float = 0.5) -> dict[str, Any]:
    terms = _tokens(subject)
    if not terms:
        return {"relationship": "RELATED_BUT_UNCLASSIFIED", "opportunity_id": None, "score": 0.0}
    rows = contexts if contexts is not None else load_opportunity_contexts()
    scored = []
    for row in rows:
        candidates = [row.get(k) for k in ("objective", "original_idea", "current_recommended_version", "target_customer", "problem", "offer")]
        candidates.extend(row.get("candidate_products") or [])
        candidates.extend(row.get("candidate_markets") or [])
        other = set().union(*(_tokens(str(x)) for x in candidates if x)) if candidates else set()
        score = len(terms & other) / max(1, len(terms))
        if score:
            scored.append((score, row))
    if not scored:
        return {"relationship": "NEW_OPPORTUNITY", "opportunity_id": None, "score": 0.0}
    score, row = max(scored, key=lambda item: (item[0], str(item[1].get("opportunity_id") or "")))
    if score >= threshold:
        relation = "MATCH_EXISTING_OPPORTUNITY"
    elif score >= 0.2:
        relation = "RELATED_BUT_DISTINCT"
    else:
        relation = "NEW_OPPORTUNITY"
    return {"relationship": relation, "opportunity_id": row.get("opportunity_id") if relation == "MATCH_EXISTING_OPPORTUNITY" else None,
            "related_opportunity_id": row.get("opportunity_id") if relation == "RELATED_BUT_DISTINCT" else None,
            "score": round(score, 3)}


def build_intake(*, title: str, objective: str = "", source_url: str = "",
                 source_type: str = "", source_id: str | None = None,
                 description: str = "", vendor_name: str = "",
                 trend_signal: Mapping[str, Any] | None = None,
                 contexts: list[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    entry_type = classify_entry_type(objective=objective, source_url=source_url,
        source_type=source_type, vendor_name=vendor_name, trend_signal=trend_signal)
    subject = str(title or objective or vendor_name).strip()
    if not subject:
        entry_type = "RELATED_BUT_UNCLASSIFIED"
    relationship = match_existing_opportunity(subject, contexts)
    if relationship["relationship"] == "RELATED_BUT_UNCLASSIFIED":
        entry_type = "RELATED_BUT_UNCLASSIFIED"
    role = classify_source_role(title=title, description=description, url=source_url)
    sid = source_id or source_url or objective or subject
    return {"intake_id": _stable("opintake", sid), "entry_type": entry_type,
        "source_role": role, "source_id": source_id, "source_url": source_url or None,
        "title": subject, "objective": objective or None, "description_summary": str(description)[:500],
        "opportunity_relationship": relationship["relationship"],
        "matched_opportunity_id": relationship.get("opportunity_id"),
        "related_opportunity_id": relationship.get("related_opportunity_id"),
        "match_score": relationship.get("score"),
        "promotion_status": "AWAITING_ALPHA_RESEARCH_DIRECTOR" if entry_type != "RELATED_BUT_UNCLASSIFIED" else "UNCLASSIFIED",
        "feeder_role": "INTAKE_ONLY", "dedicated_notebook_required_on_promotion": True,
        "one_coherent_subject_per_notebook": True,
        "independent_reputation_branch_required": entry_type == "VENDOR_LED",
        "created_at": _now()}


def record_intake_on_queue(queue: Any, item: Mapping[str, Any], *, contexts: list[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Persist intake metadata on the original queue work item, without copying source bodies."""
    record = build_intake(title=str(item.get("title") or item.get("source_name") or ""),
        objective=str(item.get("objective") or item.get("question") or ""),
        source_url=str(item.get("source_url") or ""), source_type=str(item.get("source_type") or ""),
        source_id=str(item.get("source_id") or "") or None,
        description=str(item.get("description") or ""), contexts=contexts)
    updated = dict(item)
    updated.update({"entry_type": record["entry_type"], "source_role": record["source_role"],
        "opportunity_relationship": record["opportunity_relationship"],
        "opportunity_id": record.get("matched_opportunity_id"),
        "promotion_status": record["promotion_status"], "director_mode": "RESEARCH_DIRECTOR",
        "notebook_role": "FEEDER_INTAKE_ONLY"})
    queued = queue.upsert(updated)
    return {"intake": record, "queue_item": queued, "created_new_queue_item": False}


def promote_to_dedicated_research(context: Mapping[str, Any], *, objective: str,
                                  original_source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Create/reuse a coherent opportunity identity, without inventing notebook IDs."""
    subject = str(context.get("original_idea") or context.get("objective") or objective).strip()
    opportunity_id = str(context.get("opportunity_id") or _stable("opportunity", subject.casefold()))
    existing = next((x for x in load_opportunity_contexts() if x.get("opportunity_id") == opportunity_id), None)
    row = {**(existing or {}), **dict(context), "opportunity_id": opportunity_id,
        "objective": objective, "entry_type": context.get("entry_type") or "SOURCE_LED",
        "status": "PROMOTED_TO_RESEARCH", "original_source": dict(original_source or context.get("original_source") or {}),
        "related_sources": list(context.get("related_sources") or []),
        "notebook_id": (existing or {}).get("notebook_id") or context.get("notebook_id"),
        "notebook_subject_key": _stable("notebook_subject", {"opportunity_id": opportunity_id, "subject": subject.casefold()}),
        "notebook_role": "DEDICATED_RESEARCH", "current_recommended_version": context.get("current_recommended_version") or subject,
        "verified_findings": list(context.get("verified_findings") or []),
        "partial_findings": list(context.get("partial_findings") or []),
        "unverified_findings": list(context.get("unverified_findings") or []),
        "contradicted_findings": list(context.get("contradicted_findings") or []),
        "open_questions": list(context.get("open_questions") or []),
        "discovery_questions": list(context.get("discovery_questions") or []),
        "needle_status": context.get("needle_status") or "PENDING",
        "next_department": context.get("next_department") or "BUSINESS_OPPORTUNITIES"}
    row.setdefault("required_questions", [])
    row.setdefault("discovery_questions", [])
    row.setdefault("candidate_products", [])
    row.setdefault("candidate_markets", [])
    row.setdefault("candidate_niches", [])
    row.setdefault("candidate_delivery_models", [])
    row.setdefault("candidate_monetization_models", [])
    row.setdefault("affiliate_options", [])
    row.setdefault("referral_options", [])
    row.setdefault("reseller_options", [])
    row.setdefault("white_label_options", [])
    row.setdefault("major_risks", [])
    row.setdefault("major_assumptions", [])
    row.setdefault("external_research_actions", [])
    row.setdefault("action_items", [])
    saved = save_opportunity_context(row)
    return {"status": "REUSED" if existing else "PROMOTED", "opportunity_id": opportunity_id,
        "notebook_subject_key": row["notebook_subject_key"], "notebook_id": row.get("notebook_id"),
        "notebook_must_be_created_by_existing_notebooklm_path": not bool(row.get("notebook_id")),
        "context": saved}


def prepare_opportunity_intake(*, intake: Mapping[str, Any], objective: str,
                               original_source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Bind intake to durable local opportunity context before case/notebook work."""
    matched = str(intake.get("matched_opportunity_id") or "")
    existing = next((row for row in load_opportunity_contexts() if row.get("opportunity_id") == matched), None)
    subject = str(objective or intake.get("title") or "").strip()
    opportunity_id = matched or _stable("opportunity", subject.casefold())
    source_ref = dict(original_source or {})
    prior_sources = list((existing or {}).get("related_sources") or [])
    if source_ref and source_ref not in prior_sources and source_ref != (existing or {}).get("original_source"):
        prior_sources.append(source_ref)
    context = {**(existing or {}), "opportunity_id": opportunity_id,
        "objective": (existing or {}).get("objective") or subject, "entry_type": intake.get("entry_type") or "SOURCE_LED",
        "status": "PENDING_RESEARCH_DIRECTOR", "original_idea": (existing or {}).get("original_idea") or subject,
        "original_source": (existing or {}).get("original_source") or source_ref,
        "related_sources": prior_sources,
        "source_role": intake.get("source_role"),
        "opportunity_relationship": intake.get("opportunity_relationship"),
        "notebook_id": (existing or {}).get("notebook_id"),
        "notebook_role": "DEDICATED_RESEARCH" if existing and existing.get("notebook_id") else "PENDING_DEDICATED_RESEARCH",
        "research_director_mode": "RESEARCH_DIRECTOR",
        "next_department": "BUSINESS_OPPORTUNITIES"}
    for key in ("verified_findings", "partial_findings", "unverified_findings", "contradicted_findings",
                "required_questions", "discovery_questions", "open_questions", "major_risks", "major_assumptions",
                "external_research_actions", "action_items"):
        context.setdefault(key, [])
    saved = save_opportunity_context(context)
    return {"opportunity_id": opportunity_id, "context": saved,
        "matched_existing": bool(existing), "dedicated_notebook_id": saved.get("notebook_id")}


def fast_validation_path(context: Mapping[str, Any], *, capabilities: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Describe a low-cash test while distinguishing verified Nexus capabilities from assumptions."""
    available = dict(capabilities or {})
    usable = sorted(str(name) for name, state in available.items()
        if isinstance(state, Mapping) and str(state.get("status") or state.get("health") or "").upper() in {"AVAILABLE", "ACTIVE", "WORKING", "CONNECTED"})
    unknown = sorted(str(name) for name, state in available.items()
        if isinstance(state, Mapping) and str(state.get("status") or state.get("health") or "").upper() not in {"AVAILABLE", "ACTIVE", "WORKING", "CONNECTED"})
    return {"fastest_launchable_version": context.get("fastest_launchable_version") or "Validate the smallest sellable offer before building full operations.",
        "estimated_days_to_launch": context.get("estimated_days_to_launch"),
        "estimated_incremental_cash": context.get("estimated_incremental_cash"),
        "assets_nexus_can_create": [name for name in usable if any(x in name.casefold() for x in ("creative", "image", "video", "copy", "landing", "content"))],
        "channels_nexus_can_use": [name for name in usable if any(x in name.casefold() for x in ("youtube", "instagram", "social", "web", "publish", "marketing"))],
        "capabilities_requiring_verification": unknown,
        "first_revenue_path": context.get("first_revenue_path"), "validation_window": context.get("validation_window"),
        "success_signal": context.get("success_signal"), "pivot_signal": context.get("pivot_signal"),
        "what_not_to_build_until_validated": context.get("what_not_to_build_until_validated") or "Do not build full inventory or custom software before demand validation."}


def is_material_question(question: str, topic: str | None = None) -> bool:
    text = str(question or "").strip()
    if not text:
        return False
    lowered = text.lower()
    category = str(topic or "").strip().lower()
    if category:
        return category in MATERIAL_TOPICS
    terms = {"customer": ("customer", "buyer", "who pays", "user"),
        "problem": ("problem", "pain", "need", "complaint"),
        "offer": ("offer", "sell", "product", "service"),
        "market": ("market", "competitor", "demand", "niche"),
        "pricing": ("price", "pricing", "willingness to pay", "revenue", "margin"),
        "startup_cost": ("startup cost", "capital", "cash required"),
        "operating_cost": ("operating cost", "monthly cost", "fulfillment"),
        "unit_economics": ("break-even", "contribution", "unit economics"),
        "sourcing": ("supplier", "moq", "sourcing", "manufacturer"),
        "fulfillment": ("fulfillment", "delivery time", "shipping", "returns"),
        "monetization": ("monetize", "affiliate", "commission", "reseller", "white label"),
        "customer_acquisition": ("acquire customers", "customer acquisition", "channel", "cac"),
        "risk": ("risk", "fail", "compliance", "legal", "contradiction")}
    return any(term in lowered for values in terms.values() for term in values)


def adaptive_discovery_candidates(*, finding: Mapping[str, Any], opportunity: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Generate question candidates only where a finding implies a material unknown."""
    text = " ".join(str(finding.get(key) or "") for key in ("claim", "finding", "answer", "evidence_gap", "limitation")).lower()
    candidates: list[tuple[str, str, str]] = []
    if any(x in text for x in ("minimum order", "moq", "500 units", "bulk order")):
        candidates.append(("sourcing", "Can another supplier provide lower MOQ, sample orders, or dropshipping?", "Compare supplier terms and fee schedules."))
    if any(x in text for x in ("18 days", "delivery delay", "shipping time")):
        candidates.append(("fulfillment", "Can a domestic supplier meet the needed delivery window at viable unit cost?", "Compare delivery SLA, shipping cost, and return policy."))
    if any(x in text for x in ("commission", "affiliate fee", "take rate")):
        candidates.append(("unit_economics", "Does the commission leave positive contribution after acquisition and support costs?", "Verify commission terms and calculate contribution deterministically."))
    if any(x in text for x in ("high upfront", "willingness to pay", "price resistance")):
        candidates.append(("pricing", "What lower-friction pricing or payment model is supported by buyer evidence?", "Compare public pricing and seek buyer validation before treating preference as fact."))
    if any(x in text for x in ("integration", "pos", "implementation burden")):
        candidates.append(("product", "Which existing integrations reduce implementation effort and what access do they require?", "Check official API/app documentation and reported implementation issues."))
    return [{"question": q, "materiality_topic": topic, "evidence_needed": evidence,
        "status": "HYPOTHESIS_PENDING_RESEARCH", "evidence_status": "UNVERIFIED",
        "opportunity_id": opportunity.get("opportunity_id")}
        for topic, q, evidence in candidates if is_material_question(q, topic)]


def validate_director_questions(rows: Any) -> list[dict[str, Any]]:
    """Validate Alpha Research Director output; it cannot assign evidence truth."""
    if not isinstance(rows, list):
        raise ValueError("director_questions_must_be_list")
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        question = str(row.get("question") or "").strip()
        topic = str(row.get("materiality_topic") or "").strip().lower()
        if not question or not is_material_question(question, topic):
            continue
        key = question.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append({"question": question[:500], "materiality_topic": topic,
            "why_material": str(row.get("why_material") or "")[:500],
            "evidence_needed": str(row.get("evidence_needed") or "")[:500],
            "status": "HYPOTHESIS_PENDING_RESEARCH", "evidence_status": "UNVERIFIED"})
    return out[:12]


def normalize_alpha_mode(mode: str) -> str:
    """Keep research direction and post-research evaluation as separate roles."""
    value = str(mode or "").strip().upper()
    if value not in {"RESEARCH_DIRECTOR", "POST_RESEARCH_EVALUATOR"}:
        raise ValueError("unsupported_alpha_mode")
    return value


def checkpoint_research_group(queue: Any, *, work_id: str, notebook_id: str,
                              question_statuses: list[Mapping[str, Any]],
                              findings: list[Mapping[str, Any]],
                              opportunity_id: str | None = None) -> dict[str, Any]:
    """Persist compact progress on the existing queue item; never store QA bodies."""
    item = next((row for row in queue.load().get("items", []) if row.get("work_id") == work_id), None)
    if not item:
        raise KeyError("research_queue_item_not_found")
    followups = []
    for finding in findings:
        followups.extend(adaptive_discovery_candidates(finding=finding,
            opportunity={"opportunity_id": opportunity_id or item.get("opportunity_id")}))
    # Stable IDs preserve question identity across worker restarts and avoid
    # re-adding the same adaptive question after a checkpoint is replayed.
    prior = list(item.get("discovery_questions") or [])
    known = {str(row.get("question_id") or row.get("question", "")).casefold() for row in prior}
    for row in followups:
        row["question_id"] = _stable("discoveryq", {"work_id": work_id, "question": row["question"].casefold()})
        if row["question_id"].casefold() not in known:
            prior.append(row)
            known.add(row["question_id"].casefold())
    compact_statuses = [{"question_id": str(row.get("question_id") or ""),
        "asked": bool(row.get("asked")), "evidence_status": str(row.get("evidence_status") or "UNVERIFIED")}
        for row in question_statuses]
    updated = queue.upsert({**item, "notebook_id": notebook_id,
        "notebook_role": "DEDICATED_RESEARCH", "discovery_questions": prior,
        "research_checkpoint": {"stage": "GROUP_REVIEWED", "notebook_id": notebook_id,
            "question_statuses": compact_statuses, "adaptive_question_count": len(prior),
            "updated_at": _now()}})
    return {"queue_item": updated, "new_adaptive_questions": [row for row in followups
        if row.get("question_id") not in {str(old.get("question_id")) for old in item.get("discovery_questions", [])}]}


def attach_director_plan(queue: Any, *, work_id: str, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Persist Alpha's bounded research direction as hypotheses on same work item."""
    item = next((row for row in queue.load().get("items", []) if row.get("work_id") == work_id), None)
    if not item:
        raise KeyError("research_queue_item_not_found")
    questions = validate_director_questions(plan.get("candidate_questions", []))
    prior = list(item.get("discovery_questions") or [])
    known = {str(row.get("question_id") or "").casefold() for row in prior}
    added = []
    for row in questions:
        row["question_id"] = _stable("discoveryq", {"work_id": work_id, "question": row["question"].casefold()})
        row["opportunity_id"] = item.get("opportunity_id")
        if row["question_id"].casefold() not in known:
            prior.append(row)
            added.append(row)
            known.add(row["question_id"].casefold())
    updated = queue.upsert({**item, "director_mode": "RESEARCH_DIRECTOR",
        "discovery_questions": prior, "research_checkpoint": {**(item.get("research_checkpoint") or {}),
            "stage": "DIRECTOR_PLAN_ATTACHED", "director_plan_status": "HYPOTHESES_ONLY",
            "added_questions": len(added), "updated_at": _now()}})
    return {"queue_item": updated, "added_questions": added,
        "alternatives": list(plan.get("alternatives") or [])[:8],
        "real_world_actions": [dict(row) for row in (plan.get("real_world_actions") or [])[:8]
            if isinstance(row, Mapping)], "evidence_created": False}


def research_director_prompt(*, objective: str, context: Mapping[str, Any],
                             findings: list[Mapping[str, Any]] | None = None,
                             event: str = "OPPORTUNITY_FORMATION") -> str:
    compact = {key: context.get(key) for key in (
        "opportunity_id", "current_recommended_version", "target_customer", "problem", "offer",
        "business_model", "verified_findings", "partial_findings", "unverified_findings",
        "contradicted_findings", "unit_economics", "open_questions", "major_risks",
        "outside_advisor_feedback", "fast_validation_model", "affiliate_options", "merch_option",
        "content_option", "alpha_direction", "verified_nexus_capabilities",
        "incoming_source", "candidate_existing_opportunities", "source_claims",
        "alpha_initial_direction", "opportunity_relationship")}
    package = {"objective": objective, "event": event, "opportunity_context": compact,
        "new_findings": list(findings or [])[:8]}
    return ("You are Alpha in ALPHA_MODE=RESEARCH_DIRECTOR. Plan what Research must learn next. "
        "Do not invent evidence, mark hypotheses verified, decide whether the opportunity should launch, "
        "write a business plan, or replace Research/Needle. Keep uncertainty explicit. Return JSON with "
        "intake_classification {source_role,relationship,promotion_decision,matched_opportunity_id,why}; "
        "promotion_decision is one of PROMOTE_NEW, PROMOTE_EXISTING, PROMOTE_RELATED, INTAKE_ONLY, ARCHIVE. "
        "Never select a matched opportunity ID unless it appears in candidate_existing_opportunities. "
        "candidate_questions rows {question,materiality_topic,why_material,evidence_needed}; "
        "alternatives {product,market,delivery_model,monetization,cheaper_entry_path}; "
        "real_world_actions rows {action_type,target,questions_to_resolve,why_material,approval_required}; "
        "fast_validation {fastest_launchable_version,estimated_days_to_launch,estimated_incremental_cash,"
        "assets_nexus_can_create,channels_nexus_can_use,first_revenue_path,validation_window,success_signal,pivot_signal,"
        "what_not_to_build_until_validated}; affiliate_option; merch_option; content_option; nexus_internal_execution; "
        "human_only_requirements; next_research_action. Only questions whose answers could change viability, customer, problem, offer, "
        "product, market, pricing, costs, economics, sourcing, delivery, monetization, acquisition, risk, "
        "or downstream action qualify. Treat all suggestions as UNVERIFIED hypotheses.\n"
        "INPUT=" + json.dumps(package, ensure_ascii=False, separators=(",", ":"))[:10000])


def execute_research_director(*, objective: str, context: Mapping[str, Any],
                              findings: list[Mapping[str, Any]] | None = None,
                              event: str = "OPPORTUNITY_FORMATION", operation: Callable | None = None) -> dict[str, Any]:
    """Run Alpha's director judgment through the canonical model router."""
    from model_router import execute_reasoning
    prompt = research_director_prompt(objective=objective, context=context, findings=findings, event=event)
    if operation is None:
        import urllib.request
        def operation(payload: dict[str, Any], token: str) -> dict[str, Any]:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {token}",
                "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
    result = execute_reasoning(agent_key="alpha", task_type="business_opportunity_research_director",
        sensitivity="public_research", reasoning_class="STRONG_REASONING",
        payload={"messages": [{"role": "user", "content": prompt}], "max_tokens": 1200,
                 "temperature": 0.1}, operation=operation, max_tokens=1200,
        purpose=f"ALPHA_MODE_RESEARCH_DIRECTOR:{event}")
    body = ((result.get("result") or {}).get("choices") or [{}])[0].get("message", {}).get("content", "")
    try:
        parsed = json.loads(body)
    except (ValueError, TypeError):
        return {"status": "DIRECTOR_OUTPUT_INVALID", "model_execution": result,
                "hypotheses_only": True, "error": "invalid_json"}
    parsed = parsed if isinstance(parsed, dict) else {}
    parsed["candidate_questions"] = validate_director_questions(parsed.get("candidate_questions", []))
    intake = parsed.get("intake_classification") if isinstance(parsed.get("intake_classification"),dict) else {}
    valid_roles = SOURCE_ROLES
    valid_relations = RELATIONSHIPS
    valid_decisions = {"PROMOTE_NEW","PROMOTE_EXISTING","PROMOTE_RELATED","INTAKE_ONLY","ARCHIVE"}
    candidate_ids = {str(row.get("opportunity_id")) for row in context.get("candidate_existing_opportunities",[])
        if isinstance(row,Mapping) and row.get("opportunity_id")}
    intake = dict(intake)
    intake["source_role"] = str(intake.get("source_role") or "OTHER").upper()
    intake["relationship"] = str(intake.get("relationship") or "RELATED_BUT_UNCLASSIFIED").upper()
    intake["promotion_decision"] = str(intake.get("promotion_decision") or "INTAKE_ONLY").upper()
    if intake["source_role"] not in valid_roles: intake["source_role"] = "OTHER"
    if intake["relationship"] not in valid_relations: intake["relationship"] = "RELATED_BUT_UNCLASSIFIED"
    if intake["promotion_decision"] not in valid_decisions: intake["promotion_decision"] = "INTAKE_ONLY"
    matched = str(intake.get("matched_opportunity_id") or "")
    if matched not in candidate_ids:
        intake["matched_opportunity_id"] = None
        if intake["promotion_decision"] == "PROMOTE_EXISTING": intake["promotion_decision"] = "PROMOTE_RELATED"
    parsed["intake_classification"] = {**intake,"hypotheses_only":True,"evidence_created":False}
    parsed["hypotheses_only"] = True
    parsed["alpha_mode"] = "RESEARCH_DIRECTOR"
    parsed["model_execution"] = {key: result.get(key) for key in ("provider", "model", "cost_class", "route_key", "latency_ms", "execution_metadata")}
    return {"status": "PLANNED", **parsed}


def execute_outside_advisor(*, objective: str, context: Mapping[str, Any],
                            operation: Callable | None = None) -> dict[str, Any]:
    """Bounded provider-independent critique; output is advice, never evidence."""
    from model_router import execute_reasoning
    if operation is None:
        import urllib.request
        def operation(payload: dict[str, Any], token: str) -> dict[str, Any]:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {token}",
                "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode())
    result = execute_reasoning(agent_key="alpha", task_type="business_opportunity_outside_advisor",
        sensitivity="public_research", reasoning_class="LIGHT_REASONING",
        payload={"messages": [{"role": "user", "content": build_outside_advisor_prompt(
            objective=objective, context=context)}], "max_tokens": 700, "temperature": 0.2},
        operation=operation, max_tokens=700, timeout_seconds=35,
        purpose="BOUNDED_EXTERNAL_RESEARCH_ADVISOR_HYPOTHESES_ONLY")
    body = ((result.get("result") or {}).get("choices") or [{}])[0].get("message", {}).get("content", "")
    try:
        advice = json.loads(body)
    except (ValueError, TypeError):
        advice = {"unparsed_advice": str(body)[:3000]}
    return {"status": "ADVICE_ONLY", "hypotheses_only": True, "evidence_created": False,
        "advice": advice, "model_execution": {key: result.get(key) for key in
            ("provider", "model", "cost_class", "route_key", "latency_ms", "execution_metadata")}}


def build_outside_advisor_prompt(*, objective: str, context: Mapping[str, Any]) -> str:
    keys = ("current_recommended_version", "verified_findings", "partial_findings", "unverified_findings",
            "contradicted_findings", "unit_economics", "open_questions", "major_risks")
    compact = {key: context.get(key) for key in keys}
    return ("Independent outside research advisor. Treat every suggestion as unverified advice, not evidence. "
        "Identify one missed material question, a weak assumption, better product/market/delivery/monetization, "
        "cheaper validation, contradictory possibility, and a real-world action to resolve an unknown. "
        "Do not recommend launch as a fact. Return compact JSON.\nOBJECTIVE=" + objective[:1000] +
        "\nCONTEXT=" + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))[:5000])


def create_research_action(*, action_type: str, target: str, questions_to_resolve: list[str],
                          why_material: str, owner: str = "RAY", approval_required: bool = True) -> dict[str, Any]:
    allowed = {"SUPPLIER_EMAIL", "VENDOR_INQUIRY", "AFFILIATE_TERMS_REQUEST", "QUOTE_REQUEST",
        "DROPSHIP_TERMS_REQUEST", "DELIVERY_SLA_REQUEST", "PARTNERSHIP_INQUIRY"}
    kind = action_type.strip().upper()
    if kind not in allowed:
        raise ValueError("unsupported_research_action")
    return {"action_id": _stable("research_action", {"type": kind, "target": target,
        "questions": questions_to_resolve}), "action_type": kind, "target": target[:500],
        "questions_to_resolve": [str(q)[:500] for q in questions_to_resolve[:12]],
        "why_material": why_material[:1000], "owner": owner, "approval_required": bool(approval_required),
        "status": "RAY_ACTION_REQUIRED" if approval_required else "PREPARED_GOVERNED_ACTION", "created_at": _now()}


def calculate_opportunity_economics(*, price: float, variable_cost: float, monthly_fixed_cost: float,
                                    target_operating_profits: tuple[int, ...] = (1000, 5000, 10000),
                                    monthly_quantity: float | None = None) -> dict[str, Any]:
    """Deterministic arithmetic; inputs and calculated outputs stay labeled."""
    price, variable_cost, fixed = float(price), float(variable_cost), float(monthly_fixed_cost)
    contribution = price - variable_cost
    if price < 0 or variable_cost < 0 or fixed < 0:
        raise ValueError("economic_inputs_must_be_nonnegative")
    if contribution <= 0:
        break_even = None
        targets = {str(target): None for target in target_operating_profits}
    else:
        import math
        break_even = math.ceil(fixed / contribution)
        targets = {str(target): math.ceil((fixed + int(target)) / contribution)
                   for target in target_operating_profits}
    modeled_profit = (monthly_quantity * contribution - fixed) if monthly_quantity is not None else None
    return {"inputs": {"price": {"value": price, "classification": "RESEARCHED_INPUT_OR_MODELED_ASSUMPTION"},
        "variable_cost": {"value": variable_cost, "classification": "RESEARCHED_INPUT_OR_MODELED_ASSUMPTION"},
        "monthly_fixed_cost": {"value": fixed, "classification": "RESEARCHED_INPUT_OR_MODELED_ASSUMPTION"}},
        "contribution_per_sale": {"value": contribution, "classification": "CALCULATED_OUTPUT"},
        "contribution_margin": {"value": contribution / price if price else None, "classification": "CALCULATED_OUTPUT"},
        "break_even_units": {"value": break_even, "classification": "CALCULATED_OUTPUT"},
        "units_for_target_operating_profit": {"values": targets, "classification": "CALCULATED_OUTPUT"},
        "modeled_monthly_operating_profit": {"value": modeled_profit, "classification": "CALCULATED_OUTPUT"},
        "profit_guaranteed": False}


def normalize_trend_signal(data: Mapping[str, Any]) -> dict[str, Any]:
    signal_class = str(data.get("signal_class") or "").upper()
    if signal_class not in TREND_SIGNAL_CLASSES:
        raise ValueError("unsupported_trend_signal_class")
    relative = data.get("relative_growth")
    absolute = data.get("absolute_volume")
    return {"signal_id": str(data.get("signal_id") or _stable("trend", data)),
        "signal_class": signal_class, "topic": str(data.get("topic") or "").strip(),
        "source": data.get("source"), "period": data.get("period"), "geography": data.get("geography"),
        "relative_growth": relative, "relative_metric_label": data.get("relative_metric_label") or ("RELATIVE_INDEX" if relative is not None else None),
        "absolute_volume": absolute, "absolute_volume_source": data.get("absolute_volume_source") if absolute is not None else None,
        "breakout_status": data.get("breakout_status"), "related_queries": list(data.get("related_queries") or []),
        "related_topics": list(data.get("related_topics") or []), "commercial_intent": data.get("commercial_intent", "UNKNOWN"),
        "signal_confidence": data.get("signal_confidence", "PRELIMINARY"), "cause": "UNASSESSED",
        "monetization_paths": [x for x in data.get("monetization_paths", []) if x in MONETIZATION_PATHS],
        "evidence_class": "TREND_SIGNAL_NOT_ABSOLUTE_SEARCH_VOLUME" if absolute is None else "SOURCE_REPORTED_ABSOLUTE_VOLUME",
        "status": "SIGNAL_RECORDED"}


def trend_disposition(*, commercial_intent: str, cause: str, existing_match: Mapping[str, Any],
                      evidence_confidence: str) -> str:
    if str(commercial_intent).upper() in {"NONE", "ENTERTAINMENT_ONLY"} and str(cause).upper() in {"TEMPORARY_NEWS", "CELEBRITY_SPIKE", "ENTERTAINMENT"}:
        return "TREND_NOT_COMMERCIAL_ARCHIVE"
    if existing_match.get("relationship") == "MATCH_EXISTING_OPPORTUNITY":
        return "TREND_SUPPORTS_EXISTING_OPPORTUNITY"
    if str(commercial_intent).upper() in {"PRESENT", "STRONG"} and str(evidence_confidence).upper() in {"MEDIUM", "HIGH", "VERIFIED"}:
        return "NEW_BUSINESS_OPPORTUNITY_CANDIDATE"
    return "BOUNDED_CAUSE_AND_COMMERCIAL_RESEARCH_REQUIRED"


def route_trend_signal(*, signal_class: str, commercial_intent: str,
                       cause: str, existing_match: Mapping[str, Any],
                       evidence_confidence: str, format_signal: bool = False) -> str:
    """Route a trend to opportunity research or pattern libraries without overclaiming."""
    if format_signal and str(signal_class).upper() in {"TIKTOK_FORMAT_TREND", "YOUTUBE_VIDEO_TREND", "YOUTUBE_TOPIC_TREND"}:
        if str(commercial_intent).upper() in {"NONE", "ENTERTAINMENT_ONLY"}:
            return "CREATIVE_PATTERN"
        return "MARKETING_PATTERN"
    return trend_disposition(commercial_intent=commercial_intent,cause=cause,
        existing_match=existing_match,evidence_confidence=evidence_confidence)


def vendor_reputation_questions(vendor: str) -> list[dict[str, Any]]:
    """Mandatory independent reputation branch for vendor-led investigations."""
    questions = [
        ("What independent user reviews and complaints refer to this exact vendor/product entity?", "ENTITY_RESOLUTION"),
        ("Which repeated complaint patterns are corroborated across independent communities or review sources?", "REPUTATION_PATTERN"),
        ("What do the official refund, cancellation, privacy, and service terms state?", "OFFICIAL_TERMS"),
        ("Who operates this vendor, and what independently verifiable history is available?", "OPERATOR_IDENTITY"),
        ("Are any complaints about similarly named but different products and therefore an entity mismatch?", "ENTITY_MISMATCH"),
    ]
    return [{"question":f"For {vendor}: {question}","materiality_topic":"risk",
        "why_material":"Vendor reputation, operator identity, and exit terms affect the decision to rely on this provider.",
        "evidence_needed":"Match product/vendor identity and compare official terms with independent dated sources.",
        "branch":"INDEPENDENT_REPUTATION_RESEARCH","subtopic":subtopic,
        "status":"HYPOTHESIS_PENDING_RESEARCH","evidence_status":"UNVERIFIED"}
        for question,subtopic in questions]


def queue_top3_objective(queue: Any, *, objective: str, objective_id: str) -> dict[str, Any]:
    """Seed one existing-queue mission; candidate work/notebooks are children later."""
    rows = queue.load().get("items", [])
    prior = next((row for row in rows if row.get("objective_id") == objective_id and row.get("entry_type") == "OBJECTIVE_LED"), None)
    if prior:
        return {"status": "REUSED", "work_id": prior["work_id"], "objective_id": objective_id}
    work_id = _stable("business_opportunity_objective", objective_id)
    record = queue.enqueue(work_id=work_id, work_class="ASSIGNED", priority=1,
        request_type="BUSINESS_OPPORTUNITY_MISSION", entry_type="OBJECTIVE_LED",
        objective_id=objective_id, objective=objective, question=objective,
        source_type="RESEARCH_OBJECTIVE", source_name="Top 3 online business opportunity mission",
        source_url=None, requested_by="NEXUS_ALPHA_RESEARCH_DIRECTOR", director_mode="RESEARCH_DIRECTOR",
        notebook_role="NO_NOTEBOOK_UNTIL_FINALIST_PROMOTION", promotion_status="DISCOVERY_PENDING",
        status="QUEUED", lifecycle="ONE_TIME", max_attempts=3)
    return {"status": "QUEUED", "work_id": record["work_id"], "objective_id": objective_id}


def build_opportunity_package(context: Mapping[str, Any], *, max_bytes: int) -> dict[str, Any]:
    """Compact final local/handoff object; prune redundant prose before refusing."""
    fields = ("opportunity_id", "objective", "entry_type", "original_idea", "current_recommended_version",
        "target_customer", "problem", "offer", "business_model", "demand_summary", "startup_requirements",
        "fastest_validation_model", "fastest_launchable_version", "estimated_days_to_launch",
        "estimated_incremental_cash", "external_cash_cost", "nexus_internal_execution",
        "human_only_requirements", "time_to_mvp", "time_to_first_launch", "first_revenue_path",
        "success_signal", "pivot_signal", "what_not_to_build_until_validated",
        "lean_startup_cost", "standard_startup_cost", "accelerated_startup_cost", "monthly_fixed_cost",
        "price_model", "variable_cost_model", "contribution_model", "break_even", "target_profit_scenarios",
        "customer_acquisition", "supplier_fulfillment_summary", "affiliate_options", "merch_option",
        "content_option", "referral_options", "reseller_options",
        "white_label_options", "cheaper_entry_path", "better_market_or_model_alternatives",
        "verified_findings", "partial_findings", "unverified_findings", "contradicted_findings",
        "major_risks", "major_assumptions", "outside_advisor_material_findings", "needle_status",
        "action_items", "next_department", "notebook_reference", "source_references", "receipt_id")
    package = {key: context.get(key) for key in fields if key in context}
    def serialize_size() -> int:
        return len(json.dumps(package, ensure_ascii=False, separators=(",", ":"), default=str).encode())
    cap = max(0, int(max_bytes))
    if serialize_size() > cap:
        # First remove optional advisory prose, retaining source-backed results.
        for optional in ("outside_advisor_material_findings", "better_market_or_model_alternatives",
                         "supplier_fulfillment_summary"):
            package.pop(optional, None)
            if serialize_size() <= cap:
                break
    if serialize_size() > cap:
        for key, value in list(package.items()):
            if isinstance(value, str) and len(value) > 1200:
                package[key] = value[:1197] + "..."
            elif isinstance(value, list):
                package[key] = [str(item)[:800] if isinstance(item, str) else item for item in value[:20]]
            if serialize_size() <= cap:
                break
    package["final_handoff_bytes"] = 0
    package["final_handoff_bytes"] = serialize_size()
    package["final_handoff_bytes"] = serialize_size()
    encoded_size = serialize_size()
    if encoded_size > cap:
        raise ValueError(f"OPPORTUNITY_HANDOFF_TOO_LARGE:{encoded_size}>{max_bytes}")
    return package

