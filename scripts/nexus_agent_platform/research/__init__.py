"""Deterministic research helpers used by Alpha scouting workflows."""

from .open_source_scout import (
    OPEN_SOURCE_SCOUT_CANDIDATES,
    build_open_source_scout_report,
    build_compact_delta,
    dedupe_source_records,
    normalize_source_record,
    run_open_source_scout,
)

__all__ = [
    "OPEN_SOURCE_SCOUT_CANDIDATES",
    "build_open_source_scout_report",
    "build_compact_delta",
    "dedupe_source_records",
    "normalize_source_record",
    "run_open_source_scout",
]
