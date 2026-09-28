"""Canonical Research-lane registry and bounded fair selector.

Research execution is intentionally unbounded.  The scheduler only chooses
the next eligible item; certification counters observe it and never stop it.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.research_work_queue import WORK_CLASSES, default_queue

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "research"))
REGISTRY_PATH = ROOT / "data/runtime/research_lane_registry.json"
SOURCE_REFRESH_STATE_PATH = ROOT / "data/runtime/research_source_refresh_state.json"
EXECUTION_JOBS_PATH = ROOT / "data/runtime/research_execution_jobs.jsonl"
PROGRAM_SERVICE_STATE_PATH = ROOT / "data/runtime/research_program_service_state.json"
PERMANENT_SOURCE_CONFIG = ROOT / "configs/research_permanent_sources.json"
LANES = (
    ("BUSINESS_MARKET", "Business Market", "P1"),
    ("FUNDING_LENDER", "Funding and Lender", "P1"),
    ("GRANTS_GOVERNMENT", "Grants and Government", "P2"),
    ("AFFILIATE_REVENUE", "Affiliate Revenue", "P2"),
    ("SEO_SEARCH_DEMAND", "SEO Search Demand", "P2"),
    ("SOCIAL_CONTENT", "Social Content", "P2"),
    ("YOUTUBE_CONTENT", "YouTube Content", "P2"),
    ("COMPETITOR_INTELLIGENCE", "Competitor Intelligence", "P2"),
    ("TRADING_MARKETS", "Trading Markets", "P1"),
    ("GITHUB_TECHNOLOGY", "GitHub and Open Source", "P2"),
    ("PLATFORM_CAPABILITY_INTELLIGENCE", "Platform Capability Intelligence", "P2"),
)
RESEARCH_CYCLE_LIMIT = "UNBOUNDED"
RESEARCH_RUNTIME_STOP_CONDITION = "NONE"
LIVE_SERVICE_WAKE_THRESHOLD = 3
LIVE_PROGRAM_LANES = {
    "CUSTOMER_NEEDS": "BUSINESS_MARKET",
    "BUSINESS_FUNDING": "FUNDING_LENDER",
    "YOUTUBE_INTELLIGENCE": "YOUTUBE_CONTENT",
    "SEO_SEARCH_INTELLIGENCE": "SEO_SEARCH_DEMAND",
    "GITHUB_OPEN_SOURCE": "GITHUB_TECHNOLOGY",
    "PROJECT_SUPPORT": "BUSINESS_MARKET",
    "LAST30DAYS_PROACTIVE": "BUSINESS_MARKET",
    "RESEARCH_MORE": "BUSINESS_MARKET",
}

# These are aliases over real queue/registry lanes and governed source paths;
# they are not extra schedulers or synthetic work queues.
STANDING_LANE_ALIASES = {
    "ASSIGNED_RESEARCH": ("ASSIGNED_QUEUE",),
    "RESEARCH_MORE": ("RESEARCH_MORE_QUEUE",),
    "CUSTOMER_NEEDS_COMPLAINTS_IDEAS": ("BUSINESS_MARKET",),
    "YOUTUBE_RESEARCH": ("YOUTUBE_CONTENT",),
    "SEO_SEARCH_ENGINE_RESEARCH": ("SEO_SEARCH_DEMAND",),
    "GITHUB_OPEN_SOURCE_RESEARCH": ("GITHUB_TECHNOLOGY", "PLATFORM_CAPABILITY_INTELLIGENCE"),
    "BUSINESS_FUNDING_CLYDE_INTELLIGENCE": ("FUNDING_LENDER", "GRANTS_GOVERNMENT"),
    "AFFILIATE_PRODUCT_SOLUTION_DISCOVERY": ("AFFILIATE_REVENUE",),
    "GENERAL_OPPORTUNITY_DISCOVERY": ("BUSINESS_MARKET",),
    "STALE_INTELLIGENCE_REFRESH": ("SOURCE_REFRESH_STATE",),
    "DEPARTMENT_RESEARCH_REQUESTS": ("ASSIGNED_QUEUE",),
    "MONITORED_SOURCE_REFRESH": ("SOURCE_REFRESH_STATE",),
}
PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
GOVERNED = ROOT / "data/governed"
LANE_TERMS = {
    "BUSINESS_MARKET": ("business", "market", "opportunity", "realestate", "ecommerce", "saas"),
    "FUNDING_LENDER": ("funding", "lender", "loan", "credit"),
    "GRANTS_GOVERNMENT": ("grant", "government", "regulat", "compliance"),
    "AFFILIATE_REVENUE": ("affiliate", "creator", "commission", "monetiz"),
    "SEO_SEARCH_DEMAND": ("seo", "search", "keyword", "content"),
    "SOCIAL_CONTENT": ("social", "community", "reddit", "creator"),
    "YOUTUBE_CONTENT": ("youtube", "video", "creator"),
    "COMPETITOR_INTELLIGENCE": ("competitor", "competition", "market"),
    "TRADING_MARKETS": ("trading", "forex", "market", "backtest"),
    "GITHUB_TECHNOLOGY": ("github", "software", "repository", "technical"),
    "PLATFORM_CAPABILITY_INTELLIGENCE": ("platform", "software", "api", "automation", "github"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read() -> list[dict[str, Any]]:
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, ValueError, TypeError):
        return []


def _read_source_refresh_state() -> dict[str, dict[str, Any]]:
    """Read durable per-source refresh state used by the lane selector.

    This is intentionally separate from governed Research records: those are
    append-only knowledge/provenance records, while this file is operational
    scheduling state.  A failed or unchanged refresh must not create another
    source artifact or change the meaning of the canonical record.
    """
    try:
        value = json.loads(SOURCE_REFRESH_STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _read_program_service_state() -> dict[str, dict[str, Any]]:
    try:
        value = json.loads(PROGRAM_SERVICE_STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _write_program_service_state(value: dict[str, dict[str, Any]]) -> None:
    PROGRAM_SERVICE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PROGRAM_SERVICE_STATE_PATH.with_name(f".{PROGRAM_SERVICE_STATE_PATH.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, PROGRAM_SERVICE_STATE_PATH)


def _write_source_refresh_state(value: dict[str, dict[str, Any]]) -> None:
    SOURCE_REFRESH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_REFRESH_STATE_PATH.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hydrate_refresh_state_from_history() -> None:
    """Migrate real duplicate outcomes into the new scheduler state once."""
    if SOURCE_REFRESH_STATE_PATH.exists() or not EXECUTION_JOBS_PATH.exists():
        return
    selected: dict[str, dict[str, Any]] = {}
    state: dict[str, dict[str, Any]] = {}
    try:
        lines = EXECUTION_JOBS_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        execution_id = str(event.get("execution_id", ""))
        status = str(event.get("status", ""))
        if status == "SOURCE_SELECTED" and event.get("lane_id") and event.get("source_id"):
            selected[execution_id] = event
            continue
        if status != "EVIDENCE_READY" or event.get("final_status") != "DUPLICATE_UNCHANGED":
            if status == "EVIDENCE_READY" and execution_id in selected and event.get("final_status") != "DUPLICATE_UNCHANGED":
                item = selected[execution_id]
                state[_source_state_key(str(item["lane_id"]), str(item["source_id"]))] = {
                    "lane_id": str(item["lane_id"]), "source_id": str(item["source_id"]),
                    "consecutive_duplicate_count": 0, "last_status": str(event.get("final_status", "FULLY_PROCESSED")),
                    "last_changed_at": event.get("at"), "next_eligible_refresh_at": None,
                    "source_class": str(item.get("source_type", "")),
                }
            continue
        item = selected.get(execution_id)
        if not item:
            continue
        lane_id, source_id = str(item["lane_id"]), str(item["source_id"])
        key = _source_state_key(lane_id, source_id)
        previous = state.get(key, {})
        count = int(previous.get("consecutive_duplicate_count", 0) or 0) + 1
        try:
            event_at = datetime.fromisoformat(str(event.get("at")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            event_at = datetime.now(timezone.utc)
        cooldown = min(_refresh_seconds(lane_id, source_id) * max(1, min(count, 4)), 86400)
        state[key] = {"lane_id": lane_id, "source_id": source_id,
                      "last_duplicate_at": event.get("at"), "consecutive_duplicate_count": count,
                      "next_eligible_refresh_at": (event_at + timedelta(seconds=cooldown)).isoformat(),
                      "last_status": "DUPLICATE_UNCHANGED", "source_class": str(item.get("source_type", ""))}
    if state:
        _write_source_refresh_state(state)


def _source_state_key(lane_id: str, source_id: str) -> str:
    return f"{lane_id}:{source_id}"


def _refresh_seconds(lane_id: str, source_id: str) -> int:
    """Bounded refresh intervals by source behavior, not one global delay."""
    source = source_id.lower()
    if lane_id == "YOUTUBE_CONTENT":
        return 3600
    if lane_id in {"GITHUB_TECHNOLOGY", "PLATFORM_CAPABILITY_INTELLIGENCE"} or "/" in source:
        return 21600
    if lane_id in {"GRANTS_GOVERNMENT", "TRADING_MARKETS", "FUNDING_LENDER"}:
        return 14400
    return 7200


def _source_refresh_snapshot(lane_id: str, source_id: str, now: datetime) -> dict[str, Any]:
    state = _read_source_refresh_state().get(_source_state_key(lane_id, source_id), {})
    next_at = state.get("next_eligible_refresh_at")
    cooling = bool(next_at and _parse_age(next_at, now) == 0.0)
    return {**state, "cooling_down": cooling,
            "terminal": state.get("last_status") in {"COMPLETE", "PARKED"} or bool(state.get("parked"))}


def _latest_source_for_lane(lane_id: str) -> str:
    """Recover concrete source identity for registry rows predating v2."""
    matching = [value for value in _read_source_refresh_state().values()
                if value.get("lane_id") == lane_id and value.get("source_id")]
    if not matching:
        return ""
    latest = max(matching, key=lambda value: str(value.get("last_duplicate_at") or value.get("last_changed_at") or ""))
    return str(latest.get("source_id", ""))


def mark_source_result(lane_id: str, source_id: str, status: str, *, source_class: str = "") -> dict[str, Any]:
    """Record the result that controls the next normal source refresh.

    DUPLICATE_UNCHANGED is a successful idempotent result, but it is not useful
    new Research.  Consecutive duplicates therefore receive an escalating,
    source-class-aware cooldown.  Material follow-up work can still override
    this at selection time; cooldown never deletes or hides source history.
    """
    now = _now().isoformat()
    state = _read_source_refresh_state()
    key = _source_state_key(lane_id, source_id)
    prior = state.get(key, {})
    duplicate = str(status).upper() == "DUPLICATE_UNCHANGED"
    lifecycle = str(prior.get("lifecycle") or ("ONE_TIME" if source_class in {"ONE_TIME", "YOUTUBE_VIDEO_ONE_TIME"} else "MONITORED"))
    if duplicate:
        consecutive = int(prior.get("consecutive_duplicate_count", 0) or 0) + 1
        # Escalate only within a bounded ceiling so a source can return after
        # a meaningful refresh window or an explicit investigation override.
        cooldown = min(_refresh_seconds(lane_id, source_id) * max(1, min(consecutive, 4)), 86400)
        parked = consecutive >= int(os.environ.get("NEXUS_SOURCE_PARK_AFTER_DUPLICATES", "4"))
        updated = {**prior, "lane_id": lane_id, "source_id": source_id,
                   "last_duplicate_at": now, "consecutive_duplicate_count": consecutive,
                   "next_eligible_refresh_at": None if parked else (datetime.now(timezone.utc) + timedelta(seconds=cooldown)).isoformat(),
                   "last_status": "PARKED" if parked else "DUPLICATE_UNCHANGED", "source_class": source_class or prior.get("source_class", ""),
                   "lifecycle": lifecycle, "parked": parked}
    else:
        # A successful refresh also establishes a quiet period.  Some
        # processors return FULLY_PROCESSED for an idempotent web read rather
        # than DUPLICATE_UNCHANGED, so waiting for the processor's duplicate
        # label alone is insufficient to prevent rapid replay.  This is a
        # refresh cooldown, not a rejection and it never removes history.
        refresh_due = None
        if str(status).upper() == "FULLY_PROCESSED" and lifecycle != "ONE_TIME":
            refresh_due = (datetime.now(timezone.utc) + timedelta(seconds=_refresh_seconds(lane_id, source_id))).isoformat()
        updated = {**prior, "lane_id": lane_id, "source_id": source_id,
                   "last_changed_at": now, "consecutive_duplicate_count": 0,
                   "next_eligible_refresh_at": refresh_due, "last_status": str(status),
                   "source_class": source_class or prior.get("source_class", ""),
                   "lifecycle": lifecycle, "parked": lifecycle == "ONE_TIME",
                   "source_status": "COMPLETE" if lifecycle == "ONE_TIME" and str(status).upper() == "FULLY_PROCESSED" else "MONITORING"}
    state[key] = updated
    _write_source_refresh_state(state)
    # Keep the lane registry explainable: the next selector wake can identify
    # which concrete source produced the duplicate/change result without
    # scanning processor artifacts or treating governed history as a queue.
    rows = ensure_registry()
    for row in rows:
        if row.get("lane_id") == lane_id:
            row["last_source_id"] = source_id
            row["last_source_status"] = str(status)
            row["last_source_result_at"] = now
    REGISTRY_PATH.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return updated


def select_priority_work(*, worker_id: str = "research_scheduler", blocked_buckets: set[str] | None = None,
                         lease_seconds: int = 900) -> dict[str, Any] | None:
    """Claim durable work through the deterministic objective controller."""
    queue = default_queue()
    _sync_governed_priority_work(queue)
    return queue.claim_next_for_objective(worker_id=worker_id, allowed_classes=WORK_CLASSES,
                                          blocked_buckets=blocked_buckets, lease_seconds=lease_seconds)


def ensure_permanent_source_work() -> dict[str, Any]:
    """Project due non-YouTube permanent sources into the existing queue.

    YouTube channels are already selected by the canonical channel watcher.
    This projection gives TradingView and CardRight a durable, deduplicated
    queue item without adding another scheduler or source database.
    """
    try:
        config = json.loads(PERMANENT_SOURCE_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"created": [], "status": "CONFIG_UNAVAILABLE"}
    queue = default_queue()
    rows = queue.load().get("items", [])
    created = []
    for source in config.get("sources", []):
        if not isinstance(source, dict) or str(source.get("source_type", "")).upper() == "YOUTUBE_CHANNEL":
            continue
        source_id = str(source.get("source_id") or "")
        if not source_id:
            continue
        active = any(str(row.get("source_id")) == source_id and str(row.get("status")) in {"QUEUED", "WAITING", "IN_PROGRESS"} for row in rows)
        ever_seen = any(str(row.get("source_id")) == source_id for row in rows)
        if active or ever_seen:
            continue
        work_id = f"permanent-source:{source_id}"
        queue.enqueue(
            work_id=work_id, work_class="MONITORED", priority=10,
            lane_id=source.get("lane_id") or "BUSINESS_MARKET",
            source_type="WEB_PAGE", source_id=source_id, source_url=source.get("canonical_url"),
            title=source.get("objective") or source_id,
            question=source.get("objective") or f"Assess current evidence from {source_id}.",
            requested_by="permanent_source_supervisor", lifecycle="MONITORED",
            selection_reason="permanent_source_due", objective_id=source_id,
            department_target=source.get("department"), required_work=True,
            source_candidates=[{"source_type": "WEB_PAGE", "source_id": source_id, "source_url": source.get("canonical_url"), "title": source.get("objective")}],
            source_classes=source.get("categories", []), owner="RESEARCH",
            state="OWNED", next_action="Acquire bounded public evidence and persist source checkpoint.",
        )
        created.append(work_id)
        rows.append({"work_id": work_id, "source_id": source_id, "status": "QUEUED"})
    return {"created": created, "status": "OK"}


def ensure_live_program_work() -> dict[str, Any]:
    """Materialize one bounded executable item for the two previously starved lanes.

    This is idempotent queue projection, not a second scheduler.  A completed
    item is never recreated automatically; a future refresh is a new governed
    question or explicit project request.
    """
    queue = default_queue()
    specs = {
        "SEO_SEARCH_INTELLIGENCE": {
            "lane_id": "SEO_SEARCH_DEMAND",
            "title": "Funding-readiness search demand",
            "question": "What search queries and content patterns indicate that small-business owners are seeking funding-readiness help?",
            "source_candidates": [
                {"source_type": "SEO_RESEARCH", "source_id": "google-seo-starter", "source_url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "title": "Google SEO Starter Guide"},
                {"source_type": "SEO_RESEARCH", "source_id": "google-ai-search-features", "source_url": "https://developers.google.com/search/docs/appearance/ai-features", "title": "Google Search AI features guidance"},
            ],
        },
        "GITHUB_OPEN_SOURCE": {
            "lane_id": "GITHUB_TECHNOLOGY",
            "title": "Research automation capability review",
            "question": "What current open-source agent/research automation capability is relevant to reliable Nexus Research execution, and what are its limitations?",
            "source_candidates": [
                {"source_type": "GITHUB_REPOSITORY", "source_id": "openai/openai-cookbook", "source_url": "https://github.com/openai/openai-cookbook", "title": "OpenAI Cookbook automation and agent examples"},
            ],
        },
    }
    items = queue.load().get("items", [])
    created = []
    for program_id, spec in specs.items():
        work_id = f"live-program:{program_id.lower()}"
        if any(str(row.get("work_id")) == work_id for row in items):
            continue
        candidate = spec["source_candidates"][0]
        queue.enqueue(
            work_id=work_id, work_class="ASSIGNED", priority=1,
            lane_id=spec["lane_id"], source_type="RESEARCH_OBJECTIVE",
            source_id=f"{program_id.lower()}-20260925", source_url=None,
            source_candidates=spec["source_candidates"], title=spec["title"],
            question=spec["question"], objective_id=work_id,
            requested_by="research_v2_live_service_guarantee",
            lifecycle="ONE_TIME", selection_reason="bounded_live_program_service",
            alpha_followup_required=False, evidence_refs=[],
        )
        created.append(program_id)
        items.append({"work_id": work_id, "lane_id": spec["lane_id"], "status": "QUEUED"})
    return {"created": created, "existing_or_created": sorted(specs), "task_ids": [f"live-program:{p.lower()}" for p in specs]}


def _queue_work_for_lane(lane_id: str) -> list[dict[str, Any]]:
    try:
        rows = default_queue().load().get("items", [])
    except Exception:
        return []
    return [row for row in rows
            if str(row.get("lane_id") or "").upper() == str(lane_id).upper()
            and str(row.get("status") or "").upper() in {"QUEUED", "WAITING"}
            and not (row.get("next_eligible_at") and _parse_age(row.get("next_eligible_at"), _now()) == 0.0)]


def _queue_work_for_program(program_id: str, lane_id: str) -> list[dict[str, Any]]:
    """Return work belonging to this program, avoiding shared-lane inflation."""
    rows = _queue_work_for_lane(lane_id)
    if program_id == "SEO_SEARCH_INTELLIGENCE":
        return [row for row in rows if str(row.get("work_id", "")).startswith("live-program:seo_") or str(row.get("program_id", "")) == program_id]
    if program_id == "GITHUB_OPEN_SOURCE":
        return [row for row in rows if str(row.get("work_id", "")).startswith("live-program:github_") or str(row.get("program_id", "")) == program_id]
    if program_id == "YOUTUBE_INTELLIGENCE":
        return [row for row in rows if str(row.get("source_type", "")).upper().startswith("YOUTUBE") or str(row.get("work_id", "")).startswith("yt-")]
    if program_id == "BUSINESS_FUNDING":
        return [row for row in rows if str(row.get("lane_id")) == "FUNDING_LENDER" or "fund" in str(row.get("question") or row.get("title") or "").lower()]
    if program_id == "PROJECT_SUPPORT":
        return [row for row in rows if row.get("project_id") or str(row.get("work_id", "")).startswith("project-research:") or str(row.get("work_id", "")).startswith("department-request:")]
    if program_id == "RESEARCH_MORE":
        return [row for row in rows if row.get("alpha_followup_required") or str(row.get("work_id", "")).startswith("investigation:")]
    return [row for row in rows if str(row.get("program_id", "")) == program_id]


def _persist_program_service_state(rows: list[dict[str, Any]], contexts: dict[str, dict[str, Any]], selected_lane: str | None = None) -> None:
    prior = _read_program_service_state()
    now = _now().isoformat()
    state = {}
    for program_id, lane_id in LIVE_PROGRAM_LANES.items():
        row = next((item for item in rows if item.get("lane_id") == lane_id), {})
        context = contexts.get(lane_id, {})
        executable = len(_queue_work_for_program(program_id, lane_id))
        old = prior.get(program_id, {})
        selected = selected_lane == lane_id
        skips = 0 if selected else int(old.get("consecutive_skips", 0) or 0) + (1 if executable else 0)
        last_selected = row.get("last_run_at") or old.get("last_selected_at")
        last_result = old.get("last_substantive_result_at")
        source_state = _read_source_refresh_state()
        matching = [v for v in source_state.values() if v.get("lane_id") == lane_id and v.get("last_changed_at")]
        if matching:
            last_result = max((v.get("last_changed_at") for v in matching), default=last_result)
        blocked = bool(row.get("backoff_until") and _parse_age(row.get("backoff_until"), _now()) == 0.0)
        status = "BLOCKED" if blocked else "RESEARCH_PROGRAM_STARVATION" if executable and skips >= LIVE_SERVICE_WAKE_THRESHOLD else "ELIGIBLE"
        state[program_id] = {
            "program_id": program_id, "lane_id": lane_id, "eligible": bool(row.get("enabled", True)),
            "executable_work_count": executable, "last_selected_at": last_selected,
            "last_substantive_result_at": last_result, "consecutive_skips": skips,
            "deficit_or_priority_state": {"selection_count": int(row.get("selection_count", 0) or 0), "priority": row.get("priority")},
            "blocker": row.get("last_failure_reason") if blocked else None,
            "starvation_status": status, "updated_at": now,
        }
    _write_program_service_state(state)


def program_service_snapshot() -> dict[str, Any]:
    return _read_program_service_state()


def repair_legacy_research_more_residue() -> dict[str, Any]:
    """Park old runaway follow-ups without deleting their audit evidence."""
    queue = default_queue()
    store = queue.load()
    repaired = []
    for item in store.get("items", []):
        if not item.get("alpha_followup_required") or int(item.get("attempt_count", 0) or 0) <= int(item.get("max_attempts", 3) or 3):
            continue
        if str(item.get("status") or "").upper() in {"IN_PROGRESS", "QUEUED", "WAITING"}:
            item.update({"status": "PARKED", "completed_at": datetime.now(timezone.utc).isoformat(),
                         "last_result": {**(item.get("last_result") or {}), "classification": "PARKED_LEGACY",
                                          "reason": "legacy RESEARCH_MORE attempt count exceeded current bounded policy"},
                         "claimed_by": None, "claimed_at": None, "lease_expires_at": None, "attempt_id": None})
            repaired.append(str(item.get("work_id")))
        elif str((item.get("last_result") or {}).get("classification", "")) not in {"PARKED_LEGACY", "REJECTED_LEGACY", "NO_ACTION_LEGACY", "SUPERSEDED"}:
            item["legacy_followup_classification"] = "PARKED_LEGACY"
            repaired.append(str(item.get("work_id")))
    if repaired:
        queue._save(store)
    return {"repaired": repaired, "count": len(repaired), "audit_preserved": True}


def _sync_governed_priority_work(queue) -> None:
    """Project unfinished V2 assignments into the operational queue.

    Governed ledgers remain authoritative; this projection only gives the
    scheduler a durable work item and lease.  It intentionally excludes broad
    OPEN questions, which remain lower-priority monitoring/discovery material.
    """
    existing = {str(item.get("work_id")) for item in queue.load().get("items", [])}
    # Department evidence requests are durable Research work, not merely
    # inbox metadata.  Project queued requests into the same canonical queue
    # used by Alpha follow-ups and assigned objectives.  The request ledger
    # remains authoritative; this is an idempotent scheduling projection.
    for row in _read_governed("research_requests"):
        if str(row.get("status", "")).upper() not in {"QUEUED", "WAITING", "ACTIVE"}:
            continue
        request_id = str(row.get("request_id") or "").strip()
        objective_id = str(row.get("marketing_objective_id") or row.get("objective_id") or "").strip()
        if not request_id or not objective_id:
            continue
        work_id = f"department-request:{request_id}"
        if work_id in existing:
            continue
        queue.enqueue(
            work_id=work_id,
            work_class="ASSIGNED",
            priority=2,
            lane_id="BUSINESS_MARKET",
            source_type="RESEARCH_OBJECTIVE",
            source_id=request_id,
            title=row.get("question") or request_id,
            question=row.get("question"),
            source_candidates=[
                {"source_type": "WEB_PAGE", "source_id": "sba-loans", "source_url": "https://www.sba.gov/loans", "title": "SBA loan guidance"},
                {"source_type": "WEB_PAGE", "source_id": "fed-small-business-survey", "source_url": "https://www.fedsmallbusiness.org/survey", "title": "Federal Reserve Small Business Credit Survey"},
                {"source_type": "WEB_PAGE", "source_id": "cfpb-small-business", "source_url": "https://www.consumerfinance.gov/consumer-tools/small-business/", "title": "Consumer financial education for small businesses"},
            ],
            requested_by=row.get("requested_by", "department"),
            objective_id=objective_id,
            parent_request_id=request_id,
            marketing_objective_id=objective_id,
            department_target="MARKETING",
            required_work=True,
            alpha_followup_required=False,
            lifecycle="ONE_TIME",
            selection_reason="department_evidence_request",
            evidence_refs=[row.get("research_package_id")] if row.get("research_package_id") else [],
        )
        existing.add(work_id)
    investigations = _read_governed("research_v2_investigations")
    for row in investigations:
        if str(row.get("status", "")).upper() != "RESEARCH_MORE":
            continue
        work_id = f"investigation:{row.get('investigation_id')}"
        if work_id in existing:
            continue
        source_id = row.get("source_id")
        queue.enqueue(work_id=work_id, work_class="ASSIGNED", priority=3,
                      lane_id="YOUTUBE_CONTENT" if str(source_id or "").startswith(("PVd", "Tl", "Ld", "z_", "Nps")) else "BUSINESS_MARKET",
                      source_type="YOUTUBE_VIDEO" if str(source_id or "").startswith(("PVd", "Tl", "Ld", "z_", "Nps")) else "WEB_PAGE",
                      source_id=source_id, source_url=row.get("source_url") or row.get("canonical_url") or row.get("source_ref"),
                      title=row.get("title") or row.get("question") or row.get("investigation_id"),
                      question=row.get("question"), objective_id=row.get("investigation_id"), lifecycle="ONE_TIME",
                      requested_by="research_v2_investigation", selection_reason="unfinished_high_value_investigation",
                      alpha_followup_required=True, evidence_refs=[row.get("last_evidence_package_id")] if row.get("last_evidence_package_id") else [])
    for row in _read_governed("research_v2_mission_items"):
        if str(row.get("status", "")).upper() in {"ALREADY_COMPLETED", "COMPLETED", "BLOCKED_EXTERNAL_FINAL"}:
            continue
        work_id = f"mission-item:{row.get('item_id')}"
        if work_id in existing:
            continue
        queue.enqueue(work_id=work_id, work_class="ASSIGNED", priority=1, lane_id="YOUTUBE_CONTENT",
                      source_type="YOUTUBE_VIDEO", source_id=row.get("target_id"), source_url=row.get("canonical_url_or_reference"),
                      title=row.get("display_name"), mission_id=row.get("mission_id"), mission_item_id=row.get("item_id"),
                      requested_by="bounded_research_mission", selection_reason="assigned_request", lifecycle="ONE_TIME")


def _read_governed(name: str) -> list[dict[str, Any]]:
    path = GOVERNED / f"{name}.jsonl"
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return rows


def _parse_age(value: Any, now: datetime) -> float:
    if not value:
        return 0.0
    try:
        return max(0.0, (now - datetime.fromisoformat(str(value).replace("Z", "+00:00"))).total_seconds())
    except (TypeError, ValueError):
        return 0.0


def _lane_context(lane_id: str, now: datetime) -> dict[str, Any]:
    """Read only current V2 work; legacy research_questions is not used."""
    terms = LANE_TERMS.get(lane_id, ())
    watched_sources = 0
    if lane_id == "YOUTUBE_CONTENT":
        try:
            config = json.loads((ROOT / "configs/youtube_research_channels.json").read_text(encoding="utf-8"))
            watched_sources = sum(1 for row in config.get("channels", [])
                                  if isinstance(row, dict) and row.get("enabled") and row.get("approved_by_ray"))
        except (OSError, ValueError, TypeError):
            watched_sources = 0

    def matches(row: dict[str, Any]) -> bool:
        text = " ".join(str(row.get(k, "")) for k in ("source_id", "title", "domain", "intent", "question", "research_intents")) .lower()
        return not terms or any(term in text for term in terms)

    questions = [r for r in _read_governed("research_v2_questions")
                 if str(r.get("status", "")).upper() in {"OPEN", "WAITING_ON_EVIDENCE", "ACTIVE"} and matches(r)]
    investigations = [r for r in _read_governed("research_v2_investigations")
                      if (str(r.get("status", "")).upper() in {"OPEN", "ACTIVE", "IN_PROGRESS", "RESEARCH_MORE"}
                          or (not r.get("status") and r.get("decision") == "RESEARCH_MORE")) and matches(r)]
    followups = [r for r in _read_governed("research_v2_follow_ups")
                 if str(r.get("status", "")).upper() in {"OPEN", "ACTIVE", "WAITING_ON_EVIDENCE"} and matches(r)]
    theses = [r for r in (_read_governed("research_v2_opportunities") + _read_governed("research_v2_strategies"))
              if str(r.get("status", "")).upper() not in {"COMPLETED", "ARCHIVED", "REJECTED"} and matches(r)]
    materialities = [str(r.get("materiality", "")).upper() for r in questions + investigations]
    high = sum(x == "HIGH" for x in materialities)
    medium = sum(x == "MEDIUM" for x in materialities)
    timestamps = [r.get("last_activity") or r.get("updated_at") or r.get("recorded_at") for r in questions + investigations + followups + theses]
    oldest_age = max((_parse_age(x, now) for x in timestamps), default=0.0)
    mission_pending = 0
    if lane_id == "YOUTUBE_CONTENT":
        try:
            from bounded_research_missions import next_mission_item
            mission_pending = 1 if next_mission_item(source_type="YOUTUBE_VIDEO") else 0
        except Exception:
            mission_pending = 0
    executable_work_count = len(_queue_work_for_lane(lane_id))
    return {"high": high, "medium": medium, "questions": len(questions), "investigations": len(investigations),
            "followups": len(followups), "theses": len(theses), "oldest_age_seconds": oldest_age,
            "watched_sources": watched_sources, "mission_pending": mission_pending,
            "executable_work_count": executable_work_count}


def ensure_registry() -> list[dict[str, Any]]:
    prior = {str(row.get("lane_id")): row for row in _read() if isinstance(row, dict)}
    timestamp = _now().isoformat()
    rows = []
    for lane_id, name, priority in LANES:
        old = prior.get(lane_id, {})
        rows.append({**old, "schema_version": "nexus.research-lane.v1", "lane_id": lane_id,
                     "name": name, "priority": priority, "enabled": True,
                     "selection_count": int(old.get("selection_count", 0)),
                     "last_run_at": old.get("last_run_at"), "next_due_at": old.get("next_due_at"),
                     "open_work_count": int(old.get("open_work_count", 1)),
                     "last_selection_reason": old.get("last_selection_reason"),
                     "research_cycle_limit": RESEARCH_CYCLE_LIMIT,
                     "research_runtime_stop_condition": RESEARCH_RUNTIME_STOP_CONDITION,
                     "updated_at": timestamp})
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows


def _select_live_service_work(rows: list[dict[str, Any]], blocked_buckets: set[str], now: datetime) -> dict[str, Any] | None:
    """Guarantee bounded service for executable high-priority live programs."""
    contexts = {str(row["lane_id"]): _lane_context(str(row["lane_id"]), now) for row in rows}
    _persist_program_service_state(rows, contexts)
    state = _read_program_service_state()
    candidates = []
    for program_id, lane_id in LIVE_PROGRAM_LANES.items():
        row = next((item for item in rows if item.get("lane_id") == lane_id), None)
        context = contexts.get(lane_id, {})
        program_work = _queue_work_for_program(program_id, lane_id)
        if not row or not row.get("enabled") or not program_work:
            continue
        bucket = "youtube" if lane_id == "YOUTUBE_CONTENT" else "web"
        if bucket in blocked_buckets:
            continue
        service = state.get(program_id, {})
        if service.get("blocker"):
            continue
        # Queue priority is part of the live-service contract.  Skip debt is
        # still the fairness tie-breaker, but a newly assigned/high-priority
        # question must not be hidden behind a large low-priority monitoring
        # backlog (for example YouTube historical work).
        min_priority = min((int(item.get("priority", 50) or 50) for item in program_work), default=50)
        candidates.append((-min_priority,
                           int(service.get("consecutive_skips", 0) or 0),
                           0 if not service.get("last_selected_at") else 1,
                           str(service.get("last_selected_at") or ""), program_id, lane_id, row, context))
    if not candidates:
        return None
    # Highest queue priority first, then most-skipped/oldest.  The
    # lexicographic tie-break is stable and makes the bounded guarantee
    # deterministic across daemon restarts.
    _, _, _, _, program_id, lane_id, row, context = max(
        candidates, key=lambda value: (value[0], value[1], -value[2], value[3] or "", value[4])
    )
    claimed = None
    for item in sorted(_queue_work_for_lane(lane_id), key=lambda value: (int(value.get("priority", 50)), str(value.get("created_at") or ""))):
        claimed = default_queue().claim_work(str(item.get("work_id")), worker_id=f"research_scheduler:{os.getpid()}", lease_seconds=900)
        if claimed:
            break
    selected = claimed or dict(row)
    selected.update({"lane_id": lane_id, "program_id": program_id,
                     "name": row.get("name") or lane_id.replace("_", " ").title(),
                     "selected_work_class": selected.get("work_class") or "MONITORED",
                     "selection_reason": "bounded_live_program_service",
                     "fairness_gate": "LIVE_SERVICE_GUARANTEE",
                     "live_service_guarantee": {"program_id": program_id, "consecutive_skips": state.get(program_id, {}).get("consecutive_skips", 0), "threshold": LIVE_SERVICE_WAKE_THRESHOLD},
                     "selected_at": now.isoformat(), "research_cycle_limit": RESEARCH_CYCLE_LIMIT,
                     "research_runtime_stop_condition": RESEARCH_RUNTIME_STOP_CONDITION})
    updated = []
    for existing in rows:
        if existing.get("lane_id") == lane_id:
            updated.append({**existing, "selection_count": int(existing.get("selection_count", 0) or 0) + 1,
                            "last_run_at": now.isoformat(), "last_selection_reason": "bounded_live_program_service",
                            "selected_work_class": selected.get("selected_work_class")})
        else:
            updated.append(existing)
    REGISTRY_PATH.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    contexts[lane_id] = {**context, "executable_work_count": max(0, int(context.get("executable_work_count", 0)) - (1 if claimed else 0))}
    _persist_program_service_state(updated, contexts, selected_lane=lane_id)
    return selected


def select_lane(*, reason: str = "due_fairness_rotation", blocked_buckets: set[str] | None = None) -> dict[str, Any]:
    _hydrate_refresh_state_from_history()
    ensure_live_program_work()
    permanent_projection = ensure_permanent_source_work()
    rows = [row for row in ensure_registry() if row.get("enabled")]
    blocked_buckets = {str(bucket).lower() for bucket in (blocked_buckets or set())}

    # Global objective selection must precede live-program and lane/source
    # scoring. AI may reason inside the claimed task, never across objectives.
    priority_work = select_priority_work(worker_id=f"research_scheduler:{os.getpid()}", blocked_buckets=blocked_buckets)
    if priority_work:
        lane_id = str(priority_work.get("lane_id") or priority_work.get("category") or "BUSINESS_MARKET").upper()
        lane = next((row for row in rows if row.get("lane_id") == lane_id), None)
        priority_work.update({"lane_id": lane_id, "name": (lane or {}).get("name", lane_id.replace("_", " ").title()),
                              "selection_reason": "deterministic_objective_scheduler",
                              "selected_work_class": priority_work["work_class"], "priority_contract_rank": 0,
                              "selected_at": _now().isoformat(), "fairness_gate": "OBJECTIVE_CONTROLLER",
                              "research_cycle_limit": RESEARCH_CYCLE_LIMIT,
                              "research_runtime_stop_condition": RESEARCH_RUNTIME_STOP_CONDITION})
        return priority_work

    live_selected = _select_live_service_work(rows, blocked_buckets, _now())
    if live_selected:
        return live_selected

    # Empty queue is a continuation condition, not a terminal scheduler
    # result.  The previous implementation reached the generic lane fallback
    # before this purpose-level owner could run, leaving the daemon alive but
    # producing NO_ACTION_REQUIRED forever despite active permanent goals.
    queue_rows = default_queue().load().get("items", [])
    if not any(str(item.get("status") or "").upper() in {"QUEUED", "WAITING", "IN_PROGRESS"} for item in queue_rows):
        from nexus_agent_platform.research_continuation import continue_when_empty
        continuation = continue_when_empty(queue=default_queue())
        if continuation.get("generated"):
            claimed = default_queue().claim_next_for_objective(worker_id=f"research_scheduler:{os.getpid()}", allowed_classes={"ASSIGNED"}, blocked_buckets=blocked_buckets)
            if claimed:
                claimed.update({"lane_id": "BUSINESS_MARKET", "name": "Goal-directed Research", "selection_reason": "goal_generated", "selected_work_class": "ASSIGNED", "continuation": continuation})
                return claimed

    # A continuously replenished assigned/RESEARCH_MORE stream may not starve
    # standing lanes.  We defer one priority claim whenever an enabled lane is
    # materially behind the least-served lane.  The queued item remains intact
    # and is claimed on the next eligible turn; this is a scheduling decision,
    # not a rejection or stop condition.
    counts = [int(row.get("selection_count", 0) or 0) for row in rows]
    min_count = min(counts, default=0)
    max_count = max(counts, default=0)
    starvation_debt = max_count - min_count
    fair_rotation_required = starvation_debt >= 1 and any(
        int(row.get("selection_count", 0) or 0) == min_count and not row.get("backoff_until")
        for row in rows
    )
    def lane_bucket(row: dict[str, Any]) -> str:
        lane_id = str(row.get("lane_id") or "").upper()
        if lane_id == "YOUTUBE_CONTENT":
            return "youtube"
        if str(row.get("selected_work_class") or "").upper() in {"DEMAND_DISCOVERY", "GENERAL_DISCOVERY"}:
            return "discovery"
        return "web"

    if blocked_buckets:
        rows = [row for row in rows if lane_bucket(row) not in blocked_buckets]
        if not rows:
            return {"lane_id": "GENERAL_DISCOVERY", "name": "General Discovery", "priority": "P4",
                    "enabled": True, "selection_reason": "all_lane_buckets_at_capacity",
                    "selected_work_class": "GENERAL_DISCOVERY", "no_source_selected": True,
                    "selected_at": _now().isoformat()}
    now = _now()

    def age(row: dict[str, Any]) -> float:
        raw = row.get("last_run_at")
        if not raw:
            return 10**12
        try:
            return max(0.0, (now - datetime.fromisoformat(str(raw).replace("Z", "+00:00"))).total_seconds())
        except ValueError:
            return 10**12

    candidates = []
    for row in rows:
        backoff_until = row.get("backoff_until") or row.get("retry_after")
        if backoff_until and _parse_age(backoff_until, now) == 0.0:
            continue
        context = _lane_context(str(row["lane_id"]), now)
        last_age = age(row)
        age_signal = min(35.0, (last_age if last_age < 10**12 else 86400.0) / 3600.0 * 5.0)
        materiality_signal = min(60.0, context["high"] * 30.0 + context["medium"] * 15.0 + context["questions"] * 4.0)
        progression_signal = min(60.0, context["followups"] * 25.0 + context["theses"] * 20.0 + context["investigations"] * 5.0 + context.get("mission_pending", 0) * 35.0)
        # An approved monitored source is real scheduled work even before a
        # V2 question is attached to its next item. Four approved watchlist
        # channels therefore contribute up to 60 points, bounded like the
        # materiality signal, while fairness debt still prevents lane capture.
        monitored_source_signal = min(60.0, context.get("watched_sources", 0) * 15.0)
        # The current worker has one normal source per lane.  The source id is
        # recorded after the first real execution and then participates in
        # future eligibility.  Explicit high materiality or follow-up work
        # can justify a refresh; a generic thesis count alone cannot repeatedly
        # bypass the source cooldown when the lane has only one fixed source.
        source_id = str(row.get("last_source_id") or _latest_source_for_lane(str(row["lane_id"])))
        refresh = _source_refresh_snapshot(str(row["lane_id"]), source_id, now) if source_id else {}
        if refresh.get("terminal") and not (context["high"] or context["followups"]):
            continue
        progression_override = bool(context["high"] or context["followups"])
        duplicate_penalty = 0.0
        if refresh.get("cooling_down") and not progression_override:
            duplicate_penalty = min(90.0, 35.0 + 10.0 * int(refresh.get("consecutive_duplicate_count", 1) or 1))
        candidates.append((row, context, source_id, refresh,
                           materiality_signal + monitored_source_signal + progression_signal + age_signal - duplicate_penalty,
                           materiality_signal + monitored_source_signal, progression_signal, age_signal, duplicate_penalty))
    if not candidates:
        candidates = [(row, _lane_context(str(row["lane_id"]), now), "", {}, 0.0, 0.0, 0.0, 0.0, 0.0)
                      for row in rows if not _source_refresh_snapshot(str(row["lane_id"]), str(row.get("last_source_id", "")), now).get("terminal")]
    if not candidates:
        # Purpose sits above the queue.  When no eligible source or assigned
        # item remains, inspect active company goals and the Research charter
        # before falling back to a generic demand pass.
        from nexus_agent_platform.research_continuation import continue_when_empty
        continuation = continue_when_empty(queue=default_queue())
        if continuation.get("generated"):
            claimed = default_queue().claim_next_for_objective(worker_id=f"research_scheduler:{os.getpid()}", allowed_classes={"ASSIGNED"})
            if claimed:
                claimed.update({"lane_id": "BUSINESS_MARKET", "name": "Goal-directed Research",
                                "selection_reason": "goal_generated", "selected_work_class": "ASSIGNED",
                                "priority_contract_rank": 3, "selected_at": now.isoformat(),
                                "continuation": {"goal_id": continuation.get("goal", {}).get("goal_id"),
                                                  "generation_reason": continuation.get("reason")}})
                return claimed
        demand_work = _seed_demand_discovery_work(default_queue())
        if demand_work:
            claimed = default_queue().claim_next_for_objective(worker_id=f"research_scheduler:{os.getpid()}", allowed_classes={"DEMAND_DISCOVERY"})
            if claimed:
                claimed.update({"lane_id": "GENERAL_DISCOVERY", "name": "Customer Demand Discovery",
                                "selection_reason": "customer_demand_discovery", "selected_work_class": "DEMAND_DISCOVERY",
                                "priority_contract_rank": 6, "selected_at": now.isoformat()})
                return claimed
        # All one-time/parked sources are terminal. Keep the supervisor alive
        # without inventing another processing attempt; the next wake can be
        # driven by a durable assignment or a material-change override.
        return {"lane_id": "GENERAL_DISCOVERY", "name": "General Discovery", "priority": "P4",
                "enabled": True, "selection_reason": "queue_empty_no_nonterminal_source",
                "selected_work_class": "GENERAL_DISCOVERY", "no_source_selected": True,
                "selected_at": now.isoformat()}
    max_count = max(int(row.get("selection_count", 0)) for row, *_ in candidates)
    scored = []
    for row, context, source_id, refresh, base_score, materiality_signal, progression_signal, age_signal, duplicate_penalty in candidates:
        fairness_debt = min(40.0, max(0, max_count - int(row.get("selection_count", 0))) * 8.0)
        priority_signal = max(0.0, 30.0 - PRIORITY.get(str(row.get("priority", "P4")), 4) * 6.0)
        score = base_score + fairness_debt + priority_signal
        scored.append((score, row, context, source_id, refresh, materiality_signal, progression_signal, age_signal, fairness_debt, duplicate_penalty))
    if fair_rotation_required:
        least_served = [item for item in scored if int(item[1].get("selection_count", 0) or 0) == min_count]
        score, selected_row, context, source_id, refresh, materiality_signal, progression_signal, age_signal, fairness_debt, duplicate_penalty = max(
            least_served or scored, key=lambda x: (x[7], x[2].get("oldest_age_seconds", 0), str(x[1]["lane_id"])))
    else:
        score, selected_row, context, source_id, refresh, materiality_signal, progression_signal, age_signal, fairness_debt, duplicate_penalty = max(
            scored, key=lambda x: (x[0], -int(x[1].get("selection_count", 0)), str(x[1]["lane_id"])))
    selected = dict(selected_row)
    selected["selection_reason"] = "due_monitored_source" if context.get("watched_sources") or source_id else "general_discovery"
    selected["selected_work_class"] = "MONITORED"
    if context.get("mission_pending"):
        try:
            from bounded_research_missions import next_mission_item
            selected["mission_item"] = next_mission_item(source_type="YOUTUBE_VIDEO")
        except Exception:
            selected["mission_item"] = None
    selected["materiality_basis"] = {"high_items": context["high"], "medium_items": context["medium"], "open_questions": context["questions"], "watched_sources": context.get("watched_sources", 0)}
    selected["progression_basis"] = {"active_investigations": context["investigations"], "open_followups": context["followups"], "active_theses": context["theses"]}
    selected["age_basis"] = {"lane_age_seconds": round(age(selected), 3), "oldest_matching_item_seconds": round(context["oldest_age_seconds"], 3)}
    selected["fairness_basis"] = {"selection_count": int(selected.get("selection_count", 0)), "fairness_debt": round(fairness_debt, 3)}
    selected["duplicate_basis"] = {"source_id": source_id or None, "cooling_down": bool(refresh.get("cooling_down")), "consecutive_duplicate_count": int(refresh.get("consecutive_duplicate_count", 0) or 0), "duplicate_penalty": round(duplicate_penalty, 3), "override": bool(context["high"] or context["followups"])}
    selected["alternatives_considered"] = [{"lane_id": row["lane_id"], "score": round(item_score, 3)} for item_score, row, *_ in sorted(scored, reverse=True, key=lambda x: x[0])[1:4]]
    selected["starvation_age_seconds"] = age(selected)
    selected["selection_score"] = round(score, 3)
    selected["last_source_id"] = source_id or selected.get("last_source_id")
    selected["selection_explanation"] = {
        "why_selected": "highest explainable materiality/progression/age score after bounded fairness and duplicate cooldown",
        "materiality_basis": selected["materiality_basis"], "progression_basis": selected["progression_basis"],
        "age_basis": selected["age_basis"], "fairness_basis": selected["fairness_basis"], "duplicate_basis": selected["duplicate_basis"],
        "fairness_gate": "LEAST_SERVED_LANE" if fair_rotation_required else "NORMAL_SCORE",
    }
    selected["fairness_gate"] = "LEAST_SERVED_LANE" if fair_rotation_required else "NORMAL_SCORE"
    selected["research_cycle_limit"] = RESEARCH_CYCLE_LIMIT
    selected["research_runtime_stop_condition"] = RESEARCH_RUNTIME_STOP_CONDITION
    selected["selected_at"] = now.isoformat()
    selected["selection_count"] = int(selected.get("selection_count", 0)) + 1
    selected["last_run_at"] = selected["selected_at"]
    selected["next_due_at"] = (now + timedelta(seconds=30)).isoformat()
    selected["last_selection_reason"] = reason
    REGISTRY_PATH.write_text(json.dumps([selected if row["lane_id"] == selected["lane_id"] else row for row in rows], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return selected


def _seed_demand_discovery_work(queue) -> bool:
    """Seed one bounded demand pass only when no higher-class work is due."""
    work_id = "demand-discovery:governed-question-clusters"
    items = queue.load().get("items", [])
    if any(str(item.get("work_id")) == work_id for item in items):
        return False
    rows = _read_governed("research_v2_questions")
    demand_rows = [row for row in rows if any(term in str(row.get("question") or row.get("question_or_task") or "").lower()
                                              for term in ("customer", "demand", "funding", "credit", "lender", "loan", "revenue", "bankability"))]
    if len(demand_rows) < 2:
        return False
    queue.enqueue(work_id=work_id, work_class="DEMAND_DISCOVERY", priority=10,
                  source_type="DEMAND_QUERY", source_id="governed-question-clusters",
                  title="Bounded customer-demand discovery", question="Aggregate repeated governed demand questions",
                  requested_by="research_scheduler", selection_reason="customer_demand_discovery", lifecycle="ONE_TIME",
                  evidence_refs=[str(row.get("question_id") or row.get("source_id")) for row in demand_rows[:10]])
    return True


def mark_lane_backoff(lane_id: str, reason: str, *, seconds: int = 1200) -> None:
    """Temporarily remove a failed lane from competition after a retryable error."""
    rows = ensure_registry()
    until = (_now() + timedelta(seconds=max(30, seconds))).isoformat()
    for row in rows:
        if row.get("lane_id") == lane_id:
            row["backoff_until"] = until
            row["last_failure_reason"] = str(reason)[:500]
            row["last_failure_at"] = _now().isoformat()
    REGISTRY_PATH.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
