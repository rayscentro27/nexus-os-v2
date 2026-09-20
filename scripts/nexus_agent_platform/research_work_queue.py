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

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data/runtime/research_work_queue.json"
NEEDS_PATH = ROOT / "data/governed/research_needs.jsonl"

WORK_CLASSES = ("ASSIGNED", "MONITORED", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY")
STATUS = ("QUEUED", "IN_PROGRESS", "WAITING", "COMPLETE", "BLOCKED_EXTERNAL",
          "FAILED_RETRYABLE", "FAILED_FINAL", "PARKED", "MONITORING")
CLASS_PRIORITY = {"ASSIGNED": 0, "MONITORED": 4, "DEMAND_DISCOVERY": 6, "GENERAL_DISCOVERY": 7}


def concurrency_limits() -> dict[str, int]:
    """Return conservative worker caps without requiring a new supervisor."""
    return {
        "total": max(1, int(os.environ.get("NEXUS_RESEARCH_MAX_TOTAL_CONCURRENCY", "3"))),
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


def _default_store() -> dict[str, Any]:
    return {"schema_version": "nexus.research-work-queue.v1", "items": [], "updated_at": iso()}


class ResearchWorkQueue:
    """Small JSON-backed queue with restart-safe leases for bounded workers."""

    def __init__(self, path: Path | str = QUEUE_PATH, *, now_fn=utcnow) -> None:
        self.path = Path(path)
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
            "work_class": work_class,
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "source_url": item.get("source_url"),
            # Topic/objective work may be expanded by the governed repair
            # path into bounded public candidates.  The queue stores the
            # candidates; the existing worker still owns selection and
            # acquisition.
            "source_candidates": list(item.get("source_candidates", []) or []),
            "lane_id": item.get("lane_id"),
            "title": item.get("title"),
            "question": item.get("question"),
            "objective_id": item.get("objective_id"),
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
            "blocker_type": item.get("blocker_type"),
            "parent_request_id": item.get("parent_request_id"),
            "alpha_followup_required": bool(item.get("alpha_followup_required", False)),
            "department_target": item.get("department_target"),
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
            "selected_executor_id": item.get("selected_executor_id"),
            "ai_plan_id": item.get("ai_plan_id"),
            "ai_investigation_status": item.get("ai_investigation_status"),
            "ai_interpretation": item.get("ai_interpretation"),
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
        items.append(normalized)
        self._save(store)
        return normalized

    def enqueue(self, **fields: Any) -> dict[str, Any]:
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
        for item in store["items"]:
            if item.get("status") not in {"QUEUED", "WAITING"} or item.get("work_class") not in allowed:
                continue
            if blocked and worker_bucket(item) in blocked:
                continue
            due = parse_time(item.get("next_eligible_at"))
            if due and due > now:
                continue
            class_rank = CLASS_PRIORITY.get(item.get("work_class"), 99)
            candidates.append((class_rank, int(item.get("priority", 50)), parse_time(item.get("created_at")) or now, item))
        if not candidates:
            return None
        _, _, _, item = min(candidates, key=lambda value: (value[0], value[1], value[2]))
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
            if item.get("status") not in {"QUEUED", "WAITING"}:
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

    def settle(self, work_id: str, status: str, *, result: Any = None,
               blocker_type: str | None = None, next_eligible_at: str | None = None) -> dict[str, Any] | None:
        status = str(status).upper()
        if status not in STATUS:
            raise ValueError(f"unsupported work status: {status}")
        store = self.load()
        for item in store["items"]:
            if item.get("work_id") != work_id:
                continue
            ai_fields = {}
            if isinstance(result, dict):
                for field in ("ai_plan_id", "selected_executor_id", "ai_interpretation"):
                    if field in result:
                        ai_fields[field] = result[field]
            item.update({"status": status, "last_result": result, "blocker_type": blocker_type,
                         "next_eligible_at": next_eligible_at, "completed_at": iso(self._now()) if status in {"COMPLETE", "BLOCKED_EXTERNAL", "FAILED_FINAL", "PARKED"} else None,
                         "claimed_by": None, "claimed_at": None, "lease_expires_at": None, "attempt_id": None})
            item.update(ai_fields)
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

    def summary(self) -> dict[str, Any]:
        items = self.load().get("items", [])
        return {"queue_depth": len([x for x in items if x.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"}]),
                "by_class": {work_class: sum(1 for x in items if x.get("work_class") == work_class and x.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"}) for work_class in WORK_CLASSES},
                "by_status": {status: sum(1 for x in items if x.get("status") == status) for status in STATUS},
                "active": [dict(x) for x in items if x.get("status") == "IN_PROGRESS"],
                "blocked": [dict(x) for x in items if x.get("status") in {"BLOCKED_EXTERNAL", "FAILED_FINAL"}],
                "recent_completed": sorted(
                    [dict(x) for x in items if x.get("status") in {"COMPLETE", "PARKED"}],
                    key=lambda x: str(x.get("completed_at") or ""), reverse=True,
                )[:10],
                "next_queued": sorted(
                    [dict(x) for x in items if x.get("status") in {"QUEUED", "WAITING"}],
                    key=lambda x: (CLASS_PRIORITY.get(x.get("work_class"), 99), int(x.get("priority", 50)), str(x.get("created_at", ""))),
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
    return ResearchWorkQueue()


def priority_contract() -> list[str]:
    return ["ASSIGNED", "DEPARTMENT_REQUEST", "ALPHA_FOLLOWUP", "HIGH_VALUE_INVESTIGATION",
            "MONITORED_YOUTUBE", "MONITORED_CRITICAL", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY"]
