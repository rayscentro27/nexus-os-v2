"""Bounded, secret-safe lifecycle records shared by worker and supervisor."""
from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MAX_LIFECYCLE_BYTES = 64 * 1024
_SECRET = re.compile(r"(?i)(password|passwd|token|secret|authorization|api[_-]?key|service[_-]?role[_-]?key)(\s*[:=]\s*)([^\s,;]+)")
_URI_AUTH = re.compile(r"(?i)(https?://[^:/\s]+:)[^@/\s]+@")


def sanitize(value: object, *, limit: int = 500) -> str:
    text = str(value or "")[:max(0, limit)]
    text = _SECRET.sub(r"\1\2<redacted>", text)
    return _URI_AUTH.sub(r"\1<redacted>@", text)


def lifecycle_path(job_id: str, attempt: int | str | None = None) -> Path:
    explicit = os.environ.get("NEXUS_WORKER_LIFECYCLE_PATH")
    if explicit:
        return Path(explicit)
    from nexus_agent_platform.runtime.paths import nexus_research_state_path
    safe_job = re.sub(r"[^A-Za-z0-9_-]", "_", str(job_id))
    safe_attempt = str(attempt or os.environ.get("NEXUS_JOB_ATTEMPT_COUNT") or "unknown")
    return nexus_research_state_path("runtime", "worker_supervision", safe_job,
                                     f"attempt-{safe_attempt}.lifecycle.jsonl")


def emit(job_id: str, stage: str, *, attempt: int | str | None = None,
         worker_id: str | None = None, **details: object) -> dict:
    path = lifecycle_path(job_id, attempt)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "job_id": sanitize(job_id, limit=160), "worker_id": sanitize(worker_id or os.environ.get("NEXUS_WORKER_ID", ""), limit=160),
              "pid": os.getpid(), "stage": sanitize(stage, limit=80),
              "details": {sanitize(key, limit=80): sanitize(value) for key, value in list(details.items())[:20]}}
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+b") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            current = path.read_bytes() if path.exists() else b""
            if len(current) + len(encoded) > MAX_LIFECYCLE_BYTES:
                marker = (json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                    "job_id": sanitize(job_id, limit=160), "worker_id": record["worker_id"],
                    "pid": os.getpid(), "stage": "LIFECYCLE_LOG_TRIMMED", "details": {}},
                    sort_keys=True, separators=(",", ":")) + "\n").encode()
                keep = max(0, MAX_LIFECYCLE_BYTES - len(marker) - len(encoded))
                current = marker + (current[-keep:] if keep else b"")
                if b"\n" in current:
                    current = current[current.find(b"\n") + 1:]
            fd, name = tempfile.mkstemp(prefix="worker-lifecycle-", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(current)
                    handle.write(encoded)
                os.chmod(name, 0o600)
                os.replace(name, path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return record


def last_stage(path: str | Path) -> str | None:
    target = Path(path)
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if value.get("stage") != "LIFECYCLE_LOG_TRIMMED":
                return str(value.get("stage") or "") or None
    except OSError:
        pass
    return None
