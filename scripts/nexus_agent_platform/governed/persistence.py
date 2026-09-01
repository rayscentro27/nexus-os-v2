"""Governed operating loop persistence — bounded local store.

Append-only JSONL collections under ``data/governed/`` (gitignored). Each record
is immutable once written; a new record supersedes the previous one for stateful
entities (approvals, work orders). This gives restart persistence without
introducing a new database system.

Paths are overridable via ``NEXUS_GOVERNED_DATA_DIR`` for tests.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from nexus_agent_platform.runtime.paths import nexus_data_path

COLLECTIONS = ("approvals", "work_orders", "recommendations", "audit", "queue", "opportunities", "revenue_observations", "revenue_snapshots", "growth_experiments", "creative_briefs", "creative_assets", "creative_receipts", "creative_concepts", "creative_feedback", "creative_preference_profiles", "creative_campaigns", "specialists", "specialist_permissions", "skill_assignments", "goals", "loop_state", "metrics", "improvement_candidates", "trading_strategies", "business_ideas", "business_research", "business_receipts", "launch_candidates", "outcomes")


def governed_data_dir() -> Path:
    override = os.environ.get("NEXUS_GOVERNED_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return nexus_data_path("governed")


def collection_path(name: str) -> Path:
    if name not in COLLECTIONS:
        raise ValueError(f"Unknown governed collection: {name}")
    return governed_data_dir() / f"{name}.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _ensure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600)
    os.chmod(path, 0o600)


def append_record(collection: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Append an immutable record to the collection."""
    path = collection_path(collection)
    _ensure(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return record


def read_records(collection: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Read all records, most recent last. Returns newest-first ordering."""
    path = collection_path(collection)
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit is not None:
        records = records[-limit:]
    return list(reversed(records))


def get_record(collection: str, record_id: str, key: str = "id") -> Optional[Dict[str, Any]]:
    """Return the newest record matching id, or None."""
    for record in read_records(collection):
        if record.get(key) == record_id:
            return record
    return None


def latest_record(collection: str) -> Optional[Dict[str, Any]]:
    records = read_records(collection, limit=1)
    return records[0] if records else None


def write_snapshot(collection: str, records: List[Dict[str, Any]]) -> Path:
    """Write a deterministic snapshot of a collection (superseded records included)."""
    path = governed_data_dir() / f"{collection}_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collection": collection,
        "generated_at": _now(),
        "record_count": len(records),
        "records": records,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def emit_audit_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Append an audit trail event (no sensitive message contents)."""
    record = {
        "event_id": new_id("aud"),
        "created_at": _now(),
        **event,
    }
    return append_record("audit", record)


def read_audit(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    return read_records("audit", limit=limit)
