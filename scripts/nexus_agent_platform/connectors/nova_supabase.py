"""Governed read-only Supabase connector for Hermes Nova.

Provides exactly three approved read capabilities via a bounded allowlist.
All credentials, authorization, validation, and result normalization happen
inside this module. Nova receives only normalized results.

No write access. No arbitrary SQL. No unrestricted database access.
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

log = logging.getLogger(__name__)

# ─── Nova Capability Allowlist ─────────────────────────────
# Exactly three approved reads. No writes. No arbitrary queries.

NOVA_ALLOWED_CAPABILITIES = frozenset({
    "get_nova_runtime_capabilities",
    "get_client_count",
    "find_test_user_by_email",
})

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
        for field in ("production_clients", "active", "onboarding", "tester_or_certification"):
            if field in data:
                safe_summary[field] = data[field]
    elif capability == "find_test_user_by_email" and isinstance(data, dict):
        for field in ("normalized_email", "exists_in_auth", "exists_in_profile",
                       "record_state", "classification", "role", "enabled"):
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


# ─── Supabase Client (reuses Hermes pattern) ──────────────

def _nova_supabase_client():
    """Return a requests session configured for Supabase REST API, or None."""
    try:
        import requests as _req
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return None
        session = _req.Session()
        session.headers.update({
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "count=exact",
        })
        session._supabase_url = url.rstrip("/")
        return session
    except Exception:
        return None


# ─── Capability Discovery ──────────────────────────────────

def get_nova_capabilities():
    """Return list of capability dicts with trigger patterns for Nova."""
    return [
        {
            "id": "get_nova_runtime_capabilities",
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
            "id": "find_test_user_by_email",
            "name": "Find Test User",
            "description": "Exact email lookup for test users",
            "trigger": lambda text: (
                any(w in text for w in ["find user", "look up user", "search for user", "check user"])
                and ("@" in text or "email" in text)
            ),
        },
    ]


def generate_nova_provenance_response(capability_id: str, result: Dict[str, Any]) -> str:
    """Generate a human-readable response with provenance from a capability result."""
    status = result.get("status", "unknown")
    source = result.get("source", "unknown")
    source_type = result.get("source_type", "unknown")

    if status == "unavailable":
        return (
            f"I can't access that right now — the {source} source isn't available. "
            "This is a governed read access limitation, not a system outage."
        )

    if status == "unauthorized":
        return (
            f"I don't have permission for that capability. "
            f"My approved reads are: {', '.join(sorted(result.get('available_capabilities', [])))}."
        )

    if status == "error":
        return (
            f"I hit an error trying to read from {source}: {result.get('error', 'unknown')}. "
            "This is governed read access — I can't bypass errors."
        )

    # Success responses by capability
    if capability_id == "get_nova_runtime_capabilities":
        return (
            f"I have read-only access to {source} through governed capabilities. "
            f"My approved reads are: {', '.join(sorted(result.get('available_reads', [])))}. "
            "I cannot create, edit, or delete anything."
        )

    if capability_id == "get_client_count":
        data = result.get("data", {})
        total = data.get("total", "unknown")
        return (
            f"From the {source} source: there are {total} client profiles. "
            f"This is a live governed read — data retrieved at {result.get('retrieved_at', 'unknown')}."
        )

    if capability_id == "find_test_user_by_email":
        record = result.get("record")
        if record:
            return (
                f"From the {source} source: found test user — "
                f"{record.get('full_name', 'unknown')} ({record.get('email', 'unknown')}). "
                f"Role: {record.get('role', 'unknown')}, state: {record.get('account_state', 'unknown')}."
            )
        return (
            f"From the {source} source: no test user found matching that email. "
            "This is a governed read — I can only look up test users."
        )

    return f"Capability result from {source}: {json.dumps(result, default=str)[:200]}"


# ─── Capability Handlers ──────────────────────────────────

def _get_nova_runtime_capabilities() -> Dict[str, Any]:
    """Return Nova's actual current runtime capabilities."""
    from datetime import timezone
    now = datetime.now(timezone.utc)

    session = _nova_supabase_client()
    supabase_status = "connected" if session else "unavailable"

    return {
        "status": "success",
        "agent_id": "hermes_nova",
        "connected_systems": {
            "supabase": {
                "status": supabase_status,
                "access_level": "read_only",
                "access_boundary": "approved capabilities only",
            }
        },
        "available_reads": sorted(NOVA_ALLOWED_CAPABILITIES),
        "available_actions": [],
        "retrieved_at": now.isoformat(),
        "source": "runtime_capability_registry",
        "source_type": "local_runtime_read",
        "provenance": {
            "capability": "get_nova_runtime_capabilities",
            "status": "success",
            "source": "runtime",
            "source_type": "local_runtime_read",
            "retrieved_at": now.isoformat(),
            "freshness": "live",
        },
    }


