"""Semantic demand preparation and governed Alpha routing contracts.

Last30Days remains acquisition-only.  This module filters and groups its raw
signals, then uses the existing Alpha/model and governed persistence layers for
judgment and downstream correlation.  It intentionally performs no external
mutation.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from nexus_agent_platform.governed import persistence

SOURCE_ROLES = {
    "CUSTOMER_DEMAND": {
        "primary": {"REDDIT", "YOUTUBE", "FORUM", "REVIEW"},
        "secondary": {"WEB", "HACKERNEWS"},
        "low_weight": {"GITHUB"},
    },
    "CAPABILITY_DISCOVERY": {"primary": {"GITHUB", "HACKERNEWS"}, "secondary": {"WEB"}, "low_weight": set()},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_type(signal: dict[str, Any]) -> str:
    value = str(signal.get("source_type") or signal.get("provider") or "WEB").upper()
    return value.replace("_METADATA", "")


def expand_customer_problem_queries(*, audience: str, problem: str, max_variants: int = 8) -> list[str]:
    """Generate bounded, reusable problem-language variants from an input need."""
    base = f"{audience} {problem}".strip()
    terms = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'-]+", problem.lower())
    focus = " ".join(dict.fromkeys(terms[:8]))
    templates = (
        f"{audience} denied {focus}", f"{audience} no revenue {focus}",
        f"{audience} credit requirements {focus}", f"{audience} documentation for {focus}",
        f"{audience} qualification uncertainty {focus}", f"{audience} startup {focus}",
        f"what do I need for {focus}", f"can't get {focus}",
    )
    return list(dict.fromkeys([base, *templates]))[:max(1, max_variants)]


def source_role(source_type: str, intent: str = "CUSTOMER_DEMAND") -> dict[str, Any]:
    role = SOURCE_ROLES.get(intent, SOURCE_ROLES["CUSTOMER_DEMAND"])
    source = str(source_type or "WEB").upper()
    return {"source_type": source, "role": "PRIMARY" if source in role["primary"] else "SECONDARY" if source in role["secondary"] else "LOW_WEIGHT" if source in role["low_weight"] else "UNCLASSIFIED", "weight": 1.0 if source in role["primary"] else 0.65 if source in role["secondary"] else 0.25 if source in role["low_weight"] else 0.5}


def filter_customer_signals(signals: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted, rejected = [], []
    for signal in signals:
        text = json.dumps(signal, ensure_ascii=False).lower()
        source = _source_type(signal)
        reason = None
        if source == "GITHUB" and any(token in text for token in ("repository", "pull request", "source code", "npm package")):
            reason = "capability_or_software_artifact_not_customer_pain"
        elif any(token in text for token in ("academic paper", "arxiv", "investor presentation", "press release")):
            reason = "non_customer_context"
        elif len(str(signal.get("excerpt") or signal.get("summary") or "").strip()) < 20:
            reason = "insufficient_customer_language"
        if reason:
            rejected.append({"signal_id": signal.get("signal_id"), "reason": reason})
        else:
            accepted.append({**signal, "source_role": source_role(source)})
    return accepted, rejected


def _json_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except (TypeError, ValueError):
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start : end + 1])
                return value if isinstance(value, dict) else None
            except (TypeError, ValueError):
                return None
    return None


def judge_coherence(signals: list[dict[str, Any]], query: str, *, model: str | None = None) -> dict[str, Any]:
    """Use the existing OpenRouter transport for bounded semantic preparation."""
    from alpha.alpha_live_research import http_json, load_runtime_env
    load_runtime_env()
    model = model or os.environ.get("SEMANTIC_JUDGE_MODEL") or "openai/gpt-4o-mini"
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {"status": "BLOCKED", "model": model, "model_calls": 0, "error": "missing_credential"}
    compact = [{"signal_id": row.get("signal_id"), "source_type": _source_type(row), "title": row.get("source_title") or row.get("title"), "text": (row.get("excerpt") or row.get("summary") or "")[:900], "url": row.get("source_url") or row.get("url")} for row in signals[:20]]
    instruction = {"query": query, "signals": compact, "required": ["cluster_id", "audience", "problem", "desired_outcome", "included_signal_ids", "rejected_signal_ids", "rejection_reasons", "repeated_customer_language", "commercial_intent_signals", "coherence", "evidence_gaps"], "rule": "Cluster only if audience, concrete problem, and desired outcome align. Separate demand confidence from factual confidence."}
    payload = {"model": model, "messages": [{"role": "system", "content": "You are a semantic Research evidence-preparation judge. Return one JSON object only. Do not make business decisions or invent customer quotes."}, {"role": "user", "content": json.dumps(instruction, ensure_ascii=False)}], "temperature": 0.1, "max_tokens": 900}
    ok, status, data, error, latency = http_json("POST", "https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://goclearonline.cc", "X-Title": "Nexus Research Semantic Judge"}, payload, timeout=45)
    try:
        text = str(data["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError):
        text = ""
    judgment = _json_object(text)
    if not ok or not judgment:
        return {"status": "FAILED", "model": model, "model_calls": 1 if ok else 0, "http_status": status, "error": error or "invalid_json", "latency_ms": latency}
    return {"status": "COMPLETE", "model": model, "model_calls": 1, "latency_ms": latency, "judgment": judgment}


def route_qualified_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Select a department from explicit evidence class, not incidental keywords."""
    kind = str(finding.get("finding_type") or finding.get("category") or "").upper()
    domain = str(finding.get("business_domain") or "").upper()
    if kind in {"FUNDING", "CUSTOMER_FUNDING", "CREDIT"} or domain in {"FUNDING", "CREDIT"}:
        department, reason = "CLYDE_CREDIT", "verified funding/credit customer need"
    elif kind in {"SEO", "SEARCH_OPPORTUNITY"} or domain == "SEO":
        department, reason = "SEO", "search-demand or technical SEO evidence"
    elif kind in {"CONTENT", "CONTENT_OPPORTUNITY", "CUSTOMER_ACQUISITION"} or domain in {"MARKETING", "CREATIVE"}:
        department, reason = "MARKETING", "qualified customer-acquisition/content evidence"
    elif kind in {"CAPABILITY", "SYSTEMS", "TECHNICAL_FIX"} or domain == "SYSTEMS":
        department, reason = "SYSTEMS_ENGINEERING", "qualified platform capability or technical evidence"
    elif kind in {"TRADING", "TRADING_HYPOTHESIS"} or domain == "TRADING":
        department, reason = "TRADING_RESEARCH", "research-only trading hypothesis"
    else:
        department, reason = "BUSINESS_OPPORTUNITY", "qualified business opportunity requiring internal review"
    return {"target_department": department, "reason": reason}


