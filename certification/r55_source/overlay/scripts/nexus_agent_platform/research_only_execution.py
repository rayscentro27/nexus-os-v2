"""Explicit bounded Research-only execution, ending before parent continuation.

This path is selected only by a durable RESEARCH_ONLY intent. Normal
RESEARCH_MISSION jobs retain the parent workflow and its Advisor/Needle stages.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

HANDOFF_MAX_BYTES = 8 * 1024
SUMMARY_MAX_CHARS = 1200
MAX_EVIDENCE_REFS = 5
MAX_UNANSWERED_QUESTIONS = 5


def compact_handoff(*, job_id: str, objective_id: str, project_id: str,
                    case_id: str, question: str, summary: str,
                    evidence_refs: list[str], status: str = "RESEARCH_COMPLETE",
                    unanswered_questions: list[str] | None = None,
                    next_research_action: str | None = None) -> dict[str, Any]:
    """Build the bounded operational handoff; source bodies/transcripts excluded."""
    refs = list(dict.fromkeys(str(x)[:300] for x in evidence_refs if str(x).strip()))[:MAX_EVIDENCE_REFS]
    questions = list(dict.fromkeys(str(x)[:300] for x in (unanswered_questions or []) if str(x).strip()))[:MAX_UNANSWERED_QUESTIONS]
    result = {
        "schema_version": "nexus.research-only-handoff.v1",
        "job_id": str(job_id), "objective_id": str(objective_id),
        "project_id": str(project_id), "case_id": str(case_id),
        "question": str(question)[:1000], "summary": str(summary)[:SUMMARY_MAX_CHARS],
        "key_findings": [str(summary)[:SUMMARY_MAX_CHARS]] if summary else [],
        "evidence_references": refs, "unanswered_questions": questions,
        "recommended_next_research_action": str(next_research_action or "")[:300] or None,
        "result_status": str(status)[:40],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()
    if len(encoded) > HANDOFF_MAX_BYTES:
        raise ValueError("RESEARCH_ONLY_HANDOFF_SIZE_LIMIT")
    return result


def _persist_handoff(handoff: dict[str, Any]) -> dict[str, Any]:
    from research.proactive_research_memory import persist_state
    return persist_state({**handoff, "memory_kind": "RESEARCH_ONLY_RESULT",
        "memory_id": "research_only_result_" + str(handoff["job_id"]), "namespace": "PRODUCTION"})


def _bounded_failure(work: Mapping[str, Any], *, job_id: str, reason: str,
                     status: str = "SOURCE_UNAVAILABLE", case_id: str = "") -> dict[str, Any]:
    """Retain a compact explicit failure when assignment identity is available."""
    objective_id = str(work.get("objective_id") or "").strip()
    project_id = str(work.get("project_id") or work.get("work_id") or "").strip()
    question = str(work.get("question") or work.get("research_scope") or "").strip()
    if not all((job_id, objective_id, project_id, question)):
        return {"status": "BLOCKED", "reason": reason}
    handoff = compact_handoff(job_id=job_id, objective_id=objective_id,
        project_id=project_id, case_id=case_id, question=question,
        summary="No Research answer was produced; the bounded execution stopped with an explicit failure.",
        evidence_refs=[], status=status, next_research_action="REVIEW_OR_REPLACE_SOURCE")
    _persist_handoff(handoff)
    return {"status": "BLOCKED", "reason": reason, "case_id": case_id or None,
            "research_result": handoff}


def _answer_excerpt(question: str, source_text: str) -> str:
    """Select up to three source sentences with the strongest question overlap."""
    stop = {"according", "official", "documentation", "document", "what", "does", "do",
            "return", "returns", "when", "the", "a", "an", "to", "for", "of", "in", "on",
            "this", "that", "is", "are", "be", "it", "path"}
    terms = {token for token in re.findall(r"[a-z0-9_]+", question.casefold())
             if len(token) > 2 and token not in stop}
    identifiers = {value.casefold() for value in re.findall(
        r"\b(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*\b", question)}
    terms.update(identifiers)
    sentences = [" ".join(part.split()) for part in
        re.split(r"(?<=[.!?])\s+|\s{2,}", source_text) if part.strip()]
    ranked = []
    for index, sentence in enumerate(sentences):
        lowered = sentence.casefold()
        score = sum(1 for term in terms if term in lowered)
        if score:
            ranked.append((score, -index, sentence))
    selected = [item[2] for item in sorted(ranked, reverse=True)[:3]]
    return " ".join(selected)[:SUMMARY_MAX_CHARS]


def execute_research_only(work_item: Mapping[str, Any], *, job_id: str,
                          stage: Callable[[str, Mapping[str, Any]], None] | None = None) -> dict[str, Any]:
    """Open a real case, perform one bounded public read, persist compact result."""
    work = dict(work_item)
    question = str(work.get("question") or work.get("research_scope") or "").strip()
    objective = str(work.get("original_objective") or work.get("objective") or work.get("title") or "").strip()
    objective_id = str(work.get("objective_id") or "").strip()
    project_id = str(work.get("project_id") or work.get("work_id") or "").strip()
    source_url = str(work.get("original_source_url") or work.get("source_url") or "").strip()
    if not all((question, objective, objective_id, project_id, job_id)):
        return {"status": "BLOCKED", "reason": "RESEARCH_ONLY_REQUIRED_FIELDS_MISSING"}
    if not source_url:
        return _bounded_failure(work, job_id=job_id,
            reason="RESEARCH_ONLY_PUBLIC_SOURCE_URL_REQUIRED", status="SOURCE_UNAVAILABLE")
    from nexus_agent_platform.evidence_ingestion import validate_public_url
    safe_url, reason = validate_public_url(source_url)
    if not safe_url:
        return _bounded_failure(work, job_id=job_id,
            reason=f"RESEARCH_ONLY_SOURCE_REJECTED:{reason}", status="SOURCE_REJECTED")

    lowered = f"{objective} {question}".casefold()
    objective_type = str(work.get("objective_type") or "").upper()
    if objective_type == "TRADING_INTELLIGENCE" or any(x in lowered for x in ("forex", "currency pair", "fx strategy")):
        family, owner, goal = "TRADING_INTELLIGENCE", "MERCURY_TRADING", "FOREX"
    elif objective_type == "BUSINESS_OPPORTUNITY":
        family, owner, goal = "BUSINESS_OPPORTUNITIES", "BUSINESS_OPPORTUNITIES", "BUSINESS_OPPORTUNITY"
    else:
        family, owner, goal = "RESEARCH_INTAKE", "RESEARCH", "RESEARCH_INTAKE"

    from research import research_case_engine as cases
    if stage:
        stage("CASE_OPEN_START", {"objective_id": objective_id, "project_id": project_id})
    opened = cases.open_or_join_case(objective=objective, objective_family=family,
        business_or_nexus_goal=goal, owner_department=owner, primary_question=question,
        priority=50, originating_goal_id=objective_id, objective_id=objective_id,
        project_id=project_id, requires_ray=False)
    case = opened.get("case") if isinstance(opened, dict) else None
    if not case:
        if isinstance(opened, dict) and opened.get("wait_for_capacity"):
            return {"status": "WAITING_FOR_CAPACITY", "reason": opened.get("reason") or "MAX_ACTIVE_DEEP_CASES_REACHED",
                    "retryable": True, "objective_terminated": False}
        return _bounded_failure(work, job_id=job_id,
            reason=str((opened or {}).get("reason") or "RESEARCH_ONLY_CASE_OPEN_FAILED"),
            status="CASE_OPEN_FAILED")
    case_id = str(case.get("case_id") or "")
    if not case_id:
        return _bounded_failure(work, job_id=job_id,
            reason="RESEARCH_ONLY_CASE_ID_MISSING", status="CASE_OPEN_FAILED")

    # One source-adapter call. The adapter validates public URLs and redirects,
    # applies a 1 MB response cap and returns at most 12 KB of extracted text.
    from nexus_agent_platform.research_parent_adapters import _fallback_public_page
    try:
        source = _fallback_public_page(safe_url, work)
    except Exception as exc:
        source = {"status": "SOURCE_READ_FAILED", "reason": type(exc).__name__}
    text = " ".join(str(source.get("text") or "").split())
    if stage:
        stage("RESEARCH_SOURCE_READ", {"source_url": str(source.get("url") or safe_url),
              "source_bytes": int(source.get("bytes") or 0), "text_chars": len(text)})
    if str(source.get("status") or "").upper() != "COMPLETED" and not text:
        failed_handoff = compact_handoff(job_id=job_id, objective_id=objective_id,
            project_id=project_id, case_id=case_id, question=question,
            summary="The approved source could not be read; no result was inferred.",
            evidence_refs=[], status="SOURCE_UNAVAILABLE",
            next_research_action="RETRY_OR_REPLACE_APPROVED_SOURCE")
        _persist_handoff(failed_handoff)
        return {"status": "BLOCKED", "reason": str(source.get("reason") or source.get("status") or "RESEARCH_ONLY_SOURCE_UNAVAILABLE"),
                "case_id": case_id, "research_result": failed_handoff}
    source_url_used = str(source.get("url") or safe_url)[:500]
    summary = _answer_excerpt(question, text)
    if not summary:
        insufficient = compact_handoff(job_id=job_id, objective_id=objective_id,
            project_id=project_id, case_id=case_id, question=question,
            summary="The approved source was read, but no directly relevant passage was found.",
            evidence_refs=[source_url_used], status="SOURCE_INSUFFICIENT",
            unanswered_questions=[question],
            next_research_action="REVIEW_SOURCE_OR_APPROVE_ANOTHER_SOURCE")
        _persist_handoff(insufficient)
        return {"status": "BLOCKED", "reason": "RESEARCH_ONLY_RELEVANT_EVIDENCE_NOT_FOUND",
                "case_id": case_id, "research_result": insufficient,
                "source_read_count": 1, "source_url": source_url_used}
    evidence_ref = source_url_used
    attached = cases.add_source(case_id, {"source_id": f"research-only:{job_id}",
        "url": source_url_used, "source_url": source_url_used,
        "title": str(source.get("title") or source_url_used)[:200],
        "source_type": "PUBLIC_WEB", "source_class": "OFFICIAL_DOCUMENTATION"})
    if not attached.get("ok"):
        return {"status": "BLOCKED", "reason": str(attached.get("reason") or "RESEARCH_ONLY_SOURCE_PERSIST_FAILED"),
                "case_id": case_id}
    finding = cases.record_research_only_result(case_id, question=question,
        answer=summary, evidence_ids=[evidence_ref], finding={
        "finding_id": "research_only_" + hashlib.sha256(job_id.encode()).hexdigest()[:20],
        "claim": summary, "summary": summary, "evidence_level": "SOURCE_GROUNDED",
        "evidence_ids": [evidence_ref], "source_ids": [f"research-only:{job_id}"],
        "research_job_id": job_id, "result_status": "RESEARCH_COMPLETE"})
    if not finding.get("ok"):
        return {"status": "BLOCKED", "reason": str(finding.get("reason") or "RESEARCH_ONLY_FINDING_PERSIST_FAILED"),
                "case_id": case_id}
    handoff = compact_handoff(job_id=job_id, objective_id=objective_id,
        project_id=project_id, case_id=case_id, question=question, summary=summary,
        evidence_refs=[evidence_ref], status="RESEARCH_COMPLETE",
        next_research_action="AWAIT_REVIEW_BEFORE_MORE_RESEARCH")
    persisted = _persist_handoff(handoff)
    if stage:
        stage("RESEARCH_RESULT_CREATED", {"case_id": case_id,
              "result_memory_id": persisted.get("memory_id"), "summary_chars": len(summary),
              "evidence_reference_count": len(handoff["evidence_references"])})
    return {"status": "COMPLETED", "job_type": "RESEARCH_INTAKE",
        "requested_intent": "RESEARCH_ONLY", "routed_intent": "RESEARCH_ONLY",
        "execution_path": "BOUNDED_RESEARCH_ONLY", "case_id": case_id,
        "research_result": handoff, "research_result_memory_id": persisted.get("memory_id"),
        "source_read_count": 1, "source_url": source_url_used,
        "downstream_jobs_created": 0}
