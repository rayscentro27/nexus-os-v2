"""Bounded governance for the consumer Meta browser surface.

Meta's consumer limits are dynamic and not treated as a known numeric quota.
This module classifies observed failures and prevents retry storms; it does not
attempt to bypass provider limits.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CONSUMER_META_LIMITS = "UNKNOWN_DYNAMIC"
META_RATE_LIMIT = "META_RATE_LIMIT"
META_ARTIFACT_FAILURE = "META_ARTIFACT_FAILURE"
META_SESSION_FAILURE = "META_SESSION_FAILURE"
META_PROVIDER_ERROR = "META_PROVIDER_ERROR"
UNKNOWN_TRANSIENT_FAILURE = "UNKNOWN_TRANSIENT_FAILURE"


def classify_meta_failure(*, status_code: int | None = None, body_text: str = "", error_text: str = "") -> str:
    text = f"{body_text}\n{error_text}".lower()
    explicit_limit = (
        status_code == 429
        or "usage limit" in text
        or "rate limit" in text
        or "daily limit" in text
        or "monthly quota" in text
        or "upgrade to continue" in text
        or "unlock more" in text
    )
    if explicit_limit:
        return META_RATE_LIMIT
    if any(token in text for token in ("download", "export", "preview", "artifact", "internal server error")):
        return META_ARTIFACT_FAILURE
    if any(token in text for token in ("log in", "login", "sign in", "session expired", "unauthorized", "authentication")):
        return META_SESSION_FAILURE
    if status_code is not None and status_code >= 500:
        return META_PROVIDER_ERROR
    return UNKNOWN_TRANSIENT_FAILURE


def retry_decision(failure_count: int) -> str:
    """Allow one bounded retry for a transient failure, then stop the task."""
    return "RETRY_ONCE" if failure_count == 1 else "STOP_TASK"


def ledger_event(*, artifact_type: str, status: str, failure_class: str | None = None, detail: str | None = None) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "status": status,
        "failure_class": failure_class,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
