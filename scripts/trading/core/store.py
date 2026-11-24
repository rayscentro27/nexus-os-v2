"""Durable append-only Trading state.

Follows the governed-store convention (append-only JSONL under the gitignored
``data/governed`` tree, mode 0600). Each collection is an event log: a stateful
entity (order, position, signal) is updated by appending a new revision with
the same id and a higher ``revision``. ``latest()`` projects the current state.
Immutable collections (journal trades, receipts, risk events, strategy
versions) reject a second write for the same id.

Override the location with ``NEXUS_TRADING_CORE_DATA_DIR`` (tests, Contabo).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]

COLLECTIONS = {
    "strategies": "strategy_id",
    "strategy_versions": "strategy_version_id",
    "signals": "signal_id",
    "risk_events": "risk_event_id",
    "orders": "order_id",
    "positions": "position_id",
    "trades": "trade_id",
    "execution_receipts": "receipt_id",
    "reconciliation_events": "reconciliation_id",
    "performance_snapshots": "snapshot_id",
}
IMMUTABLE = {"strategy_versions", "risk_events", "trades", "execution_receipts", "reconciliation_events", "performance_snapshots"}


class StoreError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def default_dir() -> Path:
    override = os.environ.get("NEXUS_TRADING_CORE_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return ROOT / "data" / "governed" / "trading_core"


class TradingStore:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base = Path(base_dir) if base_dir else default_dir()

    def _path(self, collection: str) -> Path:
        if collection not in COLLECTIONS:
            raise StoreError(f"unknown_collection:{collection}")
        return self.base / f"{collection}.jsonl"

    def _rows(self, collection: str) -> list[dict[str, Any]]:
        path = self._path(collection)
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def append(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        key = COLLECTIONS[collection] if collection in COLLECTIONS else None
        if key is None:
            raise StoreError(f"unknown_collection:{collection}")
        if not record.get(key):
            raise StoreError(f"missing_key:{key}")
        prior = [r for r in self._rows(collection) if r.get(key) == record[key]]
        if prior and collection in IMMUTABLE:
            raise StoreError(f"immutable_record_exists:{collection}:{record[key]}")
        value = dict(record)
        value["revision"] = (max(int(r.get("revision", 0)) for r in prior) + 1) if prior else 1
        value.setdefault("recorded_at", utc_now())
        path = self._path(collection)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch(mode=0o600)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(value, sort_keys=True, default=str) + "\n")
        return value

    def history(self, collection: str, record_id: str) -> list[dict[str, Any]]:
        key = COLLECTIONS[collection]
        return [r for r in self._rows(collection) if r.get(key) == record_id]

    def get(self, collection: str, record_id: str) -> dict[str, Any] | None:
        rows = self.history(collection, record_id)
        return max(rows, key=lambda r: int(r.get("revision", 0))) if rows else None

    def latest(self, collection: str) -> list[dict[str, Any]]:
        key = COLLECTIONS[collection]
        current: dict[str, dict[str, Any]] = {}
        for row in self._rows(collection):
            rid = row.get(key)
            if rid is None:
                continue
            if rid not in current or int(row.get("revision", 0)) >= int(current[rid].get("revision", 0)):
                current[rid] = row
        return list(current.values())

    def find(self, collection: str, **match: Any) -> list[dict[str, Any]]:
        return [r for r in self.latest(collection) if all(r.get(k) == v for k, v in match.items())]

    def all_rows(self, collection: str) -> Iterable[dict[str, Any]]:
        return list(self._rows(collection))
