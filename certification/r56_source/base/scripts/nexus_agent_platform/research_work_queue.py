"""Durable Research work classes, leases, and demand-need projection.

This is an operational projection over the existing governed Research records;
it is not a replacement knowledge ledger.  The queue owns scheduling state and
leases while governed records continue to own evidence and provenance.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from nexus_agent_platform.runtime.paths import nexus_research_state_path

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = nexus_research_state_path("runtime", "research_work_queue.json")
NEEDS_PATH = nexus_research_state_path("governed", "research_needs.jsonl")

WORK_CLASSES = ("ASSIGNED", "MONITORED", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY")
STATUS = ("QUEUED", "IN_PROGRESS", "WAITING", "COMPLETE", "BLOCKED_EXTERNAL",
          "FAILED_RETRYABLE", "FAILED_FINAL", "PARKED", "MONITORING", "SUPERSEDED")
CLAIMABLE_STATUSES = {"QUEUED", "WAITING", "FAILED_RETRYABLE"}
PRIORITY_POLICY_PATH = ROOT / "configs/research_live_input_priority.json"
try:
    PRIORITY_POLICY = json.loads(PRIORITY_POLICY_PATH.read_text(encoding="utf-8"))
except (OSError, ValueError, TypeError):
    PRIORITY_POLICY = {}
CLASS_PRIORITY = {str(k): int(v) for k, v in
                  (PRIORITY_POLICY.get("work_class_rank") or
                   {"ASSIGNED": 0, "MONITORED": 1, "DEMAND_DISCOVERY": 2, "GENERAL_DISCOVERY": 3}).items()}
OBJECTIVE_RETRY_BASE_SECONDS = 15 * 60
OBJECTIVE_RETRY_MAX_SECONDS = 24 * 60 * 60
OBJECTIVE_FAIRNESS_QUANTUM = 2


def priority_rank(item: dict[str, Any]) -> int:
    """Apply the canonical Research input order inside the existing queue."""
    request_type = str(item.get("request_type") or "").upper()
    requested_by = str(item.get("requested_by") or "").upper()
    tier = str(item.get("priority_tier") or "").upper()
    details = " ".join(str(item.get(key) or "") for key in
                       ("selection_reason", "research_question", "question", "objective", "lifecycle")).upper()
    historical_markers = [str(x).upper() for x in PRIORITY_POLICY.get("historical_markers", [])]
    normalized_details = details.replace("_", " ")
    if item.get("archive_lane") == "HISTORICAL_BACKLOG" and not item.get("historical_reactivated_at"):
        return int(PRIORITY_POLICY.get("historical_backlog_rank", 6))
    if tier == "RAY_OR_DEPARTMENT_REQUEST":
        return int(PRIORITY_POLICY.get("ray_or_department_rank", 0))
    if tier == "RAY_REQUESTED" or request_type.startswith("RAY") or requested_by.startswith("RAY"):
        return int(PRIORITY_POLICY.get("ray_requested_rank", 0))
    if tier == "DEPARTMENT_REQUESTED" or request_type.startswith("DEPARTMENT") or requested_by.startswith("DEPARTMENT"):
        return int(PRIORITY_POLICY.get("department_request_rank", 1))
    if tier == "ACTIVE_GOAL_FOLLOW_UP" or item.get("parent_queue_item_id") or item.get("parent_goal_id") or \
            item.get("parent_research_id") or item.get("followup_of") or \
            any(token in request_type for token in ("FOLLOW_UP", "FOLLOWUP", "CONTINUATION", "GAP_CLOSURE")):
        return int(PRIORITY_POLICY.get("active_goal_follow_up_rank", 2))
    if item.get("work_class") == "MONITORED" and item.get("monitor_mode") in {None, "NEW_CONTENT_ONLY"}:
        return int(PRIORITY_POLICY.get("fresh_monitored_source_rank", 3))
    viral_text = " ".join(str(item.get(key) or "") for key in
                           ("objective_id", "lane_id", "category", "objective", "question")).upper()
    if "VIRAL_TREND_DISCOVERY" in viral_text:
        return int(PRIORITY_POLICY.get("viral_trend_discovery_rank", 5))
    if tier in {"HISTORICAL_BACKLOG", "ARCHIVED_BACKLOG"} or any(marker.replace("_", " ") in normalized_details for marker in historical_markers):
        return int(PRIORITY_POLICY.get("historical_backlog_rank", 6))
    return CLASS_PRIORITY.get(str(item.get("work_class") or ""), 99)


def is_historical_backlog(item: dict[str, Any]) -> bool:
    """Archived history stays inert until an explicit, recorded reactivation."""
    if item.get("historical_reactivated_at"):
        return False
    if item.get("archive_lane") == "HISTORICAL_BACKLOG" or str(item.get("priority_tier") or "").upper() in {"HISTORICAL_BACKLOG", "ARCHIVED_BACKLOG"}:
        return True
    details = " ".join(str(item.get(key) or "") for key in
                        ("selection_reason", "research_question", "question", "objective", "lifecycle")).upper().replace("_", " ")
    return any(str(marker).upper().replace("_", " ") in details
               for marker in PRIORITY_POLICY.get("historical_markers", []))


def is_claimable(item: dict[str, Any]) -> bool:
    """Exhausted same-route failures wait for an explicit reroute/recovery."""
    status = str(item.get("status") or "").upper()
    exhausted = bool(item.get("retry_exhausted"))
    if status == "FAILED_RETRYABLE":
        exhausted = exhausted or int(item.get("attempt_count", 0) or 0) >= int(item.get("max_attempts", 3) or 3)
    if status == "QUEUED":
        exhausted = exhausted or int(item.get("attempt_count", 0) or 0) >= int(item.get("max_attempts", 3) or 3)
    return status in CLAIMABLE_STATUSES and not exhausted

PERMANENT_FAILURE_MARKERS = (
    "unknown url type",
    "http error 404",
    "http error 410",
    "source not found",
    "source deleted",
    "video unavailable",
    "unsupported source",
)


def permanence_evidence(result: Any = None, blocker_type: str | None = None) -> str | None:
    """Return explicit permanence evidence; retry exhaustion is not evidence."""
    if isinstance(result, dict):
        if result.get("permanent_failure") is True:
            return str(result.get("permanence_evidence") or result.get("error") or "explicit_permanent_failure")
        evidence = result.get("permanence_evidence")
        if evidence:
            return str(evidence)
        error = str(result.get("error") or result.get("message") or "").lower()
    else:
        error = str(result or "").lower()
    blocker = str(blocker_type or "").upper()
    if blocker in {"SOURCE_NOT_FOUND_CONFIRMED", "MALFORMED_SOURCE_URL", "UNSUPPORTED_SOURCE_CONFIRMED"}:
        return blocker
    for marker in PERMANENT_FAILURE_MARKERS:
        if marker in error:
            return marker
    return None


def concurrency_limits() -> dict[str, int]:
    """Return conservative worker caps without requiring a new supervisor."""
    return {
        # V2 research expansion must honor the owner safety ceiling even when
        # an inherited environment variable contains the former value of 3.
        "total": min(2, max(1, int(os.environ.get("NEXUS_RESEARCH_MAX_TOTAL_CONCURRENCY", "2")))),
        "youtube": max(1, int(os.environ.get("NEXUS_RESEARCH_MAX_YOUTUBE_CONCURRENCY", "1"))),
        "web": max(1, int(os.environ.get("NEXUS_RESEARCH_MAX_WEB_CONCURRENCY", "1"))),
        "discovery": max(1, int(os.environ.get("NEXUS_RESEARCH_MAX_DISCOVERY_CONCURRENCY", "1"))),
    }


def worker_bucket(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_type") or "").upper()
    work_class = str(item.get("work_class") or "").upper()
    if source_type.startswith("YOUTUBE") or str(item.get("lane_id") or "").upper() == "YOUTUBE_CONTENT":
        return "youtube"
    if work_class in {"DEMAND_DISCOVERY", "GENERAL_DISCOVERY"} or source_type in {"DEMAND_QUERY", "DISCOVERY"}:
        return "discovery"
    return "web"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat()


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"


def objective_key(item: dict[str, Any]) -> str:
    """Return the deterministic global scheduling key for one work item."""
    explicit = str(item.get("objective_id") or item.get("marketing_objective_id") or "").strip()
    if explicit:
        return explicit
    lane = str(item.get("lane_id") or "").strip().upper()
    if lane:
        return f"permanent:{lane}"
    return f"work-class:{str(item.get('work_class') or 'GENERAL_DISCOVERY').upper()}"


def _default_store() -> dict[str, Any]:
    return {"schema_version": "nexus.research-work-queue.v1", "items": [], "updated_at": iso()}


class ResearchWorkQueue:
    """Small JSON-backed queue with restart-safe leases for bounded workers."""

    def __init__(self, path: Path | str | None = None, *, now_fn=utcnow) -> None:
        self.path = Path(path) if path is not None else nexus_research_state_path(
            "runtime", "research_work_queue.json")
        self.now_fn = now_fn

    def _now(self) -> datetime:
        return self.now_fn()

    def load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("items"), list):
                return value
        except (OSError, ValueError, TypeError):
            pass
        return _default_store()

    def _save(self, store: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        store["updated_at"] = iso(self._now())
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(store, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def normalize(item: dict[str, Any]) -> dict[str, Any]:
        work_class = str(item.get("work_class", "GENERAL_DISCOVERY")).upper()
        if work_class not in WORK_CLASSES:
            raise ValueError(f"unsupported work_class: {work_class}")
        status = str(item.get("status", "QUEUED")).upper()
        if status not in STATUS:
            raise ValueError(f"unsupported work status: {status}")
        now = iso()
        result = {
            "work_id": str(item.get("work_id") or stable_id("work", item)),
            "research_work_id": str(item.get("research_work_id") or item.get("work_id") or stable_id("work", item)),
            "queue_sequence": item.get("queue_sequence"),
            "request_type": item.get("request_type") or item.get("research_mode") or "MANUAL_PROJECT",
            "priority_tier": item.get("priority_tier"),
            "category": item.get("category") or item.get("lane_id") or "OTHER",
            "work_class": work_class,
            "source_type": item.get("source_type"),
            "source_name": item.get("source_name") or item.get("title") or item.get("source_id"),
            "source_id": item.get("source_id"),
            "source_url": item.get("source_url"),
            # NotebookLM Research work uses this same durable FIFO. Preserve
            # the processor/profile routing contract through normalization so
            # the canonical dispatcher cannot silently downgrade it to the
            # generic document-ingestion path.
            "research_profile_id": item.get("research_profile_id"),
            "research_processor": item.get("research_processor"),
            "notebook_reference": item.get("notebook_reference"),
            "notebook_id": item.get("notebook_id") or item.get("notebook_reference"),
            "exact_research_question": item.get("exact_research_question") or item.get("research_question") or item.get("question"),
            "recommended_research_method": item.get("recommended_research_method"),
            "research_session_id": item.get("research_session_id"),
            "default_profile_hint": item.get("default_profile_hint"),
            "default_notebook_hint": item.get("default_notebook_hint"),
            "target_departments": list(item.get("target_departments", []) or []),
            "source_qualification": item.get("source_qualification"),
            # Topic/objective work may be expanded by the governed repair
            # path into bounded public candidates.  The queue stores the
            # candidates; the existing worker still owns selection and
            # acquisition.
            "source_candidates": list(item.get("source_candidates", []) or []),
            "lane_id": item.get("lane_id"),
            "title": item.get("title"),
            "question": item.get("question"),
            # Nova assignments carry a semantic route contract. Preserve it
            # through the durable Research FIFO so operational requests can
            # never be downgraded to untyped search text by normalization.
            "requested_intent": item.get("requested_intent"),
            "routed_intent": item.get("routed_intent"),
            "execution_path": item.get("execution_path"),
            "objective_type": item.get("objective_type"),
            "research_scope": item.get("research_scope"),
            "notebook_operation": item.get("notebook_operation"),
            "notebook_prompt": item.get("notebook_prompt"),
            "objective": item.get("objective") or item.get("title") or item.get("objective_id"),
            "original_objective": item.get("original_objective") or item.get("objective") or item.get("title"),
            "original_source_url": item.get("original_source_url") or item.get("source_url"),
            "original_source_type": item.get("original_source_type"),
            "source_type": item.get("source_type"),
            "current_research_context": item.get("current_research_context") or {},
            "research_question": item.get("research_question") or item.get("question"),
            "research_instructions": item.get("research_instructions") or item.get("why_this_research"),
            "required_tool": item.get("required_tool") or item.get("required_capabilities", [None])[0] if item.get("required_capabilities") else item.get("required_tool"),
            "required_capability": item.get("required_capability") or (item.get("required_capabilities") or [None])[0],
            "expected_output": item.get("expected_output"),
            "objective_id": item.get("objective_id"),
            "project_id": item.get("project_id"),
            "parent_goal_id": item.get("parent_goal_id"),
            "research_case_id": item.get("research_case_id"),
            "mission_id": item.get("mission_id"),
            "mission_item_id": item.get("mission_item_id"),
            "requested_by": item.get("requested_by", "scheduler"),
            "priority": int(item.get("priority", 50)),
            "status": status,
            "created_at": item.get("created_at", now),
            "started_at": item.get("started_at"),
            "completed_at": item.get("completed_at"),
            "next_eligible_at": item.get("next_eligible_at"),
            "attempt_count": int(item.get("attempt_count", 0) or 0),
            "max_attempts": int(item.get("max_attempts", 3) or 3),
            "last_result": item.get("last_result"),
            "result_id": item.get("result_id"),
            "artifact_id": item.get("artifact_id"),
            "blocker_type": item.get("blocker_type"),
            "parent_request_id": item.get("parent_request_id"),
            "parent_queue_item_id": item.get("parent_queue_item_id"),
            "parent_research_id": item.get("parent_research_id") or item.get("parent_finding_id") or item.get("parent_request_id"),
            "followup_of": item.get("followup_of") or item.get("parent_research_id") or item.get("parent_finding_id"),
            "alpha_followup_required": bool(item.get("alpha_followup_required", False)),
            "department_target": item.get("department_target") or item.get("department") or item.get("DEPARTMENT"),
            "department": item.get("department") or item.get("DEPARTMENT") or item.get("department_target"),
            "marketing_objective_id": item.get("marketing_objective_id"),
            "evidence_refs": list(item.get("evidence_refs", []) or []),
            "selection_reason": item.get("selection_reason"),
            "claimed_by": item.get("claimed_by"),
            "claimed_at": item.get("claimed_at"),
            "lease_expires_at": item.get("lease_expires_at"),
            "attempt_id": item.get("attempt_id"),
            "lifecycle": item.get("lifecycle", "MONITORED"),
            "source_purpose": item.get("source_purpose"),
            "unchanged_count": int(item.get("unchanged_count", 0) or 0),
            "required_capabilities": list(item.get("required_capabilities", []) or []),
            "required_work": item.get("required_work"),
            "work_role": item.get("work_role"),
            "selected_executor_id": item.get("selected_executor_id"),
            "ai_plan_id": item.get("ai_plan_id"),
            "ai_investigation_status": item.get("ai_investigation_status"),
            "ai_interpretation": item.get("ai_interpretation"),
            "dedup_key": item.get("dedup_key"),
            "why_it_matters": item.get("why_it_matters"),
            "unknown_to_resolve": item.get("unknown_to_resolve"),
            "evidence_gaps": list(item.get("evidence_gaps", []) or []),
            "stop_condition": item.get("stop_condition"),
            "program_id": item.get("program_id"),
            "channel_id": item.get("channel_id"),
            "channel_name": item.get("channel_name"),
            "channel_url": item.get("channel_url"),
            "monitor_mode": item.get("monitor_mode"),
            "published_at": item.get("published_at"),
            "selection_reason": item.get("selection_reason"),
            "backfill_rank": item.get("backfill_rank"),
            "research_mode": item.get("research_mode"), "WHY_THIS_RESEARCH": item.get("WHY_THIS_RESEARCH"),
            "TRIGGER": item.get("TRIGGER"), "DEPARTMENT": item.get("DEPARTMENT") or item.get("department"),
            "BUSINESS_OR_NEXUS": item.get("BUSINESS_OR_NEXUS"), "PARENT_GOAL": item.get("PARENT_GOAL"),
            "PROJECT": item.get("PROJECT") or item.get("project_id"), "QUESTION": item.get("QUESTION") or item.get("question"),
            "EXPECTED_VALUE": item.get("EXPECTED_VALUE"), "SOURCE_PLAN": list(item.get("SOURCE_PLAN", []) or []),
            "alpha_eligible": bool(item.get("alpha_eligible", False)), "alpha_review_required": bool(item.get("alpha_review_required", False)),
            "followup_department": str(item.get("followup_department") or "").upper() or None,
            "alpha_followup_required": bool(item.get("alpha_followup_required", False)),
            "parent_finding_id": item.get("parent_finding_id"), "parent_alpha_receipt_id": item.get("parent_alpha_receipt_id"),
            "parent_alpha_request_id": item.get("parent_alpha_request_id"), "parent_handoff_id": item.get("parent_handoff_id"),
            "owner": item.get("owner"), "mission": item.get("mission"), "why_this_research": item.get("why_this_research"),
            "missing_evidence": list(item.get("missing_evidence", []) or []), "source_classes": list(item.get("source_classes", []) or []),
            "preferred_sources": list(item.get("preferred_sources", []) or []), "fallback_sources": list(item.get("fallback_sources", []) or []),
            "return_target": item.get("return_target"), "state": item.get("state"), "last_attempt": item.get("last_attempt"),
            "next_action": item.get("next_action"), "max_attempts": int(item.get("max_attempts", 3) or 3),
            "archive_lane": item.get("archive_lane"),
            "historical_archive": item.get("historical_archive"),
            "historical_reactivated_at": item.get("historical_reactivated_at"),
            "historical_reactivation": item.get("historical_reactivation"),
            # Business Opportunity Research V2 intake and adaptive loop state
            # live on the existing queue item; the queue remains authoritative.
            "opportunity_id": item.get("opportunity_id"),
            "opportunity_intake_id": item.get("opportunity_intake_id"),
            "entry_type": item.get("entry_type"),
            "source_role": item.get("source_role"),
            "opportunity_relationship": item.get("opportunity_relationship"),
            "promotion_status": item.get("promotion_status"),
            "director_mode": item.get("director_mode"),
            "discovery_questions": list(item.get("discovery_questions", []) or []),
            "notebook_role": item.get("notebook_role"),
            "research_checkpoint": item.get("research_checkpoint"),
            "selected_provider": item.get("selected_provider"),
            "selected_route_id": item.get("selected_route_id"),
            "route_history": list(item.get("route_history", []) or []),
            "retry_exhausted": bool(item.get("retry_exhausted", False)),
        }
        return result

    def upsert(self, item: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalize(item)
        store = self.load()
        items = store["items"]
        for index, existing in enumerate(items):
            if existing.get("work_id") == normalized["work_id"]:
                items[index] = {**existing, **normalized}
                self._save(store)
                return items[index]
        if normalized.get("queue_sequence") is None:
            normalized["queue_sequence"] = max((int(row.get("queue_sequence", 0) or 0) for row in items), default=0) + 1
        items.append(normalized)
        self._save(store)
        return normalized

    def migrate_fifo(self) -> dict[str, Any]:
        """Assign durable FIFO sequence numbers without reordering history."""
        store = self.load()
        changed = 0
        next_sequence = 1
        for index, item in enumerate(store["items"]):
            original = dict(item)
            normalized = self.normalize(item)
            item.update(normalized)
            source_url = str(item.get("source_url") or "").lower()
            source_type = str(item.get("source_type") or "").upper()
            if source_type in {"", "WEB_PAGE", "RESEARCH_OBJECTIVE"}:
                if "youtube.com/watch" in source_url or "youtu.be/" in source_url:
                    item["source_type"] = "YOUTUBE_VIDEO"
                elif "youtube.com/@" in source_url or "youtube.com/channel/" in source_url:
                    item["source_type"] = "YOUTUBE_CHANNEL"
                elif "tradingview.com" in source_url:
                    item["source_type"] = "TRADINGVIEW_STRATEGY"
                elif "github.com/" in source_url:
                    item["source_type"] = "GITHUB_REPO"
                elif source_url.endswith(".pdf"):
                    item["source_type"] = "PDF"
            if not item.get("required_tool"):
                tool_map = {"YOUTUBE_VIDEO": "YOUTUBE", "YOUTUBE_CHANNEL": "YOUTUBE",
                            "TRADINGVIEW_STRATEGY": "TRADINGVIEW", "TRADINGVIEW_INDICATOR": "TRADINGVIEW",
                            "GITHUB_REPO": "GITHUB", "GITHUB_SEARCH": "GITHUB", "PDF": "PDF", "DOCUMENT": "DOCUMENT"}
                item["required_tool"] = tool_map.get(str(item.get("source_type") or "").upper(), "WEB")
            if not item.get("request_type") or item.get("request_type") == "MANUAL_PROJECT":
                item["request_type"] = {"YOUTUBE_VIDEO": "YOUTUBE_VIDEO", "YOUTUBE_CHANNEL": "YOUTUBE_CHANNEL",
                                         "TRADINGVIEW_STRATEGY": "TRADINGVIEW_STRATEGY", "GITHUB_REPO": "GITHUB_REPO",
                                         "PDF": "PDF", "DOCUMENT": "DOCUMENT"}.get(str(item.get("source_type") or "").upper(), item.get("request_type") or "MANUAL_PROJECT")
            if item != original:
                changed += 1
            # Normalize legacy objective wrappers before FIFO execution. The
            # first governed candidate is the assigned source; alternates stay
            # attached for an explicit retry/fallback record and are never
            # chosen by an AI planner.
            if str(item.get("source_type") or "").upper() == "RESEARCH_OBJECTIVE":
                candidates = [row for row in (item.get("source_candidates") or [])
                              if isinstance(row, dict) and row.get("source_url")]
                if candidates and not item.get("source_url"):
                    candidate = candidates[0]
                    item.update({
                        "source_type": candidate.get("source_type", "WEB_PAGE"),
                        "source_id": candidate.get("source_id") or item.get("source_id"),
                        "source_url": candidate.get("source_url"),
                        "source_name": candidate.get("title") or item.get("title") or item.get("source_id"),
                        "title": candidate.get("title") or item.get("title"),
                        "required_tool": candidate.get("required_tool") or item.get("required_tool"),
                        "category": item.get("category") or item.get("lane_id") or "OTHER",
                    })
                    changed += 1
            value = item.get("queue_sequence")
            if value is None:
                item["queue_sequence"] = next_sequence
                changed += 1
            next_sequence = max(next_sequence, int(item.get("queue_sequence", next_sequence) or next_sequence) + 1)
        store["next_queue_sequence"] = next_sequence
        store["fifo_mode"] = True
        if changed or not self.load().get("fifo_mode"):
            self._save(store)
        return {"changed": changed, "next_queue_sequence": next_sequence,
                "total_items": len(store["items"]), "fifo_mode": True}

    def enqueue(self, **fields: Any) -> dict[str, Any]:
        """Create once by stable work_id; duplicate intake never resets progress."""
        work_id = str(fields.get("work_id") or "")
        if not work_id:
            raise ValueError("work_id_required")
        existing = next((row for row in self.load().get("items", [])
                         if str(row.get("work_id") or "") == work_id), None)
        if existing:
            return existing
        return self.upsert(fields)

    def recover_expired_leases(self) -> int:
        store = self.load()
        now = self._now()
        recovered = 0
        for item in store["items"]:
            if item.get("status") != "IN_PROGRESS":
                continue
            expires = parse_time(item.get("lease_expires_at"))
            if expires and expires <= now:
                item.update({"status": "QUEUED", "claimed_by": None, "claimed_at": None,
                             "lease_expires_at": None, "attempt_id": None})
                recovered += 1
        if recovered:
            self._save(store)
        return recovered

    def claim_next(self, *, worker_id: str, allowed_classes: Iterable[str] | None = None,
                   blocked_buckets: Iterable[str] | None = None, lease_seconds: int = 900) -> dict[str, Any] | None:
        self.recover_expired_leases()
        store = self.load()
        now = self._now()
        allowed = {str(value).upper() for value in allowed_classes} if allowed_classes else set(WORK_CLASSES)
        blocked = {str(value).lower() for value in blocked_buckets} if blocked_buckets else set()
        candidates = []
        for index, item in enumerate(store["items"]):
            if is_historical_backlog(item) or not is_claimable(item) or item.get("work_class") not in allowed:
                continue
            if blocked and worker_bucket(item) in blocked:
                continue
            due = parse_time(item.get("next_eligible_at"))
            if due and due > now:
                continue
            candidates.append((priority_rank(item), int(item.get("priority", 50) or 50),
                               int(item.get("queue_sequence", index + 1) or index + 1), item))
        if not candidates:
            return None
        # Preserve FIFO within each canonical tier so old backlog age cannot
        # outrank current requested, follow-up, monitored, or discovery work.
        _, _, _, item = min(candidates, key=lambda value: value[:3])
        attempt_id = stable_id("attempt", (item["work_id"], iso(now), worker_id))
        item.update({"status": "IN_PROGRESS", "started_at": item.get("started_at") or iso(now),
                     "attempt_count": int(item.get("attempt_count", 0)) + 1,
                     "claimed_by": worker_id, "claimed_at": iso(now),
                     "lease_expires_at": iso(now + timedelta(seconds=max(30, lease_seconds))),
                     "attempt_id": attempt_id})
        self._save(store)
        return dict(item)

    def claim_work(self, work_id: str, *, worker_id: str, lease_seconds: int = 900) -> dict[str, Any] | None:
        """Claim one explicitly assigned item without changing queue ordering."""
        self.recover_expired_leases()
        store = self.load()
        now = self._now()
        for item in store["items"]:
            if item.get("work_id") != work_id:
                continue
            if is_historical_backlog(item) or not is_claimable(item):
                return None
            due = parse_time(item.get("next_eligible_at"))
            if due and due > now:
                return None
            attempt_id = stable_id("attempt", (work_id, iso(now), worker_id))
            item.update({"status": "IN_PROGRESS", "started_at": item.get("started_at") or iso(now),
                         "attempt_count": int(item.get("attempt_count", 0)) + 1,
                         "claimed_by": worker_id, "claimed_at": iso(now),
                         "lease_expires_at": iso(now + timedelta(seconds=max(30, lease_seconds))),
                         "attempt_id": attempt_id})
            self._save(store)
            return dict(item)
        return None

    def select_objective(self, *, allowed_classes: Iterable[str] | None = None,
                         blocked_buckets: Iterable[str] | None = None) -> dict[str, Any] | None:
        """Select the next objective without consulting an AI planner."""
        self.recover_expired_leases()
        store = self.load()
        now = self._now()
        allowed = {str(value).upper() for value in allowed_classes} if allowed_classes else set(WORK_CLASSES)
        blocked = {str(value).lower() for value in blocked_buckets} if blocked_buckets else set()
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in store.get("items", []):
            if is_historical_backlog(item) or not is_claimable(item) or item.get("work_class") not in allowed:
                continue
            if blocked and worker_bucket(item) in blocked:
                continue
            due = parse_time(item.get("next_eligible_at"))
            if due and due > now:
                continue
            groups.setdefault(objective_key(item), []).append(item)
        if not groups:
            return None

        objective_counts = store.get("objective_selection_counts") or {}
        last_objective = str(store.get("last_objective_id") or "")
        streak = int(store.get("last_objective_streak", 0) or 0)
        ordered = sorted(groups)

        def objective_sort(key: str) -> tuple[int, int, float, int, str]:
            rows = groups[key]
            class_rank = min(priority_rank(row) for row in rows)
            priority = min(int(row.get("priority", 50) or 50) for row in rows)
            oldest = min(parse_time(row.get("created_at")) or now for row in rows)
            age_seconds = max(0.0, (now - oldest).total_seconds())
            served = int(objective_counts.get(key, 0) or 0)
            return class_rank, priority, -age_seconds, served, key

        chosen_key: str | None = None
        if last_objective in groups and streak >= OBJECTIVE_FAIRNESS_QUANTUM and len(groups) > 1:
            start = ordered.index(last_objective)
            for offset in range(1, len(ordered) + 1):
                candidate = ordered[(start + offset) % len(ordered)]
                if candidate in groups:
                    chosen_key = candidate
                    break
        if chosen_key is None:
            chosen_key = min(ordered, key=objective_sort)
        rows = sorted(groups[chosen_key], key=lambda row: (
            priority_rank(row),
            int(row.get("priority", 50) or 50),
            parse_time(row.get("created_at")) or now,
            str(row.get("work_id") or ""),
        ))
        return {"objective_id": chosen_key, "work_id": rows[0].get("work_id"),
                "eligible_work_count": len(rows),
                "objective_selection_count": int(objective_counts.get(chosen_key, 0) or 0),
                "objective_selection_reason": "deterministic_objective_scheduler"}

    def objective_availability_state(self, *, allowed_classes: Iterable[str] | None = None,
                                     blocked_buckets: Iterable[str] | None = None) -> str:
        """Return CLAIMABLE, PENDING_BUT_UNAVAILABLE, or NONE deterministically."""
        self.recover_expired_leases()
        store = self.load()
        now = self._now()
        allowed = {str(value).upper() for value in allowed_classes} if allowed_classes else set(WORK_CLASSES)
        blocked = {str(value).lower() for value in blocked_buckets} if blocked_buckets else set()
        pending_statuses = CLAIMABLE_STATUSES | {"IN_PROGRESS"}
        pending = False
        for item in store.get("items", []):
            if is_historical_backlog(item):
                continue
            if item.get("work_class") not in allowed or item.get("status") not in pending_statuses:
                continue
            pending = True
            if not is_claimable(item):
                continue
            due = parse_time(item.get("next_eligible_at"))
            if due and due > now:
                continue
            if blocked and worker_bucket(item) in blocked:
                continue
            return "CLAIMABLE"
        return "PENDING_BUT_UNAVAILABLE" if pending else "NONE"

    def claim_next_for_objective(self, *, worker_id: str,
                                 allowed_classes: Iterable[str] | None = None,
                                 blocked_buckets: Iterable[str] | None = None,
                                 lease_seconds: int = 900) -> dict[str, Any] | None:
        """Claim exactly one item from the controller-selected objective."""
        selection = self.select_objective(allowed_classes=allowed_classes, blocked_buckets=blocked_buckets)
        if not selection:
            return None
        objective_id = selection["objective_id"]
        store = self.load()
        now = self._now()
        allowed = {str(value).upper() for value in allowed_classes} if allowed_classes else set(WORK_CLASSES)
        blocked = {str(value).lower() for value in blocked_buckets} if blocked_buckets else set()
        candidates = []
        for item in store.get("items", []):
            if is_historical_backlog(item) or objective_key(item) != objective_id or not is_claimable(item):
                continue
            if item.get("work_class") not in allowed or (blocked and worker_bucket(item) in blocked):
                continue
            due = parse_time(item.get("next_eligible_at"))
            if due and due > now:
                continue
            candidates.append(item)
        if not candidates:
            return None
        item = min(candidates, key=lambda row: (
            priority_rank(row),
            int(row.get("priority", 50) or 50),
            parse_time(row.get("created_at")) or now,
            str(row.get("work_id") or ""),
        ))
        attempt_id = stable_id("attempt", (item["work_id"], iso(now), worker_id))
        item.update({"status": "IN_PROGRESS", "started_at": item.get("started_at") or iso(now),
                     "attempt_count": int(item.get("attempt_count", 0)) + 1,
                     "claimed_by": worker_id, "claimed_at": iso(now),
                     "lease_expires_at": iso(now + timedelta(seconds=max(30, lease_seconds))),
                     "attempt_id": attempt_id})
        counts = dict(store.get("objective_selection_counts") or {})
        counts[objective_id] = int(counts.get(objective_id, 0) or 0) + 1
        store["objective_selection_counts"] = counts
        store["last_objective_streak"] = int(store.get("last_objective_streak", 0) or 0) + 1 if store.get("last_objective_id") == objective_id else 1
        store["last_objective_id"] = objective_id
        store["objective_cursor"] = objective_id
        self._save(store)
        return {**dict(item), "objective_id": item.get("objective_id") or objective_id,
                "scheduler_objective_id": objective_id,
                "scheduler_selection_reason": selection["objective_selection_reason"]}

    def settle(self, work_id: str, status: str, *, result: Any = None,
               blocker_type: str | None = None, next_eligible_at: str | None = None) -> dict[str, Any] | None:
        status = str(status).upper()
        if status not in STATUS:
            raise ValueError(f"unsupported work status: {status}")
        store = self.load()
        for item in store["items"]:
            if item.get("work_id") != work_id:
                continue
            permanence = permanence_evidence(result, blocker_type)
            if status == "FAILED_FINAL" and not permanence:
                status = "FAILED_RETRYABLE"
            failure_history = list(item.get("failure_history") or [])
            if status in {"FAILED_RETRYABLE", "FAILED_FINAL"}:
                failure_history.append({
                    "at": iso(self._now()), "attempt_count": int(item.get("attempt_count", 0) or 0),
                    "requested_status": str(status), "error": (result or {}).get("error") if isinstance(result, dict) else result,
                    "blocker_type": blocker_type, "permanence_evidence": permanence,
                })
                failure_history = failure_history[-50:]
            ai_fields = {}
            if isinstance(result, dict):
                for field in ("ai_plan_id", "selected_executor_id", "ai_interpretation"):
                    if field in result:
                        ai_fields[field] = result[field]
            if status in {"FAILED_RETRYABLE", "WAITING"} and next_eligible_at is None:
                attempt = int(item.get("attempt_count", 0) or 0)
                max_attempts = int(item.get("max_attempts", 3) or 3)
                if permanence:
                    status = "FAILED_FINAL"
                    next_eligible_at = None
                else:
                    # Exhausting the current route records route exhaustion but
                    # does not prove the source is permanently unavailable.
                    delay = min(OBJECTIVE_RETRY_BASE_SECONDS * (2 ** max(0, attempt - 1)), OBJECTIVE_RETRY_MAX_SECONDS)
                    next_eligible_at = iso(self._now() + timedelta(seconds=delay))
            item.update({"status": status, "last_result": result, "blocker_type": blocker_type,
                         "failure_history": failure_history,
                         "finality_evidence": permanence,
                         "retry_exhausted": bool(status == "FAILED_RETRYABLE" and int(item.get("attempt_count", 0) or 0) >= int(item.get("max_attempts", 3) or 3)),
                         "next_eligible_at": next_eligible_at, "completed_at": iso(self._now()) if status in {"COMPLETE", "BLOCKED_EXTERNAL", "FAILED_FINAL", "PARKED", "SUPERSEDED"} else None,
                         "claimed_by": None, "claimed_at": None, "lease_expires_at": None, "attempt_id": None})
            item.update(ai_fields)
            self._save(store)
            return dict(item)
        return None

    def reclassify_recoverable_final(self, work_id: str, *, reason: str,
                                     next_eligible_at: str | None = None) -> dict[str, Any] | None:
        """Move one evidence-supported final failure back to durable retry."""
        store = self.load()
        for item in store["items"]:
            if item.get("work_id") != work_id or item.get("status") != "FAILED_FINAL":
                continue
            history = list(item.get("failure_history") or [])
            history.append({"at": iso(self._now()), "event": "RECLASSIFIED_RECOVERABLE",
                            "previous_status": "FAILED_FINAL", "reason": reason,
                            "previous_last_result": item.get("last_result"),
                            "previous_attempt_count": item.get("attempt_count")})
            item.update({"status": "FAILED_RETRYABLE", "completed_at": None,
                         "next_eligible_at": next_eligible_at or iso(self._now() + timedelta(seconds=OBJECTIVE_RETRY_BASE_SECONDS)),
                         "claimed_by": None, "claimed_at": None, "lease_expires_at": None,
                         "attempt_id": None, "retry_exhausted": True,
                         "reclassification": {"status": "RECOVERABLE", "reason": reason, "at": iso(self._now())},
                         "failure_history": history[-50:]})
            self._save(store)
            return dict(item)
        return None

    def reroute_recoverable(self, work_id: str, *, provider: str, reason: str,
                            route_id: str | None = None, max_reroutes: int = 2) -> dict[str, Any] | None:
        """Resume an exhausted recoverable item on a different approved route.

        Same-route retries remain bounded by ``max_attempts``.  A provider
        change is explicit, recorded, and bounded separately; it never clears
        permanent-failure evidence or creates another queue item.
        """
        if not str(provider).strip() or not str(reason).strip():
            raise ValueError("reroute_requires_provider_and_reason")
        store = self.load()
        for item in store["items"]:
            if item.get("work_id") != work_id:
                continue
            if item.get("status") not in {"FAILED_RETRYABLE", "WAITING", "BLOCKED_EXTERNAL"}:
                return None
            if item.get("finality_evidence") or permanence_evidence(item.get("last_result"), item.get("blocker_type")):
                return None
            history = list(item.get("route_history") or [])
            reroutes = [row for row in history if row.get("event") == "REROUTE"]
            if len(reroutes) >= max(0, int(max_reroutes)):
                return None
            current = str(item.get("selected_provider") or item.get("provider") or "").strip()
            if current and current.casefold() == provider.strip().casefold():
                return None
            history.append({"event": "REROUTE", "from_provider": current or None,
                "to_provider": provider.strip(), "route_id": route_id,
                "reason": reason[:500], "at": iso(self._now())})
            item.update({"status": "WAITING", "attempt_count": 0,
                "retry_exhausted": False, "next_eligible_at": iso(self._now()),
                "selected_provider": provider.strip(), "selected_route_id": route_id,
                "route_history": history[-20:], "claimed_by": None,
                "claimed_at": None, "lease_expires_at": None, "attempt_id": None,
                "completed_at": None,
                "last_result": {"rerouted": True, "provider": provider.strip(), "reason": reason[:500]}})
            self._save(store)
            return dict(item)
        return None

    def release(self, work_id: str, *, reason: str = "worker_cap") -> dict[str, Any] | None:
        """Return a claim to the queue when a bounded worker slot is full."""
        store = self.load()
        for item in store["items"]:
            if item.get("work_id") != work_id:
                continue
            if item.get("status") == "IN_PROGRESS":
                item.update({"status": "QUEUED", "last_result": {"released": reason},
                             "claimed_by": None, "claimed_at": None,
                             "lease_expires_at": None, "attempt_id": None})
                self._save(store)
            return dict(item)
        return None

    def reactivate_historical(self, work_id: str, *, requested_by: str, reason: str) -> dict[str, Any] | None:
        """Explicitly reopen one archived item, keeping its history and reason."""
        if not str(requested_by).strip() or not str(reason).strip():
            raise ValueError("historical_reactivation_requires_requester_and_reason")
        store = self.load()
        for item in store["items"]:
            if item.get("work_id") != work_id or not is_historical_backlog(item):
                continue
            item.update({
                "status": "QUEUED", "priority_tier": "HISTORICAL_BACKLOG",
                "historical_reactivated_at": iso(self._now()),
                "historical_reactivation": {"requested_by": requested_by, "reason": reason},
                "next_eligible_at": iso(self._now()), "claimed_by": None,
                "claimed_at": None, "lease_expires_at": None, "attempt_id": None,
            })
            self._save(store)
            return dict(item)
        return None

    def summary(self) -> dict[str, Any]:
        items = self.load().get("items", [])
        return {"queue_depth": len([x for x in items if (is_claimable(x) or x.get("status") == "IN_PROGRESS")]),
                "by_class": {work_class: sum(1 for x in items if x.get("work_class") == work_class and (is_claimable(x) or x.get("status") == "IN_PROGRESS")) for work_class in WORK_CLASSES},
                "by_status": {status: sum(1 for x in items if x.get("status") == status) for status in STATUS},
                "active": [dict(x) for x in items if x.get("status") == "IN_PROGRESS"],
                "blocked": [dict(x) for x in items if x.get("status") in {"BLOCKED_EXTERNAL", "FAILED_FINAL"}],
                "recent_completed": sorted(
                    [dict(x) for x in items if x.get("status") in {"COMPLETE", "PARKED"}],
                    key=lambda x: str(x.get("completed_at") or ""), reverse=True,
                )[:10],
                "next_queued": sorted(
                    [dict(x) for x in items if is_claimable(x)],
                    key=lambda x: (priority_rank(x), int(x.get("priority", 50)), str(x.get("created_at", ""))),
                )[:10]}

    def create_need(self, *, audience: str, problem: str, question: str,
                    desired_outcome: str, source_refs: list[str],
                    where_customers_congregate: list[str], demand_signals: list[str],
                    evidence_gaps: list[str], commercial_intent: str = "UNKNOWN",
                    existing_solutions: list[str] | None = None,
                    pain_points: list[str] | None = None,
                    terminology: list[str] | None = None,
                    competitor_promises: list[str] | None = None,
                    competitor_complaints: list[str] | None = None,
                    confidence: str = "PRELIMINARY") -> dict[str, Any]:
        """Create one deduplicated customer-need projection, not one row/comment."""
        need_id = stable_id("need", (audience.strip().lower(), problem.strip().lower()))
        record = {"schema_version": "nexus.research-need.v1", "need_id": need_id,
                  "audience": audience, "problem": problem, "question": question,
                  "desired_outcome": desired_outcome, "pain_points": pain_points or [], "terminology": terminology or [],
                  "demand_signals": demand_signals, "commercial_intent": commercial_intent,
                  "source_refs": source_refs, "where_customers_congregate": where_customers_congregate,
                  "existing_solutions": existing_solutions or [], "competitor_promises": competitor_promises or [],
                  "competitor_complaints": competitor_complaints or [], "confidence": confidence,
                  "evidence_gaps": evidence_gaps, "status": "OPEN", "alpha_review_required": True,
                  "created_at": iso(), "updated_at": iso()}
        existing = []
        if NEEDS_PATH.exists():
            for line in NEEDS_PATH.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    if isinstance(row, dict): existing.append(row)
                except json.JSONDecodeError:
                    continue
        if not any(row.get("need_id") == need_id for row in existing):
            NEEDS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with NEEDS_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record


def default_queue() -> ResearchWorkQueue:
    return ResearchWorkQueue(nexus_research_state_path("runtime", "research_work_queue.json"))


def priority_contract() -> list[str]:
    return ["ASSIGNED", "DEPARTMENT_REQUEST", "ALPHA_FOLLOWUP", "HIGH_VALUE_INVESTIGATION",
            "MONITORED_YOUTUBE", "MONITORED_CRITICAL", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY"]