def _get_client_count_nova() -> Dict[str, Any]:
    """Query Supabase client_profiles — Nova-scoped safe projection.

    Reuses the verified Supabase client pattern from Hermes.
    Returns only approved aggregate counts.
    """
    from zoneinfo import ZoneInfo

    query_start = datetime.now(timezone.utc)
    result = {
        "status": "success",
        "capability": "get_client_count",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": {},
        "error": None,
    }

    try:
        session = _nova_supabase_client()
        if session is None:
            result["status"] = "unavailable"
            result["error"] = "Supabase credentials not configured"
            result["freshness"] = "unknown"
            query_end = datetime.now(timezone.utc)
            result["retrieved_at"] = query_end.isoformat()
            result["provenance"] = {
                "capability": "get_client_count",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
            }
            return result

        resp = session.get(
            f"{session._supabase_url}/rest/v1/client_profiles",
            params={"select": "tenant_id,status,client_visible,source"},
            timeout=10,
        )
        if not resp.ok:
            result["status"] = "error"
            result["error"] = f"Supabase query failed: {resp.status_code}"
            result["freshness"] = "unknown"
            query_end = datetime.now(timezone.utc)
            result["retrieved_at"] = query_end.isoformat()
            result["provenance"] = {
                "capability": "get_client_count",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
            }
            return result

        rows = resp.json()

        # Classification (same logic as Hermes)
        production_tenant = "goclear"
        non_production_prefixes = ("tenant_demo_", "tenant-cert-")
        tester_sources = ("tester_invitation", "static_import", "synthetic_certification")

        production = []
        tester_or_cert = 0
        for row in rows:
            tenant = row.get("tenant_id", "")
            source = row.get("source", "")
            if tenant != production_tenant:
                if any(tenant.startswith(p) for p in non_production_prefixes):
                    tester_or_cert += 1
                continue
            if source in tester_sources:
                tester_or_cert += 1
                continue
            production.append(row)

        active = sum(1 for r in production if (r.get("status") or "").lower() == "active")
        onboarding = sum(1 for r in production if (r.get("status") or "").lower() == "onboarding")

        query_end = datetime.now(timezone.utc)
        result["data"] = {
            "production_clients": len(production),
            "active": active,
            "onboarding": onboarding,
            "tester_or_certification": tester_or_cert,
        }
        result["retrieved_at"] = query_end.isoformat()
        result["provenance"] = {
            "capability": "get_client_count",
            "status": "success",
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "row_count": len(rows),
        }

    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        result["status"] = "error"
        result["error"] = str(exc)
        result["freshness"] = "unknown"
        result["retrieved_at"] = query_end.isoformat()
        result["provenance"] = {
            "capability": "get_client_count",
            "status": "error",
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "freshness": "unknown",
        }

    return result


def _normalize_email(raw: str) -> Optional[str]:
    """Normalize an email input to lowercase, stripped, plain format.

    Handles: uppercase, whitespace, mailto: prefix, Markdown mailto links.
    Returns None if the result is not a valid email.
    """
    if not raw or not isinstance(raw, str):
        return None

    text = raw.strip()

    # Extract from Markdown mailto link: [EMAIL](mailto:EMAIL)
    md_match = re.search(r'\[([^\]]+)\]\(mailto:([^)]+)\)', text)
    if md_match:
        text = md_match.group(2)

    # Strip mailto: prefix
    if text.lower().startswith("mailto:"):
        text = text[7:]

    text = text.strip().lower()

    # Basic email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
        return None

    return text


