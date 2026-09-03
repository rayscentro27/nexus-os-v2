"""Bounded, turn-local recovery for non-progressing Hermes tool loops."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def progress_trace(tool_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify tool results without treating HTTP success as useful progress."""
    seen: set[tuple[str, str]] = set()
    trace: list[dict[str, Any]] = []
    for row in tool_rows:
        name = str(row.get("name") or row.get("tool_name") or "unknown")
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        result_fp = fingerprint(payload)
        key = (name, result_fp)
        status = str(payload.get("status") or payload.get("error") or "UNKNOWN").upper()
        if key in seen:
            progress = "SAME_FAILURE" if status in {"ERROR", "FAILED", "FAILURE", "UNAVAILABLE"} else "NO_NEW_INFORMATION"
        elif status in {"ERROR", "FAILED", "FAILURE", "UNAVAILABLE"}:
            progress = "TRANSIENT_FAILURE" if payload.get("retryable") else "STRUCTURALLY_BLOCKED"
        else:
            progress = "PROGRESS"
        seen.add(key)
        trace.append({
            "tool": name,
            "result_fingerprint": result_fp,
            "status": status,
            "progress": progress,
            "new_information": progress == "PROGRESS",
        })
    return trace


def recovery_plan(question: str, draft: str, tool_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose one bounded alternate strategy after a method failure."""
    lowered = (draft or "").lower()
    trace = progress_trace(tool_rows)
    halt = any(marker in lowered for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts"))
    repeated = [row["tool"] for row in trace if row["progress"] in {"SAME_FAILURE", "NO_NEW_INFORMATION"}]
    failed = [row["tool"] for row in trace if row["progress"] in {"TRANSIENT_FAILURE", "STRUCTURALLY_BLOCKED", "SAME_FAILURE"}]
    suppressed = sorted(set(repeated or failed)) if halt else []
    return {
        "schema_version": "nexus.nova-tool-recovery.v1",
        "parent_question": (question or "")[:1000],
        "guardrail_halt_detected": halt,
        "progress_trace": trace[-20:],
        "failed_tools": failed,
        "temporarily_suppressed_tools": suppressed,
        "action": "SYNTHESIZE_EXISTING_EVIDENCE" if halt else "CONTINUE_NORMAL_LOOP",
        "bounded_attempt": 1 if halt else 0,
        "max_recovery_attempts": 1,
        "preserve_evidence": True,
        "mutation_policy": "READ_ONLY_ALTERNATES_ONLY; NEVER_REPEAT_MUTATION",
        "next_instruction": (
            "The prior tool method failed or stopped making progress. Do not call the suppressed tool again in this recovery continuation. "
            "Use returned evidence, state what remains unknown, compare any specialist positions, and provide a conditional recommendation or honest unknown."
            if halt else "No recovery needed."
        ),
    }
