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
SELECTED_EVIDENCE_MAX_BYTES = 8 * 1024
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


_ANCHOR_STOP_WORDS = {
    "according", "official", "documentation", "document", "docs", "what", "does", "do",
    "return", "returns", "when", "if", "where", "the", "a", "an", "to", "for", "of",
    "in", "on", "this", "that", "is", "are", "be", "it", "please", "explain",
}
_CONDITION_STOP_WORDS = {"the", "a", "an", "does", "do", "is", "are", "be", "it", "path"}
_BEHAVIOR_WORDS = {"return", "returns", "returned", "indicate", "indicates", "show", "shows",
                   "report", "reports", "represent", "represents", "mean", "means", "produce",
                   "produces", "yield", "yields", "calculate", "calculates", "accept", "accepts",
                   "raise", "raises", "throw", "throws", "contain", "contains", "identify", "identifies"}
_BEHAVIOR_VARIANTS = {
    "return": ("return", "returns", "returned"),
    "returns": ("return", "returns", "returned"),
    "returned": ("return", "returns", "returned"),
    "indicate": ("indicate", "indicates", "report", "reports", "show", "shows", "represent", "represents", "return", "returns"),
    "indicates": ("indicate", "indicates", "report", "reports", "show", "shows", "represent", "represents", "return", "returns"),
    "show": ("show", "shows", "indicate", "indicates", "report", "reports", "return", "returns"),
    "shows": ("show", "shows", "indicate", "indicates", "report", "reports", "return", "returns"),
    "report": ("report", "reports", "indicate", "indicates", "show", "shows", "return", "returns"),
    "reports": ("report", "reports", "indicate", "indicates", "show", "shows", "return", "returns"),
}


def assignment_anchors(question: str) -> dict[str, Any]:
    """Derive API, behavior, and condition anchors from the actual assignment."""
    without_urls = re.sub(r"https?://\S+", " ", str(question or ""), flags=re.I)
    symbols = list(dict.fromkeys(re.findall(
        r"\b(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*(?:\(\))?", without_urls)))
    symbols = [value.removesuffix("()") for value in symbols]
    parts = [part for symbol in symbols for part in symbol.split(".") if part]
    method = parts[-1].casefold() if len(parts) > 1 else ""
    entity = parts[-2].casefold() if len(parts) > 1 else ""
    tokens = {token.casefold() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", without_urls)
              if token.casefold() not in _ANCHOR_STOP_WORDS and len(token) > 1}
    conditional = re.search(r"\b(?:when|if|where|unless|while|under|without|for)\b(.+)$",
                            without_urls, flags=re.I)
    condition_text = conditional.group(1) if conditional else ""
    condition_tokens = {token.casefold() for token in re.findall(
        r"[A-Za-z_][A-Za-z0-9_]*", condition_text)
        if token.casefold() not in _CONDITION_STOP_WORDS and len(token) > 1}
    asks_return = bool(re.search(r"\b(return|returns|returned)\b", without_urls, flags=re.I))
    behavior_tokens = {token.casefold() for token in re.findall(
        r"[A-Za-z_][A-Za-z0-9_]*", without_urls)
        if token.casefold() in _BEHAVIOR_WORDS}
    return {"symbols": symbols, "method": method, "entity": entity,
            "tokens": tokens, "condition_tokens": condition_tokens,
            "behavior_tokens": behavior_tokens, "asks_return": asks_return}


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])",
                          text.casefold()))


