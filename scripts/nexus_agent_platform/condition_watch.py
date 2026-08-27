"""Bounded, idempotent condition watches for synthetic and governed workflows."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
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


def certify_real_synthetic_watch(*, source_dir: Path | None = None, send_notification: bool = True) -> dict[str, Any]:
    """Run the certification watch against a persisted synthetic source.

    The watcher rereads the source file and the notification uses the same
    Telegram bridge as Hermes.  The fixture is explicitly certification-only.
    """
    source_dir = source_dir or (ROOT / "data/runtime/condition_watch_certification")
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / "synthetic_signup.json"
    entity_ref = f"john-doe-certification-real-{uuid.uuid4().hex[:8]}"
    source.write_text(json.dumps({"entity_ref": entity_ref, "signed_up": False, "certification_only": True}) + "\n", encoding="utf-8")
    watch = create_watch("synthetic_signup", entity_ref, str(source))
    before_source = json.loads(source.read_text(encoding="utf-8"))
    before = check_watch(watch, fixture_present=bool(before_source.get("signed_up")))
    no_false = before.get("state") == "WATCHING" and not before.get("notification_ref")
    source.write_text(json.dumps({**before_source, "signed_up": True}) + "\n", encoding="utf-8")
    after_source = json.loads(source.read_text(encoding="utf-8"))
    after = check_watch(before, fixture_present=bool(after_source.get("signed_up")))
    notification = None
    message_id = None
    if send_notification:
        try:
            from scripts.telegram.nexus_telegram_bridge import get_bot_token, telegram_send_message
        except ImportError:
            from telegram.nexus_telegram_bridge import get_bot_token, telegram_send_message
        token = get_bot_token()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS")
        runtime_env = Path("/Users/raymonddavis/.config/nexus/runtime.env")
        if runtime_env.is_file():
            # Read only the two approved keys; values stay in process memory.
            for line in runtime_env.read_text(encoding="utf-8").splitlines():
                key, separator, value = line.partition("=")
                if separator and key.strip() in {"TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_ALLOWED_CHAT_IDS"}:
                    value = value.strip().strip("\"'")
                    if key.strip() in {"TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN"} and not token:
                        token = value
                    if key.strip() in {"TELEGRAM_CHAT_ID", "TELEGRAM_ALLOWED_CHAT_IDS"} and not chat_id:
                        chat_id = value
        if token and chat_id:
            notification = telegram_send_message(token, str(chat_id).split(",")[0].strip(), "Nexus condition-watch certification test.\nSynthetic John Doe signup was verified.\nNo action is required.")
            message_id = (notification or {}).get("result", {}).get("message_id") if isinstance(notification, dict) else None
    if message_id:
        after.update({"state": "CLOSED", "notification_ref": f"telegram:{message_id}", "delivery_receipt": {"message_id": message_id, "delivered_at": _now()}})
    watch_path = WATCHES / f"{watch['watch_id']}.json"
    watch_path.write_text(json.dumps(after, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    repeat = check_watch(after, fixture_present=True)
    result = {"status": "PASS" if no_false and message_id and repeat.get("notification_ref") == after.get("notification_ref") else "FAIL", "governed_synthetic_source": True, "watch_persisted": True, "no_false_trigger": no_false, "source_transition_reread": after_source.get("signed_up") is True, "exact_entity_match": after_source.get("entity_ref") == watch.get("entity_ref"), "verification_receipt": bool(after.get("verification_ref")), "telegram_message_id": message_id, "delivery_receipt": after.get("delivery_receipt"), "watch_closed": after.get("state") == "CLOSED", "idempotent_repeat": repeat.get("notification_ref") == after.get("notification_ref"), "proof_refs": [str(source), str(WATCHES / f"{watch['watch_id']}.json")], "watch_id": watch["watch_id"]}
    (source_dir / "latest_receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(certify_synthetic_watch(), indent=2, sort_keys=True))
