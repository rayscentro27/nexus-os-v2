"""Phase 15 bounded live research session.

Runs a bounded live-web research session through the existing, already
connected Hermes web-search layer (Brave). No new infrastructure is installed
(Crawl4AI remains a pilot-proposed decision), no client PII is used, and the
session never blocks the runtime when live web is partially unavailable.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

from nexus_agent_platform.phase15.common import (
    MODERNIZATION_DIR,
    PHASE15_DATA,
    atomic_write_json,
    ensure_sources_loaded,
    load_runtime_env,
    strip_pii,
    utc_now,
)
from nexus_agent_platform.phase15.research_decisions import build_research_decisions

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parents[1]
HERMES_DIR = SCRIPTS_DIR / "hermes"

BOUNDED_QUERIES = [
    "credit repair readiness checklist small business 2026",
    "business credit building vendors 2026",
    "credit repair affiliate programs payout 2026",
    "small business funding readiness checklist SEO",
    "open source credit report parsing tool",
    "marketing ideas local credit repair service 2026",
    "lead generation strategies credit repair business",
]

MAX_QUERIES = 5


def _load_web_search():
    ensure_sources_loaded()
    # Resolve provider aliases through the canonical runtime env before the
    # existing Hermes provider selector runs.  This keeps legacy BRAVE_API_KEY
    # and BRAVE_SEARCH_API_KEY usable without duplicating credential stores.
    load_runtime_env()
    from nexus_agent_platform.credential_control_plane import apply_to_process
    apply_to_process("credential.brave.web_search.prod.v1")
    if str(HERMES_DIR) not in sys.path:
        sys.path.insert(0, str(HERMES_DIR))
    try:
        from hermes_web_search import web_search  # type: ignore

        return web_search, None
    except Exception as exc:  # noqa: BLE001
        return None, f"hermes_web_search import failed: {exc}"


def run_live_research_session(max_queries: int = MAX_QUERIES) -> Dict[str, Any]:
    started = utc_now()
    web_search, import_blocker = _load_web_search()
    blocker: List[str] = []
    query_records: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    sources_searched: int = 0
    sources_ok: int = 0
    errors: int = 0
    accepted_urls: set = set()

    if import_blocker:
        blocker.append(import_blocker)

    if web_search is not None:
        queries = BOUNDED_QUERIES[:max_queries]
        for query in queries:
            safe_query = strip_pii(query)
            result = web_search(safe_query)
            status = result.get("status", "error")
            sources_searched += 1
            entries = result.get("results", []) if isinstance(result.get("results"), list) else []
            if status == "ok":
                sources_ok += 1
                for entry in entries:
                    url = str(entry.get("url") or "")
                    title = str(entry.get("title") or "")
                    if not url and not title:
                        continue
                    item = {
                        "candidate_id": f"live:{url or title[:60]}",
                        "title": title or url,
                        "category": "live_web_research",
                        "source_url": url,
                        "snippet": str(entry.get("snippet") or "")[:500],
                        "evidence_classification": "INFERRED",
                        "freshness": "FRESH",
                        "score": None,
                        "query": safe_query,
                    }
                    candidates.append(item)
                    if url not in accepted_urls:
                        accepted_urls.add(url)
                    query_records.append({"query": safe_query, "status": "ok", "source": status, "results": len(entries), "error": None})
            elif status in {"not_configured", "error"}:
                errors += 1
                note = (result.get("notes") or [""])[0] if result.get("notes") else ""
                if not blocker:
                    blocker.append(f"live web provider for query '{safe_query}' returned {status}: {note}")
                query_records.append({"query": safe_query, "status": status, "source": status, "results": 0, "error": note})
    else:
        blocker.append("no search provider available; hermes_web_search not importable")

    freshness = "FRESH" if sources_ok > 0 else "BLOCKED"
    state = "LIVE_PARTIAL" if (sources_ok > 0 and errors > 0) else ("LIVE" if sources_ok > 0 else "BOUNDED_DEGRADED")

    session = {
        "phase": "PHASE 15 — BOUNDED LIVE RESEARCH SESSION",
        "started_at": started,
        "completed_at": utc_now(),
        "state": state,
        "provider": {
            "name": "brave",
            "configured": _brave_configured(),
            "blocker": (blocker[0] if blocker else None),
        },
        "governance": {"no_client_pii": True, "no_installation": True, "no_publishing": True, "bounded": True},
        "sources_searched": sources_searched,
        "sources_ok": sources_ok,
        "sources_failed": errors,
        "query_records": query_records,
        "blockers": blocker,
        "freshness": freshness,
    }

    decisions = build_research_decisions(candidates, session={"session_id": session.get("completed_at"), "provider": "brave"})

    counts = decisions["counts"]
    outcome = {
        "session": session,
        "decisions_source": "reports/hermes_modernization/live_research_decisions.json",
        "opportunities_created": counts["accept"],
        "watch_items": counts["watch"],
        "rejections": counts["reject"],
        "duplicates": counts["duplicate"],
        "needs_more_evidence": counts["needs_more_evidence"],
        "stale": counts["stale"],
        "top_accepted": [
            {"candidate_id": row["candidate_id"], "title": row["title"], "reason": row["decision_reason"]}
            for row in decisions["decisions"] if row["decision"] == "ACCEPT"
        ][:5],
        "top_rejected": [
            {"candidate_id": row["candidate_id"], "title": row["title"], "reason": row.get("rejection_reason", row["decision_reason"])}
            for row in decisions["decisions"] if row["decision"] in {"REJECT", "STALE", "DUPLICATE"}
        ][:5],
    }
    PHASE15_DATA.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PHASE15_DATA / "live_research_session.json", session)
    atomic_write_json(MODERNIZATION_DIR / "live_research_session.json", session)
    return outcome


def _brave_configured() -> bool:
    return bool(__import__("os").environ.get("BRAVE_SEARCH_API_KEY") or "")
