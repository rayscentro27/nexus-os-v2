"""Durable transcript, claim-validation, and downstream-gate contracts."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed.persistence import append_record, new_id, read_records


def persist_asr_required(*, video: dict[str, Any], failure_reason: str, attempts: int = 1, priority: str = "P1") -> dict[str, Any]:
    """Queue caption failures without blocking other portfolio work."""
    video_id = str(video.get("video_id") or "")
    record = {"schema_version": "nexus.youtube-asr-job.v1", "asr_job_id": new_id("youtube_asr"),
              "video_id": video_id, "video_url": video.get("video_url"), "channel": video.get("channel_name"),
              "failure_reason": failure_reason, "attempts": attempts, "created_at": video.get("created_at"),
              "priority": priority, "status": "ASR_REQUIRED", "next_attempt_at": video.get("next_attempt_at")}
    append_record("youtube_asr_jobs", record)
    return record


def persist_transcript_artifact(root: Path, *, video: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    text = str(result.get("transcript") or "").strip()
    if not text:
        raise ValueError("TRANSCRIPT_EMPTY")
    video_id = str(video.get("video_id") or result.get("video_id") or "")
    if not video_id:
        raise ValueError("VIDEO_ID_MISSING")
    path = root / "reports" / "runtime" / "youtube_transcripts" / f"{video_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "video_id": video_id,
        "channel_name": video.get("channel_name"),
        "video_title": video.get("video_title"),
        "video_url": video.get("video_url"),
        "published_at": video.get("published_at"),
        "transcript_source": result.get("transcript_method") or "unknown",
        "transcript_method": result.get("transcript_method") or "unknown",
        "transcript_fetched_at": result.get("retrieved_at"),
        "transcript_artifact_path": str(path.relative_to(root)),
        "transcript_text": text,
        "transcript_length_chars": len(text),
        "transcript_length_words": len(text.split()),
        "transcript_sha256": digest,
        "transcript_status": "TRANSCRIPT_RETRIEVED",
    }


def validation_result(*, claim: dict[str, Any], supporting: list[dict[str, Any]], contradicting: list[dict[str, Any]]) -> dict[str, Any]:
    if contradicting and supporting:
        status = "PARTIALLY_SUPPORTED"
    elif contradicting:
        status = "CONTRADICTED"
    elif len({x.get("source_family") for x in supporting}) >= 2:
        status = "VALIDATED"
    elif supporting:
        status = "PARTIALLY_SUPPORTED"
    else:
        status = "UNVERIFIED"
    score = 1.0 if status == "VALIDATED" else .5 if status == "PARTIALLY_SUPPORTED" else 0.0
    return {"validation_attempted": True, "validation_result": status, "validation_score": score,
            "evidence_source_count": len(supporting) + len(contradicting),
            "validator_receipt": new_id("youtube_validation")}


def persist_validation(*, claim: dict[str, Any], video: dict[str, Any], supporting: list[dict[str, Any]], contradicting: list[dict[str, Any]], at: str) -> dict[str, Any]:
    result = validation_result(claim=claim, supporting=supporting, contradicting=contradicting)
    record = {"schema_version": "nexus.youtube-claim-validation.v1", "claim_id": claim["claim_id"],
              "video_id": video.get("video_id"), "validation_started_at": at,
              "validation_completed_at": at, "primary_sources": supporting,
              "contradicting_sources": contradicting, **result}
    append_record("youtube_claim_validations", record)
    if result["validation_result"] in {"UNVERIFIED", "PARTIALLY_SUPPORTED", "VALIDATION_FAILED"}:
        follow_up = {"schema_version": "nexus.youtube-follow-up.v1",
            "follow_up_id": new_id("youtube_followup"), "claim_id": claim["claim_id"],
            "video_id": video.get("video_id"),
            "exact_missing_evidence": "Independent primary evidence for the extracted claim",
            "next_search_question": f"What current primary evidence verifies: {claim.get('claim', '')}?",
            "suggested_source_types": ["official documentation", "government/regulator", "primary company page"],
            "priority": "P1", "retry_after": at, "status": "OPEN"}
        if not any(row.get("claim_id") == follow_up["claim_id"] and row.get("status") == "OPEN" for row in read_records("youtube_follow_ups")):
            append_record("youtube_follow_ups", follow_up)
        queue_item = {"schema_version": "nexus.research-question.v1", "question_id": new_id("youtube_followup_question"),
                      "claim_id": claim["claim_id"], "video_id": video.get("video_id"),
                      "question": follow_up["next_search_question"], "priority": "P1", "status": "OPEN",
                      "next_attempt_at": at, "source": "youtube_validation", "created_at": at}
        if not any(row.get("claim_id") == queue_item["claim_id"] and row.get("status") == "OPEN" for row in read_records("research_questions")):
            append_record("research_questions", queue_item)
    return result


def downstream_handoff_allowed(*, validation: dict[str, Any], explicit_follow_up: bool = False, internal_experiment: bool = False) -> bool:
    return validation.get("validation_result") == "VALIDATED" or explicit_follow_up or internal_experiment
