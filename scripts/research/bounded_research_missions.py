"""Finite Research assignments layered over continuous Research watchlists.

Mission state is append-only and derived from mission-item projections.  A
watchlist remains recurring monitoring; a mission has a finite item set and a
terminal completion rule.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Iterable

from nexus_agent_platform.governed.persistence import append_record, get_record, read_records

NONTERMINAL = {"PENDING", "READY", "CLAIMED", "IN_PROGRESS", "FAILED_RETRYABLE", "ASR_REQUIRED", "WAITING_ON_EVIDENCE"}
TERMINAL = {"COMPLETED", "ALREADY_COMPLETED", "BLOCKED_EXTERNAL_FINAL", "FAILED_FINAL", "SKIPPED_WITH_RECORDED_REASON"}
MISSION_TYPES = {"FINITE_RESEARCH_ASSIGNMENT", "BOUNDED_RESEARCH_MISSION"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(repr(value).encode()).hexdigest()[:20]}"


def _latest_items(mission_id: str) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in read_records("research_v2_mission_items"):
        if str(row.get("mission_id")) == mission_id and row.get("item_id") and row["item_id"] not in latest:
            latest[str(row["item_id"])] = row
    return list(latest.values())


def mission_counts(mission_id: str) -> dict[str, int]:
    items = _latest_items(mission_id)
    statuses = [str(x.get("status", "PENDING")).upper() for x in items]
    return {
        "total_items": len(items),
        "completed_items": sum(x in {"COMPLETED", "ALREADY_COMPLETED"} for x in statuses),
        "in_progress_items": sum(x in {"CLAIMED", "IN_PROGRESS"} for x in statuses),
        "remaining_items": sum(x in NONTERMINAL for x in statuses),
        "blocked_items": sum(x == "BLOCKED_EXTERNAL_FINAL" for x in statuses),
        "failed_retryable_items": sum(x == "FAILED_RETRYABLE" for x in statuses),
        "failed_final_items": sum(x == "FAILED_FINAL" for x in statuses),
    }


def mission_status(mission_id: str) -> str:
    counts = mission_counts(mission_id)
    if counts["remaining_items"] == 0 and counts["in_progress_items"] == 0 and counts["failed_retryable_items"] == 0:
        if counts["failed_final_items"] or counts["blocked_items"]:
            return "PARTIAL"
        return "COMPLETED"
    if counts["in_progress_items"] or counts["completed_items"]:
        return "ACTIVE"
    return "PENDING"


def reconcile_mission(mission_id: str) -> dict[str, Any]:
    mission = get_record("research_v2_missions", mission_id, key="mission_id") or {"mission_id": mission_id}
    counts = mission_counts(mission_id)
    status = mission_status(mission_id)
    update = {**mission, **counts, "status": status, "updated_at": _now()}
    if status == "ACTIVE" and not mission.get("started_at"):
        update["started_at"] = _now()
    if status in {"COMPLETED", "PARTIAL"} and not mission.get("completed_at"):
        update["completed_at"] = _now()
    if any(mission.get(k) != update.get(k) for k in (*counts, "status")):
        append_record("research_v2_missions", update)
    return update


def create_mission(*, title: str, description: str, source_type: str, items: Iterable[dict[str, Any]], parent_links: dict[str, Any] | None = None) -> dict[str, Any]:
    item_specs = [dict(x) for x in items]
    mission_id = _id("mission", (title, [(x.get("target_type"), x.get("target_id")) for x in item_specs]))
    existing = get_record("research_v2_missions", mission_id, key="mission_id")
    if existing:
        return reconcile_mission(mission_id)
    append_record("research_v2_missions", {"schema_version": "nexus.research-v2-mission.v1", "mission_id": mission_id, "title": title, "description": description, "mission_type": "FINITE_RESEARCH_ASSIGNMENT", "source_type": source_type, "created_at": _now(), "status": "PENDING", "parent_links": parent_links or {}, **{k: 0 for k in ("total_items", "completed_items", "in_progress_items", "remaining_items", "blocked_items", "failed_retryable_items", "failed_final_items")}})
    for spec in item_specs:
        item_id = str(spec.get("item_id") or _id("mission_item", (mission_id, spec.get("target_type"), spec.get("target_id"))))
        status = str(spec.get("status", "PENDING")).upper()
        append_record("research_v2_mission_items", {"schema_version": "nexus.research-v2-mission-item.v1", "item_id": item_id, "mission_id": mission_id, "target_type": spec.get("target_type", "SOURCE"), "target_id": spec.get("target_id"), "display_name": spec.get("display_name", spec.get("target_id")), "canonical_url_or_reference": spec.get("canonical_url_or_reference"), "status": status, "attempt_count": int(spec.get("attempt_count", 0)), "last_attempt_at": spec.get("last_attempt_at"), "last_result": spec.get("last_result"), "block_reason": spec.get("block_reason"), "next_action": spec.get("next_action", "verify channel and process one representative video"), "completed_at": _now() if status in TERMINAL else None, "completion_evidence": spec.get("completion_evidence", {})})
    return reconcile_mission(mission_id)


def next_mission_item(*, source_type: str = "") -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    rank = {"PENDING": 0, "READY": 1, "ASR_REQUIRED": 2, "WAITING_ON_EVIDENCE": 3, "FAILED_RETRYABLE": 4}
    candidates = []
    for mission in read_records("research_v2_missions"):
        if str(mission.get("status")) not in {"PENDING", "ACTIVE"}:
            continue
        for item in _latest_items(str(mission["mission_id"])):
            status = str(item.get("status", "PENDING"))
            if status not in {"PENDING", "READY", "FAILED_RETRYABLE", "ASR_REQUIRED", "WAITING_ON_EVIDENCE"}:
                continue
            if status == "FAILED_RETRYABLE" and item.get("next_eligible_at"):
                try:
                    if datetime.fromisoformat(str(item["next_eligible_at"])) > now:
                        continue
                except ValueError:
                    pass
            if not source_type or str(mission.get("source_type")) == source_type:
                candidates.append((rank.get(status, 9), item))
    return min(candidates, key=lambda pair: (pair[0], pair[1].get("last_attempt_at") or ""))[1] if candidates else None


def claim_item(item_id: str, *, worker_id: str) -> dict[str, Any] | None:
    for item in read_records("research_v2_mission_items"):
        if str(item.get("item_id")) == item_id:
            if str(item.get("status", "PENDING")) not in {"PENDING", "READY", "FAILED_RETRYABLE", "ASR_REQUIRED", "WAITING_ON_EVIDENCE"}:
                return None
            claimed = {**item, "status": "IN_PROGRESS", "attempt_count": int(item.get("attempt_count", 0)) + 1, "last_attempt_at": _now(), "claimed_by": worker_id}
            append_record("research_v2_mission_items", claimed)
            return claimed
    return None


def record_item_result(item_id: str, *, status: str, result: Any, next_action: str = "") -> dict[str, Any] | None:
    current = next((x for x in read_records("research_v2_mission_items") if str(x.get("item_id")) == item_id), None)
    if not current or str(status).upper() not in NONTERMINAL | TERMINAL:
        return None
    normalized_status = str(status).upper()
    updated = {**current, "status": normalized_status, "last_result": result, "next_action": next_action or current.get("next_action")}
    if isinstance(result, dict) and isinstance(result.get("completion_evidence"), dict):
        updated["completion_evidence"] = {**(current.get("completion_evidence") or {}), **result["completion_evidence"]}
    if normalized_status == "FAILED_RETRYABLE":
        updated["next_eligible_at"] = (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat()
    else:
        updated.pop("next_eligible_at", None)
    if updated["status"] in TERMINAL:
        updated["completed_at"] = _now()
    append_record("research_v2_mission_items", updated)
    reconcile_mission(str(current["mission_id"]))
    return updated


def completion_criteria() -> list[str]:
    return ["canonical identity verified", "one eligible representative video discovered", "one real video processed successfully", "Research V2 package persisted", "claims/methods/opportunities/questions extracted", "knowledge comparison attempted", "source reputation created or updated", "material follow-up need persisted"]


def admin_contract() -> dict[str, Any]:
    return {"read": ["research_v2_missions", "research_v2_mission_items", "research_v2_mission_reports"], "write": ["create_mission", "claim_item", "record_item_result"], "pause": "NOT_IMPLEMENTED", "resume": "NOT_IMPLEMENTED", "cancel": "NOT_IMPLEMENTED"}