def _condition_covered(text: str, anchors: dict[str, Any]) -> bool:
    terms = set(anchors.get("condition_tokens") or ())
    if not terms:
        return True
    lowered = text.casefold()
    # Wording variants are semantic variants of question conditions, not answer
    # values. The selected evidence must still cover the condition itself.
    variants = {"exist": ("exist", "exists", "existing", "nonexistent", "missing", "not found"),
                "exists": ("exist", "exists", "existing", "nonexistent", "missing", "not found"),
                "missing": ("missing", "nonexistent", "does not exist", "not found", "absent"),
                "not": ("not", "no", "without", "nonexistent", "missing"),
                "no": ("no", "not", "without", "nonexistent", "missing")}
    matched = 0
    for term in terms:
        options = variants.get(term, (term,))
        if any(_contains_term(lowered, option) for option in options):
            matched += 1
    return matched >= max(1, (len(terms) + 1) // 2)


def _responsive_to_assignment(question: str, evidence: str) -> bool:
    """Require subject, requested behavior, and conditional coverage when present."""
    anchors = assignment_anchors(question)
    lowered = evidence.casefold()
    method = str(anchors.get("method") or "")
    entity = str(anchors.get("entity") or "")
    if method:
        subject_covered = _contains_term(lowered, method)
    elif entity:
        subject_covered = _contains_term(lowered, entity)
    else:
        principal = set(anchors.get("tokens") or ())
        subject_covered = bool(principal & set(re.findall(r"[a-z0-9_]+", lowered)))
    if not subject_covered or not _condition_covered(lowered, anchors):
        return False
    behavior_tokens = set(anchors.get("behavior_tokens") or ())
    if "return" in behavior_tokens or "returns" in behavior_tokens or "returned" in behavior_tokens:
        return bool(re.search(
            r"\b(?:true|false|none|null)\b|\breturn(?:s|ed)?\s+(?!(?:when|if|for|because|that)\b)[a-z0-9_'\"`<]",
            lowered))
    if behavior_tokens:
        return any(_contains_term(lowered, variant)
                   for term in behavior_tokens
                   for variant in _BEHAVIOR_VARIANTS.get(term, (term,)))
    return bool(not anchors.get("asks_return") or re.search(
        r"\b(?:true|false|none|null)\b|\breturn(?:s|ed)?\s+(?!(?:when|if|for|because|that)\b)[a-z0-9_'\"`<]",
        lowered))


def _sentence_score(sentence: str, anchors: dict[str, Any]) -> int:
    lowered = sentence.casefold()
    score = 0
    method = str(anchors.get("method") or "")
    entity = str(anchors.get("entity") or "")
    if method and _contains_term(lowered, method):
        score += 100
    if entity and _contains_term(lowered, entity):
        score += 20
    score += 5 * sum(1 for term in anchors.get("condition_tokens", ()) if _contains_term(lowered, term))
    score += sum(1 for term in anchors.get("tokens", ()) if _contains_term(lowered, term))
    if anchors.get("asks_return") and re.search(r"\b(?:return|returns|returned|true|false|none|null)\b", lowered):
        score += 15
    return score


def _section_window(question: str, sections: list[dict[str, Any]]) -> str:
    """Choose a definition/heading and nearby same-section description blocks."""
    anchors = assignment_anchors(question)
    method = str(anchors.get("method") or "")
    candidates: list[tuple[int, int]] = []
    for index, block in enumerate(sections):
        if not isinstance(block, dict):
            continue
        metadata = " ".join(str(block.get(key) or "") for key in ("id", "section_id", "heading"))
        text = str(block.get("text") or "")
        score = _sentence_score(metadata + " " + text, anchors)
        if method and _contains_term(metadata, method):
            score += 1000
        if method and str(block.get("tag") or "").lower() == "dt" and _contains_term(text, method):
            score += 500
        if score:
            candidates.append((score, index))
    if not candidates:
        return ""
    _, start = max(candidates, key=lambda value: (value[0], -value[1]))
    selected: list[str] = []
    base_section = str(sections[start].get("section_id") or "")
    for index in range(start, min(len(sections), start + 5)):
        block = sections[index]
        section_id = str(block.get("section_id") or "")
        if index > start and base_section and section_id and section_id != base_section:
            break
        if index > start and block.get("tag") == "dt" and block.get("id"):
            break
        label = str(block.get("id") or block.get("heading") or "").strip()
        text = str(block.get("text") or "").strip()
        value = f"{label}: {text}" if label and label.casefold() not in text.casefold() else text
        if value:
            selected.append(value)
        encoded = "\n".join(selected).encode("utf-8")
        if len(encoded) >= SELECTED_EVIDENCE_MAX_BYTES:
            break
    return "\n".join(selected).encode("utf-8")[:SELECTED_EVIDENCE_MAX_BYTES].decode("utf-8", errors="ignore").strip()


def select_assignment_evidence(question: str, source_text: str,
                               sections: list[dict[str, Any]] | None = None) -> str | None:
    """Return a compact source excerpt only when it answers the assignment."""
    structural = _section_window(question, sections or []) if sections else ""
    candidate = structural or str(source_text or "")
    sentences = [" ".join(part.split()) for part in re.split(r"(?<=[.!?])\s+|\s{2,}", candidate)
                 if part.strip()]
    anchors = assignment_anchors(question)
    ranked = sorted(enumerate(sentences), key=lambda item: (-_sentence_score(item[1], anchors), item[0]))
    selected: list[str] = []
    for _, sentence in ranked:
        if not _sentence_score(sentence, anchors) and (not structural or len(selected) >= 3):
            continue
        proposal = " ".join(selected + [sentence])
        if len(proposal.encode("utf-8")) > SELECTED_EVIDENCE_MAX_BYTES:
            continue
        selected.append(sentence)
        if len(selected) >= 3:
            break
    if not selected:
        return None
    summary = " ".join(selected)
    # Put the API symbol in the compact handoff when the definition ID carries
    # it but the descriptive sentence omits it. This is a label, not an answer.
    if anchors.get("method") and not _contains_term(summary, str(anchors["method"])):
        symbol = next((str(value) for value in anchors.get("symbols", [])
                       if str(value).casefold().endswith("." + str(anchors["method"]))), "")
        if symbol:
            summary = f"{symbol}: {summary}"
    summary = summary[:SUMMARY_MAX_CHARS]
    if not summary.encode("utf-8") or len(summary.encode("utf-8")) > SELECTED_EVIDENCE_MAX_BYTES:
        return None
    return summary if _responsive_to_assignment(question, summary) else None


def _answer_excerpt(question: str, source_text: str,
                    sections: list[dict[str, Any]] | None = None) -> str | None:
    """Compatibility wrapper for the assignment-grounded evidence selector."""
    return select_assignment_evidence(question, source_text, sections)


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
    summary = _answer_excerpt(question, text, source.get("sections"))
    if not summary:
        insufficient = compact_handoff(job_id=job_id, objective_id=objective_id,
            project_id=project_id, case_id=case_id, question=question,
            summary="The approved source was fetched, but no selected passage covered the requested API behavior and conditions; no answer was inferred.",
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
