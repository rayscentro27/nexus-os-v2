"""Reusable Nexus current-state classification and filtering policy.

Persistence is not currentness.  This module is intentionally small and
source-agnostic so governed readers and future specialist adapters can share
the same vocabulary without moving truth decisions into Hermes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

CURRENTNESS_CLASSES = (
    "REAL_CURRENT",
    "REAL_HISTORICAL",
    "SIMULATED",
    "SYNTHETIC",
    "FIXTURE",
    "DEVELOPMENT",
    "LEGACY_UNKNOWN",
    "UNKNOWN",
)

DEFAULT_MAX_AGE_SECONDS = 172800


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp


def age_seconds(value: Any, *, now: datetime | None = None) -> float | None:
    stamp = parse_time(value)
    if stamp is None:
        return None
    return max(0.0, ((now or now_utc()) - stamp).total_seconds())


def source_is_current(value: Any, *, max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
                      now: datetime | None = None) -> bool:
    age = age_seconds(value, now=now)
    return age is not None and age <= max_age_seconds


def classify_record(record: dict[str, Any], *, source_timestamp: Any = None,
                    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
                    synthetic: bool = False, fixture: bool = False,
                    development: bool = False,
                    now: datetime | None = None) -> dict[str, Any]:
    """Return classification metadata; callers decide whether to expose it."""
    source_time = source_timestamp or record.get("updated_at") or record.get("created_at")
    if synthetic:
        classification, reason = "SYNTHETIC", "record is explicitly synthetic"
    elif fixture:
        classification, reason = "FIXTURE", "record is a fixture"
    elif development:
        classification, reason = "DEVELOPMENT", "record is development-only"
    elif source_time is None:
        classification, reason = "UNKNOWN", "no authoritative timestamp"
    elif source_is_current(source_time, max_age_seconds=max_age_seconds, now=now):
        classification, reason = "REAL_CURRENT", "eligible source timestamp is within policy"
    else:
        classification, reason = "REAL_HISTORICAL", "source timestamp is outside policy"
    return {
        "classification": classification,
        "as_of": source_time,
        "source_generated_at": source_timestamp,
        "record_created_at": record.get("created_at"),
        "record_updated_at": record.get("updated_at"),
        "record_resolved_at": record.get("resolved_at") or record.get("completed_at"),
        "currentness_status": "CURRENT" if classification == "REAL_CURRENT" else "NOT_CURRENT",
        "currentness_reason": reason,
        "live_response_eligible": classification == "REAL_CURRENT",
    }


def is_synthetic_record(record: dict[str, Any]) -> bool:
    text = " ".join(str(record.get(key, "")) for key in ("id", "candidate_id", "title", "source"))
    refs = " ".join(str(value) for value in (record.get("source_refs") or []))
    return (
        str(record.get("synthetic", "")).lower() == "true"
        or str(record.get("environment", "")).lower() in {"test", "synthetic", "development"}
        or "item 0" in text.lower()
        or "item 1" in text.lower()
        or "e.com/x" in refs.lower()
    )


def count_by_class(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in CURRENTNESS_CLASSES}
    for record in records:
        name = record.get("classification", "UNKNOWN")
        counts[name if name in counts else "UNKNOWN"] += 1
    return counts
