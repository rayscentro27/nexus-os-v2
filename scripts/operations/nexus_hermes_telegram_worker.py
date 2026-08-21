#!/usr/bin/env python3
"""Governed one-shot Telegram operator for Nexus Hermes.

This worker is intentionally closed-world. It reads canonical Nexus status,
creates governed pending work orders, and can resolve an explicitly identified
approval. It has no shell, filesystem traversal, financial, external-message,
deployment, Alpha, or Nova capability.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import approvals, work_orders  # noqa: E402

RUNTIME_ENV = Path("/Users/raymonddavis/.config/nexus/runtime.env")
OFFSET_PATH = ROOT / "data/runtime/telegram_last_update_id.json"
HEARTBEAT_PATH = ROOT / "reports/runtime/nexus_hermes_telegram_heartbeat_latest.json"
RECEIPT_DIR = ROOT / "reports/telegram/hermes_operator_receipts"
LOCK_PATH = ROOT / "data/runtime/nexus_hermes_telegram.lock"
API_BASE = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE = 4000
MAX_INPUT = 1000
HTTP_TIMEOUT = 10

BLOCKED_PATTERNS = (
    r"\b(charge|refund|pay|payment|stripe|transfer|withdraw|deposit)\b",
    r"\b(funded?\s+trade|place\s+(a\s+)?trade|buy|sell|execute\s+trade)\b",
    r"\b(send|email|text|sms|post|publish|message)\b.*\b(customer|client|external|social|telegram)\b",
    r"\b(shell|terminal|bash|zsh|sudo|command|exec|run)\b",
    r"\b(token|secret|credential|password|runtime\.env|api key)\b",
    r"\b(deploy|production|install|security settings?)\b",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, path)


def load_runtime_env(path: Path = RUNTIME_ENV) -> Dict[str, str]:
    values: Dict[str, str] = {}
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip().removeprefix("export ")] = value.strip().strip("'\"")
    except OSError:
        return values
    return values


def _token_and_allowlist() -> tuple[str, set[int]]:
    env = load_runtime_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or env.get("NEXUS_TELEGRAM_BOT_TOKEN", "")
    raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS") or env.get("TELEGRAM_ALLOWED_CHAT_IDS") or os.environ.get("TELEGRAM_CHAT_ID") or env.get("TELEGRAM_CHAT_ID", "")
    allowed: set[int] = set()
    for item in raw.split(","):
        try:
            if item.strip():
                allowed.add(int(item.strip()))
        except ValueError:
            continue
    return token, allowed


def semantic_config() -> Dict[str, Any]:
    token, allowed = _token_and_allowlist()
    return {"token": "PRESENT" if token else "ABSENT", "authorized_chat": "PRESENT" if allowed else "ABSENT", "authorized_chat_count": len(allowed)}


def telegram_call(token: str, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not token:
        return {"ok": False, "error_code": 0, "description": "token_missing"}
    body = urllib.parse.urlencode(params or {}).encode("utf-8")
    request = urllib.request.Request(API_BASE.format(token=token, method=method), data=body)
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {"ok": False, "description": "malformed_response"}
    except Exception as exc:
        return {"ok": False, "description": type(exc).__name__}


def load_offset() -> int:
    value = load_json(OFFSET_PATH, {})
    try:
        return int(value.get("last_update_id", 0)) if isinstance(value, dict) else 0
    except (TypeError, ValueError):
        return 0


def save_offset(update_id: int) -> None:
    write_json(OFFSET_PATH, {"last_update_id": int(update_id), "updated_at": utc_now()})


@contextmanager
def single_run_lock(path: Path = LOCK_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def message_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def classify(text: str) -> str:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in BLOCKED_PATTERNS):
        return "NOT_AUTHORIZED"
    if lowered.startswith(("/request ", "/work ", "create a work order", "turn this into a work order")):
        return "APPROVAL_REQUIRED"
    if lowered.startswith(("/approve ", "/reject ")):
        return "APPROVAL_REQUIRED"
    return "AUTO_EXECUTE_INTERNAL_SAFE"


def _health(path: Path, health_key: str, status_key: str = "operator_health") -> Dict[str, Any]:
    value = load_json(path, {})
    if not isinstance(value, dict):
        return {"status": "UNAVAILABLE", "source": str(path.relative_to(ROOT))}
    status = value.get(status_key) or value.get("run_status") or value.get("status") or "UNKNOWN"
    return {"status": str(status), "last_run": value.get("last_run") or value.get("last_successful_run"), "source": str(path.relative_to(ROOT))}


def build_context() -> Dict[str, Any]:
    pending = approvals.get_pending_approvals(requested_for="ray", include_self=True)
    orders = work_orders.list_work_orders(limit=100)
    priority = [o for o in orders if (o.get("inputs") or {}).get("priority") in {"P0", "P1"} and o.get("status") not in {"completed", "cancelled", "rejected"}]
    live_runtime = load_json(ROOT / "reports/hermes_modernization/live_runtime_status.json", {})
    core = live_runtime.get("core_autonomy_runtime", {}) if isinstance(live_runtime, dict) else {}
    core_health = {"status": str(core.get("status", "UNAVAILABLE")), "last_run": live_runtime.get("generated_at") if isinstance(live_runtime, dict) else None, "source": "reports/hermes_modernization/live_runtime_status.json"}
    return {
        "core_runtime": core_health,
        "active_operator": _health(ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json", "operator_health"),
        "recovery_check": _health(ROOT / "reports/runtime/nexus_recovery_check_heartbeat_latest.json", "run_status"),
        "pending_work_orders": len(orders), "pending_approvals": len(pending), "high_priority_items": len(priority), "last_updated": utc_now(),
    }


def status_response() -> str:
    context = build_context()
    core = context["core_runtime"]["status"]
    active = context["active_operator"]["status"]
    recovery = context["recovery_check"]["status"]
    return (f"Nexus Hermes status\n\nCore runtime: {core}\nActive Operator: {active}\nRecovery Check: {recovery}\n"
            f"Pending approvals: {context['pending_approvals']}\nP0/P1 work orders: {context['high_priority_items']}\n"
            "Alpha/Nova: not enabled\nStripe/live money: disabled for autonomous execution")


def is_status_request(text: str) -> bool:
    """Recognize bounded, unambiguous status questions only."""
    normalized = re.sub(r"[?.!]+$", "", text.strip().lower())
    normalized = re.sub(r"^(?:@?nexus|hermes)\s*[,\:\-]?\s*", "", normalized)
    patterns = (
        r"^(?:give me )?(?:the )?(?:current )?(?:nexus )?system status$",
        r"^what(?: is|'s) (?:the )?(?:current )?(?:nexus )?system status$",
        r"^what(?: is|'s) nexus status$",
        r"^how is nexus doing$",
        r"^what is running right now$",
        r"^give me nexus status$",
        r"^system status$",
        r"^what(?: is|'s) the health of nexus$",
        r"^what(?: is|'s) nexus health$",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in patterns)


def approval_response() -> str:
    pending = approvals.get_pending_approvals(requested_for="ray", include_self=True)
    if not pending:
        return "No pending approvals."
    lines = [f"Pending approvals: {len(pending)}"]
    for item in pending[:10]:
        lines.append(f"- {item.get('id')}: {item.get('action_id')} ({item.get('risk_level')})")
    return "\n".join(lines)


def orders_response() -> str:
    orders = work_orders.list_work_orders(limit=10)
    if not orders:
        return "No governed work orders found."
    return "Recent governed work orders:\n" + "\n".join(f"- {o.get('work_order_id')}: {o.get('status')} / {o.get('action_id')}" for o in orders)


def _safe_summary(text: str) -> str:
    summary = re.sub(r"\s+", " ", text).strip()[:160]
    return re.sub(r"(?i)(token|secret|password|api[_ ]?key|runtime\.env)\s*[:=]?\s*\S+", r"\1 [REDACTED]", summary)


def create_governed_request(text: str) -> Dict[str, Any]:
    fingerprint = message_hash(re.sub(r"\s+", " ", text).strip().lower())
    key = f"telegram:hermes:{fingerprint}"
    existing = work_orders.list_work_orders(limit=1000)
    for order in existing:
        if order.get("idempotency_key") == key:
            return {"status": "DUPLICATE_SUPPRESSED", "work_order_id": order.get("work_order_id"), "receipt_id": f"hermes_command_{fingerprint}"}
    priority = "P0" if re.search(r"safety|security|failure|recovery", text, re.I) else "P1" if re.search(r"client|customer", text, re.I) else "P3"
    approval = approvals.create_approval_request(action_id="runtime_report.generate", requested_by="hermes_telegram", requested_for="ray", input_summary={"request_fingerprint": fingerprint, "priority": priority}, action_summary="Review Hermes internal work request", evidence_refs=["telegram:hermes"])
    order = work_orders.create_work_order(approval_id=approval["id"], action_id="runtime_report.generate", requested_by="hermes_telegram", inputs={"source": "telegram/hermes", "request_fingerprint": fingerprint, "request_summary": _safe_summary(text), "priority": priority}, expected_outcome="Prepare an internal report or bounded work product after explicit approval", idempotency_key=key, status="pending_approval")
    return {"status": "CREATED", "work_order_id": order["work_order_id"], "approval_id": approval["id"], "priority": priority, "receipt_id": f"hermes_command_{fingerprint}"}


def handle_command(text: str) -> tuple[str, Dict[str, Any]]:
    text = re.sub(r"\s+", " ", text.strip())[:MAX_INPUT]
    route = classify(text)
    if route == "NOT_AUTHORIZED":
        return "I can’t perform that action. It is outside Hermes authority and remains blocked by Nexus safety policy.", {"route": route, "outcome": "BLOCKED"}
    lowered = text.lower()
    if lowered in {"/start", "/help", "help"}:
        return "Nexus Hermes commands: /status, /approvals, /orders, /request <internal work>, /approve <approval_id>, /reject <approval_id>.", {"route": route, "outcome": "ANSWERED"}
    if lowered in {"/status", "status", "what is happening with nexus", "refresh nexus status"} or is_status_request(text):
        return status_response(), {"route": route, "outcome": "ANSWERED"}
    if lowered in {"/approvals", "approvals", "what approvals are waiting"}:
        return approval_response(), {"route": route, "outcome": "ANSWERED"}
    if lowered in {"/orders", "work orders", "what needs my attention"}:
        return orders_response(), {"route": route, "outcome": "ANSWERED"}
    if lowered.startswith("/approve ") or lowered.startswith("/reject "):
        parts = text.split(maxsplit=2)
        approval_id = parts[1] if len(parts) > 1 else ""
        if not re.fullmatch(r"appr_[a-f0-9]+", approval_id):
            return "Use an exact approval identifier, for example: /approve appr_<id>", {"route": "APPROVAL_REQUIRED", "outcome": "REJECTED_INVALID_REFERENCE"}
        decision = "approve" if parts[0].lower() == "/approve" else "reject"
        result = approvals.resolve_approval(approval_id, decision, resolved_by="ray", feedback=parts[2] if len(parts) > 2 else "Telegram Hermes decision")
        if result.get("status") != "ok":
            return f"Approval not changed: {result.get('status')}", {"route": "APPROVAL_REQUIRED", "outcome": "NOT_CHANGED", "approval_id": approval_id}
        return f"Approval {approval_id} {decision}d. No action executes unless its separate governed execution contract permits it.", {"route": "APPROVAL_REQUIRED", "outcome": "APPROVAL_RECORDED", "approval_id": approval_id}
    if route == "APPROVAL_REQUIRED":
        result = create_governed_request(text)
        if result["status"] == "DUPLICATE_SUPPRESSED":
            return f"Duplicate request suppressed. Existing work order: {result['work_order_id']}", {"route": route, **result}
        return f"Governed work order created: {result['work_order_id']}\nPriority: {result['priority']}\nStatus: pending_approval\nApproval: {result['approval_id']}", {"route": route, **result}
    return "I can report Nexus status, show approvals and work orders, or create bounded internal work for approval. Try /status.", {"route": route, "outcome": "ANSWERED"}


def _update_message(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    message = update.get("message")
    sender = message.get("from") if isinstance(message, dict) else None
    if not isinstance(message, dict) or (isinstance(sender, dict) and sender.get("is_bot")):
        return None
    text = message.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT:
        return None
    return message


def _send(token: str, chat_id: int, text: str) -> bool:
    result = telegram_call(token, "sendMessage", {"chat_id": chat_id, "text": text[:MAX_MESSAGE]})
    return bool(result.get("ok"))


def run_once(*, dry_run: bool = False, api: Any = telegram_call) -> Dict[str, Any]:
    started = utc_now()
    token, allowed = _token_and_allowlist()
    result: Dict[str, Any] = {"started_at": started, "trigger": os.environ.get("NEXUS_HERMES_TRIGGER", "manual"), "bot_identity": "Nexus Hermes", "config": {"token": "PRESENT" if token else "ABSENT", "authorized_user": "PRESENT" if allowed else "ABSENT"}, "updates_seen": 0, "updates_processed": 0, "unauthorized_rejected": 0, "duplicates_suppressed": 0, "commands_blocked": 0, "receipts": [], "errors": [], "status": "HEALTHY"}
    if not token or not allowed:
        result.update(status="DEGRADED", outcome="CONFIGURATION_UNAVAILABLE")
        return result
    bot = api(token, "getMe", {})
    if not bot.get("ok"):
        result.update(status="DEGRADED", outcome="TELEGRAM_API_UNAVAILABLE")
        return result
    result["bot_username"] = bot.get("result", {}).get("username", "UNVERIFIED")
    last_id = load_offset()
    response = api(token, "getUpdates", {"offset": last_id + 1, "limit": 20, "timeout": 0, "allowed_updates": json.dumps(["message"])})
    if not response.get("ok"):
        result.update(status="DEGRADED", outcome="GET_UPDATES_FAILED")
        return result
    updates = response.get("result", []) if isinstance(response.get("result", []), list) else []
    result["updates_seen"] = len(updates)
    if not updates:
        result["outcome"] = "NO_UPDATES"
        result["completed_at"] = utc_now()
        return result
    max_id = last_id
    seen_ids: set[int] = set()
    for update in updates:
        try:
            uid = int(update.get("update_id", 0))
        except (TypeError, ValueError):
            continue
        max_id = max(max_id, uid)
        if uid in seen_ids or uid <= last_id:
            result["duplicates_suppressed"] += 1
            continue
        seen_ids.add(uid)
        message = _update_message(update)
        if not message:
            continue
        chat_id = message.get("chat", {}).get("id")
        if not isinstance(chat_id, int) or chat_id not in allowed:
            result["unauthorized_rejected"] += 1
            continue
        text = message["text"]
        fingerprint = message_hash(text)
        response_text, metadata = handle_command(text)
        if metadata.get("outcome") == "BLOCKED":
            result["commands_blocked"] += 1
        if metadata.get("status") == "DUPLICATE_SUPPRESSED":
            result["duplicates_suppressed"] += 1
        delivered = True if dry_run else _send(token, chat_id, response_text)
        receipt = {"receipt_id": f"hermes_tg_{uid}_{fingerprint}", "update_id": uid, "message_fingerprint": fingerprint, "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16], "outcome": metadata.get("outcome"), "route": metadata.get("route"), "delivered": delivered, "created_work_order_id": metadata.get("work_order_id"), "approval_id": metadata.get("approval_id"), "created_at": utc_now()}
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        write_json(RECEIPT_DIR / f"{receipt['receipt_id']}.json", receipt)
        result["receipts"].append(receipt["receipt_id"])
        result["updates_processed"] += 1
    save_offset(max_id)
    result["outcome"] = "PROCESSED" if result["updates_processed"] else "NO_AUTHORIZED_TEXT_UPDATES"
    result["completed_at"] = utc_now()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded Hermes Telegram polling cycle")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.once and not args.dry_run:
        parser.error("--once or --dry-run is required")
    with single_run_lock() as acquired:
        if not acquired:
            print(json.dumps({"status": "SKIPPED_OVERLAP", "outcome": "SKIPPED_OVERLAP"}, indent=2))
            return 0
        result = run_once(dry_run=args.dry_run)
        heartbeat = {"bot_identity": result.get("bot_identity"), "bot_username": result.get("bot_username"), "last_run": result.get("completed_at") or utc_now(), "run_status": result.get("outcome", result.get("status")), "api_status": result.get("status"), "updates_seen": result.get("updates_seen", 0), "updates_processed": result.get("updates_processed", 0), "unauthorized_rejected": result.get("unauthorized_rejected", 0), "commands_blocked": result.get("commands_blocked", 0), "errors": result.get("errors", []), "authority": {"external_actions": "BLOCKED", "stripe_autonomous_execution": "DISABLED", "arbitrary_shell": "UNAVAILABLE", "alpha": "NOT_ENABLED", "nova": "NOT_ENABLED"}}
        write_json(HEARTBEAT_PATH, heartbeat)
        print(json.dumps({**result, "heartbeat_path": str(HEARTBEAT_PATH.relative_to(ROOT))}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
