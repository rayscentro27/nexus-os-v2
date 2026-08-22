"""Evidence-backed, draft-only SEO and Growth Operations.

This is an adapter around the existing SEO scout, Alpha, Opportunity Engine,
and Revenue Truth Hub. It owns growth planning and measurement semantics; it
does not publish, send, spend, or create a second scheduler.
"""
from __future__ import annotations

import hashlib
import html.parser
import re
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from nexus_agent_platform.governed import persistence

GROWTH_EXPERIMENT_SCHEMA = "nexus.growth-experiment.v1"
GROWTH_STATUSES = ("CANDIDATE", "RESEARCHING", "NEEDS_RESEARCH", "READY_FOR_REVIEW", "NEEDS_RAY_REVIEW", "APPROVED_FOR_PLANNING", "DRAFTING", "READY_TO_IMPLEMENT", "MEASUREMENT_PENDING", "MEASURING", "RESULT_OBSERVED", "INCONCLUSIVE", "PARKED", "REJECTED", "STALE", "CLOSED")
GROWTH_TYPES = ("SEO_CONTENT", "SEO_TECHNICAL", "LANDING_PAGE", "CONTENT_REFRESH", "CONTENT_CLUSTER", "LEAD_MAGNET", "LOCAL_SEARCH", "COMPETITOR_RESPONSE", "AFFILIATE_CONTENT", "FUNNEL_OPTIMIZATION", "CONVERSION_OPTIMIZATION", "EMAIL_DRAFT", "SOCIAL_DRAFT", "VIDEO_BRIEF")
INTENTS = ("INFORMATIONAL", "COMMERCIAL_INVESTIGATION", "TRANSACTIONAL", "NAVIGATIONAL", "LOCAL", "UNKNOWN")
_TRANSITIONS = {"CANDIDATE": {"RESEARCHING", "READY_FOR_REVIEW", "NEEDS_RESEARCH", "PARKED", "STALE"}, "RESEARCHING": {"READY_FOR_REVIEW", "NEEDS_RESEARCH", "PARKED", "STALE"}, "NEEDS_RESEARCH": {"RESEARCHING", "READY_FOR_REVIEW", "PARKED", "STALE"}, "READY_FOR_REVIEW": {"NEEDS_RAY_REVIEW", "APPROVED_FOR_PLANNING", "DRAFTING", "PARKED", "STALE"}, "NEEDS_RAY_REVIEW": {"APPROVED_FOR_PLANNING", "PARKED", "REJECTED", "STALE"}, "APPROVED_FOR_PLANNING": {"DRAFTING", "READY_TO_IMPLEMENT", "PARKED", "STALE"}, "DRAFTING": {"READY_TO_IMPLEMENT", "MEASUREMENT_PENDING", "PARKED"}, "READY_TO_IMPLEMENT": {"MEASUREMENT_PENDING", "PARKED"}, "MEASUREMENT_PENDING": {"MEASURING", "INCONCLUSIVE", "STALE", "PARKED"}, "MEASURING": {"RESULT_OBSERVED", "INCONCLUSIVE", "STALE", "PARKED"}, "RESULT_OBSERVED": {"CLOSED", "INCONCLUSIVE"}, "INCONCLUSIVE": {"MEASURING", "PARKED", "CLOSED"}, "PARKED": {"CANDIDATE", "RESEARCHING", "CLOSED"}, "REJECTED": {"CANDIDATE", "CLOSED"}, "STALE": {"RESEARCHING", "CANDIDATE", "CLOSED"}, "CLOSED": set()}

def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _norm(value: Any) -> str: return re.sub(r"\s+", " ", str(value or "").strip().lower())
def _hash(value: Any) -> str: return hashlib.sha256(_norm(value).encode()).hexdigest()

def _freshness(observed_at: Any, *, max_age_days: int = 90) -> str:
    if not observed_at: return "UNKNOWN"
    try: age = (datetime.now(timezone.utc) - datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))).total_seconds()
    except (TypeError, ValueError): return "UNKNOWN"
    return "STALE" if age > max_age_days * 86400 else ("CURRENT" if age >= -300 else "TRANSIENT")

def _latest() -> List[Dict[str, Any]]:
    seen, rows = set(), []
    for row in persistence.read_records("growth_experiments"):
        if row.get("growth_id") in seen: continue
        seen.add(row.get("growth_id")); rows.append(row)
    return rows

