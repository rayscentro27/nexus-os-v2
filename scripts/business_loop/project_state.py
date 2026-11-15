"""Durable business-loop project + work-item state (append-only, revisioned).

Location: ``data/governed/business_loop/`` (gitignored governed tree), override
with ``NEXUS_BUSINESS_LOOP_DATA_DIR``. Handoff envelopes are additionally
appended to the existing governed ``company_handoffs`` collection.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TERMINAL_ALLOWED = {"OBJECTIVE_COMPLETE", "CANCELLED_BY_RAY", "STOPPED_UNAUTHORIZED_COST", "STOPPED_SAFETY"}
DEPARTMENTS = ("RESEARCH", "MARKETING", "CREATIVE", "COMMERCE", "DISTRIBUTION", "METRICS", "ANALYSIS")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class ProjectStore:
    def __init__(self, base: Path | str | None = None) -> None:
        self.base = Path(base or os.environ.get("NEXUS_BUSINESS_LOOP_DATA_DIR") or ROOT / "data/governed/business_loop")

    def _file(self, name: str) -> Path:
        return self.base / f"{name}.jsonl"

    def _rows(self, name: str) -> list[dict]:
        p = self._file(name)
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def _append(self, name: str, row: dict) -> dict:
        self.base.mkdir(parents=True, exist_ok=True)
        p = self._file(name)
        if not p.exists():
            p.touch(mode=0o600)
        with p.open("a") as fh:
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        return row

    def _latest(self, name: str, key: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for r in self._rows(name):
            out[r[key]] = r
        return out

    # ---- project ----------------------------------------------------
    def project(self, project_id: str) -> dict | None:
        return self._latest("projects", "project_id").get(project_id)

    def save_project(self, project: dict, **changes: Any) -> dict:
        status = changes.get("status", project.get("status"))
        if status not in {"ACTIVE", *TERMINAL_ALLOWED}:
            raise ValueError(f"illegal_project_status:{status}")
        if project.get("status") == "ACTIVE" and status in TERMINAL_ALLOWED and not changes.get("termination_authority"):
            raise PermissionError("project_termination_requires_recorded_authority")
        row = {**project, **changes, "revision": int(project.get("revision", 0)) + 1, "updated_at": now()}
        return self._append("projects", row)

    def event(self, project: dict, kind: str, **data: Any) -> dict:
        """Record an issue/recovery/cost/etc. event against the project (never terminates it)."""
        return self._append("events", {"event_id": new_id("evt"), "project_id": project["project_id"], "kind": kind, "at": now(), **data})

    def events(self, project_id: str, kind: str | None = None) -> list[dict]:
        return [e for e in self._rows("events") if e["project_id"] == project_id and (kind is None or e["kind"] == kind)]

    # ---- work items -------------------------------------------------
    def work_item(self, work_item_id: str) -> dict | None:
        return self._latest("work_items", "work_item_id").get(work_item_id)

    def work_items(self, project_id: str) -> list[dict]:
        return [w for w in self._latest("work_items", "work_item_id").values() if w["project_id"] == project_id]

    def save_work_item(self, item: dict, **changes: Any) -> dict:
        return self._append("work_items", {**item, **changes, "revision": int(item.get("revision", 0)) + 1, "updated_at": now()})

    def open_work_item(self, project: dict, department: str, stage: str, instructions: str, *, source_handoff_id: str | None = None,
                       status: str = "READY") -> dict:
        return self.save_work_item({"work_item_id": new_id("wi"), "project_id": project["project_id"], "venture_id": project["venture_id"],
                                    "opportunity_id": project["opportunity_id"], "department": department, "stage": stage,
                                    "instructions": instructions, "source_handoff_id": source_handoff_id, "status": status,
                                    "created_at": now(), "attempts": 0, "outputs": {}, "artifacts": []})

    # ---- handoffs ---------------------------------------------------
    def save_handoff(self, handoff: dict) -> dict:
        self._append("handoffs", handoff)
        try:  # existing governed company handoff collection (best effort, never blocks the loop)
            import sys
            sys.path.insert(0, str(ROOT / "scripts"))
            from nexus_agent_platform.governed import persistence
            persistence.append_record("company_handoffs", {**handoff, "source": "business_loop_r1"})
        except Exception as exc:  # noqa: BLE001
            handoff["governed_mirror_error"] = type(exc).__name__
        return handoff

    def handoffs(self, project_id: str) -> list[dict]:
        return [h for h in self._rows("handoffs") if h["project_id"] == project_id]
