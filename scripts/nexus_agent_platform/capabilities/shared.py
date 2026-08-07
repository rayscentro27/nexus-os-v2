"""Shared certified capability adapter for Nova.

Provides a single execution boundary that routes Nova requests through
the same canonical handlers used by Hermes.  Nova must never bypass
this module to query Supabase directly.

No write access.  No raw SQL.  No credential exposure.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

log = logging.getLogger(__name__)

# ─── Agent Permission Profiles ─────────────────────────────
# Code-enforced capability allowlists per agent.

NOVA_ALLOWED_READS = frozenset({
    "get_runtime_capabilities",
    "get_client_count",
    "resolve_user_identity_by_email",
})

NOVA_ALLOWED_WRITES: frozenset = frozenset()

HERMES_ALLOWED_READS = frozenset({
    "get_client_count",
    "get_system_status",
    "get_failure_report",
    "get_alpha_status",
    "process_status",
    "process_failures",
    "research_history",
    "opportunities",
    "trading_status",
    "pending_approvals",
})

HERMES_ALLOWED_WRITES = frozenset({
    "send_approved_email",
    "schedule_report",
    "create_work_order",
})

_AGENT_PERMISSIONS: Dict[str, Dict[str, frozenset]] = {
    "hermes_nova": {"reads": NOVA_ALLOWED_READS, "writes": NOVA_ALLOWED_WRITES},
    "nexus_hermes": {"reads": HERMES_ALLOWED_READS, "writes": HERMES_ALLOWED_WRITES},
}


def _check_permission(agent_id: str, capability: str, is_write: bool) -> Optional[str]:
    """Return error message if permission denied, None if allowed."""
    perms = _AGENT_PERMISSIONS.get(agent_id)
    if perms is None:
        return f"Unknown agent: {agent_id}"
    bucket = "writes" if is_write else "reads"
    if capability not in perms[bucket]:
        return (
            f"Capability '{capability}' is not in {agent_id}'s approved "
            f"{'write' if is_write else 'read'} allowlist."
        )
    return None


# ─── Write Detection ───────────────────────────────────────

_WRITE_PATTERNS = re.compile(
    r'(create|add|insert|update|delete|remove|disable|enable|invite|'
    r'edit|modify|set|change|revoke|approve|reject)\s+.*'
    r'\b(user|account|profile|record)\b',
    re.IGNORECASE,
)


_WRITE_USER_PATTERNS = re.compile(
    r'\b(?:add|create|invite|new)\b.*\b(?:user|account|profile|record)\b',
    re.IGNORECASE,
)


def detect_write_request(user_message: str) -> Optional[Dict[str, Any]]:
    """Detect if the user is requesting a write operation."""
    if _WRITE_USER_PATTERNS.search(user_message):
        email_match = re.search(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', user_message
        )
        email = _normalize_email(email_match.group(0)) if email_match else None
        return {
            "requested_action": "create_test_user",
            "target_system": "supabase",
            "arguments": {"email": email},
            "execution_allowed": False,
            "read_available": email is not None,
        }
    return None


# ─── Supabase Client (single shared instance) ─────────────

_shared_session = None


def _supabase_session():
    """Return a shared requests session for Supabase REST API, or None."""
    global _shared_session
    if _shared_session is not None:
        return _shared_session
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
        _shared_session = session
        return session
    except Exception:
        return None


# ─── Email Normalization ───────────────────────────────────

def _normalize_email(raw: str) -> Optional[str]:
    """Normalize an email input to lowercase, stripped, plain format.

    Handles: uppercase, whitespace, mailto: prefix, Markdown mailto links.
    Returns None if the result is not a valid email.
    """
    if not raw or not isinstance(raw, str):
        return None

    text = raw.strip()

    # Strip angle brackets
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1]

    md_match = re.search(r'\[([^\]]+)\]\(mailto:([^)]+)\)', text)
    if md_match:
        text = md_match.group(2)

    if text.lower().startswith("mailto:"):
        text = text[7:]

    text = text.strip().lower()

    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
        return None

    return text


# ─── Shared Handler: Client Count ──────────────────────────

def _handle_client_count(arguments: Optional[Dict[str, Any]] = None,
                         trace_id: str = "") -> Dict[str, Any]:
    """Route to the certified Hermes client-count handler.

    Returns the canonical result envelope with provenance.
    """
    from nexus_agent_platform.agents.hermes import _get_client_count

    query_start = datetime.now(timezone.utc)
    try:
        raw = _get_client_count()
    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        log.error("Shared client_count handler failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_client_count",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_client_count",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
                "error": str(exc),
            },
        }

    query_end = datetime.now(timezone.utc)

    # Normalize Hermes schema into shared canonical schema
    canonical_data = {
        "production_clients": raw.get("production_total", 0),
        "active": raw.get("active", 0),
        "onboarding": raw.get("onboarding", 0),
        "inactive": raw.get("inactive", 0),
        "hidden": raw.get("hidden", 0),
        "tester_or_certification": raw.get("tester_or_certification", 0),
        "all_profiles": raw.get("all_profiles", 0),
    }

    existing_prov = raw.get("provenance", {})
    provenance = {
        "capability": "get_client_count",
        "status": existing_prov.get("status", "success"),
        "source": existing_prov.get("source", "supabase"),
        "source_type": existing_prov.get("source_type", "live_governed_read"),
        "retrieved_at": existing_prov.get("retrieved_at", query_end.isoformat()),
        "query_start": existing_prov.get("query_start", query_start.isoformat()),
        "query_end": existing_prov.get("query_end", query_end.isoformat()),
        "freshness": existing_prov.get("freshness", "live"),
        "row_count": existing_prov.get("row_count", 0),
        "trace_id": trace_id,
        "handler": "hermes._get_client_count",
        "access_boundary": "approved read capability only",
    }

    return {
        "status": "success",
        "capability": "get_client_count",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": canonical_data,
        "error": raw.get("error"),
        "provenance": provenance,
    }


# ─── Identity Resolution ───────────────────────────────────

# Approved identity sources for exact-email lookup.
# Only sources that actually exist in the codebase Supabase schema.

IDENTITY_SOURCES = {
    "supabase_auth": {
        "source_id": "supabase_auth",
        "handler": "auth_admin_api",
        "available": True,
        "lookup_type": "exact_email",
        "classification_fields": ["email_confirmed_at"],
        "safe_output_fields": ["exists", "email_confirmed"],
    },
    "client_profiles": {
        "source_id": "client_profiles",
        "handler": "rest_table",
        "available": True,
        "lookup_type": "exact_email",
        "classification_fields": ["status", "source", "tenant_id"],
        "safe_output_fields": ["exists", "status", "classification", "tenant"],
    },
}

# Classification rules based on client_profiles.source and tenant_id
_PRODUCION_TENANT = "goclear"
_NON_PROD_PREFIXES = ("tenant_demo_", "tenant-cert-")
_TESTER_SOURCES = ("tester_invitation", "static_import", "synthetic_certification")


def _classify_profile(source: str, tenant_id: str, status: str) -> str:
    """Classify a client_profiles record into a safe classification label."""
    if source in _TESTER_SOURCES:
        return "tester"
    if tenant_id != _PRODUCION_TENANT:
        if any(tenant_id.startswith(p) for p in _NON_PROD_PREFIXES):
            return "certification"
        return "non_production"
    return "production"


def _handle_identity_resolution(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Canonical exact-email identity resolution across approved sources.

    Checks:
      1. Supabase Auth admin API (paginated)
      2. client_profiles table (exact email filter)

    Returns a normalized result with per-source status.
    """
    args = arguments or {}
    raw_email = args.get("email", "")
    normalized = _normalize_email(raw_email)

    if normalized is None:
        return {
            "status": "error",
            "capability": "resolve_user_identity_by_email",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved exact-email identity lookup",
            "data": {
                "normalized_email": None,
                "exists_anywhere": False,
                "verification_complete": False,
                "account_classifications": [],
                "sources": {},
            },
            "error": f"Invalid email format: {raw_email}",
            "provenance": {
                "capability": "resolve_user_identity_by_email",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    query_start = datetime.now(timezone.utc)
    sources: Dict[str, Dict[str, Any]] = {}
    classifications: list = []
    verification_complete = True

    session = _supabase_session()
    if session is None:
        return {
            "status": "unavailable",
            "capability": "resolve_user_identity_by_email",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved exact-email identity lookup",
            "data": {
                "normalized_email": normalized,
                "exists_anywhere": False,
                "verification_complete": False,
                "account_classifications": [],
                "sources": {},
            },
            "error": "Supabase credentials not configured",
            "provenance": {
                "capability": "resolve_user_identity_by_email",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    # ── Source 1: Supabase Auth (paginated) ───────────────
    auth_exists = False
    auth_email_confirmed = False
    auth_complete = True
    try:
        page = 1
        per_page = 200
        max_pages = 10  # safety limit
        while page <= max_pages:
            auth_resp = session.get(
                f"{session._supabase_url}/auth/v1/admin/users",
                params={"page": page, "per_page": per_page},
                timeout=10,
            )
            if not auth_resp.ok:
                sources["supabase_auth"] = {
                    "status": "error",
                    "exists": False,
                    "error": f"Auth API returned {auth_resp.status_code}",
                }
                verification_complete = False
                auth_complete = False
                break

            auth_users = auth_resp.json().get("users", [])
            for user in auth_users:
                if (user.get("email") or "").lower() == normalized:
                    auth_exists = True
                    auth_email_confirmed = user.get("email_confirmed_at") is not None
                    break

            if auth_exists:
                break

            if len(auth_users) < per_page:
                break

            page += 1
        else:
            # Reached max_pages without completing
            sources["supabase_auth"] = {
                "status": "incomplete",
                "exists": False,
                "error": f"Auth lookup incomplete after {max_pages} pages",
            }
            verification_complete = False
            auth_complete = False

        if auth_complete and "supabase_auth" not in sources:
            sources["supabase_auth"] = {
                "status": "success",
                "exists": auth_exists,
                "email_confirmed": auth_email_confirmed if auth_exists else None,
            }
            if auth_exists:
                classifications.append("auth_user")

    except Exception as exc:
        sources["supabase_auth"] = {
            "status": "error",
            "exists": False,
            "error": str(exc),
        }
        verification_complete = False

    # ── Source 2: client_profiles (by client_label) ────────
    # Note: client_profiles has no email column; emails are in client_label.
    profile_exists = False
    profile_classification = None
    try:
        profile_resp = session.get(
            f"{session._supabase_url}/rest/v1/client_profiles",
            params={
                "select": "id,client_label,status,source,tenant_id",
                "client_label": f"eq.{normalized}",
            },
            timeout=10,
        )
        if not profile_resp.ok:
            sources["client_profiles"] = {
                "status": "error",
                "exists": False,
                "error": f"Profile query returned {profile_resp.status_code}",
            }
            verification_complete = False
        else:
            profiles = profile_resp.json()
            if profiles:
                profile_exists = True
                p = profiles[0]
                profile_classification = _classify_profile(
                    p.get("source", ""),
                    p.get("tenant_id", ""),
                    (p.get("status") or "").lower(),
                )
                sources["client_profiles"] = {
                    "status": "success",
                    "exists": True,
                    "classification": profile_classification,
                    "status_value": (p.get("status") or "").lower(),
                }
                classifications.append(profile_classification)
            else:
                sources["client_profiles"] = {
                    "status": "success",
                    "exists": False,
                }
    except Exception as exc:
        sources["client_profiles"] = {
            "status": "error",
            "exists": False,
            "error": str(exc),
        }
        verification_complete = False

    # ── Determine overall status ───────────────────────────
    exists_anywhere = auth_exists or profile_exists
    error_sources = [k for k, v in sources.items() if v.get("status") == "error"]
    incomplete_sources = [k for k, v in sources.items() if v.get("status") == "incomplete"]

    if error_sources or incomplete_sources:
        overall_status = "partial"
    elif exists_anywhere:
        overall_status = "success"
    else:
        overall_status = "success"

    query_end = datetime.now(timezone.utc)

    return {
        "status": overall_status,
        "capability": "resolve_user_identity_by_email",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved exact-email identity lookup",
        "data": {
            "normalized_email": normalized,
            "exists_anywhere": exists_anywhere,
            "verification_complete": verification_complete,
            "account_classifications": sorted(set(classifications)),
            "sources": sources,
        },
        "error": None,
        "provenance": {
            "capability": "resolve_user_identity_by_email",
            "status": overall_status,
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "sources_checked": list(sources.keys()),
            "sources_with_errors": error_sources,
            "sources_incomplete": incomplete_sources,
            "verification_complete": verification_complete,
        },
    }


# ─── Runtime Capabilities ──────────────────────────────────

def _handle_runtime_capabilities(
    agent_id: str,
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return the runtime capability manifest for the requesting agent."""
    now = datetime.now(timezone.utc)
    session = _supabase_session()
    supabase_status = "connected" if session else "unavailable"

    perms = _AGENT_PERMISSIONS.get(agent_id, {"reads": frozenset(), "writes": frozenset()})

    return {
        "status": "success",
        "capability": "get_runtime_capabilities",
        "source": "runtime_capability_registry",
        "source_type": "local_runtime_read",
        "freshness": "live",
        "access_boundary": "approved capabilities only",
        "data": {
            "agent_id": agent_id,
            "connected_systems": {
                "supabase": {
                    "status": supabase_status,
                    "access_level": "read_only",
                    "access_boundary": "approved capabilities only",
                }
            },
            "available_reads": sorted(perms["reads"]),
            "available_actions": sorted(perms["writes"]),
        },
        "error": None,
        "provenance": {
            "capability": "get_runtime_capabilities",
            "status": "success",
            "source": "runtime",
            "source_type": "local_runtime_read",
            "retrieved_at": now.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
        },
    }


# ─── Capability Dispatch ───────────────────────────────────

_CAPABILITY_HANDLERS: Dict[str, Callable] = {
    "get_client_count": lambda args, tid: _handle_client_count(args, tid),
    "resolve_user_identity_by_email": lambda args, tid: _handle_identity_resolution(args, tid),
    "get_runtime_capabilities": None,  # handled specially (needs agent_id)
}

_WRITE_CAPABILITIES: frozenset = frozenset()


def execute_shared_capability(
    agent_id: str,
    capability: str,
    arguments: Optional[Dict[str, Any]] = None,
    conversation_id: str = "",
    trace_id: str = "",
) -> Dict[str, Any]:
    """Execute a certified capability through the shared adapter.

    This is the single execution boundary.  Nova and Hermes must both
    route through here for shared capabilities.

    Returns a normalized capability result envelope.
    """
    if not trace_id:
        trace_id = f"shared_{agent_id}_{capability}_{int(time.time())}"

    is_write = capability in _WRITE_CAPABILITIES

    # Permission check
    perm_err = _check_permission(agent_id, capability, is_write)
    if perm_err:
        return {
            "status": "unauthorized",
            "capability": capability,
            "source": "permission_registry",
            "source_type": "local_runtime_read",
            "freshness": "live",
            "access_boundary": "approved capability only",
            "data": {},
            "error": perm_err,
            "provenance": {
                "capability": capability,
                "status": "unauthorized",
                "source": "permission_registry",
                "source_type": "local_runtime_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "trace_id": trace_id,
            },
        }

    # Write detection
    raw_text = (arguments or {}).get("raw_text", "") or ""
    if raw_text and _WRITE_PATTERNS.search(str(raw_text)):
        return {
            "status": "denied",
            "capability": capability,
            "source": "write_detector",
            "source_type": "local_runtime_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": "Write operations are not permitted.",
            "requested_action": "write",
            "execution_allowed": False,
            "provenance": {
                "capability": capability,
                "status": "denied",
                "source": "write_detector",
                "source_type": "local_runtime_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "trace_id": trace_id,
            },
        }

    # Special handler: runtime_capabilities needs agent_id
    if capability == "get_runtime_capabilities":
        return _handle_runtime_capabilities(agent_id, arguments, trace_id)

    # Standard handler dispatch
    handler = _CAPABILITY_HANDLERS.get(capability)
    if handler is None:
        return {
            "status": "unavailable",
            "capability": capability,
            "source": "capability_registry",
            "source_type": "local_runtime_read",
            "freshness": "live",
            "access_boundary": "approved capability only",
            "data": {},
            "error": f"No shared handler registered for '{capability}'.",
            "provenance": {
                "capability": capability,
                "status": "unavailable",
                "source": "capability_registry",
                "source_type": "local_runtime_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "trace_id": trace_id,
            },
        }

    try:
        result = handler(arguments, trace_id)
        # Ensure trace_id is in provenance
        prov = result.get("provenance", {})
        if trace_id:
            prov["trace_id"] = trace_id
            result["provenance"] = prov
        return result
    except Exception as exc:
        log.error("Shared capability %s failed for %s: %s", capability, agent_id, exc)
        return {
            "status": "error",
            "capability": capability,
            "source": "shared_capability_adapter",
            "source_type": "local_runtime_read",
            "freshness": "unknown",
            "access_boundary": "approved capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": capability,
                "status": "error",
                "source": "shared_capability_adapter",
                "source_type": "local_runtime_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }
