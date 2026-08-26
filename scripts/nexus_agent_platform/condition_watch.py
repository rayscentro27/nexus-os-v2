"""Bounded, idempotent condition watches for synthetic and governed workflows."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WATCHES = ROOT / "reports/runtime/condition_watches"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(condition_type: str, entity_ref: str) -> str:
    return "watch_" + hashlib.sha256(f"{condition_type}:{entity_ref}".encode()).hexdigest()[:16]


def create_watch(condition_type: str, entity_ref: str, source_of_truth: str) -> dict[str, Any]:
    WATCHES.mkdir(parents=True, exist_ok=True)
    watch_id = _id(condition_type, entity_ref)
    path = WATCHES / f"{watch_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    watch = {"watch_id": watch_id, "condition_type": condition_type, "entity_ref": entity_ref,
             "source_of_truth": source_of_truth, "created_at": _now(), "last_checked_at": None,
             "state": "WATCHING", "triggered_at": None, "verification_ref": None,
             "action_ref": None, "notification_ref": None, "closed_at": None,
             "triad_test": True, "external_action_performed": False}
    path.write_text(json.dumps(watch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return watch


def check_watch(watch: dict[str, Any], *, fixture_present: bool = False) -> dict[str, Any]:
    updated = dict(watch)
    updated["last_checked_at"] = _now()
    if updated.get("state") in {"NOTIFIED", "CLOSED"}:
        return updated
    if not fixture_present:
        updated["state"] = "WATCHING"
        return updated
    updated.update({"state": "NOTIFIED", "triggered_at": updated.get("triggered_at") or _now(),
                    "verification_ref": f"verify_{updated['watch_id']}",
                    "action_ref": f"action_{updated['watch_id']}",
                    "notification_ref": f"notify_{updated['watch_id']}", "closed_at": _now()})
    return updated


def certify_synthetic_watch() -> dict[str, Any]:
    watch = create_watch("synthetic_signup", "john-doe-certification", "synthetic_signup_fixture")
    before = check_watch(watch, fixture_present=False)
    after = check_watch(before, fixture_present=True)
    repeat = check_watch(after, fixture_present=True)
    no_false = before["state"] == "WATCHING"
    idempotent = repeat.get("notification_ref") == after.get("notification_ref")
    return {"status": "PASS" if no_false and after["state"] == "NOTIFIED" and idempotent else "FAIL",
            "no_false_trigger": no_false, "notification_idempotency": idempotent,
            "watch_id": watch["watch_id"], "before": before, "after": after, "repeat": repeat}


if __name__ == "__main__":
    print(json.dumps(certify_synthetic_watch(), indent=2, sort_keys=True))
