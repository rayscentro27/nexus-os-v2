"""Bounded Nova control and presentation for R60 RESEARCH_ONLY jobs."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from datetime import datetime, timedelta, timezone

HANDOFF_SCHEMA = "nexus.research-only-handoff.v1"
MAX_HANDOFF_BYTES = 8192
MAX_SUMMARY_CHARS = 1200
MAX_POLLS_PER_INTERACTION = 1
STATUS_POLL_INTERVAL_SECONDS = 10


def deterministic_correlation(chat_id: Any, update_id: Any, question: str) -> str:
    material = f"{chat_id}:{update_id}:{' '.join(str(question).split()).casefold()}".encode()
    return "nova-research-only-" + hashlib.sha256(material).hexdigest()[:32]


def status_poll_allowed(last_poll_at: str = "", *, now: datetime | None = None) -> bool:
    """Allow at most one exact status read per job in each ten-second window."""
    if not last_poll_at:
        return True
    try:
        previous = datetime.fromisoformat(str(last_poll_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if previous.tzinfo is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc) - previous.astimezone(timezone.utc) >= timedelta(
        seconds=STATUS_POLL_INTERVAL_SECONDS)


def progress_for(job_state: str, result_status: str = "", lifecycle_stage: str = "") -> str:
    state = str(job_state or "").upper()
    result = str(result_status or "").upper()
    if result == "SOURCE_INSUFFICIENT":
        return "The source I checked didn’t provide enough evidence to answer that confidently."
    stage = str(lifecycle_stage or "").casefold()
    if "source" in stage and any(word in stage for word in ("read", "fetch", "acquir")):
        return "I’m reviewing the approved source."
    if any(word in stage for word in ("evidence", "finding", "extract")):
        return "I’m checking the evidence."
    return {
        "READY": "Research is queued.", "QUEUED": "Research is queued.",
        "CLAIMED": "I’m researching that now.", "RUNNING": "I’m researching that now.",
        "RESEARCH_READING_SOURCE": "I’m reviewing the approved source.",
        "RESEARCH_REVIEWING_EVIDENCE": "I’m checking the evidence.",
        "COMPLETED": "Research is complete.", "COMPLETE": "Research is complete.",
        "FAILED_RETRYABLE": "Research hit a temporary execution issue. I’ve kept the exact job linked and haven’t created a replacement.",
        "BLOCKED": "Research is blocked and needs review. I haven’t created replacement work.",
    }.get(state, "Research is still in progress.")


def parse_handoff(exact_job_result: dict[str, Any]) -> dict[str, Any] | None:
    """Read only compact Research handoff fields from an exact-job response."""
    job = exact_job_result.get("job") if isinstance(exact_job_result.get("job"), dict) else {}
    work = exact_job_result.get("research_work_item") if isinstance(exact_job_result.get("research_work_item"), dict) else {}
    candidates = [work.get("result"), job.get("result_summary"), job.get("result"), work.get("result_summary")]
    for candidate in candidates:
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except (TypeError, ValueError):
                continue
        if not isinstance(candidate, dict):
            continue
        handoff = candidate.get("research_result") if isinstance(candidate.get("research_result"), dict) else candidate
        if isinstance(candidate.get("handoff"), dict):
            handoff = candidate["handoff"]
        schema = handoff.get("schema_version") or handoff.get("schema")
        if schema != HANDOFF_SCHEMA:
            continue
        try:
            encoded = json.dumps(handoff, ensure_ascii=False, separators=(",", ":")).encode()
        except (TypeError, ValueError):
            continue
        if len(encoded) > MAX_HANDOFF_BYTES:
            return None
        raw_summary = handoff.get("summary")
        if not raw_summary and isinstance(handoff.get("key_findings"), list):
            raw_summary = " ".join(str(item) for item in handoff["key_findings"] if str(item).strip())
        summary = str(raw_summary or "").strip()
        if len(summary) > MAX_SUMMARY_CHARS:
            return None
        return {
            "schema": HANDOFF_SCHEMA,
            "status": str(handoff.get("result_status") or handoff.get("status") or
                          candidate.get("status") or "COMPLETED").upper(),
            "summary": summary,
            "evidence_refs": _bounded_list(handoff.get("evidence_refs") or
                                             handoff.get("evidence_references") or handoff.get("evidence"), 5),
            "unanswered_questions": _bounded_list(handoff.get("unanswered_questions"), 5),
        }
    return None


def render_handoff(handoff: dict[str, Any]) -> str:
    status = str(handoff.get("status") or "").upper()
    summary = " ".join(str(handoff.get("summary") or "").split())[:MAX_SUMMARY_CHARS]
    if status == "SOURCE_INSUFFICIENT":
        return "The source I checked didn’t provide enough evidence to answer that confidently."
    if not summary:
        return "Research completed, but its compact handoff did not contain a readable summary."
    answer = summary
    refs = _bounded_list(handoff.get("evidence_refs"), 5)
    questions = _bounded_list(handoff.get("unanswered_questions"), 5)
    if refs:
        labels = [str(item.get("title") or item.get("url") or item.get("reference") or "source")
                  if isinstance(item, dict) else str(item) for item in refs]
        answer += "\n\nEvidence: " + "; ".join(labels)[:500]
    if questions:
        answer += "\n\nStill unresolved: " + "; ".join(str(item) for item in questions)[:500]
    return answer


def user_facing_job_status(exact_job_result: dict[str, Any]) -> str:
    if exact_job_result.get("status") != "ok":
        return "I couldn’t confirm the status of that exact Research job. No replacement job was created."
    job = exact_job_result.get("job") if isinstance(exact_job_result.get("job"), dict) else {}
    state = str(job.get("state") or job.get("status") or "UNKNOWN").upper()
    handoff = parse_handoff(exact_job_result)
    if handoff:
        return render_handoff(handoff)
    work = exact_job_result.get("research_work_item") if isinstance(exact_job_result.get("research_work_item"), dict) else {}
    result_status = str(job.get("result_status") or work.get("result_status") or "").upper()
    return progress_for(state, result_status, str(work.get("current_stage") or ""))


def _bounded_list(value: Any, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit]
