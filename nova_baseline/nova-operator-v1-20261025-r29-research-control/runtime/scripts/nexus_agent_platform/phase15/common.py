"""Shared, side-effect-light helpers for bounded Phase 15 jobs and reports."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATA_RUNTIME = ROOT / "data" / "runtime"
PHASE15_DATA = DATA_RUNTIME / "phase15"
MODERNIZATION_DIR = ROOT / "reports" / "hermes_modernization"
RUNTIME_REPORTS = ROOT / "reports" / "runtime"
RUNTIME_ENV = Path("/Users/raymonddavis/.config/nexus/runtime.env")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def load_jsonl(path: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows[-limit:] if limit is not None else rows


def load_json_lines(path: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    return load_jsonl(path, limit=limit)


def atomic_write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def load_runtime_env() -> dict[str, str]:
    """Load the canonical env file through the existing alias-aware loader."""
    import sys

    ops = ROOT / "scripts" / "ops"
    if str(ops) not in sys.path:
        sys.path.insert(0, str(ops))
    try:
        from nexus_runtime_env import load_runtime_env as load
    except ImportError:
        return {}
    return load()


def ensure_sources_loaded() -> None:
    # Provider/source helpers read their own registries; this phase helper only
    # makes existing secure runtime configuration available in-process.
    load_runtime_env()


def strip_pii(value: str) -> str:
    text = str(value)
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]", text, flags=re.I)
    text = re.sub(r"(?<!\w)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\w)", "[REDACTED_PHONE]", text)
    return text


def refresh_process_ledger(process_id: str, detail: dict[str, Any]) -> dict[str, Any]:
    """Append a compact Phase 15 process receipt without recording secrets."""
    safe = {key: value for key, value in dict(detail).items()
            if not any(secret in key.lower() for secret in ("token", "secret", "password", "credential", "api_key"))}
    row = {"process_id": process_id, "updated_at": utc_now(), **safe}
    path = DATA_RUNTIME / "phase15_process_ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return row
