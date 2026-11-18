"""Research Room shadow entry adapters. Automated YouTube events stay disabled."""
from __future__ import annotations

from typing import Any


MANUAL_SHADOW_ENTRY = True
AUTOMATED_YOUTUBE_WATCHER = False


def open_manual_shadow(worker: Any, *, case_id: str, objective: str,
                       source_url: str | None = None, source_type: str = "UNKNOWN",
                       metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return worker.open_case(case_id=case_id, objective=objective, source_url=source_url,
                            source_type=source_type, metadata=metadata)


def youtube_event_shadow(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {"status": "NOT_ACTIVE", "reason": "AUTOMATED_YOUTUBE_WATCHER_DISABLED"}
