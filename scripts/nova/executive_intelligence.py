"""Small, deterministic executive-planning contract for Hermes Nova.

This module does not answer questions, execute work, or replace Nexus goals.
It records the minimum planning metadata that lets the existing Hermes/Nexus
path choose depth, specialists, and durable follow-through consistently.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROCESS_DIR = ROOT / "data" / "runtime" / "nova_executive_processes"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(text: str) -> str:
    return hashlib.sha256((text or "").strip().casefold().encode()).hexdigest()[:16]


def classify_query(question: str) -> str:
    """Classify depth without forcing every question through specialists."""
    text = (question or "").strip().lower()
    if not text:
        return "SIMPLE_FACT"
    if re.search(r"\b(continue|resume|manage|track|come back|over time|multi[- ]?day|process|execute|turn .* into)", text):
        return "DURABLE_PROCESS_REQUEST"
    if re.search(r"\b(browse|browser|website|web page|ui|login|search online|serp)", text):
        return "BROWSER_REQUIRED"
    if re.search(r"\b(run|backtest|compute|benchmark|calculate|simulation|heavy)", text):
        return "EXECUTION_REQUEST"
    if re.search(r"\b(current|today|now|still|latest|status|changed|what needs|what happened)", text):
        if re.search(r"\b(should|recommend|prioritize|why|compare|plan|focus|blocking|opportunity|model|offer|free|subscription)", text):
            return "MULTI_LEVEL_STRATEGIC_QUERY"
        return "CURRENT_STATE_QUERY"
    specialists = specialist_selection(text)
    if len(specialists) > 1:
        return "MULTI_SPECIALIST_QUERY"
    if re.search(r"\b(should|recommend|prioritize|compare|why|plan|impact|economic|strategy|opportunity|blocking|concerns?)\b", text):
        return "MULTI_LEVEL_STRATEGIC_QUERY"
    if specialists:
        return "SINGLE_SPECIALIST_QUERY"
    if re.search(r"\b(should|recommend|prioritize|compare|why|plan|impact|economic|strategy|opportunity|blocking|concerns?)", text):
        return "MULTI_LEVEL_STRATEGIC_QUERY"
    return "SIMPLE_FACT"


def specialist_selection(question: str) -> list[str]:
    text = (question or "").lower()
    selected: list[str] = []
    rules = (
        ("RESEARCH", r"research|evidence|market|current|latest|competitor|unknown"),
        ("ALPHA", r"alpha|challenge|contradict|confidence|assumption|risk"),
        ("FINANCE", r"finance|cost|margin|revenue|price|pricing|subscription|capital|economic"),
        ("MARKETING", r"marketing|customer|acquisition|funnel|offer|demand|channel"),
        ("CREATIVE", r"creative|video|design|asset|campaign idea|thumbnail"),
        ("SEO", r"seo|search intent|keyword|serp|ranking"),
        ("CLYDE", r"credit|readiness|bankability|clyde"),
        ("FUNDING", r"funding|lender|capital access|application"),
        ("OPPORTUNITY", r"opportunit|venture|business model|affiliate"),
        ("TRADING", r"trading|strategy|backtest|oos|paper"),
        ("SYSTEMS", r"system|runtime|reliability|model|tool|browser|remote|latency|status|health"),
    )
    for name, pattern in rules:
        if re.search(pattern, text):
            selected.append(name)
    return selected


def decompose_question(question: str) -> dict[str, Any]:
    """Return an auditable plan hint; specialists still decide the evidence."""
    complexity = classify_query(question)
    specialists = specialist_selection(question)
    if complexity in {"SIMPLE_FACT", "CURRENT_STATE_QUERY"}:
        specialists = specialists[:1]
    needs_research = complexity not in {"SIMPLE_FACT"} and bool(
        re.search(r"\b(current|latest|evidence|market|unknown|research|changed|competitor)", question or "", re.I)
    )
    return {
        "schema_version": "nexus.nova-executive-plan.v1",
        "complexity": complexity,
        "parent_question": (question or "").strip()[:1000],
        "subquestion_prompt": "Identify assumptions, unknowns, alternatives, and the decision criterion before answering." if complexity in {"MULTI_LEVEL_STRATEGIC_QUERY", "DURABLE_PROCESS_REQUEST"} else None,
        "specialists": specialists,
        "parallel_candidates": specialists[:],
        "needs_research": needs_research,
        "requires_recommendation": complexity in {"MULTI_LEVEL_STRATEGIC_QUERY", "MULTI_SPECIALIST_QUERY", "DURABLE_PROCESS_REQUEST"},
        "goal_completion_rule": "Do not close the parent goal when only a task, report, asset, or specialist response is complete.",
        "created_at": _now(),
    }


def process_record(session_id: str, question: str, plan: dict[str, Any], *, result: str | None = None) -> dict[str, Any] | None:
    """Persist a lightweight process record for durable requests only."""
    if plan.get("complexity") != "DURABLE_PROCESS_REQUEST":
        return None
    process_id = f"nova-process-{_key(session_id + ':' + question)}"
    path = PROCESS_DIR / f"{process_id}.json"
    try:
        existing = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        existing = {}
    record = {
        **existing,
        "schema_version": "nexus.nova-process.v1",
        "process_id": process_id,
        "session_id": session_id,
        "parent_question": question[:1000],
        "plan": plan,
        "status": "ADVANCING" if result else existing.get("status", "ACTIVE"),
        "next_action": "Evaluate evidence and preserve the parent objective until its success criterion is met.",
        "last_result": (result or "")[-1500:] if result else existing.get("last_result"),
        "updated_at": _now(),
    }
    PROCESS_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", dir=PROCESS_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass
    return record


def decision_framework(question: str, *, evidence: list[str] | None = None, recommendation: str | None = None) -> dict[str, Any]:
    """Create a compact persisted-decision shape without inventing evidence."""
    return {
        "schema_version": "nexus.nova-decision.v1",
        "question": question[:1000],
        "evidence": list(evidence or [])[:12],
        "specialist_positions": [],
        "contradictions": [],
        "unknowns": [],
        "recommended_option": recommendation,
        "confidence": "UNKNOWN",
        "next_test": "Identify the cheapest reversible test that would change the decision.",
        "review_trigger": "New authoritative evidence, material result, or changed objective.",
        "created_at": _now(),
    }


def telegram_executive_format(recommendation: str, *, why: str = "", decision: str = "") -> str:
    """Keep executive answers useful on a first mobile screen."""
    parts = [recommendation.strip()]
    if why.strip():
        parts.append(f"Why: {why.strip()}")
    if decision.strip():
        parts.append(f"Ray decision: {decision.strip()}")
    return "\n\n".join(parts)
