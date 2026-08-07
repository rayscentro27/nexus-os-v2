"""Nova-owned Supabase adapter — thin wrapper over shared capabilities.

This module provides Nova's read-only Supabase access through the shared
certified capability layer. It does NOT contain:
  - Trigger patterns
  - Pre-model capability interception
  - Response generation that bypasses Nova's brain

Nova's conversational brain decides when to use these tools.
The tools return data. Nova's brain explains the data naturally.
"""

from __future__ import annotations

import logging
import os
import re
import stat
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexus_agent_platform.capabilities.shared import (
    NOVA_ALLOWED_READS,
    _normalize_email,
    detect_write_request,
    execute_shared_capability,
)

log = logging.getLogger(__name__)

# ─── Provenance Store (Nova-scoped) ────────────────────────

_NOVA_STORE_DIR = os.path.expanduser("~/.config/nexus/nova_context")
_NOVA_DEFAULT_TTL = 3600
_NOVA_SCHEMA_VERSION = 1

_UNSAFE_FIELDS = frozenset({
    "credentials", "token", "api_key", "service_role_key", "bot_token",
    "secret", "password", "authorization", "raw_rows", "raw_data",
    "client_name", "client_email", "email_body", "credit_report",
    "trading_position", "research_document", "conversation_full",
    "provider_payload", "stack_trace", "service_role", "supabase_key",
})


def _nova_ensure_store() -> None:
    os.makedirs(_NOVA_STORE_DIR, mode=0o700, exist_ok=True)


def _nova_store_path(chat_id: int) -> str:
    _nova_ensure_store()
    import hashlib
    key = hashlib.sha256(f"nova_{chat_id}".encode()).hexdigest()[:16]
    return os.path.join(_NOVA_STORE_DIR, f"{key}.json")


def _nova_atomic_write(path: str, data: Dict[str, Any]) -> None:
    _nova_ensure_store()
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_nova_conversation(chat_id: int) -> Dict[str, Any]:
    path = _nova_store_path(chat_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if data.get("schema_version", 0) < _NOVA_SCHEMA_VERSION:
        return {}
    expires_at = data.get("expires_at", 0)
    if expires_at and time.time() > expires_at:
        return {}
    return data


def save_nova_conversation(chat_id: int, data: Dict[str, Any]) -> None:
    data["updated_at"] = time.time()
    data["schema_version"] = _NOVA_SCHEMA_VERSION
    if "expires_at" not in data:
        data["expires_at"] = time.time() + _NOVA_DEFAULT_TTL
    _nova_atomic_write(_nova_store_path(chat_id), data)


def save_nova_capability_result(chat_id: int, capability: str,
                                 result: Dict[str, Any]) -> None:
    ctx = load_nova_conversation(chat_id)
    provenance = result.get("provenance", {})
    data = result.get("data", {})

    safe_summary = {}
    if capability == "get_client_count" and isinstance(data, dict):
        for field in ("production_clients", "active", "onboarding",
                       "tester_or_certification"):
            if field in data:
                safe_summary[field] = data[field]
    elif capability == "resolve_user_identity_by_email" and isinstance(data, dict):
        for field in ("normalized_email", "exists_anywhere",
                       "verification_complete", "account_classifications"):
            if field in data:
                safe_summary[field] = data[field]

    for field in _UNSAFE_FIELDS:
        safe_summary.pop(field, None)

    ctx["last_capability"] = capability
    ctx["last_capability_result"] = {
        "capability": capability,
        "status": result.get("status", "unknown"),
        "source": provenance.get("source", "unknown"),
        "source_type": provenance.get("source_type", "unknown"),
        "retrieved_at": provenance.get("retrieved_at", ""),
        "freshness": provenance.get("freshness", "unknown"),
        "access_boundary": "approved read capability only",
        "trace_id": provenance.get("trace_id", ""),
        "safe_summary": safe_summary,
    }
    ctx["last_mode"] = "operational_read"
    save_nova_conversation(chat_id, ctx)


def get_nova_last_capability_result(chat_id: int) -> Optional[Dict[str, Any]]:
    ctx = load_nova_conversation(chat_id)
    return ctx.get("last_capability_result")


def clear_nova_conversation(chat_id: int) -> None:
    path = _nova_store_path(chat_id)
    if os.path.exists(path):
        os.unlink(path)


# ─── Capability Execution (thin adapter) ───────────────────

def execute_nova_capability(
    capability: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a governed read-only capability for Nova.

    Delegates entirely to the shared capability adapter.
    """
    args = arguments or {}

    if capability not in NOVA_ALLOWED_READS:
        return {
            "status": "unauthorized",
            "capability": capability,
            "error": f"Capability '{capability}' is not in Nova's approved read allowlist.",
            "available_capabilities": sorted(NOVA_ALLOWED_READS),
        }

    return execute_shared_capability(
        agent_id="hermes_nova",
        capability=capability,
        arguments=args,
    )


def detect_nova_write_request(user_message: str) -> Optional[Dict[str, Any]]:
    """Detect if the user is requesting a write operation."""
    return detect_write_request(user_message)
