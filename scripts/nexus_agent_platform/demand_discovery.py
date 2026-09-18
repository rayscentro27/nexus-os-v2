"""Bounded customer-demand discovery projection.

This module turns repeated, source-backed questions into a deduplicated need
record. It does not infer demand from a single comment and does not choose a
product or execute an external action.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_agent_platform.research_work_queue import ResearchWorkQueue

ROOT = Path(__file__).resolve().parents[2]


def discover_from_questions(rows: list[dict[str, Any]], *, queue: ResearchWorkQueue | None = None) -> list[dict[str, Any]]:
    """Project repeated demand-shaped questions into governed need objects.

    A question is eligible only when it is marked as search-demand/customer
    oriented and appears from at least two distinct records or source refs.
    """
    queue = queue or ResearchWorkQueue()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        text = str(row.get("question") or row.get("question_or_task") or "").strip()
        if not text:
            continue
        haystack = f"{text} {row.get('lane', '')} {row.get('target_decision', '')}".lower()
        if not any(term in haystack for term in ("customer", "demand", "funding", "credit", "lender", "loan", "revenue", "bankability")):
            continue
        key = " ".join(text.lower().split())
        grouped.setdefault(key, []).append(row)
    needs = []
    for question, evidence in grouped.items():
        refs = sorted({str(row.get("source_or_finding_origin") or row.get("source_id") or row.get("source_ref")) for row in evidence if row.get("source_or_finding_origin") or row.get("source_id") or row.get("source_ref")})
        if len(evidence) < 2 and len(refs) < 2:
            continue
        audience = "small-business owners seeking funding or credit readiness"
        problem = question
        need = queue.create_need(
            audience=audience,
            problem=problem,
            question=question,
            desired_outcome="clear, evidence-backed next step",
            source_refs=refs,
            where_customers_congregate=["search-demand question clusters"],
            demand_signals=[f"repeated in {len(evidence)} governed question records"],
            evidence_gaps=["independent search-volume or complaint-level evidence", "solution economics"],
            commercial_intent="PRELIMINARY" if any(term in question for term in ("funding", "lender", "loan", "credit")) else "UNKNOWN",
        )
        needs.append(need)
    return needs


def discover_from_governed_questions(*, root: Path = ROOT, queue: ResearchWorkQueue | None = None) -> list[dict[str, Any]]:
    path = root / "data/governed/research_questions.jsonl"
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict): rows.append(row)
            except json.JSONDecodeError:
                continue
    return discover_from_questions(rows, queue=queue)
