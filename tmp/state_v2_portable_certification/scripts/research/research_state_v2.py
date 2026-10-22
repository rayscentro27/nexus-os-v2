"""Bounded Research current-state and partitioned history persistence.

Production current state reuses the governed ``research_proactive_memory``
table, keyed by ``memory_id``. Isolated certification uses a namespace-local
SQLite file. No normal operation reads or writes the legacy runtime JSONL.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import tempfile
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.runtime.paths import nexus_research_state_path

try:
    from social import _supabase as supabase
except Exception:  # pragma: no cover
    supabase = None

MAX_CURRENT_RECORD_BYTES = 256 * 1024
MAX_HISTORY_EVENT_BYTES = 64 * 1024
MAX_HISTORY_PARTITION_BYTES = 64 * 1024 * 1024
# Four exact path probes cover the authoritative active segment, a stale hint,
# one interrupted/adjacent rotation, and the next writable segment. More probes
# require explicit recovery rather than work proportional to archive age.
MAX_HISTORY_SEGMENT_PROBES = 4
MAX_QUERY_ROWS = 100
MAX_CONTROL_ROWS = 20_000
CURRENT_FIELDS = (
    "memory_id", "memory_kind", "objective_id", "query_family", "recorded_at",
    "query_id:payload->>query_id", "event_id:payload->>event_id", "objective_key:payload->>objective_key",
    "query:payload->>query", "run_at:payload->>run_at", "created_at:payload->>created_at",
    "source_strategy_id:payload->>source_strategy_id", "result_identity:payload->>result_identity",
    "objective_type:payload->>objective_type", "topic:payload->>topic",
    "business_priority:payload->>business_priority", "department_request:payload->>department_request",
    "open_questions:payload->open_questions", "result_ids:payload->result_ids",
    "results_seen:payload->>results_seen", "new_results:payload->>new_results",
    "duplicate_results:payload->>duplicate_results", "sources_seen:payload->>sources_seen",
    "findings_created:payload->>findings_created", "novel_findings:payload->>novel_findings",
    "saturation_state:payload->>saturation_state",
    "case_id:payload->>case_id", "project_id:payload->>project_id",
    "work_id:payload->>work_id", "job_id:payload->>job_id",
    "status:payload->>status", "turn:payload->>turn",
    "case_schema_version:payload->>case_schema_version",
)


class StateV2Error(RuntimeError):
    pass


class CurrentStateUnavailable(StateV2Error):
    pass


class StateWriteFailure(StateV2Error):
    pass


class HistoryPartitionFailure(StateV2Error):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _certification() -> bool:
    return bool(os.environ.get("NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT", "").strip())


def _state_root() -> Path:
    if _certification():
        cert_root = Path(os.environ["NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT"]).expanduser().resolve()
        effective = Path(os.environ.get("NEXUS_RESEARCH_STATE_ROOT", "")).expanduser().resolve()
        if effective != cert_root:
            raise ValueError("CERTIFICATION_RESEARCH_STATE_ROOT_MISMATCH")
        return cert_root / "state_v2"
    return nexus_research_state_path("state_v2")


def _archive_root() -> Path:
    if _certification():
        return Path(os.environ["NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT"]).expanduser().resolve() / "history" / "research"
    return nexus_research_state_path("history", "research")


def _bounded_record(state: dict[str, Any]) -> dict[str, Any]:
    # Current state carries the operational case and bounded result references;
    # event history owns the transition trail. Never silently truncate identity
    # or lineage fields to satisfy the storage bound.
    row = dict(state)
    row.setdefault("recorded_at", _now())
    row.setdefault("schema_version", "nexus.research-current-state.v2")
    if not row.get("latest_synthesis_ref") and isinstance(row.get("syntheses"), list) and row["syntheses"]:
        latest = row["syntheses"][-1]
        if isinstance(latest, dict):
            row["latest_synthesis_ref"] = latest.get("synthesis_id") or latest.get("id") or latest.get("recorded_at")
    if not row.get("latest_advisor_result_ref") and isinstance(row.get("current_advisor_attempt"), dict):
        attempt = row["current_advisor_attempt"]
        row["latest_advisor_result_ref"] = attempt.get("result_reference") or attempt.get("review_id") or attempt.get("attempt_id")
    encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    if len(encoded) > MAX_CURRENT_RECORD_BYTES - 128:
        # Keep operational answers and lineage; reduce bulky evidence to stable
        # references/summaries already represented by their source/finding IDs.
        for field in ("sources", "results", "latest_results",
                      "needle_results", "advisor_attempts", "question_answers"):
            values = row.get(field)
            if not isinstance(values, list): continue
            compact = []
            for item in values[:200]:
                if not isinstance(item, dict): continue
                keep = {key: item[key] for key in ("source_id", "research_source_id", "finding_id", "review_id",
                    "attempt_id", "job_id", "synthesis_id", "needle_id", "id", "url", "canonical_url",
                    "title", "source_class", "extraction_status", "status", "evidence_ids", "identity",
                    "question_id", "answer_id", "confidence", "provider", "result_reference",
                    "created_at", "recorded_at") if key in item}
                summary = item.get("summary") or item.get("claim") or item.get("text")
                if summary: keep["summary"] = str(summary)[:500]
                if item.get("answer") is not None: keep["answer"] = item.get("answer")
                compact.append(keep)
            row[field] = compact
        for field in ("latest_synthesis", "synthesis", "advisor_result", "latest_advisor_result"):
            value = row.get(field)
            if isinstance(value, dict):
                refs = {key: value[key] for key in ("id", "synthesis_id", "review_id", "attempt_id", "job_id", "recorded_at", "created_at", "status") if key in value}
                for key in ("summary", "recommendation", "conclusion"):
                    if value.get(key): refs[key] = str(value[key])[:4000]
                row[field] = refs
        for field in ("current_advisor_attempt", "latest_advisor_attempt", "needle_result", "latest_needle_result"):
            value = row.get(field)
            if isinstance(value, dict):
                row[field] = {key: value[key] for key in ("review_id", "attempt_id", "job_id", "needle_id",
                    "result_id", "result_reference", "status", "provider", "created_at", "recorded_at") if key in value}
        encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str).encode()
        if len(encoded) > MAX_CURRENT_RECORD_BYTES - 128:
            raise ValueError(f"CURRENT_STATE_RECORD_TOO_LARGE:{len(encoded)}>{MAX_CURRENT_RECORD_BYTES}")
    return row


def _event_for(row: dict[str, Any], event_type: str | None = None) -> dict[str, Any]:
    def refs(primary: str, *fallbacks: str) -> list[str]:
        value = row.get(primary)
        if isinstance(value, list): return [str(item)[:160] for item in value[:100] if item]
        for name in fallbacks:
            items = row.get(name)
            if isinstance(items, dict): items = [items]
            if isinstance(items, list):
                result = []
                for item in items[:100]:
                    if isinstance(item, dict):
                        identity = next((item.get(key) for key in ("source_id", "research_source_id", "finding_id", "id", "review_id", "attempt_id", "synthesis_id") if item.get(key)), None)
                        identity = identity or item.get("recorded_at") or item.get("created_at")
                    else: identity = item
                    if identity: result.append((name + ":" + str(identity))[:160])
                return result
        return []
    event = {
        "event_id": str(row.get("event_id") or "evt_" + hashlib.sha256(
            (str(row.get("memory_id")) + ":" + str(row.get("recorded_at"))).encode()).hexdigest()[:24]),
        "timestamp": str(row.get("recorded_at") or _now()),
        "case_id": row.get("case_id"), "objective_id": row.get("objective_id"),
        "project_id": row.get("project_id") or row.get("work_id"), "job_id": row.get("job_id"),
        "event_type": event_type or str(row.get("event_type") or row.get("memory_kind") or "STATE_UPDATED"),
        "previous_state": row.get("previous_state"),
        "new_state": {key: row.get(key) for key in (
            "status", "turn", "open_questions", "question_answers", "current_advisor_attempt",
            "latest_advisor_result_ref", "needle_status", "needle_result_ref", "latest_synthesis_ref",
            "source_count", "finding_count", "last_activity_at", "blocked_by", "lineage_refs")
            if key in row},
        "attempt_refs": refs("attempt_refs", "advisor_attempts", "current_advisor_attempt"),
        "receipt_refs": refs("receipt_refs", "receipt_references"),
        "source_refs": refs("source_refs", "sources", "source_ids"),
        "advisor_refs": refs("advisor_refs", "advisor_attempts", "current_advisor_attempt", "latest_advisor_review"),
        "needle_refs": refs("needle_refs", "needle_results", "needle_result"),
        "synthesis_refs": refs("synthesis_refs", "syntheses", "latest_synthesis"),
    }
    encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    if len(encoded) > MAX_HISTORY_EVENT_BYTES:
        raise ValueError(f"HISTORY_EVENT_TOO_LARGE:{len(encoded)}>{MAX_HISTORY_EVENT_BYTES}")
    event["event_sha256"] = hashlib.sha256(encoded).hexdigest()
    if len(json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str).encode()) > MAX_HISTORY_EVENT_BYTES:
        raise ValueError(f"HISTORY_EVENT_TOO_LARGE_AFTER_INTEGRITY_FIELD:{MAX_HISTORY_EVENT_BYTES}")
    return event


def _emit_failure(code: str, state: dict[str, Any], detail: str) -> None:
    """Route a schema-shaped recovery event without recursing through state writes."""
    event_id = "re_" + hashlib.sha256(
        f"{code}:{state.get('memory_id')}:{state.get('recorded_at')}".encode()).hexdigest()[:24]
    event = {"schema_version": "nexus.recovery-event.v1", "event_id": event_id,
        "occurred_at": _now(), "objective_id": state.get("objective_id"),
        "project_id": state.get("project_id") or state.get("work_id"), "job_id": state.get("job_id"),
        "case_id": state.get("case_id"), "department": "RESEARCH", "job_type": "RESEARCH_STATE_PERSISTENCE",
        "failure_domain": "RESEARCH_STATE", "current_state": code, "expected_state": "STATE_AND_HISTORY_CONSISTENT",
        "last_successful_transition": None, "failed_transition": "CURRENT_STATE_AND_HISTORY_COMMIT",
        "error_code": code, "error_summary": ("Research State v2 persistence requires reconciliation: " + detail)[:1000],
        "attempt_count": 0, "recent_attempts": [], "available_capabilities": ["BOUNDED_STATE_RECONCILIATION"],
        "authorized_actions": ["PAUSE_HEAVY_WORK", "REQUEST_CODEX_SPECIALIST", "VERIFY_RECOVERY"],
        "prohibited_actions": ["TERMINATE_OBJECTIVE", "DELETE_HISTORY", "UNAPPROVED_SPEND", "BYPASS_GOVERNANCE"],
        "cost_boundary": {"incremental_spend_authorized": False, "max_incremental_cost": 0},
        "evidence_references": [str(_pending_path(event_id))],
        "relevant_self_knowledge": ["Pending outbox is durable and replayable; no objective termination is authorized."],
        "objective_termination_authorized": False}
    try:
        from nexus_agent_platform.stability_supervisor import route_recovery_event
        route_recovery_event(event, artifact_ref=event["evidence_references"][0])
    except Exception:
        # Preserve a compact diagnostic if the Supervisor store itself is
        # unavailable. This file is outside Research history and does not recurse.
        path = _state_root() / "recovery_events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            handle.flush(); os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _upsert_current(row: dict[str, Any]) -> dict[str, Any]:
    memory_id = str(row.get("memory_id") or "")
    if not memory_id:
        raise ValueError("CURRENT_STATE_MEMORY_ID_REQUIRED")
    if _certification():
        root = Path(os.environ["NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT"]).expanduser().resolve()
        production = os.environ.get("NEXUS_PRODUCTION_RESEARCH_STATE_ROOT", "").strip()
        if production and (root == Path(production).expanduser().resolve() or root.is_relative_to(Path(production).expanduser().resolve())):
            raise ValueError("CERTIFICATION_STATE_ROOT_OVERLAPS_PRODUCTION")
        path = root / "current" / "research_state_v2.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=3) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS current_state (memory_id TEXT PRIMARY KEY, memory_kind TEXT NOT NULL, objective_id TEXT, project_id TEXT, job_id TEXT, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("INSERT INTO current_state VALUES(?,?,?,?,?,?,?) ON CONFLICT(memory_id) DO UPDATE SET memory_kind=excluded.memory_kind, objective_id=excluded.objective_id, project_id=excluded.project_id, job_id=excluded.job_id, recorded_at=excluded.recorded_at, payload=excluded.payload",
                       (memory_id, str(row.get("memory_kind") or "STATE"), row.get("objective_id"), row.get("project_id") or row.get("work_id"), row.get("job_id"), str(row["recorded_at"]), json.dumps(row, separators=(",", ":"), default=str)))
        return {"status": "PASS", "verified": True, "memory_id": memory_id, "namespace": "CERTIFICATION"}
    if supabase is None or not supabase.configured():
        raise CurrentStateUnavailable("CURRENT_STATE_BACKEND_UNAVAILABLE")
    payload = {"memory_id": memory_id, "memory_kind": row.get("memory_kind", "STATE"),
               "objective_id": row.get("objective_id"), "query_family": row.get("query_family"),
               "recorded_at": row["recorded_at"], "payload": row}
    status, body = supabase.rest("POST", "research_proactive_memory?on_conflict=memory_id", body=[payload],
                                 prefer="return=representation,resolution=merge-duplicates")
    echoed = next((item for item in body if isinstance(item, dict) and item.get("memory_id") == memory_id), None) if isinstance(body, list) else None
    if status not in {200, 201, 204} or not echoed or echoed.get("recorded_at") != row["recorded_at"]:
        raise StateWriteFailure(f"CURRENT_STATE_WRITE_FAILED:HTTP_{status}")
    return {"status": "PASS", "verified": True, "memory_id": memory_id, "namespace": "PRODUCTION"}


def _exact_current(memory_id: str) -> dict[str, Any] | None:
    if _certification():
        root = Path(os.environ["NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT"]).expanduser().resolve()
        path = root / "current" / "research_state_v2.sqlite3"
        if not path.exists(): return None
        with sqlite3.connect(path, timeout=3) as db:
            found = db.execute("SELECT payload FROM current_state WHERE memory_id=?", (memory_id,)).fetchone()
        return json.loads(found[0]) if found else None
    if supabase is None or not supabase.configured():
        raise CurrentStateUnavailable("CURRENT_STATE_BACKEND_UNAVAILABLE")
    safe_id = urllib.parse.quote(str(memory_id), safe="")
    status, rows = supabase.rest("GET", f"research_proactive_memory?memory_id=eq.{safe_id}&select=memory_id,payload&limit=1")
    if status != 200:
        raise CurrentStateUnavailable(f"CURRENT_STATE_LOOKUP_FAILED:HTTP_{status}")
    if not isinstance(rows, list) or not rows: return None
    payload = rows[0].get("payload")
    return payload if isinstance(payload, dict) else None


def lookup_case(case_id: str) -> dict[str, Any] | None:
    return _exact_current(str(case_id)) if case_id else None


def lookup_case_control(case_id: str) -> dict[str, Any] | None:
    """Fetch only bounded routing fields for one exact case identity."""
    if not case_id: return None
    if _certification():
        row = _exact_current(str(case_id))
        if row is None: return None
        return {key: row.get(key) for key in ("memory_id", "memory_kind", "recorded_at", "case_id", "status",
            "department_requests", "objective_id", "project_id", "job_id")}
    if supabase is None or not supabase.configured():
        raise CurrentStateUnavailable("CURRENT_STATE_BACKEND_UNAVAILABLE")
    safe_id = urllib.parse.quote(str(case_id), safe="")
    fields = ("memory_id,memory_kind,recorded_at,case_id:payload->>case_id,status:payload->>status,"
              "department_requests:payload->department_requests,objective_id,project_id:payload->>project_id,"
              "job_id:payload->>job_id")
    query = urllib.parse.urlencode({"memory_id": f"eq.{safe_id}", "select": fields, "limit": "1"})
    status, rows = supabase.rest("GET", "research_proactive_memory?" + query)
    if status != 200 or not isinstance(rows, list):
        raise CurrentStateUnavailable(f"CURRENT_STATE_LOOKUP_FAILED:HTTP_{status}")
    return rows[0] if rows else None


def lookup_lineage(kind: str, identifier: str, *, limit: int = 100) -> list[dict[str, Any]]:
    """Resolve bounded lineage by indexed objective or exact projected linkage."""
    if not identifier: return []
    key = str(kind).strip().lower()
    if key in {"case", "case_id", "memory_id"}:
        row = _exact_current(str(identifier)); return [row] if row else []
    if _certification():
        rows = list_current(limit=MAX_CONTROL_ROWS, include_payload=True)
        field = {"objective": "objective_id", "objective_id": "objective_id", "project": "project_id",
                 "project_id": "project_id", "work_id": "work_id", "job": "job_id", "job_id": "job_id"}.get(key)
        if not field: raise ValueError("UNSUPPORTED_LINEAGE_LOOKUP")
        return [row for row in rows if str(row.get(field) or "") == str(identifier)][:max(1, min(int(limit), MAX_QUERY_ROWS))]
    if supabase is None or not supabase.configured():
        raise CurrentStateUnavailable("CURRENT_STATE_BACKEND_UNAVAILABLE")
    cap = max(1, min(int(limit), MAX_CONTROL_ROWS))
    safe = urllib.parse.quote(str(identifier), safe="")
    if key in {"objective", "objective_id"}:
        filter_name = "objective_id"
    elif key in {"project", "project_id", "work_id"}:
        filter_name = "payload->>project_id"
    elif key in {"job", "job_id"}:
        filter_name = "payload->>job_id"
    else:
        raise ValueError("UNSUPPORTED_LINEAGE_LOOKUP")
    query = urllib.parse.urlencode({filter_name: f"eq.{safe}", "select": "memory_id", "limit": str(cap)})
    status, rows = supabase.rest("GET", "research_proactive_memory?" + query)
    if status != 200 or not isinstance(rows, list):
        raise CurrentStateUnavailable(f"CURRENT_STATE_LINEAGE_LOOKUP_FAILED:HTTP_{status}")
    found = []
    for item in rows[:cap]:
        memory_id = str(item.get("memory_id") or "") if isinstance(item, dict) else ""
        if memory_id:
            value = _exact_current(memory_id)
            if value is not None: found.append(value)
    return found


def list_current(*, kinds: tuple[str, ...] = (), limit: int = 100, include_payload: bool = True,
                 max_bytes: int | None = None) -> list[dict[str, Any]]:
    """Bounded indexed projection; optional case hydration remains capped at 100."""
    cap = max(1, min(int(limit), MAX_QUERY_ROWS if include_payload else MAX_CONTROL_ROWS))
    byte_cap = max(64 * 1024, min(int(max_bytes or (1_500_000 if include_payload else 2_000_000)),
                                 1_500_000 if include_payload else 2_000_000))
    if _certification():
        root = Path(os.environ["NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT"]).expanduser().resolve()
        path = root / "current" / "research_state_v2.sqlite3"
        if not path.exists(): return []
        where = " WHERE memory_kind IN (" + ",".join("?" for _ in kinds) + ")" if kinds else ""
        with sqlite3.connect(path, timeout=3) as db:
            rows = db.execute("SELECT payload FROM current_state" + where + " ORDER BY recorded_at DESC LIMIT ?", (*kinds, cap)).fetchall()
        output = []
        used = 0
        for row in rows:
            value = json.loads(row[0]); size = len(json.dumps(value, separators=(",", ":"), default=str).encode())
            if output and used + size > byte_cap: break
            output.append(value); used += size
        return output
    if supabase is None or not supabase.configured():
        raise CurrentStateUnavailable("CURRENT_STATE_BACKEND_UNAVAILABLE")
    output = []
    used_bytes = 0
    offset = 0
    while offset < cap:
        page_size = min(4 if include_payload else 500, cap - offset)
        query = {"select": "memory_id,memory_kind,recorded_at,payload" if include_payload else ",".join(CURRENT_FIELDS),
                 "order": "recorded_at.desc", "limit": str(page_size), "offset": str(offset)}
        if kinds: query["memory_kind"] = "in.(" + ",".join(kinds) + ")"
        status, rows = supabase.rest("GET", "research_proactive_memory?" + urllib.parse.urlencode(query))
        if status != 200 or not isinstance(rows, list):
            raise CurrentStateUnavailable(f"CURRENT_STATE_LIST_FAILED:HTTP_{status}")
        shaped = ([item["payload"] for item in rows if isinstance(item, dict) and isinstance(item.get("payload"), dict)]
                  if include_payload else [{key: value for key, value in item.items() if key != "payload"}
                                           for item in rows if isinstance(item, dict)])
        for value in shaped:
            size = len(json.dumps(value, separators=(",", ":"), default=str).encode())
            if output and used_bytes + size > byte_cap: return output
            output.append(value); used_bytes += size
        if len(rows) < page_size: break
        offset += page_size
    return output


def _pending_path(event_id: str) -> Path:
    return _state_root() / "pending" / (event_id + ".json")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="state-v2-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


def _update_partition_manifest(target: Path, event: dict[str, Any], *, encoded_size: int,
                               appended: bool) -> None:
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    current_size = target.stat().st_size
    prior = None
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        if int(prior.get("size_bytes", -1)) > current_size:
            raise HistoryPartitionFailure("HISTORY_PARTITION_MANIFEST_AHEAD_OF_DATA")
    elif current_size > encoded_size:
        raise HistoryPartitionFailure("HISTORY_PARTITION_MANIFEST_MISSING_REQUIRES_AUDIT")
    already_accounted = bool(prior and prior.get("last_event_id") == event["event_id"]
                             and int(prior.get("size_bytes", -1)) == current_size)
    if already_accounted: return
    if prior and int(prior.get("size_bytes", -1)) != current_size - encoded_size:
        raise HistoryPartitionFailure("HISTORY_PARTITION_MANIFEST_SIZE_DIVERGENCE")
    if not prior and current_size not in {0, encoded_size}:
        raise HistoryPartitionFailure("HISTORY_PARTITION_MANIFEST_MISSING_REQUIRES_AUDIT")
    event_hash = str(event.get("event_sha256") or "")
    previous_chain = str((prior or {}).get("chain_sha256") or "")
    chain_hash = hashlib.sha256((previous_chain + event_hash).encode()).hexdigest()
    moment = str(event["timestamp"])
    value = {"partition_id": target.stem, "start_time": (prior or {}).get("start_time", moment),
        "end_time": moment, "record_count": int((prior or {}).get("record_count", 0)) + 1,
        "size_bytes": current_size, "last_event_id": event["event_id"],
        "chain_sha256": chain_hash, "integrity": "SHA256_CHAIN_OF_EVENT_SHA256"}
    _atomic_write(manifest_path, json.dumps(value, separators=(",", ":")).encode())


def _partition_family_manifest(base: Path, day: str) -> Path:
    return base / f"{day}.segments.json"


def _segment_number(path: Path, day: str) -> int:
    if path.name == f"{day}.jsonl": return 0
    prefix = f"{day}."
    suffix = ".jsonl"
    if not path.name.startswith(prefix) or not path.name.endswith(suffix):
        raise HistoryPartitionFailure("HISTORY_PARTITION_SEGMENT_NAME_INVALID")
    number = path.name[len(prefix):-len(suffix)]
    if not number.isdigit():
        raise HistoryPartitionFailure("HISTORY_PARTITION_SEGMENT_NAME_INVALID")
    return int(number)


def _validated_segment_size(path: Path) -> int:
    size = path.stat().st_size
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    if not manifest_path.exists():
        raise HistoryPartitionFailure("HISTORY_PARTITION_SEGMENT_MANIFEST_MISSING")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("partition_id") != path.stem or int(manifest.get("size_bytes", -1)) != size:
            raise HistoryPartitionFailure("HISTORY_PARTITION_SEGMENT_MANIFEST_STALE")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        if isinstance(exc, HistoryPartitionFailure): raise
        raise HistoryPartitionFailure("HISTORY_PARTITION_SEGMENT_MANIFEST_INVALID") from exc
    if size > MAX_HISTORY_PARTITION_BYTES:
        raise HistoryPartitionFailure("HISTORY_PARTITION_SEGMENT_SIZE_EXCEEDED")
    return size


def _write_segment_family_hint(target: Path) -> None:
    day = target.name[:10]
    segment = _segment_number(target, day)
    manifest_path = _partition_family_manifest(target.parent, day)
    prior_segment = -1
    if manifest_path.exists():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            if prior.get("partition_date") != day:
                raise HistoryPartitionFailure("HISTORY_PARTITION_FAMILY_MANIFEST_INVALID")
            prior_segment = int(prior.get("latest_segment", -1))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            if isinstance(exc, HistoryPartitionFailure): raise
            raise HistoryPartitionFailure("HISTORY_PARTITION_FAMILY_MANIFEST_INVALID") from exc
    # Replaying an older pending event must not move the family hint backwards.
    if segment < prior_segment: return
    _atomic_write(manifest_path, json.dumps({"schema_version": "nexus.research-history-segments.v1",
        "partition_date": day, "latest_segment": segment, "latest_partition_id": target.stem,
        "latest_size_bytes": target.stat().st_size}, separators=(",", ":")).encode())


def _partition_for_event(event: dict[str, Any], encoded_size: int) -> Path:
    moment = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00")).astimezone(timezone.utc)
    day = moment.strftime("%Y-%m-%d")
    base = _archive_root() / moment.strftime("%Y") / moment.strftime("%m")
    if encoded_size > MAX_HISTORY_PARTITION_BYTES:
        raise HistoryPartitionFailure("HISTORY_EVENT_EXCEEDS_PARTITION_SIZE")
    base.mkdir(parents=True, exist_ok=True)
    family_manifest = _partition_family_manifest(base, day)
    hinted = family_manifest.exists()
    if hinted:
        try:
            metadata = json.loads(family_manifest.read_text(encoding="utf-8"))
            if metadata.get("partition_date") != day:
                raise HistoryPartitionFailure("HISTORY_PARTITION_FAMILY_MANIFEST_INVALID")
            start = int(metadata.get("latest_segment", -1))
            if start < 0:
                raise HistoryPartitionFailure("HISTORY_PARTITION_FAMILY_MANIFEST_INVALID")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            if isinstance(exc, HistoryPartitionFailure): raise
            raise HistoryPartitionFailure("HISTORY_PARTITION_FAMILY_MANIFEST_INVALID") from exc
    else:
        start = 0

    latest_path: Path | None = None
    latest_size = 0
    for offset in range(MAX_HISTORY_SEGMENT_PROBES):
        segment = start + offset
        suffix = "" if segment == 0 else f".{segment:04d}"
        target = base / f"{day}{suffix}.jsonl"
        if not target.exists():
            if latest_path is None:
                if hinted:
                    raise HistoryPartitionFailure(
                        f"HISTORY_PARTITION_SELECTION_EXHAUSTED:date={day};start={start};"
                        f"probe_limit={MAX_HISTORY_SEGMENT_PROBES};last={target.name};reason=hinted_candidate_missing")
                return target
            if latest_size + encoded_size <= MAX_HISTORY_PARTITION_BYTES:
                return latest_path
            return target
        size = _validated_segment_size(target)
        latest_path, latest_size = target, size
        # Without a family hint, a segment-zero chain that exceeds this bound
        # is intentionally not enumerated further.
    raise HistoryPartitionFailure(
        f"HISTORY_PARTITION_SELECTION_EXHAUSTED:date={day};start={start};"
        f"probe_limit={MAX_HISTORY_SEGMENT_PROBES};last={latest_path.name if latest_path else 'NONE'};"
        "reason=adjacent_probe_limit_reached")


def _append_event(event: dict[str, Any], target_hint: str | None = None) -> str:
    moment = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00")).astimezone(timezone.utc)
    encoded = (json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode()
    if len(encoded) > MAX_HISTORY_PARTITION_BYTES:
        raise HistoryPartitionFailure("HISTORY_EVENT_EXCEEDS_PARTITION_SIZE")
    try:
        target = Path(target_hint) if target_hint else _partition_for_event(event, len(encoded))
        if not target.is_relative_to(_archive_root()):
            raise HistoryPartitionFailure("HISTORY_PARTITION_PATH_OUTSIDE_STATE_ROOT")
        # Under the global writer lock, only the oldest pending event can have
        # reached history without its receipt. A tail check makes replay idempotent
        # without scanning an archive partition.
        duplicate = False
        if target.exists() and target.stat().st_size:
            with target.open("rb") as handle:
                handle.seek(max(0, target.stat().st_size - MAX_HISTORY_EVENT_BYTES - 2))
                tail = handle.read().splitlines()
            if tail:
                try:
                    if json.loads(tail[-1]).get("event_id") == event["event_id"]:
                        duplicate = True
                except (ValueError, TypeError):
                    pass
        if not duplicate:
            current_size = target.stat().st_size if target.exists() else 0
            if current_size + len(encoded) > MAX_HISTORY_PARTITION_BYTES:
                raise HistoryPartitionFailure("HISTORY_PARTITION_TARGET_CAPACITY_CHANGED")
            with target.open("ab") as handle:
                handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
        _update_partition_manifest(target, event, encoded_size=len(encoded), appended=not duplicate)
        _write_segment_family_hint(target)
    except OSError as exc:
        raise HistoryPartitionFailure("HISTORY_PARTITION_ROTATION_FAILED_OR_APPEND_FAILED") from exc
    return str(target)


def _apply_pending(event_id: str, pending: dict[str, Any]) -> dict[str, Any]:
    row = pending["current_state"]
    receipt_path = _state_root() / "receipts" / (event_id + ".json")
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        _pending_path(event_id).unlink(missing_ok=True)
        return receipt
    # Reconciliation always retries current state first. Pending state is
    # durable before either authoritative write, so crashes are replayable.
    row["last_state_event_id"] = event_id
    current_receipt = _upsert_current(row)
    event = pending["history_event"]
    archive_path = _append_event(event, pending.get("history_path"))
    receipt = {"event_id": event_id, "memory_id": row["memory_id"], "current_state": current_receipt,
               "history_path": archive_path, "completed_at": _now(), "status": "COMMITTED"}
    _atomic_write(receipt_path, json.dumps(receipt, separators=(",", ":")).encode())
    _pending_path(event_id).unlink(missing_ok=True)
    return receipt


def persist_state(state: dict[str, Any], *, event_type: str | None = None) -> dict[str, Any]:
    """Persist a durable outbox intent, then current state, then history receipt."""
    try:
        row = _bounded_record(dict(state))
    except ValueError as exc:
        try: _emit_failure("CURRENT_STATE_WRITE_FAILED", state, str(exc))
        except Exception: pass
        raise
    if not row.get("memory_id"):
        stable = row.get("case_id") if row.get("memory_kind") in {"RESEARCH_CASE", "PROACTIVE_RESEARCH_CASE"} else None
        row["memory_id"] = str(stable or row.get("query_id") or row.get("objective_id") or row.get("event_id") or
                                "mem_" + hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()[:20])
    try:
        event = _event_for(row, event_type)
    except ValueError as exc:
        try: _emit_failure("HISTORY_WRITE_FAILED", row, str(exc))
        except Exception: pass
        raise
    event_id = str(event["event_id"])
    pending = {"event_id": event_id, "current_state": row, "history_event": event, "created_at": _now()}
    pending_path = _pending_path(event_id)
    lock_path = _state_root() / "writer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        # Resolve previous interrupted transactions before accepting another
        # event, preserving append ordering and the one-pending-event invariant.
        pending_dir = _state_root() / "pending"
        if pending_dir.exists():
            pending_paths = sorted(pending_dir.glob("*.json"))[:101]
            if len(pending_paths) > 100:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                _emit_failure("RECONCILIATION_REQUIRED", row, "PENDING_TRANSACTION_LIMIT_EXCEEDED")
                raise StateWriteFailure("RECONCILIATION_REQUIRED_BEFORE_NEW_WRITE")
            for previous in pending_paths:
                if previous == pending_path: continue
                try: _apply_pending(previous.stem, json.loads(previous.read_text()))
                except Exception as exc:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                    _emit_failure("RECONCILIATION_REQUIRED", row, type(exc).__name__)
                    raise StateWriteFailure("RECONCILIATION_REQUIRED_BEFORE_NEW_WRITE") from exc
        try:
            # Persist intent before selecting a segment. If bounded discovery
            # cannot establish a safe target, the objective's write remains
            # durable and can be reconciled after operator recovery.
            _atomic_write(pending_path, json.dumps(pending, ensure_ascii=False, separators=(",", ":"), default=str).encode())
            pending["history_path"] = str(_partition_for_event(event,
                len((json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode())))
            _atomic_write(pending_path, json.dumps(pending, ensure_ascii=False, separators=(",", ":"), default=str).encode())
        except (OSError, HistoryPartitionFailure) as exc:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            if isinstance(exc, HistoryPartitionFailure):
                if "HISTORY_PARTITION_SELECTION_EXHAUSTED:" in str(exc):
                    _emit_failure("HISTORY_PARTITION_SELECTION_EXHAUSTED", row, str(exc))
                    _emit_failure("RECONCILIATION_REQUIRED", row, event_id)
                else:
                    _emit_failure("HISTORY_PARTITION_ROTATION_FAILED", row, str(exc))
                raise
            _emit_failure("CURRENT_STATE_WRITE_FAILED", row, "PENDING_INTENT_WRITE_FAILED:" + type(exc).__name__)
            raise StateWriteFailure("PENDING_INTENT_WRITE_FAILED") from exc
        try:
            receipt = _apply_pending(event_id, pending)
        except Exception as exc:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            code = "CURRENT_STATE_WRITE_FAILED" if isinstance(exc, (CurrentStateUnavailable, StateWriteFailure)) else (
                "HISTORY_PARTITION_ROTATION_FAILED" if isinstance(exc, HistoryPartitionFailure) else "HISTORY_WRITE_FAILED")
            _emit_failure(code, row, type(exc).__name__)
            try: _emit_failure("RECONCILIATION_REQUIRED", row, event_id)
            except OSError: pass
            raise
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return {**row, "state_v2_receipt": receipt, "supabase_sync": {"status": "PASS", "verified": True,
            "memory_id": row["memory_id"], "namespace": receipt["current_state"].get("namespace", "PRODUCTION")}}


def reconcile_pending(*, limit: int = 20) -> dict[str, Any]:
    """Explicit bounded recovery operation; no archive scan is performed."""
    directory = _state_root() / "pending"
    if not directory.exists(): return {"status": "PASS", "processed": 0, "failed": 0}
    paths = sorted(directory.glob("*.json"))[:max(0, min(int(limit), 100))]
    processed = failed = 0
    lock_path = _state_root() / "writer.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        for path in paths:
            try:
                pending = json.loads(path.read_text())
                _apply_pending(str(pending["event_id"]), pending); processed += 1
            except Exception as exc:
                failed += 1
                try: _emit_failure("RECONCILIATION_REQUIRED", {}, type(exc).__name__)
                except OSError: pass
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return {"status": "PASS" if not failed else "DEGRADED", "processed": processed, "failed": failed}


def detect_divergence(*, limit: int = 100) -> dict[str, Any]:
    """Report interrupted current/history transactions without scanning archives."""
    directory = _state_root() / "pending"
    lock_path = _state_root() / "writer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"consistent": None, "pending_transactions": [], "writer_active": True,
                    "archive_scanned": False, "reconciliation_required": False}
        paths = sorted(directory.glob("*.json"))[:max(0, min(int(limit), 100))] if directory.exists() else []
        pending = []
        for path in paths:
            try:
                row = json.loads(path.read_text()).get("current_state", {})
                pending.append({"event_id": path.stem, "memory_id": row.get("memory_id"),
                                "case_id": row.get("case_id"), "objective_id": row.get("objective_id")})
                _emit_failure("STATE_DIVERGENCE_DETECTED", row, path.stem)
            except (OSError, ValueError, TypeError):
                pending.append({"event_id": path.stem, "error": "PENDING_INTENT_UNREADABLE"})
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return {"consistent": not pending, "pending_transactions": pending,
            "archive_scanned": False, "reconciliation_required": bool(pending)}


def activate_seed(seed_path: str | Path) -> dict[str, Any]:
    """Idempotently seed current records only; never creates objectives or jobs."""
    path = Path(seed_path)
    seed = json.loads(path.read_text(encoding="utf-8"))
    seed_id = hashlib.sha256(path.read_bytes()).hexdigest()
    cases = seed.get("cases")
    if not isinstance(cases, list): raise ValueError("HOT_STATE_SEED_CASES_REQUIRED")
    manifest_path = path.with_name("selective_preservation_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    retained_items = [item for item in manifest.get("retained_items", []) if isinstance(item, dict) and item.get("CLASS") == "A"]
    retained_a = {str(item.get("CASE_ID") or "") for item in retained_items if item.get("TYPE") == "RESEARCH_CASE"}
    retained_ids = {str(item.get("ID") or "") for item in retained_items}
    excluded = {str(item.get("CASE_ID") or "") for item in manifest.get("EXCLUDED_FROM_STATE_V2_IMPORT", [])
                if isinstance(item, dict) and item.get("CLASS") == "C"}
    if not retained_a or retained_a & excluded:
        raise ValueError("PRESERVATION_MANIFEST_INVALID")
    imported = skipped = 0
    for case in cases:
        if not isinstance(case, dict):
            skipped += 1; continue
        case_id = str(case.get("case_id") or "")
        if case_id in excluded or case_id not in retained_a:
            skipped += 1; continue
        if not case_id: raise ValueError("SEED_CASE_ID_REQUIRED")
        # Preserve IDs and lineage; no intake/job/objective regeneration.
        row = {"memory_id": case_id, "case_id": case_id, "memory_kind": "RESEARCH_CASE",
               "source_seed_id": seed_id,
               "case_schema_version": "nexus.research-case.v1", "objective_id": case.get("objective_id"),
               "project_id": case.get("project_id"), "job_id": case.get("job_id"),
               "status": case.get("case_status"), "turn": case.get("current_turn"),
               "open_questions": case.get("open_questions", []), "source_count": case.get("source_count", 0),
               "finding_count": case.get("finding_count", 0), "needle_status": case.get("needle_status"),
               "latest_results": case.get("latest_results", []), "latest_synthesis": case.get("latest_synthesis"),
               "current_advisor_attempt": case.get("current_advisor_attempt"),
               "last_activity_at": case.get("last_activity_at"), "lineage_refs": {"source": case.get("source_reference")}}
        prior = _exact_current(case_id)
        if prior is not None:
            # Idempotent, non-regressive activation: never overwrite newer live state.
            if prior.get("source_seed_id") == seed_id or str(prior.get("recorded_at") or "") > str(seed.get("created_at") or ""):
                skipped += 1; continue
        persist_state(row, event_type="STATE_V2_SEED_ACTIVATED")
        imported += 1
    recovery = seed.get("recovery") if isinstance(seed.get("recovery"), dict) else {}
    operational = []
    incident = recovery.get("incident")
    if isinstance(incident, dict):
        if str(incident.get("event_id") or "") not in retained_ids: raise ValueError("RECOVERY_INCIDENT_NOT_PRESERVED")
        operational.append({**incident, "source_seed_id": seed_id, "memory_id": str(incident.get("event_id") or ""),
            "event_id": incident.get("event_id"), "memory_kind": "RECOVERY_EVENT",
            "status": recovery.get("incident_status", "ACTIVE")})
    recovery_job = recovery.get("recovery_job")
    if isinstance(recovery_job, dict):
        if str(recovery_job.get("recovery_job_id") or "") not in retained_ids: raise ValueError("RECOVERY_JOB_NOT_PRESERVED")
        operational.append({**recovery_job, "source_seed_id": seed_id, "memory_id": str(recovery_job.get("recovery_job_id") or ""),
            "job_id": recovery_job.get("recovery_job_id"), "memory_kind": "SYSTEMS_RECOVERY_JOB",
            "status": recovery_job.get("execution_state")})
    dependency = recovery.get("state_v2_dependency")
    if isinstance(dependency, dict):
        if str(dependency.get("dependency_id") or "") not in retained_ids: raise ValueError("RECOVERY_DEPENDENCY_NOT_PRESERVED")
        operational.append({**dependency, "source_seed_id": seed_id, "memory_id": str(dependency.get("dependency_id") or ""),
            "memory_kind": "RECOVERY_DEPENDENCY", "status": dependency.get("execution_state")})
    for relationship in recovery.get("blocked_by_relationships", []):
        if isinstance(relationship, dict) and relationship.get("objective_id") and relationship.get("event_id"):
            operational.append({**relationship,
            "source_seed_id": seed_id, "memory_id": "blocked_by_" + hashlib.sha256(
                    f"{relationship['objective_id']}:{relationship['event_id']}".encode()).hexdigest()[:24],
                "memory_kind": "BLOCKED_BY_RELATIONSHIP"})
    for row in operational:
        if not row.get("memory_id"): raise ValueError("RECOVERY_SEED_ID_REQUIRED")
        prior = _exact_current(row["memory_id"])
        if prior is not None and (prior.get("source_seed_id") == seed_id or
                                  str(prior.get("recorded_at") or "") > str(seed.get("created_at") or "")):
            skipped += 1; continue
        persist_state(row, event_type="STATE_V2_RECOVERY_SEED_ACTIVATED")
        imported += 1
    return {"status": "PASS", "imported": imported, "skipped": skipped, "production_activation": not _certification()}


def explicit_archive_events(*, day: str, purpose: str, max_records: int = 100,
                            max_bytes: int = MAX_HISTORY_PARTITION_BYTES,
                            timeout_seconds: float = 2.0) -> list[dict[str, Any]]:
    """Bounded explicit audit read for one UTC date and numbered segments."""
    if len(day) != 10 or day[4] != "-" or day[7] != "-": raise ValueError("ISO_DAY_REQUIRED")
    if not str(purpose).strip(): raise ValueError("ARCHIVE_ACCESS_PURPOSE_REQUIRED")
    out = []
    base = _archive_root() / day[:4] / day[5:7]
    cap = max(1, min(int(max_records), 1000))
    byte_cap = max(1, min(int(max_bytes), MAX_HISTORY_PARTITION_BYTES))
    deadline = time.monotonic() + max(0.05, min(float(timeout_seconds), 5.0))
    bytes_read = 0
    for segment in range(1000):
        suffix = "" if segment == 0 else f".{segment:04d}"
        path = base / f"{day}{suffix}.jsonl"
        if not path.exists():
            if segment == 0: return []
            break
        if path.stat().st_size > MAX_HISTORY_PARTITION_BYTES:
            raise StateV2Error("ARCHIVE_PARTITION_SIZE_GUARD_FAILED")
        with path.open("rb") as handle:
            for line in handle:
                if time.monotonic() > deadline: raise StateV2Error("ARCHIVE_AUDIT_TIMEOUT")
                bytes_read += len(line)
                if bytes_read > byte_cap: return out
                if len(out) >= cap: return out
                try:
                    event = json.loads(line)
                    checksum = event.pop("event_sha256", None)
                    expected = hashlib.sha256(json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str).encode()).hexdigest()
                    if checksum != expected: raise StateV2Error("ARCHIVE_EVENT_INTEGRITY_FAILED")
                    event["event_sha256"] = checksum
                    out.append(event)
                except ValueError:
                    continue
    return out