def build_growth_experiment(*, title: str, growth_type: str = "SEO_CONTENT", business_id: str = "goclear", topic: str = "", intent: str = "UNKNOWN", hypothesis: str = "", target_audience: str = "", target_offer: str = "", primary_metric: str = "", evidence_refs: Optional[List[str]] = None, source_opportunity_id: Optional[str] = None, source_research_job_id: Optional[str] = None, source_research_pack_ref: Optional[str] = None, baseline: Optional[Dict[str, Any]] = None, planned_asset_types: Optional[List[str]] = None, risks: Optional[List[str]] = None, dependencies: Optional[List[str]] = None, observed_at: Optional[str] = None) -> Dict[str, Any]:
    created = _now()
    evidence = list(evidence_refs or [])
    fingerprint = _hash({"title": title, "growth_type": growth_type, "topic": topic, "offer": target_offer, "opportunity": source_opportunity_id})
    baseline_value = baseline or {"source": "phase_l_revenue_truth", "metric": primary_metric, "value": None, "truth_class": "UNKNOWN", "observed_at": None}
    return {"schema_version": GROWTH_EXPERIMENT_SCHEMA, "growth_id": persistence.new_id("growth"), "fingerprint": fingerprint, "business_id": business_id, "title": title, "growth_type": growth_type, "topic": topic, "search_intent": intent, "hypothesis": hypothesis, "target_audience": target_audience, "target_offer": target_offer, "source_opportunity_id": source_opportunity_id, "source_research_job_id": source_research_job_id, "source_research_pack_ref": source_research_pack_ref, "evidence_refs": evidence, "planned_asset_types": list(planned_asset_types or []), "baseline": baseline_value, "primary_metric": primary_metric, "secondary_metrics": [], "measurement_window": "30_days", "expected_direction": "IMPROVE_OR_OBSERVE", "status": "READY_FOR_REVIEW" if evidence else "NEEDS_RESEARCH", "risks": list(risks or []), "dependencies": list(dependencies or []), "approval_required": True, "approval_id": None, "work_order_ids": [], "freshness": {"observed_at": observed_at, "status": _freshness(observed_at)}, "external_action_performed": False, "created_at": created, "updated_at": created}

def validate_growth_experiment(row: Dict[str, Any]) -> Dict[str, Any]:
    required = ("schema_version", "growth_id", "title", "growth_type", "primary_metric", "evidence_refs", "status")
    missing = [key for key in required if key not in row]
    if missing: return {"valid": False, "reason": "missing: " + ", ".join(missing)}
    if row.get("schema_version") != GROWTH_EXPERIMENT_SCHEMA: return {"valid": False, "reason": "schema_version"}
    if row.get("growth_type") not in GROWTH_TYPES: return {"valid": False, "reason": "growth_type"}
    if row.get("search_intent", "UNKNOWN") not in INTENTS: return {"valid": False, "reason": "search_intent"}
    if row.get("status") not in GROWTH_STATUSES: return {"valid": False, "reason": "status"}
    return {"valid": True, "reason": ""}

def persist_growth_experiment(row: Dict[str, Any]) -> Dict[str, Any]:
    check = validate_growth_experiment(row)
    if not check["valid"]: raise ValueError("invalid growth experiment: " + check["reason"])
    for existing in _latest():
        if existing.get("fingerprint") == row.get("fingerprint"):
            persistence.emit_audit_event({"type": "growth_experiment_duplicate_suppressed", "growth_id": existing.get("growth_id"), "external_action_performed": False})
            return {"status": "DUPLICATE_SUPPRESSED", "experiment": existing}
    persistence.append_record("growth_experiments", row)
    persistence.emit_audit_event({"type": "growth_experiment_created", "growth_id": row["growth_id"], "evidence_refs": row.get("evidence_refs", []), "primary_metric": row.get("primary_metric"), "external_action_performed": False})
    return {"status": "CREATED", "experiment": row}

def list_growth_experiments() -> List[Dict[str, Any]]: return _latest()
def get_growth_experiment(growth_id: str) -> Optional[Dict[str, Any]]: return next((r for r in _latest() if r.get("growth_id") == growth_id), None)

