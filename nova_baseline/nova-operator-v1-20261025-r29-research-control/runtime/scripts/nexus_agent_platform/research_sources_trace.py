"""Opt-in, local-only attribution for research_sources REST requests.

The trace deliberately records query shape, never query values or payloads.
It is bounded and written outside the repository with owner-only permissions.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

TRACE_PATH = Path.home() / ".nexus/diagnostics/research_sources_trace.jsonl"
MAX_BYTES = 2_000_000
MAX_LINES = 5000
_LOCK = threading.RLock()
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")


def _safe_env(name: str) -> str | None:
    value = os.environ.get(name, "")
    return value if _SAFE_ID.fullmatch(value) else None


def _query_shape(path: str) -> dict:
    parsed = urlsplit(path)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    selected = None
    filters = []
    limit = None
    for key, value in pairs:
        if key == "select":
            selected = [x.split("(", 1)[0].strip()[:64] for x in value.split(",")[:100]]
        elif key == "limit" and value.isdigit():
            limit = min(int(value), 100000)
        elif key not in {"order", "offset", "on_conflict", "columns"}:
            # Keep field/operator only. Filter values can contain PII and are omitted.
            operator = value.split(".", 1)[0] if "." in value else "eq"
            item = {"field": key[:80], "operator": operator[:24]}
            # Only opaque IDs are retained; URL/title/query values are never logged.
            if key in {"id", "source_id", "job_id", "gap_id", "question_id"}:
                candidate = value.split(".", 1)[-1]
                if _SAFE_ID.fullmatch(candidate):
                    item["opaque_id"] = candidate
            filters.append(item)
    return {"table": parsed.path.rstrip("/").split("/")[-1][:64],
            "selected_fields": selected, "limit": limit, "filters": filters[:40]}


def trace_request(method: str, path: str) -> dict | None:
    """Append a safe caller trace when the REST target is research_sources."""
    try:
        if os.environ.get("NEXUS_RESEARCH_SOURCES_TRACE", "1").strip().lower() in {"0", "false", "no", "off"}:
            return
        shape = _query_shape(path)
        if shape["table"] != "research_sources":
            return
        frames = traceback.extract_stack(limit=14)[:-1]
        relevant = [{"module": Path(frame.filename).stem[:80], "function": frame.name[:100],
                     "line": frame.lineno} for frame in frames[-8:]]
        application_frames = [frame for frame in relevant
                              if frame["module"] not in {"research_sources_trace", "supabase_egress_guard", "_supabase", "feeder_runtime"}]
        caller = application_frames[-1] if application_frames else (relevant[-1] if relevant else {"module": "unknown", "function": "unknown"})
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": str(method).upper()[:10],
            "caller_module": caller["module"],
            "caller_function": caller["function"],
            "stack": relevant,
            "query": shape,
            "wake_id": _safe_env("NEXUS_WAKE_ID"),
            "worker_id": _safe_env("NEXUS_WORKER_ID") or _safe_env("NEXUS_EXECUTION_ID"),
            "kernel_phase": _safe_env("NEXUS_KERNEL_PHASE"),
            "job_id": _safe_env("NEXUS_RESEARCH_JOB_ID"),
            "gap_id": _safe_env("NEXUS_RESEARCH_GAP_ID"),
            "source_id": _safe_env("NEXUS_RESEARCH_SOURCE_ID"),
        }
        encoded = (json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n").encode()
        with _LOCK:
            TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(TRACE_PATH.parent, 0o700)
            if TRACE_PATH.exists() and TRACE_PATH.stat().st_size + len(encoded) > MAX_BYTES:
                lines = TRACE_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[-MAX_LINES // 2:]
                fd, name = tempfile.mkstemp(prefix="research-sources-trace-", suffix=".tmp", dir=TRACE_PATH.parent)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(lines) + ("\n" if lines else ""))
                os.chmod(name, 0o600)
                os.replace(name, TRACE_PATH)
            fd = os.open(TRACE_PATH, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "ab") as handle:
                handle.write(encoded)
            os.chmod(TRACE_PATH, 0o600)
        return record
    except Exception:
        # Diagnostics cannot alter workflow availability.
        return None


def clear_trace() -> None:
    """Test-only helper to start a bounded local reproduction cleanly."""
    with _LOCK:
        TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRACE_PATH.write_text("", encoding="utf-8")
        os.chmod(TRACE_PATH, 0o600)
