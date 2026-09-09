"""Worker-side, non-secret skill attachment receipts for R15.6.

The hook runs in the Hermes worker process after its real kanban_complete call.
It records only task/run metadata and a SHA-256 of the resolved skill file;
skill content and credentials never enter the receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path


def _skill_file(home: Path, name: str) -> Path | None:
    clean = name.strip().replace("/", "_")
    if not clean:
        return None
    candidates = [
        home / "skills" / name / "SKILL.md",
        Path("/opt/hermes/skills") / name / "SKILL.md",
    ]
    for path in candidates:
        if path.is_file():
            return path
    for root in (home / "skills", Path("/opt/hermes/skills")):
        if root.is_dir():
            for path in root.rglob("SKILL.md"):
                if path.parent.name == clean:
                    return path
    return None


def _write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".skill-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _on_completed(task_id: str = "", profile_name: str = "", run_id: int | None = None,
                 **_: object) -> None:
    if not task_id:
        return
    db_path = os.environ.get("HERMES_KANBAN_DB", "")
    if not db_path:
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        task = conn.execute("select * from tasks where id = ?", (task_id,)).fetchone()
        if task is None:
            return
        effective_run = run_id or task["current_run_id"]
        run = conn.execute("select * from task_runs where id = ?", (effective_run,)).fetchone()
        worker_id = task["claim_lock"] if task["claim_lock"] else None
        if not worker_id:
            event = conn.execute(
                "select payload from task_events where task_id = ? and kind = 'claimed' "
                "order by id desc limit 1", (task_id,)
            ).fetchone()
            if event and event["payload"]:
                try:
                    worker_id = json.loads(event["payload"]).get("lock")
                except (TypeError, json.JSONDecodeError):
                    worker_id = None
        requested = json.loads(task["skills"] or "[]")
        if not isinstance(requested, list):
            requested = []
        home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
        loaded = []
        paths = []
        hashes = {}
        for raw in requested:
            name = str(raw)
            path = _skill_file(home, name)
            if path is None:
                continue
            loaded.append(name)
            paths.append(str(path))
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        now = int(time.time())
        payload = {
            "schema_version": "nexus.hermes.r15.6.skill-attachment.v1",
            "execution_id": f"hermes-kanban:{task_id}:{effective_run or 'unknown'}",
            "task_id": task_id,
            "worker_id": worker_id,
            "profile": profile_name or task["assignee"],
            "requested_skills": requested,
            "resolved_skills": loaded,
            "loaded_skills": loaded,
            "skill_path": paths,
            "skill_hash_or_version": hashes,
            "worker_start_time": run["started_at"] if run else task["started_at"],
            "end_time": run["ended_at"] if run else task["completed_at"] or now,
            "result_id": f"{task_id}:{effective_run or 'unknown'}",
            "result_status": task["status"],
            "provenance": "worker_on_kanban_task_completed_hook",
        }
        root = Path(db_path).parent / "receipts" / "r15_6_skill_attachments"
        _write_atomic(root / f"{task_id}-{effective_run or 'unknown'}.json", payload)
    finally:
        conn.close()


def register(ctx) -> None:
    ctx.register_hook("kanban_task_completed", _on_completed)
