#!/usr/bin/env python3
"""Bounded executor for existing YouTube validation follow-ups."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from alpha.alpha_discovery import retrieve_page  # noqa: E402
from nexus_agent_platform.governed.persistence import append_record, new_id, read_records  # noqa: E402

TARGETS = {
    "CJtGjic7SIc": ["https://hyperagent.ai/"],
    "i7bRUHH1O1M": ["https://buildonaut-yt.netlify.app/"],
    "A5vj0ZJiVl0": ["https://www.waiterscapital.com/"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _retry_after() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


def _latest_claim(claim_id: str) -> dict | None:
    return next((row for row in read_records("alpha_claims") if row.get("claim_id") == claim_id), None)


def execute(limit: int = 2) -> dict:
    heartbeat = ROOT / "reports/runtime/youtube_followup_worker_heartbeat.json"
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text(json.dumps({"status": "RUNNING", "started_at": _now()}, indent=2) + "\n", encoding="utf-8")
    completed_claims = {row.get("claim_id") for row in read_records("youtube_follow_up_executions") if row.get("claim_id") and row.get("status") == "COMPLETED"}
    now = datetime.now(timezone.utc)
    followups = []
    for row in read_records("youtube_follow_ups"):
        if not row.get("claim_id") or row.get("status") not in {None, "OPEN", "PARTIALLY_SUPPORTED", "UNVERIFIED", "FAILED_RETRYABLE"}:
            continue
        retry_after = row.get("retry_after")
        if row.get("claim_id") in completed_claims and (not retry_after or datetime.fromisoformat(retry_after.replace("Z", "+00:00")) > now):
            continue
        followups.append(row)
    followups.sort(key=lambda row: (0 if row.get("video_id") in TARGETS else 1, str(row.get("retry_after") or "")))
    seen = set(); selected = []
    for row in followups:
        if row["claim_id"] not in seen:
            seen.add(row["claim_id"]); selected.append(row)
        if len(selected) >= max(1, min(limit, 2)): break
    results = []
    for followup in selected:
        started = _now(); claim = _latest_claim(followup["claim_id"]) or {}
        video_id = followup.get("video_id") or claim.get("video_id")
        urls = TARGETS.get(video_id, [])
        retrieved = []
        failures = []
        for url in urls[:2]:
            try:
                result = retrieve_page(url, timeout=12)
            except Exception as exc:  # isolate one source/job from the worker loop
                failures.append({"url": url, "error": type(exc).__name__})
                result = {"ok": False, "error": type(exc).__name__}
            retrieved.append({"url": url, "ok": bool(result.get("ok")), "title": result.get("title"), "content_length": result.get("content_length", 0), "retrieved_at": result.get("retrieved_at"), "text_hash": result.get("text_hash")})
        usable = [row for row in retrieved if row["ok"] and row.get("content_length", 0) > 0]
        validation = "PARTIALLY_SUPPORTED" if usable else ("FAILED_RETRYABLE" if failures else "UNVERIFIED")
        completed = _now(); receipt = {"schema_version": "nexus.youtube-follow-up-execution.v1", "execution_id": new_id("youtube_followup_exec"), "follow_up_id": followup.get("follow_up_id"), "claim_id": followup["claim_id"], "video_id": video_id, "claimed_at": started, "started_at": started, "completed_at": completed, "sources_searched": len(urls), "sources_retrieved": len(usable), "primary_sources": usable, "evidence_created": bool(usable), "revalidation_result": validation, "next_action": "Search an additional independent primary source" if validation != "VALIDATED" else "Evaluate qualified downstream routing", "status": "COMPLETED", "attempt_count": 1, "last_evidence_delta": len(usable), "next_research_justification": "Independent evidence remains insufficient for a business decision.", "receipt": new_id("youtube_followup_receipt")}
        receipt["source_failures"] = failures
        append_record("youtube_follow_up_executions", receipt)
        append_record("youtube_follow_ups", {**followup, "status": validation, "attempt_count": int(followup.get("attempt_count") or 0) + 1, "last_execution_id": receipt["execution_id"], "retry_after": _retry_after() if validation != "VALIDATED" else None, "updated_at": completed})
        append_record("youtube_claim_validations", {"schema_version": "nexus.youtube-claim-validation.v1", "claim_id": followup["claim_id"], "video_id": video_id, "validation_attempted": True, "validation_started_at": started, "validation_completed_at": completed, "primary_sources": usable, "contradicting_sources": [], "validation_result": validation, "validation_score": .5 if validation == "PARTIALLY_SUPPORTED" else 0.0, "evidence_source_count": len(usable), "validator_receipt": receipt["receipt"]})
        if claim:
            append_record("alpha_claims", {**claim, "validation_attempted": True, "validation_result": validation, "validation_score": .5 if validation == "PARTIALLY_SUPPORTED" else 0.0, "evidence_source_count": len(usable), "revision": int(claim.get("revision", 1)) + 1, "supersedes": claim.get("claim_id"), "updated_at": completed})
        results.append({"follow_up_id": followup.get("follow_up_id"), "video_id": video_id, "receipt": receipt})
    output = {"ok": True, "executed": len(results), "results": results, "selector": "youtube_follow_ups oldest distinct claim", "executor": "bounded primary-source retrieval + validation", "external_action_performed": False}
    heartbeat.write_text(json.dumps({"status": "ACTIVE", "completed_at": _now(), "last_real_output": output, "executed": len(results)}, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2))