def transition_growth(growth_id: str, status: str) -> Dict[str, Any]:
    row = get_growth_experiment(growth_id)
    if not row: raise ValueError("growth experiment not found")
    status = status.upper()
    if status not in _TRANSITIONS.get(row.get("status"), set()): raise ValueError(f"invalid growth transition: {row.get('status')} -> {status}")
    updated = {**row, "status": status, "updated_at": _now()}
    persistence.append_record("growth_experiments", updated)
    persistence.emit_audit_event({"type": "growth_experiment_status_changed", "growth_id": growth_id, "previous_status": row.get("status"), "new_status": status, "external_action_performed": False})
    return updated

def request_growth_review(growth_id: str, *, opportunity_id: Optional[str] = None) -> Dict[str, Any]:
    """Create the existing governed review request; never approve or publish."""
    row = get_growth_experiment(growth_id)
    if not row: raise ValueError("growth experiment not found")
    if row.get("status") == "READY_FOR_REVIEW": row = transition_growth(growth_id, "NEEDS_RAY_REVIEW")
    approval = None
    if opportunity_id:
        from nexus_agent_platform.opportunities.engine import create_opportunity_review_request
        result = create_opportunity_review_request(opportunity_id)
        approval = result.get("approval")
    return {"growth": row, "approval": approval, "approval_required": True, "external_action_performed": False}

def keyword_record(row: Dict[str, Any], *, source_type: str = "MANUAL_REVIEWED") -> Dict[str, Any]:
    result = dict(row)
    result.update({"source_type": source_type, "truth_class": source_type, "search_volume": None, "ranking": None, "traffic": None, "cpc_status": "IMPORTED_ESTIMATE" if row.get("cpc_estimate") else "UNKNOWN", "freshness": "UNKNOWN"})
    return result

def build_content_gap(*, topic: str, intent: str, existing_coverage: str, competitor_coverage: str, evidence_refs: Optional[List[str]] = None, target_offer: str = "") -> Dict[str, Any]:
    evidence = list(evidence_refs or [])
    if not existing_coverage and competitor_coverage: recommendation = "NEW_PAGE"
    elif existing_coverage and competitor_coverage: recommendation = "REFRESH_EXISTING"
    elif competitor_coverage: recommendation = "SUPPORTING_CONTENT"
    else: recommendation = "NEEDS_RESEARCH"
    return {"topic": topic, "intent": intent if intent in INTENTS else "UNKNOWN", "existing_goclear_coverage": existing_coverage or "UNKNOWN", "competitor_coverage": competitor_coverage or "UNKNOWN", "business_relevance": "EVIDENCE_BACKED" if evidence else "UNKNOWN", "offer_relevance": target_offer or "UNKNOWN", "evidence_refs": evidence, "evidence_strength": "HIGH" if len(evidence) >= 2 else ("MEDIUM" if evidence else "LOW"), "recommended_action": recommendation, "freshness": "CURRENT" if evidence else "UNKNOWN"}

def build_content_brief(*, gap: Dict[str, Any], evidence_refs: Optional[List[str]] = None) -> Dict[str, Any]:
    refs = list(evidence_refs or gap.get("evidence_refs", []))
    return {"status": "DRAFT_ONLY", "title_ideas": [f"{gap.get('topic', 'Funding readiness')}: what to know before applying"], "search_intent": gap.get("intent", "UNKNOWN"), "reader_problem": f"Understand {gap.get('topic', 'the topic')} without unsupported promises.", "outline": ["Problem and audience", "Evidence-backed explanation", "Checklist or next steps", "Offer-aligned CTA"], "key_questions": [f"What does the evidence show about {gap.get('topic', 'this topic')}?", "What remains unknown?"], "evidence_refs": refs, "claims_requiring_evidence": [] if refs else ["NEEDS_SOURCE"], "cta": {"primary": gap.get("offer_relevance") or "readiness checklist", "secondary": "$97 readiness review"}, "internal_links": ["pillar -> supporting topic -> offer page"], "conversion_goal": "readiness_review_leads", "compliance_notes": ["No guaranteed approval, funding, score increase, ranking, or income claims.", "Ray approval required before publication."], "external_action_performed": False}

