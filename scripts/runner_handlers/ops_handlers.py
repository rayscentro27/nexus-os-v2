"""Ops handlers — read-only diagnostics that summarize real counts into the ledger."""
from __future__ import annotations

from ._base import sb, ok


def _count(table: str, query: str = "select=id") -> int:
    st, rows = sb.get(table, query + "&limit=1000")
    return len(rows) if isinstance(rows, list) else 0


def system_status(job, ctx) -> dict:
    counts = {
        "events": _count("nexus_events"),
        "jobs_queued": _count("agent_jobs", "select=id&status=eq.queued"),
        "jobs_failed": _count("agent_jobs", "select=id&status=eq.failed"),
        "approvals_pending": _count("approvals", "select=id&status=eq.pending"),
        "creative_assets": _count("creative_assets"),
        "social_drafts": _count("social_posts", "select=id&status=eq.draft"),
        "agents_client": _count("agent_registry", "select=id&agent_class=eq.client_agent"),
        "agents_hermes": _count("agent_registry", "select=id&agent_class=eq.hermes_advisor"),
        "agents_can_execute": _count("agent_registry", "select=id&can_execute_actions=eq.true"),
    }
    sb.health("dashboard", "ok", f"system_status: {counts}")
    return ok({"summary": counts})


def ops_diagnostic(job, ctx) -> dict:
    failed = _count("agent_jobs", "select=id&status=eq.failed")
    blocked_n = _count("agent_jobs", "select=id&status=eq.blocked")
    status = "ok" if failed == 0 else "partial"
    sb.health("ops_doctor", status, f"failed_jobs={failed} blocked_jobs={blocked_n}")
    return ok({"failed_jobs": failed, "blocked_jobs": blocked_n, "health": status})
