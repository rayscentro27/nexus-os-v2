"""Thin Nova adapter over shared certified capabilities.

Nova-specific code is responsible ONLY for:
  - recognizing intent (trigger patterns)
  - extracting validated arguments
  - requesting an approved capability via the shared adapter
  - receiving a normalized result
  - preserving safe provenance
  - generating a natural response

All Supabase queries, credential handling, result schemas,
classification logic, and safety controls live in the shared layer.
"""

from __future__ import annotations

import json
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


# ─── Intent Recognition ────────────────────────────────────

def get_nova_capabilities():
    """Return list of capability dicts with trigger patterns for Nova."""
    return [
        {
            "id": "get_runtime_capabilities",
            "name": "Runtime Capabilities",
            "description": "What systems Nova can access",
            "trigger": lambda text: any(w in text for w in [
                "what can you access", "your capabilities", "what do you have access",
                "what systems", "can you access supabase", "your access",
            ]),
        },
        {
            "id": "get_client_count",
            "name": "Client Count",
            "description": "Live client profile counts",
            "trigger": lambda text: any(w in text for w in [
                "client count", "how many clients", "total clients",
                "number of clients", "client profiles",
            ]),
        },
        {
            "id": "resolve_user_identity_by_email",
            "name": "Identity Resolution",
            "description": "Exact email lookup across approved identity sources",
            "trigger": lambda text: (
                any(w in text for w in [
                    "find user", "look up user", "search for user", "check user",
                    "does this email exist", "does the email exist",
                    "is this email registered", "email exist",
                    "identity source", "identity lookup", "check identity",
                    "who is this", "where does this email",
                ])
                or ("@" in text and any(w in text for w in [
                    "exist", "registered", "find", "check", "look up",
                    "who is", "identity", "user", "account", "profile",
                    "login", "tester", "admin", "client",
                ]))
            ),
        },
    ]


# ─── Response Generation ───────────────────────────────────

def generate_nova_provenance_response(capability_id: str, result: Dict[str, Any]) -> str:
    """Generate a human-readable response with provenance from a capability result."""
    status = result.get("status", "unknown")
    source = result.get("source", "unknown")

    if status == "unavailable":
        return (
            f"I can't access that right now — the {source} source isn't available. "
            "This is a governed read access limitation, not a system outage."
        )

    if status == "unauthorized":
        return (
            f"I don't have permission for that capability. "
            f"My approved reads are: {', '.join(sorted(NOVA_ALLOWED_READS))}."
        )

    if status == "error":
        return (
            f"I hit an error trying to read from {source}: {result.get('error', 'unknown')}. "
            "This is governed read access — I can't bypass errors."
        )

    if status == "denied":
        return (
            "Write operations are not permitted. I have read-only access to Supabase. "
            "I can look up existing information but cannot create, modify, or delete anything."
        )

    prov = result.get("provenance", {})

    if capability_id == "get_runtime_capabilities":
        data = result.get("data", {})
        reads = data.get("available_reads", [])
        return (
            f"I have read-only access to {source} through governed capabilities. "
            f"My approved reads are: {', '.join(sorted(reads))}. "
            "I cannot create, edit, or delete anything."
        )

    if capability_id == "get_client_count":
        data = result.get("data", {})
        return (
            f"From the {source} source: {data.get('production_clients', 'unknown')} production clients, "
            f"{data.get('active', 'unknown')} active, "
            f"{data.get('onboarding', 'unknown')} onboarding, "
            f"{data.get('tester_or_certification', 'unknown')} tester/certification. "
            f"This is a live governed read — data retrieved at {prov.get('retrieved_at', 'unknown')}."
        )

    if capability_id == "resolve_user_identity_by_email":
        data = result.get("data", {})
        email = data.get("normalized_email", "unknown")
        exists = data.get("exists_anywhere", False)
        complete = data.get("verification_complete", True)
        classifications = data.get("account_classifications", [])
        sources = data.get("sources", {})

        if not complete:
            failed = [k for k, v in sources.items()
                      if v.get("status") in ("error", "incomplete")]
            return (
                f"I checked the approved identity sources for {email}, but verification "
                f"was not complete. The following sources could not be fully checked: "
                f"{', '.join(failed)}. I cannot confirm whether the email exists."
            )

        if not exists:
            return (
                f"I checked the approved identity sources and did not find {email}."
            )

        parts = [f"I found {email} in the approved identity sources."]
        if classifications:
            parts.append(f"Classifications: {', '.join(classifications)}.")
        source_details = []
        for src_name, src_data in sources.items():
            if src_data.get("exists"):
                source_details.append(f"{src_name}: found")
            else:
                source_details.append(f"{src_name}: not found")
        if source_details:
            parts.append(f"Source details: {'; '.join(source_details)}.")
        return " ".join(parts)

    return f"Capability result from {source}: {json.dumps(result, default=str)[:200]}"


# ─── Capability Execution (thin adapter) ───────────────────

# Requests that look like writes — must be denied
_WRITE_PATTERNS = re.compile(
    r'(create|add|insert|update|delete|remove|disable|enable|invite|'
    r'edit|modify|set|change|revoke|approve|reject)\s+.*'
    r'\b(user|account|profile|record)\b',
    re.IGNORECASE,
)


def execute_nova_capability(
    capability: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a governed read-only capability for Nova.

    Delegates entirely to the shared capability adapter.
    Nova-specific code only handles argument normalization and
    the permission check is enforced in the shared layer.
    """
    args = arguments or {}

    # Reject unregistered capabilities
    if capability not in NOVA_ALLOWED_READS:
        return {
            "status": "unauthorized",
            "capability": capability,
            "error": f"Capability '{capability}' is not in Nova's approved read allowlist.",
            "available_capabilities": sorted(NOVA_ALLOWED_READS),
        }

    # Delegate to shared adapter
    return execute_shared_capability(
        agent_id="hermes_nova",
        capability=capability,
        arguments=args,
    )


def detect_nova_write_request(user_message: str) -> Optional[Dict[str, Any]]:
    """Detect if the user is requesting a write operation."""
    return detect_write_request(user_message)
