"""Persistent operational context store for Nexus Hermes.

Survives --once worker process exits. Stores only safe metadata needed for
conversation continuity and provenance follow-ups. One record per authorized
conversation, keyed by hashed conversation ID.

No credentials, PII, tokens, or raw database rows are persisted.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import time
from typing import Any, Dict, Optional

_STORE_DIR = os.path.expanduser("~/.config/nexus/hermes_context")
_DEFAULT_TTL = 3600  # 1 hour


def _ensure_store() -> None:
    os.makedirs(_STORE_DIR, mode=0o700, exist_ok=True)


def _conversation_key(chat_id: int) -> str:
    """Hash a chat ID to a safe file key."""
    raw = f"hermes_{chat_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _store_path(chat_id: int) -> str:
    _ensure_store()
    return os.path.join(_STORE_DIR, f"{_conversation_key(chat_id)}.json")


def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically using a temp file + rename."""
    _ensure_store()
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_conversation(chat_id: int) -> Dict[str, Any]:
    """Load persisted conversation context. Returns empty dict if missing/expired."""
    path = _store_path(chat_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    # Check expiry
    expires_at = data.get("expires_at", 0)
    if expires_at and time.time() > expires_at:
        return {}
    return data


def save_conversation(chat_id: int, data: Dict[str, Any]) -> None:
    """Persist conversation context atomically with 0600 permissions."""
    data["updated_at"] = time.time()
    if "expires_at" not in data:
        data["expires_at"] = time.time() + _DEFAULT_TTL
    _atomic_write(_store_path(chat_id), data)


def save_capability_result(chat_id: int, capability: str, result: Dict[str, Any]) -> None:
    """Save a capability result with provenance to the conversation store."""
    ctx = load_conversation(chat_id)

    # Build safe summary — no PII, no raw rows
    provenance = result.get("provenance", {})
    data = result.get("data", {})
    safe_summary = {}
    if capability == "get_client_count":
        safe_summary = {
            "production_clients": data.get("production_total", 0),
            "active": data.get("active", 0),
            "onboarding": data.get("onboarding", 0),
            "tester_or_certification": data.get("tester_or_certification", 0),
        }

    ctx["last_capability"] = capability
    ctx["last_capability_result"] = {
        "capability": capability,
        "result_id": provenance.get("trace_id", ""),
        "status": result.get("status", "unknown"),
        "source": provenance.get("source", "unknown"),
        "source_type": provenance.get("source_type", "unknown"),
        "retrieved_at": provenance.get("retrieved_at", ""),
        "freshness": provenance.get("freshness", "unknown"),
        "query_target": provenance.get("query_target", ""),
        "filters": provenance.get("filters", {}),
        "access_boundary": "certified capability only",
        "trace_id": provenance.get("trace_id", ""),
        "safe_summary": safe_summary,
    }
    ctx["last_mode"] = "operational_read"
    ctx["last_topic"] = capability.replace("_", " ")
    save_conversation(chat_id, ctx)


def save_mode_result(chat_id: int, mode: str, capability: Optional[str],
                     response: str) -> None:
    """Save mode and capability info after any graph execution."""
    ctx = load_conversation(chat_id)
    ctx["last_mode"] = mode
    if capability:
        ctx["last_capability"] = capability
    ctx["last_response_preview"] = response[:200] if response else ""
    save_conversation(chat_id, ctx)


def get_last_capability_result(chat_id: int) -> Optional[Dict[str, Any]]:
    """Get the last capability result for provenance follow-ups."""
    ctx = load_conversation(chat_id)
    return ctx.get("last_capability_result")


def clear_conversation(chat_id: int) -> None:
    """Clear a conversation store."""
    path = _store_path(chat_id)
    if os.path.exists(path):
        os.unlink(path)


def cleanup_expired() -> int:
    """Remove expired conversation files. Returns count removed."""
    _ensure_store()
    removed = 0
    now = time.time()
    for fname in os.listdir(_STORE_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(_STORE_DIR, fname)
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get("expires_at", 0) < now:
                os.unlink(path)
                removed += 1
        except (json.JSONDecodeError, OSError):
            pass
    return removed