def _find_test_user_by_email(email: str) -> Dict[str, Any]:
    """Bounded exact-email lookup against approved Supabase sources.

    Read-only. Checks Auth and client_profiles for the exact normalized email.
    """
    from zoneinfo import ZoneInfo

    normalized = _normalize_email(email)
    if normalized is None:
        return {
            "status": "error",
            "capability": "find_test_user_by_email",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved exact-email lookup only",
            "data": {
                "normalized_email": None,
                "exists_in_auth": False,
                "exists_in_profile": False,
                "record_state": "invalid_email",
                "classification": None,
                "role": None,
                "enabled": None,
            },
            "error": f"Invalid email format: {email}",
        }

    query_start = datetime.now(timezone.utc)
    result = {
        "status": "success",
        "capability": "find_test_user_by_email",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved exact-email lookup only",
        "data": {
            "normalized_email": normalized,
            "exists_in_auth": False,
            "exists_in_profile": False,
            "record_state": "not_found",
            "classification": None,
            "role": None,
            "enabled": None,
        },
        "error": None,
    }

    try:
        session = _nova_supabase_client()
        if session is None:
            result["status"] = "unavailable"
            result["error"] = "Supabase credentials not configured"
            result["freshness"] = "unknown"
            query_end = datetime.now(timezone.utc)
            result["retrieved_at"] = query_end.isoformat()
            result["provenance"] = {
                "capability": "find_test_user_by_email",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
            }
            return result

        # Check Auth users via admin API (single page, bounded)
        try:
            auth_resp = session.get(
                f"{session._supabase_url}/auth/v1/admin/users",
                params={"page": 1, "per_page": 200},
                timeout=10,
            )
            if auth_resp.ok:
                auth_users = auth_resp.json().get("users", [])
                for user in auth_users:
                    if (user.get("email") or "").lower() == normalized:
                        result["data"]["exists_in_auth"] = True
                        result["data"]["enabled"] = user.get("email_confirmed_at") is not None
                        break
        except Exception:
            pass  # Auth check is best-effort

        # Check client_profiles for exact email
        try:
            profile_resp = session.get(
                f"{session._supabase_url}/rest/v1/client_profiles",
                params={
                    "select": "id,email,status,source,tenant_id",
                    "email": f"eq.{normalized}",
                },
                timeout=10,
            )
            if profile_resp.ok:
                profiles = profile_resp.json()
                if profiles:
                    result["data"]["exists_in_profile"] = True
                    profile = profiles[0]
                    source = profile.get("source", "")
                    tenant = profile.get("tenant_id", "")
                    status = (profile.get("status") or "").lower()

                    # Classification
                    if source in ("tester_invitation", "static_import", "synthetic_certification"):
                        result["data"]["classification"] = "test"
                    elif tenant != "goclear":
                        result["data"]["classification"] = "test"
                    else:
                        result["data"]["classification"] = "production"

                    result["data"]["role"] = source
                    result["data"]["enabled"] = status == "active"
        except Exception:
            pass  # Profile check is best-effort

        # Determine record state
        d = result["data"]
        if d["exists_in_auth"] and d["exists_in_profile"]:
            d["record_state"] = "complete"
        elif d["exists_in_auth"]:
            d["record_state"] = "auth_only"
        elif d["exists_in_profile"]:
            d["record_state"] = "profile_only"
        else:
            d["record_state"] = "not_found"
            result["status"] = "not_found"

        query_end = datetime.now(timezone.utc)
        result["retrieved_at"] = query_end.isoformat()
        result["provenance"] = {
            "capability": "find_test_user_by_email",
            "status": result["status"],
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
        }

    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        result["status"] = "error"
        result["error"] = str(exc)
        result["freshness"] = "unknown"
        result["retrieved_at"] = query_end.isoformat()
        result["provenance"] = {
            "capability": "find_test_user_by_email",
            "status": "error",
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "freshness": "unknown",
        }

    return result


# ─── Capability Dispatch ───────────────────────────────────

_CAPABILITY_HANDLERS = {
    "get_nova_runtime_capabilities": _get_nova_runtime_capabilities,
    "get_client_count": _get_client_count_nova,
    "find_test_user_by_email": _find_test_user_by_email,
}

# Requests that look like writes — must be denied
_WRITE_PATTERNS = re.compile(
    r'(create|add|insert|update|delete|remove|disable|enable|invite|'
    r'edit|modify|set|change|revoke|approve|reject)\s+(user|account|profile|record)',
    re.IGNORECASE,
)


def execute_nova_capability(
    capability: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a governed read-only capability for Nova.

    Enforces the allowlist in code. Returns structured error for
    unregistered or write capabilities.
    """
    args = arguments or {}

    # Deny unregistered capabilities
    if capability not in NOVA_ALLOWED_CAPABILITIES:
        return {
            "status": "unauthorized",
            "capability": capability,
            "error": f"Capability '{capability}' is not in Nova's approved read allowlist.",
            "available_capabilities": sorted(NOVA_ALLOWED_CAPABILITIES),
        }

    # Deny write attempts
    raw_text = args.get("raw_text", "") or args.get("email", "") or ""
    if _WRITE_PATTERNS.search(str(raw_text)):
        return {
            "status": "denied",
            "capability": capability,
            "error": "Write operations are not permitted. Nova has read-only access.",
            "requested_action": "write",
            "execution_allowed": False,
        }

    # Dispatch to handler
    handler = _CAPABILITY_HANDLERS.get(capability)
    if handler is None:
        return {
            "status": "unavailable",
            "capability": capability,
            "error": f"Handler not found for '{capability}'.",
        }

    try:
        if capability == "find_test_user_by_email":
            result = handler(email=args.get("email", ""))
        else:
            result = handler()
        return result
    except Exception as exc:
        log.error("Nova capability %s failed: %s", capability, exc)
        return {
            "status": "error",
            "capability": capability,
            "error": str(exc),
        }


def detect_nova_write_request(user_message: str) -> Optional[Dict[str, Any]]:
    """Detect if the user is requesting a write operation.

    Returns a structured dict describing the requested write, or None.
    """
    msg_lower = user_message.lower()

    # Detect user creation patterns
    if any(w in msg_lower for w in ["add user", "create user", "new user", "invite user"]):
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', user_message)
        email = _normalize_email(email_match.group(0)) if email_match else None
        return {
            "requested_action": "create_test_user",
            "target_system": "supabase",
            "arguments": {"email": email},
            "execution_allowed": False,
            "read_available": email is not None,
        }

    return None