def create_accept_execute_feedback(*, finding: dict[str, Any], alpha_receipt_id: str, department: str, task: str) -> dict[str, Any]:
    """Create a governed internal handoff, acceptance, bounded result, and feedback."""
    handoff_id = persistence.new_id("handoff")
    work_item_id = persistence.new_id("dept_work")
    result_id = persistence.new_id("dept_result")
    correlation = {"finding_id": finding.get("finding_id"), "need_id": finding.get("need_id"), "investigation_id": finding.get("investigation_id"), "alpha_receipt_id": alpha_receipt_id}
    persistence.append_record("research_v2_handoffs", {"schema_version": "nexus.department-handoff.v1", "handoff_id": handoff_id, **correlation, "target_department": department, "reason": task, "status": "ACCEPTED", "accepted_at": _now(), "external_action_allowed": False})
    persistence.append_record("work_orders", {"work_order_id": work_item_id, **correlation, "work_type": "bounded_internal_department_task", "owner_specialist": department, "status": "COMPLETED", "execution_class": "INTERNAL_READ_ONLY", "task": task, "external_mutation": False, "created_at": _now(), "completed_at": _now(), "receipt_id": result_id})
    persistence.append_record("result_feedback", {"schema_version": "nexus.department-result-feedback.v1", "result_id": result_id, **correlation, "department": department, "work_item_id": work_item_id, "status": "COMPLETE", "result": f"Bounded internal review completed for {task}.", "research_review_state": "PENDING", "alpha_review_state": "PENDING", "external_mutation": False, "created_at": _now()})
    return {"handoff_id": handoff_id, "work_item_id": work_item_id, "result_id": result_id, "department": department, "status": "COMPLETE", "external_mutation": False, **correlation}


def topicless_two_stage(themes: Iterable[dict[str, Any]], limit: int = 3) -> dict[str, Any]:
    """Keep topicless discovery as candidates, then bounded investigation."""
    stage1 = [dict(theme) for theme in themes if isinstance(theme, dict)][: max(0, limit)]
    stage2 = [{**theme, "investigation_status": "CANDIDATE", "promotion": "REQUIRES_COHERENCE_AND_ALPHA"} for theme in stage1]
    return {"stage1": stage1, "stage2": stage2, "theme_count": len(stage1), "investigated_theme_count": len(stage2)}
