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

from nexus_agent_platform.capabilities.nexus_knowledge import (
    get_nexus_overview as _nk_get_nexus_overview,
    get_nexus_architecture as _nk_get_nexus_architecture,
    get_agent_registry as _nk_get_agent_registry,
    get_agent_details as _nk_get_agent_details,
    get_tool_registry as _nk_get_tool_registry,
    get_capability_registry as _nk_get_capability_registry,
    get_process_registry_live as _nk_get_process_registry_live,
    get_process_details as _nk_get_process_details,
    get_report_index_live as _nk_get_report_index_live,
    get_latest_reports_live as _nk_get_latest_reports_live,
    get_recent_activity_live as _nk_get_recent_activity_live,
)

# ─── Agent Permission Profiles ─────────────────────────────
# Code-enforced capability allowlists per agent.

NOVA_ALLOWED_READS = frozenset({
    "get_runtime_capabilities",
    "get_client_count",
    "resolve_user_identity_by_email",
    "general_search",
    "get_system_health",
    "get_pending_approvals",
    "get_recent_research",
    "get_opportunities",
    "get_client_profile",
    "get_funding_readiness",
    "get_operational_summary",
    # Nexus Knowledge Layer
    "get_nexus_overview",
    "get_agent_registry",
    "get_agent_details",
    "get_tool_registry",
    "get_capability_registry",
    "get_process_registry",
    "get_process_details",
    "get_report_index",
    "get_latest_reports",
    "get_recent_activity",
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


# ─── General Search (approved tables only) ──────────────────

# Approved tables for read-only search. Each entry:
#   (table_name, searchable_columns, description)
_APPROVED_SEARCH_TABLES = [
    ("client_profiles", ["client_label", "legal_name", "business_name"], "Client profiles"),
    ("nexus_process_definitions", ["name"], "Process/webhook definitions"),
]


def _handle_general_search(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Read-only search across approved Supabase tables.

    Searches approved tables for keyword matches. Returns safe results only.
    No write access. No arbitrary tables. No PII beyond what is needed.
    """
    args = arguments or {}
    query = args.get("query", "")
    if not query:
        return {
            "status": "error",
            "capability": "general_search",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": "No search query provided.",
            "provenance": {
                "capability": "general_search",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    session = _supabase_session()
    if session is None:
        return {
            "status": "unavailable",
            "capability": "general_search",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": "Supabase credentials not configured.",
            "provenance": {
                "capability": "general_search",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    query_start = datetime.now(timezone.utc)
    search_terms = re.findall(r'\b[a-zA-Z]{3,}\b', query)
    if not search_terms:
        search_terms = [query]

    results = []
    sources_searched = []

    for table, columns, description in _APPROVED_SEARCH_TABLES:
        sources_searched.append(table)
        try:
            for term in search_terms[:3]:
                for col in columns:
                    resp = session.get(
                        f"{session._supabase_url}/rest/v1/{table}",
                        params={
                            "select": f"id,{col},status,source,tenant_id",
                            col: f"ilike.*{term}*",
                            "limit": 5,
                        },
                        timeout=10,
                    )
                    if resp.ok:
                        for row in resp.json():
                            safe_match = {
                                "source": table,
                                "column": col,
                                "match": row.get(col, ""),
                                "status": row.get("status", ""),
                                "type": description,
                            }
                            results.append(safe_match)
        except Exception as exc:
            log.warning("General search failed for table %s: %s", table, exc)

    query_end = datetime.now(timezone.utc)

    return {
        "status": "success" if results else "not_found",
        "capability": "general_search",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": {
            "matches": results[:10],
            "sources_searched": sources_searched,
            "match_count": len(results),
        },
        "error": None,
        "provenance": {
            "capability": "general_search",
            "status": "success" if results else "not_found",
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "tables_searched": sources_searched,
            "search_terms": search_terms[:3],
        },
    }


# ─── Shared Handler: System Health ──────────────────────────

def _handle_system_health(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Aggregate system health from process registry, heartbeat, and process status.

    Combines local JSON file reads (system_status, failure_report) with
    Supabase process status into a single health summary.

    Status semantics:
    - active_services: processes confirmed running
    - degraded_services: processes with POSITIVE evidence of degradation
    - failed_services: processes with POSITIVE evidence of failure
    - unknown_services: processes where status could not be determined
    - overall_status: healthy only if all sources succeed and no failures
    """
    query_start = datetime.now(timezone.utc)
    health_data: Dict[str, Any] = {
        "overall_status": "unknown",
        "active_services": 0,
        "degraded_services": 0,
        "failed_services": 0,
        "unknown_services": 0,
        "recent_failures": [],
        "important_warnings": [],
        "sources_checked": [],
        "source_statuses": {},
        "verification_complete": False,
    }
    source_errors: list = []
    total_services = 0

    # Source 1: Process registry (local JSON)
    source_1_ok = False
    try:
        from nexus_agent_platform.agents.hermes import _get_system_status
        raw = _get_system_status()
        working = raw.get("working", "")
        if "Unable to read" in working:
            health_data["source_statuses"]["process_registry"] = "unavailable"
            source_errors.append(f"process_registry: {raw.get('needs_attention', 'unknown')}")
        else:
            health_data["sources_checked"].append("process_registry")
            health_data["source_statuses"]["process_registry"] = "success"
            source_1_ok = True
            if "/" in working:
                parts = working.split("/")
                try:
                    active = int(parts[0].strip())
                    total = int(parts[1].split()[0].strip())
                    health_data["active_services"] = active
                    total_services = total
                    # Non-running processes are unknown, NOT degraded
                    # Degradation requires positive evidence (from failure_report or process_failures)
                    health_data["unknown_services"] = max(0, total - active)
                except (ValueError, IndexError):
                    pass
            detail = raw.get("detail", "")
            if detail:
                health_data["important_warnings"].extend(
                    [line.strip() for line in detail.split("\n") if line.strip()]
                )
    except Exception as exc:
        health_data["source_statuses"]["process_registry"] = "error"
        source_errors.append(f"process_registry: {exc}")

    # Source 2: Failure report (local JSON)
    source_2_ok = False
    try:
        from nexus_agent_platform.agents.hermes import _get_failure_report
        raw = _get_failure_report()
        working = raw.get("working", "")
        if "Unable to read" in working:
            health_data["source_statuses"]["failure_report"] = "unavailable"
            source_errors.append(f"failure_report: {raw.get('needs_attention', 'unknown')}")
        else:
            health_data["sources_checked"].append("failure_report")
            health_data["source_statuses"]["failure_report"] = "success"
            source_2_ok = True
            needs = raw.get("needs_attention", "")
            if needs:
                health_data["recent_failures"].append(needs)
    except Exception as exc:
        health_data["source_statuses"]["failure_report"] = "error"
        source_errors.append(f"failure_report: {exc}")

    # Source 3: Process failures from Supabase
    source_3_ok = False
    try:
        from nexus_agent_platform.agents.hermes import _get_process_failures
        raw = _get_process_failures()
        if raw.get("status") == "ok":
            health_data["sources_checked"].append("process_failures")
            health_data["source_statuses"]["process_failures"] = "success"
            source_3_ok = True
            total_failures = raw.get("total", 0)
            health_data["failed_services"] = total_failures
            by_status = raw.get("by_status", {})
            for status_name, count in by_status.items():
                if count > 0:
                    health_data["recent_failures"].append(
                        f"{count} process(es) with status {status_name}"
                    )
        else:
            health_data["source_statuses"]["process_failures"] = "unavailable"
            source_errors.append(f"process_failures: {raw.get('error', 'unavailable')}")
    except Exception as exc:
        health_data["source_statuses"]["process_failures"] = "error"
        source_errors.append(f"process_failures: {exc}")

    # Determine overall status using canonical rules:
    # - healthy: all sources OK, no failures, services active
    # - degraded: positive evidence of degradation (failures > 0 OR degraded > 0)
    # - unhealthy: critical failures
    # - unknown: insufficient telemetry to determine health
    confirmed_sources = sum(1 for s in health_data["source_statuses"].values() if s == "success")
    total_sources = len(health_data["source_statuses"])

    if confirmed_sources == 0:
        # No sources available — health is unknown, NOT degraded
        health_data["overall_status"] = "unknown"
    elif health_data["failed_services"] > 0:
        health_data["overall_status"] = "degraded"
    elif health_data["degraded_services"] > 0:
        health_data["overall_status"] = "degraded"
    elif health_data["active_services"] > 0 and health_data["failed_services"] == 0:
        health_data["overall_status"] = "healthy"
    else:
        health_data["overall_status"] = "unknown"

    health_data["verification_complete"] = (
        confirmed_sources == total_sources and total_sources > 0
    )

    if source_errors:
        health_data["important_warnings"].append(
            f"Partial telemetry: {len(source_errors)} source(s) returned errors"
        )

    # Envelope status: success if all sources OK, partial if some failed
    envelope_status = "success"
    if not health_data["verification_complete"]:
        envelope_status = "partial" if confirmed_sources > 0 else "unavailable"

    query_end = datetime.now(timezone.utc)
    return {
        "status": envelope_status,
        "capability": "get_system_health",
        "source": "composite",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": health_data,
        "error": "; ".join(source_errors) if source_errors else None,
        "provenance": {
            "capability": "get_system_health",
            "status": envelope_status,
            "source": "composite",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "sources_checked": health_data["sources_checked"],
            "source_statuses": health_data["source_statuses"],
            "handler": "shared._handle_system_health",
            "access_boundary": "approved read capability only",
        },
    }


# ─── Shared Handler: Pending Approvals ─────────────────────

def _handle_pending_approvals(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Read pending approvals from the canonical review queue."""
    from nexus_agent_platform.agents.hermes import _get_pending_approvals

    query_start = datetime.now(timezone.utc)
    try:
        raw = _get_pending_approvals()
    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        return {
            "status": "error",
            "capability": "get_pending_approvals",
            "source": "local_json",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"count": None, "items": None, "data_available": False},
            "error": str(exc),
            "provenance": {
                "capability": "get_pending_approvals",
                "status": "error",
                "source": "local_json",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    query_end = datetime.now(timezone.utc)
    status = raw.get("status", "unavailable")
    if status == "unavailable":
        return {
            "status": "unavailable",
            "capability": "get_pending_approvals",
            "source": "local_json",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"count": None, "items": None, "data_available": False},
            "error": raw.get("error", "Review queue unavailable"),
            "provenance": {
                "capability": "get_pending_approvals",
                "status": "unavailable",
                "source": "local_json",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    canonical_data = {
        "count": raw.get("pending_count", 0),
        "items": raw.get("items", []),
        "data_available": True,
    }
    return {
        "status": "success",
        "capability": "get_pending_approvals",
        "source": "local_json",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": canonical_data,
        "error": None,
        "provenance": {
            "capability": "get_pending_approvals",
            "status": "success",
            "source": "local_json",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "handler": "hermes._get_pending_approvals",
            "access_boundary": "approved read capability only",
        },
    }


# ─── Shared Handler: Recent Research ───────────────────────

def _handle_recent_research(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Read recent research runs and results from canonical source."""
    from nexus_agent_platform.agents.hermes import _get_research_history

    query_start = datetime.now(timezone.utc)
    try:
        raw = _get_research_history()
    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        return {
            "status": "error",
            "capability": "get_recent_research",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"runs": None, "results": None, "data_available": False},
            "error": str(exc),
            "provenance": {
                "capability": "get_recent_research",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    query_end = datetime.now(timezone.utc)
    status = raw.get("status", "unavailable")
    if status == "unavailable":
        return {
            "status": "unavailable",
            "capability": "get_recent_research",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"runs": None, "results": None, "data_available": False},
            "error": raw.get("error", "Research history unavailable"),
            "provenance": {
                "capability": "get_recent_research",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    # Normalize: keep safe fields only
    runs_data = raw.get("runs", {})
    results_data = raw.get("results", {})
    safe_runs = {
        "total": runs_data.get("total", 0),
        "completed": runs_data.get("completed", 0),
        "failed": runs_data.get("failed", 0),
        "items": [
            {
                "id": r.get("id"),
                "query": r.get("query"),
                "status": r.get("status"),
                "category": r.get("category"),
                "created_at": r.get("created_at"),
                "completed_at": r.get("completed_at"),
            }
            for r in runs_data.get("items", [])[:10]
        ],
    }
    safe_results = {
        "total": results_data.get("total", 0),
        "items": [
            {
                "id": r.get("id"),
                "source": r.get("source"),
                "title": r.get("title"),
                "created_at": r.get("created_at"),
            }
            for r in results_data.get("items", [])[:10]
        ],
    }

    return {
        "status": "success",
        "capability": "get_recent_research",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": {"runs": safe_runs, "results": safe_results, "data_available": True},
        "error": None,
        "provenance": {
            "capability": "get_recent_research",
            "status": "success",
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "handler": "hermes._get_research_history",
            "access_boundary": "approved read capability only",
        },
    }


# ─── Shared Handler: Opportunities ─────────────────────────

def _handle_opportunities(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Read current business opportunities from canonical source."""
    from nexus_agent_platform.agents.hermes import _get_opportunities

    query_start = datetime.now(timezone.utc)
    try:
        raw = _get_opportunities()
    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        return {
            "status": "error",
            "capability": "get_opportunities",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"total": None, "by_state": None, "items": None, "data_available": False},
            "error": str(exc),
            "provenance": {
                "capability": "get_opportunities",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    query_end = datetime.now(timezone.utc)
    status = raw.get("status", "unavailable")
    if status == "unavailable":
        return {
            "status": "unavailable",
            "capability": "get_opportunities",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"total": None, "by_state": None, "items": None, "data_available": False},
            "error": raw.get("error", "Opportunities unavailable"),
            "provenance": {
                "capability": "get_opportunities",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    # Normalize: safe fields only
    items = raw.get("opportunities", [])
    safe_items = [
        {
            "id": o.get("id"),
            "title": o.get("title"),
            "status": o.get("status"),
            "revenue_potential": o.get("revenue_potential"),
            "action_state": o.get("action_state"),
            "updated_at": o.get("updated_at"),
        }
        for o in items
    ]
    canonical_data = {
        "total": raw.get("total", 0),
        "by_state": raw.get("by_state", {}),
        "items": safe_items,
        "data_available": True,
    }

    return {
        "status": "success",
        "capability": "get_opportunities",
        "source": "supabase",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": canonical_data,
        "error": None,
        "provenance": {
            "capability": "get_opportunities",
            "status": "success",
            "source": "supabase",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "handler": "hermes._get_opportunities",
            "access_boundary": "approved read capability only",
        },
    }


# ─── Shared Handler: Client Profile ────────────────────────

def _handle_client_profile(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Look up a single client profile by exact email or exact ID.

    Returns safe fields only: status, classification, tenant, onboarding state.
    Does not expose raw credit data, SSN, bank details, or credentials.
    """
    args = arguments or {}
    raw_email = args.get("email", "")
    client_id = args.get("client_id", "")

    query_start = datetime.now(timezone.utc)
    session = _supabase_session()
    if session is None:
        return {
            "status": "unavailable",
            "capability": "get_client_profile",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"found": False, "ambiguous": False},
            "error": "Supabase credentials not configured",
            "provenance": {
                "capability": "get_client_profile",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    # Normalize email if provided
    normalized = _normalize_email(raw_email) if raw_email else None
    if raw_email and normalized is None:
        return {
            "status": "error",
            "capability": "get_client_profile",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"found": False, "ambiguous": False},
            "error": f"Invalid email format: {raw_email}",
            "provenance": {
                "capability": "get_client_profile",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    # Build query
    if normalized:
        params = {
            "select": "id,client_label,status,source,tenant_id,business_name,legal_name,onboarding_step,created_at,updated_at",
            "client_label": f"eq.{normalized}",
        }
    elif client_id:
        params = {
            "select": "id,client_label,status,source,tenant_id,business_name,legal_name,onboarding_step,created_at,updated_at",
            "id": f"eq.{client_id}",
        }
    else:
        return {
            "status": "error",
            "capability": "get_client_profile",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"found": False, "ambiguous": False},
            "error": "Provide an email or client_id for lookup.",
            "provenance": {
                "capability": "get_client_profile",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    try:
        resp = session.get(
            f"{session._supabase_url}/rest/v1/client_profiles",
            params=params,
            timeout=10,
        )
        query_end = datetime.now(timezone.utc)

        if not resp.ok:
            return {
                "status": "error",
                "capability": "get_client_profile",
                "source": "supabase",
                "source_type": "live_governed_read",
                "freshness": "unknown",
                "access_boundary": "approved read capability only",
                "data": {"found": False, "ambiguous": False},
                "error": f"Profile query returned {resp.status_code}",
                "provenance": {
                    "capability": "get_client_profile",
                    "status": "error",
                    "source": "supabase",
                    "source_type": "live_governed_read",
                    "retrieved_at": query_end.isoformat(),
                    "freshness": "unknown",
                    "trace_id": trace_id,
                },
            }

        profiles = resp.json()
        if not profiles:
            return {
                "status": "success",
                "capability": "get_client_profile",
                "source": "supabase",
                "source_type": "live_governed_read",
                "freshness": "live",
                "access_boundary": "approved read capability only",
                "data": {"found": False, "ambiguous": False},
                "error": None,
                "provenance": {
                    "capability": "get_client_profile",
                    "status": "success",
                    "source": "supabase",
                    "source_type": "live_governed_read",
                    "retrieved_at": query_end.isoformat(),
                    "freshness": "live",
                    "trace_id": trace_id,
                    "handler": "shared._handle_client_profile",
                },
            }

        if len(profiles) > 1:
            return {
                "status": "success",
                "capability": "get_client_profile",
                "source": "supabase",
                "source_type": "live_governed_read",
                "freshness": "live",
                "access_boundary": "approved read capability only",
                "data": {
                    "found": True,
                    "ambiguous": True,
                    "match_count": len(profiles),
                    "matches": [
                        {
                            "id": p.get("id"),
                            "client_label": p.get("client_label"),
                            "status": (p.get("status") or "").lower(),
                            "classification": _classify_profile(
                                p.get("source", ""), p.get("tenant_id", ""), (p.get("status") or "").lower()
                            ),
                        }
                        for p in profiles[:5]
                    ],
                },
                "error": None,
                "provenance": {
                    "capability": "get_client_profile",
                    "status": "success",
                    "source": "supabase",
                    "source_type": "live_governed_read",
                    "retrieved_at": query_end.isoformat(),
                    "freshness": "live",
                    "trace_id": trace_id,
                    "handler": "shared._handle_client_profile",
                },
            }

        p = profiles[0]
        classification = _classify_profile(
            p.get("source", ""), p.get("tenant_id", ""), (p.get("status") or "").lower()
        )
        safe_profile = {
            "found": True,
            "ambiguous": False,
            "client_id": p.get("id"),
            "client_label": p.get("client_label"),
            "status": (p.get("status") or "").lower(),
            "classification": classification,
            "tenant_id": p.get("tenant_id"),
            "business_name": p.get("business_name"),
            "legal_name": p.get("legal_name"),
            "onboarding_step": p.get("onboarding_step"),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
        }

        return {
            "status": "success",
            "capability": "get_client_profile",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": safe_profile,
            "error": None,
            "provenance": {
                "capability": "get_client_profile",
                "status": "success",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "query_start": query_start.isoformat(),
                "query_end": query_end.isoformat(),
                "freshness": "live",
                "trace_id": trace_id,
                "handler": "shared._handle_client_profile",
                "access_boundary": "approved read capability only",
            },
        }

    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        return {
            "status": "error",
            "capability": "get_client_profile",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"found": False, "ambiguous": False},
            "error": str(exc),
            "provenance": {
                "capability": "get_client_profile",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }


# ─── Shared Handler: Funding Readiness ─────────────────────

def _handle_funding_readiness(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Read funding readiness status for a specific client.

    Uses the client_profiles onboarding_step and status fields as the
    canonical readiness signal. If a dedicated readiness table exists,
    it will be queried; otherwise falls back to profile-based inference.
    """
    args = arguments or {}
    raw_email = args.get("email", "")
    client_id = args.get("client_id", "")

    normalized = _normalize_email(raw_email) if raw_email else None
    if raw_email and normalized is None:
        return {
            "status": "error",
            "capability": "get_funding_readiness",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"client_identifier": raw_email, "funding_readiness_status": "unknown"},
            "error": f"Invalid email format: {raw_email}",
            "provenance": {
                "capability": "get_funding_readiness",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    if not normalized and not client_id:
        return {
            "status": "error",
            "capability": "get_funding_readiness",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"client_identifier": "unknown", "funding_readiness_status": "unknown"},
            "error": "Provide an email or client_id for readiness lookup.",
            "provenance": {
                "capability": "get_funding_readiness",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    session = _supabase_session()
    if session is None:
        return {
            "status": "unavailable",
            "capability": "get_funding_readiness",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"client_identifier": normalized or client_id, "funding_readiness_status": "unknown"},
            "error": "Supabase credentials not configured",
            "provenance": {
                "capability": "get_funding_readiness",
                "status": "unavailable",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }

    query_start = datetime.now(timezone.utc)
    identifier = normalized or client_id

    # First, find the client profile
    try:
        if normalized:
            profile_resp = session.get(
                f"{session._supabase_url}/rest/v1/client_profiles",
                params={
                    "select": "id,client_label,status,source,tenant_id,onboarding_step,business_name,created_at",
                    "client_label": f"eq.{normalized}",
                },
                timeout=10,
            )
        else:
            profile_resp = session.get(
                f"{session._supabase_url}/rest/v1/client_profiles",
                params={
                    "select": "id,client_label,status,source,tenant_id,onboarding_step,business_name,created_at",
                    "id": f"eq.{client_id}",
                },
                timeout=10,
            )

        query_end = datetime.now(timezone.utc)

        if not profile_resp.ok:
            return {
                "status": "error",
                "capability": "get_funding_readiness",
                "source": "supabase",
                "source_type": "live_governed_read",
                "freshness": "unknown",
                "access_boundary": "approved read capability only",
                "data": {"client_identifier": identifier, "funding_readiness_status": "unknown"},
                "error": f"Profile query returned {profile_resp.status_code}",
                "provenance": {
                    "capability": "get_funding_readiness",
                    "status": "error",
                    "source": "supabase",
                    "source_type": "live_governed_read",
                    "retrieved_at": query_end.isoformat(),
                    "freshness": "unknown",
                    "trace_id": trace_id,
                },
            }

        profiles = profile_resp.json()
        if not profiles:
            return {
                "status": "success",
                "capability": "get_funding_readiness",
                "source": "supabase",
                "source_type": "live_governed_read",
                "freshness": "live",
                "access_boundary": "approved read capability only",
                "data": {
                    "client_identifier": identifier,
                    "funding_readiness_status": "not_found",
                    "client_found": False,
                },
                "error": None,
                "provenance": {
                    "capability": "get_funding_readiness",
                    "status": "success",
                    "source": "supabase",
                    "source_type": "live_governed_read",
                    "retrieved_at": query_end.isoformat(),
                    "freshness": "live",
                    "trace_id": trace_id,
                    "handler": "shared._handle_funding_readiness",
                },
            }

        p = profiles[0]
        status_val = (p.get("status") or "").lower()
        onboarding_step = p.get("onboarding_step") or ""
        classification = _classify_profile(
            p.get("source", ""), p.get("tenant_id", ""), status_val
        )

        # Funding readiness status:
        # onboarding_step and status are AVAILABLE SIGNALS but NOT a canonical
        # funding readiness model. Nova must not issue a readiness verdict
        # based solely on these signals. The canonical readiness model lives
        # in the client portal (clientFundingReadiness.ts) and requires
        # credit data, document completeness, business foundation, and
        # bankability signals that are not available through this handler.
        available_signals = {
            "client_status": status_val,
            "onboarding_step": onboarding_step,
            "classification": classification,
        }
        missing_signals = [
            "credit_readiness_score",
            "business_foundation_score",
            "bankability_score",
            "document_completeness",
            "funding_readiness_score",
            "tier_classification",
        ]

        canonical_data = {
            "client_identifier": identifier,
            "client_found": True,
            "funding_readiness_status": "not_yet_certified",
            "available_signals": available_signals,
            "missing_signals": missing_signals,
            "verification_complete": False,
            "client_status": status_val,
            "onboarding_step": onboarding_step,
            "classification": classification,
        }

        return {
            "status": "success",
            "capability": "get_funding_readiness",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": canonical_data,
            "error": None,
            "provenance": {
                "capability": "get_funding_readiness",
                "status": "success",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "query_start": query_start.isoformat(),
                "query_end": query_end.isoformat(),
                "freshness": "live",
                "trace_id": trace_id,
                "handler": "shared._handle_funding_readiness",
                "access_boundary": "approved read capability only",
            },
        }

    except Exception as exc:
        query_end = datetime.now(timezone.utc)
        return {
            "status": "error",
            "capability": "get_funding_readiness",
            "source": "supabase",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {"client_identifier": identifier, "funding_readiness_status": "unknown"},
            "error": str(exc),
            "provenance": {
                "capability": "get_funding_readiness",
                "status": "error",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": query_end.isoformat(),
                "freshness": "unknown",
                "trace_id": trace_id,
            },
        }


# ─── Shared Handler: Operational Summary ───────────────────

def _handle_operational_summary(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Aggregator: collect verified results from multiple read capabilities.

    This is NOT a new data source. It calls approved read capabilities
    and returns their results as a single structured context block.

    Status semantics:
    - Each component preserves its own status independently
    - "unavailable" means data could NOT be retrieved (NOT zero records)
    - "empty" means data was retrieved and zero records exist
    - "success" means data was retrieved successfully
    - "partial" means some components succeeded, some didn't
    - The component_statuses dict provides a flat status map
    """
    query_start = datetime.now(timezone.utc)
    components: Dict[str, Any] = {}
    component_statuses: Dict[str, str] = {}
    component_errors: list = []

    # System health
    try:
        result = _handle_system_health(trace_id=trace_id)
        components["system_health"] = {
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
        }
        component_statuses["system_health"] = result.get("status", "unknown")
    except Exception as exc:
        components["system_health"] = {"status": "unavailable", "error": str(exc)}
        component_statuses["system_health"] = "unavailable"
        component_errors.append(f"system_health: {exc}")

    # Client count
    try:
        result = _handle_client_count(trace_id=trace_id)
        components["client_counts"] = {
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
        }
        component_statuses["client_counts"] = result.get("status", "unknown")
    except Exception as exc:
        components["client_counts"] = {"status": "unavailable", "error": str(exc)}
        component_statuses["client_counts"] = "unavailable"
        component_errors.append(f"client_counts: {exc}")

    # Pending approvals
    try:
        result = _handle_pending_approvals(trace_id=trace_id)
        components["pending_approvals"] = {
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
        }
        component_statuses["pending_approvals"] = result.get("status", "unknown")
    except Exception as exc:
        components["pending_approvals"] = {"status": "unavailable", "error": str(exc)}
        component_statuses["pending_approvals"] = "unavailable"
        component_errors.append(f"pending_approvals: {exc}")

    # Recent research
    try:
        result = _handle_recent_research(trace_id=trace_id)
        components["recent_research"] = {
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
        }
        component_statuses["recent_research"] = result.get("status", "unknown")
    except Exception as exc:
        components["recent_research"] = {"status": "unavailable", "error": str(exc)}
        component_statuses["recent_research"] = "unavailable"
        component_errors.append(f"recent_research: {exc}")

    # Opportunities
    try:
        result = _handle_opportunities(trace_id=trace_id)
        components["opportunities"] = {
            "status": result.get("status", "unknown"),
            "data": result.get("data", {}),
        }
        component_statuses["opportunities"] = result.get("status", "unknown")
    except Exception as exc:
        components["opportunities"] = {"status": "unavailable", "error": str(exc)}
        component_statuses["opportunities"] = "unavailable"
        component_errors.append(f"opportunities: {exc}")

    query_end = datetime.now(timezone.utc)

    # Determine overall status from component statuses
    statuses = list(component_statuses.values())
    success_count = sum(1 for s in statuses if s in ("success", "empty"))
    partial_count = sum(1 for s in statuses if s == "partial")
    unavailable_count = sum(1 for s in statuses if s in ("unavailable", "error"))
    total = len(statuses)

    if total == 0:
        overall_status = "unavailable"
    elif success_count == total:
        overall_status = "success"
    elif success_count + partial_count == total:
        overall_status = "partial"
    elif unavailable_count == total:
        overall_status = "unavailable"
    else:
        overall_status = "partial"

    return {
        "status": overall_status,
        "capability": "get_operational_summary",
        "source": "composite",
        "source_type": "live_governed_read",
        "freshness": "live",
        "access_boundary": "approved read capability only",
        "data": components,
        "component_statuses": component_statuses,
        "error": "; ".join(component_errors) if component_errors else None,
        "provenance": {
            "capability": "get_operational_summary",
            "status": overall_status,
            "source": "composite",
            "source_type": "live_governed_read",
            "retrieved_at": query_end.isoformat(),
            "query_start": query_start.isoformat(),
            "query_end": query_end.isoformat(),
            "freshness": "live",
            "trace_id": trace_id,
            "components_requested": [
                "system_health", "client_counts", "pending_approvals",
                "recent_research", "opportunities",
            ],
            "component_statuses": component_statuses,
            "components_failed": component_errors,
            "handler": "shared._handle_operational_summary",
            "access_boundary": "approved read capability only",
        },
    }


# ─── Nexus Knowledge Handlers ─────────────────────────────

def _handle_nexus_overview(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return a verified overview of the Nexus system."""
    try:
        data = _nk_get_nexus_overview()
        return {
            "status": "success",
            "capability": "get_nexus_overview",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "current_commit",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None,
            "provenance": {
                "capability": "get_nexus_overview",
                "status": "success",
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "current_commit",
                "handler": "shared._handle_nexus_overview",
                "access_boundary": "approved read capability only",
            },
        }
    except Exception as exc:
        log.error("get_nexus_overview failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_nexus_overview",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_nexus_overview",
                "status": "error",
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_nexus_overview",
            },
        }


def _handle_agent_registry(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return all agents with their metadata."""
    try:
        data = _nk_get_agent_registry()
        return {
            "status": "success",
            "capability": "get_agent_registry",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "current_commit",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None,
            "provenance": {
                "capability": "get_agent_registry",
                "status": "success",
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "current_commit",
                "handler": "shared._handle_agent_registry",
            },
        }
    except Exception as exc:
        log.error("get_agent_registry failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_agent_registry",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_agent_registry",
                "status": "error",
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_agent_registry",
            },
        }


def _handle_agent_details(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return details for a specific agent."""
    args = arguments or {}
    agent_id = args.get("agent_id", "").strip().lower()
    if not agent_id:
        return {
            "status": "error",
            "capability": "get_agent_details",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "current_commit",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": "agent_id is required.",
            "provenance": {
                "capability": "get_agent_details",
                "status": "error",
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "current_commit",
                "handler": "shared._handle_agent_details",
            },
        }
    try:
        data = _nk_get_agent_details(agent_id)
        status = "success" if data.get("found") else "not_found"
        return {
            "status": status,
            "capability": "get_agent_details",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "current_commit",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None if data.get("found") else data.get("error"),
            "provenance": {
                "capability": "get_agent_details",
                "status": status,
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "current_commit",
                "handler": "shared._handle_agent_details",
            },
        }
    except Exception as exc:
        log.error("get_agent_details failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_agent_details",
            "source": "nexus_knowledge_registry",
            "source_type": "repository_registry",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_agent_details",
                "status": "error",
                "source": "nexus_knowledge_registry",
                "source_type": "repository_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_agent_details",
            },
        }


def _handle_tool_registry(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return the tool registry."""
    try:
        data = _nk_get_tool_registry()
        return {
            "status": "success",
            "capability": "get_tool_registry",
            "source": "nexus_knowledge_registry",
            "source_type": "configuration_registry",
            "freshness": "current_commit",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None,
            "provenance": {
                "capability": "get_tool_registry",
                "status": "success",
                "source": "nexus_knowledge_registry",
                "source_type": "configuration_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "current_commit",
                "handler": "shared._handle_tool_registry",
            },
        }
    except Exception as exc:
        log.error("get_tool_registry failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_tool_registry",
            "source": "nexus_knowledge_registry",
            "source_type": "configuration_registry",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_tool_registry",
                "status": "error",
                "source": "nexus_knowledge_registry",
                "source_type": "configuration_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_tool_registry",
            },
        }


def _handle_capability_registry(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return the capability registry."""
    try:
        data = _nk_get_capability_registry()
        return {
            "status": "success",
            "capability": "get_capability_registry",
            "source": "nexus_knowledge_registry",
            "source_type": "capability_registry",
            "freshness": "current_commit",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None,
            "provenance": {
                "capability": "get_capability_registry",
                "status": "success",
                "source": "nexus_knowledge_registry",
                "source_type": "capability_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "current_commit",
                "handler": "shared._handle_capability_registry",
            },
        }
    except Exception as exc:
        log.error("get_capability_registry failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_capability_registry",
            "source": "nexus_knowledge_registry",
            "source_type": "capability_registry",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_capability_registry",
                "status": "error",
                "source": "nexus_knowledge_registry",
                "source_type": "capability_registry",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_capability_registry",
            },
        }


def _handle_process_registry(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return the live process registry."""
    try:
        data = _nk_get_process_registry_live()
        status = data.get("status", "success")
        return {
            "status": status,
            "capability": "get_process_registry",
            "source": "process_registry",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": data.get("error"),
            "provenance": {
                "capability": "get_process_registry",
                "status": status,
                "source": "process_registry",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "handler": "shared._handle_process_registry",
            },
        }
    except Exception as exc:
        log.error("get_process_registry failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_process_registry",
            "source": "process_registry",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_process_registry",
                "status": "error",
                "source": "process_registry",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_process_registry",
            },
        }


def _handle_process_details(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return details for a specific process."""
    args = arguments or {}
    process_id = args.get("process_id", "").strip().lower()
    if not process_id:
        return {
            "status": "error",
            "capability": "get_process_details",
            "source": "process_registry",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": "process_id is required.",
            "provenance": {
                "capability": "get_process_details",
                "status": "error",
                "source": "process_registry",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "handler": "shared._handle_process_details",
            },
        }
    try:
        data = _nk_get_process_details(process_id)
        status = "success" if data.get("found") else "not_found"
        return {
            "status": status,
            "capability": "get_process_details",
            "source": "process_registry",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None if data.get("found") else data.get("error"),
            "provenance": {
                "capability": "get_process_details",
                "status": status,
                "source": "process_registry",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "handler": "shared._handle_process_details",
            },
        }
    except Exception as exc:
        log.error("get_process_details failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_process_details",
            "source": "process_registry",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_process_details",
                "status": "error",
                "source": "process_registry",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_process_details",
            },
        }


def _handle_report_index(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return the report index."""
    try:
        data = _nk_get_report_index_live()
        return {
            "status": "success",
            "capability": "get_report_index",
            "source": "report_index",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None,
            "provenance": {
                "capability": "get_report_index",
                "status": "success",
                "source": "report_index",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "handler": "shared._handle_report_index",
            },
        }
    except Exception as exc:
        log.error("get_report_index failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_report_index",
            "source": "report_index",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_report_index",
                "status": "error",
                "source": "report_index",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_report_index",
            },
        }


def _handle_latest_reports(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Return the latest reports."""
    try:
        data = _nk_get_latest_reports_live()
        return {
            "status": data.get("status", "success"),
            "capability": "get_latest_reports",
            "source": "report_index",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": data.get("error"),
            "provenance": {
                "capability": "get_latest_reports",
                "status": data.get("status", "success"),
                "source": "report_index",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "handler": "shared._handle_latest_reports",
            },
        }
    except Exception as exc:
        log.error("get_latest_reports failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_latest_reports",
            "source": "report_index",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_latest_reports",
                "status": "error",
                "source": "report_index",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_latest_reports",
            },
        }


def _handle_recent_activity(
    arguments: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
) -> Dict[str, Any]:
    """Aggregate recent activity from approved operational sources."""
    try:
        data = _nk_get_recent_activity_live()
        return {
            "status": data.get("status", "success"),
            "capability": "get_recent_activity",
            "source": "composite",
            "source_type": "live_governed_read",
            "freshness": "live",
            "access_boundary": "approved read capability only",
            "data": data,
            "error": None,
            "provenance": {
                "capability": "get_recent_activity",
                "status": data.get("status", "success"),
                "source": "composite",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "live",
                "handler": "shared._handle_recent_activity",
            },
        }
    except Exception as exc:
        log.error("get_recent_activity failed: %s", exc)
        return {
            "status": "error",
            "capability": "get_recent_activity",
            "source": "composite",
            "source_type": "live_governed_read",
            "freshness": "unknown",
            "access_boundary": "approved read capability only",
            "data": {},
            "error": str(exc),
            "provenance": {
                "capability": "get_recent_activity",
                "status": "error",
                "source": "composite",
                "source_type": "live_governed_read",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unknown",
                "handler": "shared._handle_recent_activity",
            },
        }


# ─── Capability Dispatch ───────────────────────────────────

_CAPABILITY_HANDLERS: Dict[str, Callable] = {
    "get_client_count": lambda args, tid: _handle_client_count(args, tid),
    "resolve_user_identity_by_email": lambda args, tid: _handle_identity_resolution(args, tid),
    "general_search": lambda args, tid: _handle_general_search(args, tid),
    "get_system_health": lambda args, tid: _handle_system_health(args, tid),
    "get_pending_approvals": lambda args, tid: _handle_pending_approvals(args, tid),
    "get_recent_research": lambda args, tid: _handle_recent_research(args, tid),
    "get_opportunities": lambda args, tid: _handle_opportunities(args, tid),
    "get_client_profile": lambda args, tid: _handle_client_profile(args, tid),
    "get_funding_readiness": lambda args, tid: _handle_funding_readiness(args, tid),
    "get_operational_summary": lambda args, tid: _handle_operational_summary(args, tid),
    "get_runtime_capabilities": None,  # handled specially (needs agent_id)
    # Nexus Knowledge Layer
    "get_nexus_overview": lambda args, tid: _handle_nexus_overview(args, tid),
    "get_agent_registry": lambda args, tid: _handle_agent_registry(args, tid),
    "get_agent_details": lambda args, tid: _handle_agent_details(args, tid),
    "get_tool_registry": lambda args, tid: _handle_tool_registry(args, tid),
    "get_capability_registry": lambda args, tid: _handle_capability_registry(args, tid),
    "get_process_registry": lambda args, tid: _handle_process_registry(args, tid),
    "get_process_details": lambda args, tid: _handle_process_details(args, tid),
    "get_report_index": lambda args, tid: _handle_report_index(args, tid),
    "get_latest_reports": lambda args, tid: _handle_latest_reports(args, tid),
    "get_recent_activity": lambda args, tid: _handle_recent_activity(args, tid),
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