class _AuditParser(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.title = ""; self.headings = []; self.meta = {}; self.canonical = None; self._title = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title": self._title = True
        if tag in {"h1", "h2", "h3"}: self.headings.append(tag)
        if tag == "meta" and attrs.get("name"): self.meta[attrs["name"].lower()] = attrs.get("content", "")
        if tag == "link" and attrs.get("rel") == "canonical": self.canonical = attrs.get("href")
    def handle_data(self, data):
        if self._title: self.title += data.strip()
    def handle_endtag(self, tag):
        if tag == "title": self._title = False

def build_public_technical_audit(url: str, *, timeout: int = 8) -> Dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1"} or any(x in parsed.path.lower() for x in ("/admin", "/client", "/dashboard", "/login")): raise ValueError("public URL required")
    request = Request(url, headers={"User-Agent": "Nexus-Growth-Audit/1.0"})
    try:
        context = None
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except (ImportError, OSError):
            context = ssl.create_default_context()
        with urlopen(request, timeout=timeout, context=context) as response: body = response.read(500_000); status = response.status; final_url = response.geturl()
    except Exception as exc: return {"url": url, "status": "DEPENDENCY_UNAVAILABLE", "error_class": type(exc).__name__, "observed_at": _now(), "lighthouse": "NOT_AVAILABLE", "external_action_performed": False}
    parser = _AuditParser(); parser.feed(body.decode("utf-8", errors="replace"))
    return {"url": url, "final_url": final_url, "status_code": status, "title": parser.title, "meta_description": parser.meta.get("description"), "canonical": parser.canonical, "robots": parser.meta.get("robots", "UNKNOWN"), "heading_counts": {key: parser.headings.count(key) for key in ("h1", "h2", "h3")}, "structured_data": "UNKNOWN", "response_bytes": len(body), "observed_at": _now(), "lighthouse": "NOT_AVAILABLE", "external_action_performed": False}

def measurement_state(*, metric: str, snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metrics = (snapshot or {}).get("metrics", {})
    observed = metrics.get(metric, {}) if isinstance(metrics, dict) else {}
    if not observed or observed.get("value") is None: return {"status": "MEASUREMENT_PENDING", "truth_class": "UNKNOWN", "metric": metric, "value": None, "source_status": "NOT_CONNECTED"}
    return {"status": "MEASURING", "truth_class": observed.get("truth_class", "UNKNOWN"), "metric": metric, "value": observed.get("value"), "source_status": observed.get("source_status", "UNKNOWN")}

def growth_portfolio() -> Dict[str, Any]:
    rows = list_growth_experiments(); counts = {status: sum(1 for row in rows if row.get("status") == status) for status in GROWTH_STATUSES}
    measurement_pending = counts.get("MEASUREMENT_PENDING", 0) + sum(1 for row in rows if (row.get("baseline") or {}).get("truth_class") == "UNKNOWN" and row.get("status") not in {"CLOSED", "REJECTED"})
    return {"status": "HEALTHY" if rows else "IDLE", "total": len(rows), "counts": {**counts, "MEASUREMENT_PENDING": measurement_pending}, "top_growth_opportunity": max(rows, key=lambda r: (bool(r.get("evidence_refs")), r.get("freshness", {}).get("status") == "CURRENT"), default=None), "measurement_source": "NOT_CONNECTED", "search_console": "NOT_CONNECTED", "analytics": "NOT_CONNECTED", "core_health_dependency": False}

def growth_priority_view() -> List[Dict[str, Any]]:
    result = []
    for row in list_growth_experiments():
        result.append({"growth_id": row.get("growth_id"), "title": row.get("title"), "priority": "P2" if row.get("evidence_refs") else "P4", "why": "Evidence-backed growth candidate" if row.get("evidence_refs") else "Measurement or evidence gap", "source": row.get("source_research_pack_ref") or "keyword scout", "truth_class": "EVIDENCE_BACKED" if row.get("evidence_refs") else "UNKNOWN", "next_governed_action": "Ray review or prepare internal draft", "external_action_performed": False})
    return result

def answer_growth_question(question: str) -> Dict[str, Any]:
    text = _norm(question); portfolio = growth_portfolio(); rows = list_growth_experiments()
    if "approval" in text or "ray" in text: rows = [r for r in rows if r.get("status") == "NEEDS_RAY_REVIEW"]
    elif "measur" in text or "traffic" in text or "worked" in text: return {"type": "measurement", "status": "MEASUREMENT_PENDING", "source": "Phase L Revenue Truth; Search Console/Analytics NOT_CONNECTED", "experiments": rows}
    elif "why" in text or "evidence" in text: return {"type": "evidence", "experiments": rows, "source": "growth_experiments and canonical evidence refs"}
    return {"type": "growth_opportunities", "experiments": rows[:5], "portfolio": portfolio, "source": "canonical growth_experiments"}
