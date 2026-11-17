"""Bounded, session-scoped acceptance evidence for Nova Telegram turns.

This module is observational only. It does not select routes, execute tools,
or alter a user-visible response. Acceptance records are written only when a
valid acceptance session ID is explicitly active.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
MAX_SESSION_BYTES = 2 * 1024 * 1024
MAX_SESSION_RECORDS = 100

TURN_FIELDS = (
    "intent_class", "resolved_capability", "resolved_engine", "operation_class",
    "used_existing_verified_result", "referent_result_id", "request_id", "correlation_id",
    "engine_call_count", "job_id", "new_objective_created", "new_job_created", "mutation_count",
    "approval_required", "receipt_ids", "provenance_refs", "delivery_state",
    "telegram_message_id", "trace_id",
)


def _process_start_time() -> str:
    """Read this process start from procfs without external commands."""
    try:
        stat = Path("/proc/self/stat").read_text(encoding="ascii").rpartition(")")[2].split()
        start_ticks = int(stat[19])
        ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        uptime = float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
        seconds_ago = max(0.0, uptime - start_ticks / ticks_per_second)
        started = datetime.now(timezone.utc).timestamp() - seconds_ago
        return datetime.fromtimestamp(started, timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, ValueError, IndexError, KeyError, ZeroDivisionError):
        return "UNAVAILABLE"


def release_identity(release_root: Path, *, code_root: str = "", pid: int | None = None,
                     process_start_time: str | None = None) -> dict[str, Any]:
    """Return exact process/release identity; hash is the packaged manifest hash."""
    root = release_root.expanduser().resolve()
    manifest = root / "RELEASE_MANIFEST.sha256"
    try:
        manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    except OSError:
        manifest_hash = "UNAVAILABLE"
    return {
        "active_release": str(root),
        "active_release_hash": manifest_hash,
        "code_root": str(code_root or "UNAVAILABLE"),
        "process_pid": int(pid if pid is not None else os.getpid()),
        "process_start_time": process_start_time or _process_start_time(),
    }


def release_root_from_entrypoint(entrypoint: str | Path) -> Path:
    """Derive a release root only from a release-layout worker entrypoint."""
    path = Path(entrypoint).expanduser().resolve()
    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index] == "releases" and index + 1 < len(parts):
            return Path(*parts[: index + 2])
    return path.parent.parent.parent


def validate_session_id(session_id: str) -> str:
    value = str(session_id or "")
    if not SESSION_ID_RE.fullmatch(value):
        raise ValueError("INVALID_ACCEPTANCE_SESSION_ID")
    return value


def _list_or_unknown(value: Any) -> list[str] | None:
    if value is None:
        return None
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [str(item)[:200] for item in list(values)[:50] if item not in (None, "")]


def build_acceptance_record(*, update_id: Any, user_message: str, nova_response: str,
                            session_id: str, identity: dict[str, Any],
                            fields: dict[str, Any], processed_at: str | None = None) -> dict[str, Any]:
    """Build the fixed-schema record. Unknown values stay explicit as null."""
    session = validate_session_id(session_id)
    safe_fields = dict(fields or {})
    intent = str(safe_fields.get("intent_class") or "").upper()
    casual = intent in {"CASUAL_CONVERSATION", "GREETING", "SMALL_TALK"}
    record: dict[str, Any] = {
        "acceptance_session_id": session,
        "update_id": str(update_id),
        "user_message": str(user_message or "")[:4000],
        "nova_response": str(nova_response or "")[:8000],
        "processed_at": processed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **{key: identity.get(key, "UNAVAILABLE") for key in (
            "active_release", "active_release_hash", "code_root", "process_pid", "process_start_time")},
    }
    for key in TURN_FIELDS:
        if key == "trace_id":
            record[key] = safe_fields.get(key)
        elif key in {"receipt_ids", "provenance_refs", "resolved_capability", "telegram_message_id"}:
            record[key] = _list_or_unknown(safe_fields.get(key))
        elif key == "engine_call_count":
            record[key] = 0 if casual and safe_fields.get(key) is None else safe_fields.get(key)
        elif key == "new_objective_created":
            record[key] = "NO" if casual and safe_fields.get(key) is None else safe_fields.get(key)
        elif key == "new_job_created":
            record[key] = "NO" if casual and safe_fields.get(key) is None else safe_fields.get(key)
        elif key == "mutation_count":
            record[key] = 0 if casual and safe_fields.get(key) is None else safe_fields.get(key)
        else:
            record[key] = safe_fields.get(key)
    return record


class AcceptanceSessionWriter:
    """Append/read a single session file; never enumerate the evidence root."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, session_id: str) -> Path:
        session = validate_session_id(session_id)
        return self.root / f"{session}.jsonl"

    def append(self, record: dict[str, Any]) -> None:
        session = validate_session_id(str(record.get("acceptance_session_id") or ""))
        path = self._path(session)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)

    def read(self, session_id: str, *, limit: int = MAX_SESSION_RECORDS) -> list[dict[str, Any]]:
        path = self._path(session_id)
        if not 1 <= int(limit) <= MAX_SESSION_RECORDS:
            raise ValueError("INVALID_ACCEPTANCE_SESSION_LIMIT")
        try:
            if path.stat().st_size > MAX_SESSION_BYTES:
                raise ValueError("ACCEPTANCE_SESSION_FILE_TOO_LARGE")
            lines = path.read_text(encoding="utf-8").splitlines()[-int(limit):]
        except FileNotFoundError:
            return []
        rows = []
        for line in lines:
            if len(line.encode("utf-8")) > 65536:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("acceptance_session_id") == str(session_id):
                rows.append(row)
        return rows
