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
import subprocess
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/operations"))
from nexus_agent_platform.governed import approvals, work_orders  # noqa: E402
from nexus_agent_platform.control_object_resolver import resolve_control_object  # noqa: E402
from nexus_agent_platform.human_gate_router import route_response  # noqa: E402
from nexus_agent_platform.loop_certification_campaign import campaign_control_intent, completion_text, handle_control as handle_loop_certification_control, load_campaign, notification_already_sent, observe_runtime_event, record_campaign_message, record_notification  # noqa: E402

RUNTIME_ENV = Path("/Users/raymonddavis/.config/nexus/runtime.env")
OFFSET_PATH = ROOT / "data/runtime/telegram_last_update_id.json"
HEARTBEAT_PATH = ROOT / "reports/runtime/nexus_hermes_telegram_heartbeat_latest.json"
RECEIPT_DIR = ROOT / "reports/telegram/hermes_operator_receipts"
LOCK_PATH = ROOT / "data/runtime/nexus_hermes_telegram.lock"
API_BASE = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE = 4000
MAX_INPUT = 1000
HTTP_TIMEOUT = 10

try:
    import certifi
except ImportError:  # pragma: no cover - launchd fallback
    certifi = None

BLOCKED_PATTERNS = (
    r"\b(charge|refund|pay|payment|stripe|transfer|withdraw|deposit)\b",
    r"\b(funded?\s+trade|place\s+(a\s+)?trade|buy|sell|execute\s+trade)\b",
    r"\b(send|email|text|sms|post|publish|message)\b.*\b(customer|client|external|social|telegram)\b",
    r"\b(shell|terminal|bash|zsh|sudo|command|exec|run)\b",
    r"\b(token|secret|credential|password|runtime\.env|api key)\b",
    r"\b(deploy|production|install|security settings?)\b",
)
PRODUCT_EVOLUTION_CONTEXT_PATH = ROOT / "data/runtime/telegram_conversation_context.json"
PRODUCT_EVOLUTION_CONTEXT_TTL = 10 * 60
MANUAL_CERT_REPORT_PATH = ROOT / "reports/runtime/manual_e2e_latest.json"
MANUAL_CERT_COMMANDS = {
    "START": re.compile(r"^START MANUAL CERT (MANUAL-E2E-[0-9]{8}-[0-9]{4})$"),
    "EMAIL": re.compile(r"^ALLOW EMAIL CANARY (MANUAL-E2E-[0-9]{8}-[0-9]{4})$"),
    "CONTINUE_REPAIR": re.compile(r"^CONTINUE ACTIVE OPERATOR REPAIR (MANUAL-E2E-[0-9]{8}-[0-9]{4})$"),
    "HOLD": re.compile(r"^HOLD (MANUAL-E2E-[0-9]{8}-[0-9]{4})$"),
}
REPAIR_APPROVAL = re.compile(r"^APPROVE REPAIR ([A-Z0-9][A-Z0-9_-]{2,40}) (MANUAL-E2E-[0-9]{8}-[0-9]{4})$")
SYSTEM_HEALTH_COMMAND = re.compile(r"^/run\s+system_health$", re.I)


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
        context = None
        if certifi is not None:
            import ssl
            context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT, context=context) as response:
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


def send_message(token: str, chat_id: int, text: str) -> Dict[str, Any]:
    """Certified Hermes Telegram sender; returns safe delivery metadata."""
    return telegram_call(token, "sendMessage", {"chat_id": chat_id, "text": text[:MAX_MESSAGE]})


def classify(text: str) -> str:
    lowered = text.lower()
    try:
        from nexus_product_evolution.telegram_control import is_product_evolution_intent, is_unsafe_product_evolution_request
        if is_unsafe_product_evolution_request(text):
            return "NOT_AUTHORIZED"
        if is_product_evolution_intent(text):
            return "PRODUCT_EVOLUTION"
    except Exception:
        pass
    if any(re.search(pattern, lowered) for pattern in BLOCKED_PATTERNS):
        return "NOT_AUTHORIZED"
    if lowered.startswith(("/request ", "/work ", "create a work order", "turn this into a work order")):
        return "APPROVAL_REQUIRED"
    if lowered.startswith(("/approve ", "/reject ")):
        return "APPROVAL_REQUIRED"
    return "AUTO_EXECUTE_INTERNAL_SAFE"


def _context_key(chat_id: Optional[int]) -> str:
    return str(chat_id) if chat_id is not None else "direct"


def _load_chat_context(chat_id: Optional[int]) -> Dict[str, Any]:
    if chat_id is None:
        return {}
    value = load_json(PRODUCT_EVOLUTION_CONTEXT_PATH, {})
    if not isinstance(value, dict):
        return {}
    item = value.get(_context_key(chat_id))
    if not isinstance(item, dict):
        return {}
    try:
        age = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(str(item.get("last_updated"))).timestamp()
    except (TypeError, ValueError):
        return {}
    return item if 0 <= age <= PRODUCT_EVOLUTION_CONTEXT_TTL else {}


def _save_chat_context(chat_id: Optional[int], route: str, topic: str = "product_evolution", mission_id: Optional[str] = None) -> None:
    if chat_id is None:
        return
    value = load_json(PRODUCT_EVOLUTION_CONTEXT_PATH, {})
    if not isinstance(value, dict):
        value = {}
    prior = value.get(_context_key(chat_id)) if isinstance(value.get(_context_key(chat_id)), dict) else {}
    value[_context_key(chat_id)] = {"last_route": route, "last_topic": topic, "last_updated": utc_now(), "last_mission_id": mission_id or prior.get("last_mission_id")}
    write_json(PRODUCT_EVOLUTION_CONTEXT_PATH, value)


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
    operator_state = _active_operator_runtime_state()
    repair_state = load_json(ROOT / "reports/runtime/voice_repair_latest.json", {})
    return {
        "core_runtime": core_health,
        "active_operator": {**_health(ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json", "operator_health"), **operator_state},
        "current_repair": repair_state.get("repair_id") if isinstance(repair_state, dict) and repair_state.get("state") not in {None, "PASS", "FAIL", "BLOCKED"} else "NONE",
        "recovery_check": _health(ROOT / "reports/runtime/nexus_recovery_check_heartbeat_latest.json", "run_status"),
        "pending_work_orders": len(orders), "pending_approvals": len(pending), "high_priority_items": len(priority), "last_updated": utc_now(),
    }


def _active_operator_runtime_state() -> Dict[str, Any]:
    """Read scheduler state separately from the operator's software health."""
    service = "com.nexus.active-operator-v2"
    try:
        check = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{service}"], capture_output=True, text=True, timeout=2, check=False)
        loaded = check.returncode == 0
    except (OSError, subprocess.SubprocessError):
        loaded = False
    return {"execution": "RUNNABLE" if loaded else "PAUSED", "scheduled": "YES" if loaded else "NO", "service": service if loaded else None}


def status_response() -> str:
    context = build_context()
    core = context["core_runtime"]["status"]
    active = context["active_operator"]["status"]
    recovery = context["recovery_check"]["status"]
    return (f"Nexus Hermes status\n\nCore runtime: {core}\nActive Operator health: {active}\n"
            f"Active Operator execution: {context['active_operator'].get('execution', 'UNKNOWN')}\n"
            f"Active Operator scheduled: {context['active_operator'].get('scheduled', 'UNKNOWN')}\n"
            f"Current repair: {context.get('current_repair', 'NONE')}\nRecovery Check: {recovery}\n"
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
        r"^(?:can you )?(?:please )?(?:provide|give me) (?:a )?(?:current )?system status(?: report)?$",
        r"^what(?: is|'s) the health of nexus$",
        r"^what(?: is|'s) nexus health$",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in patterns)


def is_portfolio_request(text: str) -> bool:
    normalized = re.sub(r"[?.!]+$", "", text.strip().lower())
    normalized = re.sub(r"^(?:@?nexus|hermes)\s*[,:\-]?\s*", "", normalized)
    return normalized in {"/portfolio", "portfolio", "portfolio status", "executive portfolio status", "what is nexus working on"}


def portfolio_response() -> str:
    try:
        from nexus_agent_platform.executive_portfolio import portfolio_status_response
        return portfolio_status_response()
    except Exception:
        return "Executive portfolio is temporarily unavailable; no work state was changed."


def ideas_response() -> str:
    from nexus_agent_platform.overnight_autonomy import list_ideas
    value = list_ideas()
    newest = value.get("newest") or []
    lines = [f"Idea Inbox: {value['count']} captured | research-ready: {value['research_ready']} | promoted: {value['promoted']}"]
    lines.extend(f"- {row.get('idea_id')}: {str(row.get('text', ''))[:120]} ({row.get('status')})" for row in newest)
    return "\n".join(lines)


def morning_response() -> str:
    from nexus_agent_platform.overnight_autonomy import morning_report
    return morning_report()


def models_response() -> str:
    from nexus_agent_platform.overnight_autonomy import MODEL_REGISTRY
    return "Nexus Model Control\n" + "\n".join(f"- {role}: {'available' if info['enabled'] else 'not configured'} / {info['provider']}" for role, info in MODEL_REGISTRY.items()) + "\nCritic action authority: NONE"


def brain_response() -> str:
    from nexus_agent_platform.overnight_autonomy import campaign_status
    return "Hermes brain decision stack: L0 input → L1 authority → L2 intent → L3 evidence → L4 model routing → L5 executor → L6 critic → L7 approval → L8 execution → L9 verification → L10 response.\nCampaign: " + str(campaign_status().get("status", "UNKNOWN"))


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


def _manual_certification_command(text: str) -> Optional[Dict[str, str]]:
    """Recognize only exact, run-shaped manual certification commands."""
    for command, pattern in MANUAL_CERT_COMMANDS.items():
        match = pattern.fullmatch(text.strip())
        if match:
            return {"command": command, "run_id": match.group(1)}
    return None


def _record_manual_certification_approval(command: Dict[str, str], *, chat_id: Optional[int], update_id: Optional[int]) -> Dict[str, Any]:
    """Record a real, exact approval against the currently active run only."""
    report = load_json(MANUAL_CERT_REPORT_PATH, {})
    run_id = command["run_id"]
    if report.get("run_id") != run_id:
        return {"status": "REJECTED_WRONG_RUN", "run_id": run_id}
    key = f"{command['command']}:{run_id}"
    approvals_state = report.setdefault("human_approvals", {})
    existing = approvals_state.get(key)
    if existing:
        return {"status": "DUPLICATE_SUPPRESSED", "run_id": run_id, "approval_key": key}
    approvals_state[key] = {
        "status": "PASS",
        "command": command["command"],
        "run_id": run_id,
        "update_id": update_id,
        "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16] if chat_id is not None else None,
        "received_at": utc_now(),
    }
    if command["command"] == "EMAIL":
        report["email_canary_approval"] = "PASS"
        report["approval_run_id_match"] = "PASS"
        report["current_phase"] = "EMAIL_CANARY_EXECUTION"
    elif command["command"] == "START":
        report["ray_start_approval"] = "PASS"
    write_json(MANUAL_CERT_REPORT_PATH, report)
    return {"status": "PASS", "run_id": run_id, "approval_key": key}


def _repair_approval_command(text: str) -> Optional[Dict[str, str]]:
    match = REPAIR_APPROVAL.fullmatch(text.strip())
    return {"repair_id": match.group(1), "run_id": match.group(2)} if match else None


def _natural_repair_command(text: str) -> Optional[Dict[str, str]]:
    report = load_json(MANUAL_CERT_REPORT_PATH, {})
    run_id = report.get("run_id")
    if not run_id or report.get("status") not in {"WAITING_HUMAN_ACTION", "WAITING_APPROVAL"}:
        return None
    normalized = re.sub(r"[^a-z0-9_-]+", " ", text.lower()).strip()
    if normalized not in {"nexus repair voice", "approve voice", "repair voice", "repair voice-001", "can you start repair", "start repair", "start the repair", "continue the voice repair", "resume voice", "start voice-001", "start the voice repair"}:
        return None
    return {"repair_id": "VOICE-001", "run_id": run_id}


def _repair_progress_request(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9_-]+", " ", text.lower()).strip()
    words = set(normalized.split())
    return ("voice" in words or "voice-001" in words) and ("repair" in words or "voice-001" in words) and bool(words.intersection({"status", "happening", "doing", "done", "progress", "working", "dispatcher", "queued", "process", "mission"}))


def _repair_progress_response() -> tuple[str, Dict[str, Any]]:
    state = load_json(ROOT / "reports/runtime/voice_repair_latest.json", {})
    if not isinstance(state, dict) or not state.get("repair_id"):
        return "No active Voice repair work order exists.", {"route": "VOICE_REPAIR_STATUS", "outcome": "NOT_FOUND"}
    return (f"VOICE-001\nState: {state.get('state', 'UNKNOWN')}\nWork order: {state.get('work_order_id', 'UNKNOWN')}\n"
            f"Current step: {state.get('executor', 'governed repair')}\nNo other repairs are executing.",
            {"route": "VOICE_REPAIR_STATUS", "outcome": "ANSWERED", "repair_id": "VOICE-001", "state": state.get("state")})


def _repair_dispatch_diagnostic() -> tuple[str, Dict[str, Any]]:
    state = load_json(ROOT / "reports/runtime/voice_repair_latest.json", {})
    order = next((item for item in work_orders.list_work_orders(limit=1000) if item.get("work_order_id") == state.get("work_order_id")), None)
    mission_path = ROOT / "reports/product_evolution/campaign-capability-gap-voice_full_machine_acceptance.json"
    mission = load_json(mission_path, {})
    mission_result = mission.get("result", {}) if isinstance(mission, dict) else {}
    return (f"VOICE-001 dispatch diagnostic\n\nWork order: {state.get('work_order_id', 'NOT_FOUND')}\n"
            f"Repair state: {state.get('state', 'UNKNOWN')}\nDispatcher: {state.get('dispatcher', 'manual-approved-repair-dispatch')}\n"
            f"Worker pickup: {state.get('runtime_pickup_state', 'NOT_OBSERVED')}\nWorker PID: {state.get('worker_pid', 'UNKNOWN')}\n"
            f"Engineering run: {state.get('engineering_run_id', 'NOT_OBSERVED')}\n"
            f"Queue reason: {('awaiting immediate approved-repair pickup' if state.get('state') == 'QUEUED' else 'not queued')}\n"
            f"Observed Product Evolution mission: {mission_result.get('mission_id', 'NOT_FOUND')}\n"
            f"Mission linkage: {'YES' if mission_result.get('work_order_id') == state.get('work_order_id') else 'NO — generic capability-gap mission is not this repair'}\n"
            f"Mission queue state: {mission_result.get('status', 'UNKNOWN')}\n", {"route": "VOICE_REPAIR_DISPATCH_DIAGNOSTIC", "outcome": "ANSWERED", "repair_id": "VOICE-001", "state": state.get("state"), "work_order_id": state.get("work_order_id")})


def _record_repair_approval(command: Dict[str, str], *, chat_id: Optional[int], update_id: Optional[int]) -> Dict[str, Any]:
    report = load_json(MANUAL_CERT_REPORT_PATH, {})
    run_id, repair_id = command["run_id"], command["repair_id"]
    if report.get("run_id") != run_id:
        return {"status": "REJECTED_WRONG_RUN", "run_id": run_id, "repair_id": repair_id}
    candidates = report.get("repair_queue", [])
    candidate = next((x for x in candidates if (x.get("repair_id") if isinstance(x, dict) else x) == repair_id), None)
    if isinstance(candidate, str):
        candidate = {"repair_id": candidate, "status": "WAITING_APPROVAL"}
    if not candidate:
        return {"status": "REJECTED_UNKNOWN_REPAIR", "run_id": run_id, "repair_id": repair_id}
    if candidate.get("status") != "WAITING_APPROVAL":
        return {"status": "REJECTED_REPAIR_NOT_WAITING", "run_id": run_id, "repair_id": repair_id}
    key = f"{repair_id}:{run_id}"
    approvals_state = report.setdefault("repair_approvals", {})
    if key in approvals_state:
        return {"status": "DUPLICATE_SUPPRESSED", "run_id": run_id, "repair_id": repair_id, "authority_scope": [repair_id]}
    approvals_state[key] = {"status": "PASS", "run_id": run_id, "repair_id": repair_id, "authority_scope": [repair_id], "channel": "telegram", "update_id": update_id, "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16] if chat_id is not None else None, "approved_at": utc_now()}
    report["approved_repair_ids"] = sorted({*report.get("approved_repair_ids", []), repair_id})
    write_json(MANUAL_CERT_REPORT_PATH, report)
    return {"status": "PASS", "run_id": run_id, "repair_id": repair_id, "authority_scope": [repair_id]}


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


def handle_command(text: str, *, chat_id: Optional[int] = None, update_id: Optional[int] = None) -> tuple[str, Dict[str, Any]]:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) > MAX_INPUT:
        return ("Message received but exceeds Hermes command limit. Use /portfolio, /status, /approvals, or send a shorter request.", {"route": "INPUT_TOO_LONG", "outcome": "REJECTED_INPUT_TOO_LONG", "input_too_long": True})
    campaign_control = handle_loop_certification_control(text, update_id=update_id, chat_id=chat_id)
    if campaign_control is not None:
        return campaign_control
    if SYSTEM_HEALTH_COMMAND.fullmatch(text):
        from nexus_active_operator_runner import run_system_health_check
        correlation_id = f"{load_campaign().get('campaign_id', 'NO_CAMPAIGN')}:{update_id or 'DIRECT'}"
        result = run_system_health_check(incoming_update_id=int(update_id or 0), correlation_id=correlation_id, trigger="telegram")
        completed = result.get("execution_status") == "COMPLETED"
        overall = ((result.get("health_result") or {}).get("data") or {}).get("overall_status", "UNKNOWN")
        response = (f"System Health Check {'completed' if completed else 'failed'}.\nOverall health: {overall}\n"
                    f"Report: {result.get('canonical_report_path')}\nReceipt: {result.get('canonical_receipt_path')}\n"
                    "No external action was performed.")
        return response, {"route": "SYSTEM_HEALTH_PROCESS", "outcome": "ANSWERED" if completed else "BLOCKED", "process_id": "system_health", "system_health_run_id": result.get("run_id"), "system_health_run_started": bool(result.get("started_at")), "system_health_run_completed": completed, "canonical_report_written": result.get("canonical_report_written") is True, "canonical_receipt_written": result.get("canonical_receipt_written") is True, "canonical_report_path": result.get("canonical_report_path"), "canonical_receipt_path": result.get("canonical_receipt_path"), "read_only": True, "external_side_effects": False, "health_status": overall}
    route = classify(text)
    lowered = text.lower()
    control_object = resolve_control_object(text, _load_chat_context(chat_id))
    if control_object.get("object_type") == "UNKNOWN_REPAIR":
        return f"I could not find persisted repair {control_object['object_id']}. No repair or mission was created.", {"route": "GOVERNED_REPAIR_CONTROL", "outcome": "UNKNOWN_REPAIR", **control_object}
    if control_object.get("object_type") == "REPAIR":
        repair_id = control_object.get("object_id") or control_object.get("repair_id")
        state = load_json(ROOT / "reports/runtime/voice_repair_latest.json", {}) if repair_id == "VOICE-001" else {}
        if re.search(r"\b(?:deploy|production deployment|promote)\b", lowered):
            return (f"{repair_id} is not deployed. Production deployment requires separate scoped approval; no deployment was performed.\n\n"
                    "The existing repair lineage remains preserved.", {"route": "GOVERNED_REPAIR_DEPLOYMENT", "outcome": "WAITING_HUMAN", "repair_id": repair_id, "work_order_id": control_object.get("work_order_id"), "authority_scope": [repair_id], "deployment_authority": "SEPARATE_APPROVAL_REQUIRED"})
        if re.search(r"\b(?:continue|resume|start|repair|status|state|why|who|working|happening|doing)\b", lowered):
            return (f"{repair_id}\nState: {state.get('state', 'UNKNOWN')}\nWork order: {control_object.get('work_order_id') or state.get('work_order_id', 'UNKNOWN')}\n"
                    f"Worker: {state.get('executor', 'NONE')}\nCurrent step: {state.get('failure') or state.get('runtime_pickup_state') or 'NONE'}\n"
                    "No repair was executed by this status request.", {"route": "GOVERNED_REPAIR_CONTROL", "outcome": "ANSWERED", "repair_id": repair_id, "work_order_id": control_object.get("work_order_id"), "state": state.get("state"), "worker": state.get("executor"), "current_step": state.get("failure") or state.get("runtime_pickup_state"), "control_object": control_object, "read_only": True, "repair_executed": False})
    manual_command = _manual_certification_command(text)
    if manual_command and manual_command["command"] == "CONTINUE_REPAIR":
        report = load_json(MANUAL_CERT_REPORT_PATH, {})
        pending = [
            (x.get("repair_id") if isinstance(x, dict) else x)
            for x in report.get("repair_queue", [])
            if (x.get("status") == "WAITING_APPROVAL" if isinstance(x, dict) else True)
        ]
        return f"Which repair should I approve?\n\nPending: {', '.join(pending)}\n\nReply: APPROVE REPAIR <REPAIR_ID> {report.get('run_id', manual_command['run_id'])}", {"route": "MANUAL_REPAIR_SELECTION", "outcome": "SELECTION_REQUIRED", "authority_scope": []}
    if manual_command:
        result = _record_manual_certification_approval(manual_command, chat_id=chat_id, update_id=update_id)
        if result["status"] == "PASS":
            return "Manual certification approval recorded. No canary action executed yet.", {"route": "MANUAL_CERTIFICATION_APPROVAL", "outcome": "APPROVAL_RECORDED", **result}
        if result["status"] == "DUPLICATE_SUPPRESSED":
            return "Manual certification approval already recorded. No duplicate action executed.", {"route": "MANUAL_CERTIFICATION_APPROVAL", "outcome": "DUPLICATE_SUPPRESSED", **result}
        return "Manual certification approval rejected because the run is not active.", {"route": "MANUAL_CERTIFICATION_APPROVAL", "outcome": result["status"], **result}
    repair_command = _repair_approval_command(text)
    natural_repair = _natural_repair_command(text)
    if not repair_command:
        repair_command = natural_repair
    if repair_command:
        if natural_repair is not None:
            from nexus_agent_platform.governed.voice_repair import start_voice_repair
            result = start_voice_repair(repair_command["run_id"], chat_id=chat_id)
            if result["status"] in {"started", "queued"}:
                wording = "repair queued; immediate dispatcher pickup requested" if result["status"] == "queued" else "repair started"
                return (f"VOICE-001 {wording}.\n\nRun: {repair_command['run_id']}\nWork order: {result['work_order_id']}\n"
                        "Scope: Repair production Voice routing through the governed Netlify relay.\n\n"
                        "Email and Meta remain unapproved.\nActive Operator remains paused.",
                        {"route": "VOICE_REPAIR_START", "outcome": "STARTED" if result["status"] == "started" else "QUEUED", "repair_started": result["status"] == "started", "repair_queued": True, "wording": wording, **result})
            if result["status"] == "already_started":
                return (f"VOICE-001 repair is already {result.get('state', 'active')}.\nWork order: {result.get('work_order_id')}\nNo duplicate execution started.", {"route": "VOICE_REPAIR_START", "outcome": "DUPLICATE_SUPPRESSED", **result})
            if result["status"] == "waiting_approval":
                return "VOICE-001 still requires approval. No repair started.", {"route": "VOICE_REPAIR_START", "outcome": "WAITING_APPROVAL", **result}
        result = _record_repair_approval(repair_command, chat_id=chat_id, update_id=update_id)
        if result["status"] == "PASS":
            report = load_json(MANUAL_CERT_REPORT_PATH, {})
            remaining = [
                (x.get("repair_id") if isinstance(x, dict) else x)
                for x in report.get("repair_queue", [])
                if (x.get("status") == "WAITING_APPROVAL" if isinstance(x, dict) else x != repair_command["repair_id"])
                and (x.get("repair_id") if isinstance(x, dict) else x) != repair_command["repair_id"]
            ]
            return f"Repair approval recorded.\n\nRun: {repair_command['run_id']}\nApproved: {repair_command['repair_id']}\nStill waiting approval: {', '.join(remaining) or 'none'}\n\nActive Operator remains paused.\nNo repair has executed.", {"route": "MANUAL_REPAIR_APPROVAL", "outcome": "APPROVAL_RECORDED", **result}
        if result["status"] == "DUPLICATE_SUPPRESSED":
            return "That repair approval was already recorded. No repair has executed.", {"route": "MANUAL_REPAIR_APPROVAL", "outcome": "DUPLICATE_SUPPRESSED", **result}
        return "Repair approval rejected. No Nexus state was changed.", {"route": "MANUAL_REPAIR_APPROVAL", "outcome": result["status"], **result}
    if _repair_progress_request(text):
        if any(word in text.lower() for word in ("dispatcher", "process", "mission", "queued")):
            return _repair_dispatch_diagnostic()
        return _repair_progress_response()
    if text == "CONTINUE ACTIVE OPERATOR REPAIR MANUAL-E2E-20260827-2992":
        report = load_json(MANUAL_CERT_REPORT_PATH, {})
        pending = [x.get("repair_id") for x in report.get("repair_queue", []) if x.get("status") == "WAITING_APPROVAL"]
        return f"Which repair should I approve?\n\nPending: {', '.join(pending)}\n\nReply: APPROVE REPAIR <REPAIR_ID> {report.get('run_id', 'MANUAL-E2E-20260827-2992')}", {"route": "MANUAL_REPAIR_SELECTION", "outcome": "SELECTION_REQUIRED", "authority_scope": []}
    if is_portfolio_request(text):
        return portfolio_response(), {"route": "EXECUTIVE_PORTFOLIO_READ", "outcome": "ANSWERED", "read_only": True}
    if re.match(r"^\s*(?:IDEA\s*:|idea\s+)", text, re.I):
        from nexus_agent_platform.overnight_autonomy import capture_idea
        idea = capture_idea(text)
        return f"Idea saved: {idea['idea_id']}\nCategory: {idea['category']}\nPortfolio status: BACKLOG\nNo execution started.", {"route": "IDEA_INBOX_CAPTURE", "outcome": "CAPTURED", "idea_id": idea["idea_id"], "read_only": False}
    try:
        from nexus_product_evolution.telegram_control import classify_product_evolution_request, handle_product_evolution_intake
        recent = _load_chat_context(chat_id)
        contextual_blocked = bool(re.fullmatch(r"(?:nexus[, :\-]*)?\s*what(?: is|'s) blocked\??", lowered.strip())) and recent.get("last_topic") == "product_evolution"
        contextual_diagnostic = bool(re.search(r"\b(?:picked|runtime|dispatcher|queued|waiting|started|execution)\b", lowered)) and recent.get("last_topic") == "product_evolution"
        classification = classify_product_evolution_request(text, context_mission_id=recent.get("last_mission_id"))
        # Explicit Hermes approval commands belong to the governed approval
        # handler below; Product Evolution's natural-language classifier must
        # not reinterpret the approval identifier as mission evidence.
        if not lowered.startswith(("/approve ", "/reject ")) and (classification != "CLARIFICATION" or contextual_blocked or contextual_diagnostic):
            evolution = handle_product_evolution_intake(text if not contextual_blocked else "Product Evolution: what is blocked?", context_mission_id=recent.get("last_mission_id"))
            if evolution.get("handled"):
                _save_chat_context(chat_id, evolution.get("route", "PRODUCT_EVOLUTION"), mission_id=evolution.get("mission_id"))
                metadata = {"route": evolution.get("route"), "outcome": evolution.get("status"), "product_evolution": evolution}
                if evolution.get("mission_id"):
                    metadata["mission_id"] = evolution["mission_id"]
                return evolution["response"], metadata
    except Exception as exc:
        if route == "PRODUCT_EVOLUTION":
            return "Product Evolution intake is temporarily unavailable; no mission was started.", {"route": "PRODUCT_EVOLUTION", "outcome": "BLOCKED", "error": type(exc).__name__}
    if route == "NOT_AUTHORIZED":
        return "I can’t perform that action. It is outside Hermes authority and remains blocked by Nexus safety policy.", {"route": route, "outcome": "BLOCKED"}
    if lowered in {"/start", "/help", "help"}:
        return "Nexus Hermes commands: /status, /approvals, /orders, /request <internal work>, /approve <approval_id>, /reject <approval_id>.", {"route": route, "outcome": "ANSWERED"}
    if lowered in {"/status", "status", "what is happening with nexus", "refresh nexus status"} or is_status_request(text):
        return status_response(), {"route": route, "outcome": "ANSWERED"}
    if lowered in {"/ideas", "ideas", "idea inbox"}:
        return ideas_response(), {"route": "IDEA_INBOX_READ", "outcome": "ANSWERED", "read_only": True}
    if lowered in {"/morning", "morning", "morning report"}:
        return morning_response(), {"route": "MORNING_REPORT_READ", "outcome": "ANSWERED", "read_only": True}
    if lowered in {"/models", "models", "model control"}:
        return models_response(), {"route": "MODEL_CONTROL_READ", "outcome": "ANSWERED", "read_only": True}
    if lowered in {"/brain", "brain", "hermes brain"}:
        return brain_response(), {"route": "HERMES_BRAIN_READ", "outcome": "ANSWERED", "read_only": True}
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
    if not isinstance(text, str) or not text.strip():
        return None
    return message


def _send(token: str, chat_id: int, text: str) -> bool:
    result = send_message(token, chat_id, text)
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
        # Manual certification and repair-control phrases must reach their
        # deterministic handler before generic conversational routing.
        manual_control = bool(
            _manual_certification_command(text)
            or _repair_approval_command(text)
            or _natural_repair_command(text)
            or _repair_progress_request(text)
            or campaign_control_intent(text)
        )
        gate_result = None if manual_control else route_response(text, sender=(lambda body: {"delivered": _send(token, chat_id, body)}))
        if gate_result is not None:
            response_text = gate_result.pop("response")
            metadata = gate_result
        else:
            response_text, metadata = handle_command(text, chat_id=chat_id, update_id=uid)
        evolution = metadata.get("product_evolution") if isinstance(metadata, dict) else None
        if isinstance(evolution, dict) and evolution.get("status") == "CONTRACT_READY":
            try:
                from nexus_product_evolution.telegram_control import ProductEvolutionReporter, dispatch_product_evolution_mission, run_safe_mobile_reporting_mission
                reporter = ProductEvolutionReporter(lambda body: send_message(token, chat_id, body))
                contract_data = evolution.get("contract") or {}
                if "status reporting" in text.lower() or "mobile reporting" in text.lower():
                    from nexus_product_evolution.loop import MissionContract
                    safe_result = run_safe_mobile_reporting_mission(MissionContract(**contract_data), reporter)
                    response_text = safe_result["response"]
                    metadata["product_evolution_result"] = safe_result["result"].status
                    metadata["product_evolution_skip_reply"] = True
                    deliveries = reporter.deliveries
                    metadata["product_evolution_message_id"] = deliveries[-1].get("message_id") if deliveries else None
                else:
                    from nexus_product_evolution.loop import MissionContract
                    registered = dispatch_product_evolution_mission(MissionContract(**contract_data))
                    response_text = f"🧠 Nexus Product Evolution started\n\nMission: {registered['mission_id']}\nGoal: {(evolution.get('contract') or {}).get('goal', 'Product experience improvement')}\n\nQueued for the existing governed Product Evolution runtime. I will only interrupt you for a true blocker."
                    metadata.update({"product_evolution_started": True, "mission_id": registered["mission_id"], "mission_status": registered["status"], "receipt_path": registered["receipt_path"]})
                    _save_chat_context(chat_id, "PRODUCT_EVOLUTION", mission_id=registered["mission_id"])
            except Exception as exc:
                response_text = "Product Evolution was not started because its bounded runner failed safely."
                metadata["product_evolution_error"] = type(exc).__name__
        if metadata.get("outcome") == "BLOCKED":
            result["commands_blocked"] += 1
        if metadata.get("status") == "DUPLICATE_SUPPRESSED":
            result["duplicates_suppressed"] += 1
        outgoing_message_id = None
        if metadata.get("confirmation_delivered"):
            # HumanGateResponseRouter already sent and recorded the executive
            # confirmation through the same real Telegram transport.
            delivered = True
        elif metadata.get("product_evolution_skip_reply"):
            delivered = True
        else:
            if dry_run:
                delivered = True
                outgoing_message_id = None
            else:
                delivery = send_message(token, chat_id, response_text)
                delivered = bool(delivery.get("ok"))
                outgoing_message_id = (delivery.get("result") or {}).get("message_id") if delivered else None
        if not dry_run:
            active_campaign = load_campaign()
            certification = observe_runtime_event(campaign_id=active_campaign.get("campaign_id", ""), current_loop=active_campaign.get("current_loop"), incoming_update_id=uid, route=metadata.get("route", "UNKNOWN"), outcome=metadata.get("outcome"), metadata=metadata, response_text=response_text, outgoing_message_id=outgoing_message_id, delivered=delivered)
            campaign_id = certification.get("campaign_id") or active_campaign.get("campaign_id")
            state_key = f"{certification.get('current_loop')}:{certification.get('certified_at')}"
            if certification.get("newly_certified") and delivered and campaign_id and not notification_already_sent(campaign_id=campaign_id, notification_type="LOOP_CERTIFICATION_COMPLETE", requested_action="WAIT_NEXT_LOOP_APPROVAL", state_key=state_key):
                completion = completion_text(certification)
                completion_delivery = send_message(token, chat_id, completion)
                completion_id = (completion_delivery.get("result") or {}).get("message_id") if completion_delivery.get("ok") else None
                record_campaign_message(campaign_id=campaign_id, loop_id=certification.get("current_loop"), incoming_update_id=uid, outgoing_message_id=completion_id, correlation_id=f"{campaign_id}:{uid}", action="CERTIFICATION_COMPLETE", delivered=bool(completion_delivery.get("ok")))
                record_notification(campaign_id=campaign_id, notification_type="LOOP_CERTIFICATION_COMPLETE", requested_action="WAIT_NEXT_LOOP_APPROVAL", state_key=state_key, delivered=bool(completion_delivery.get("ok")))
        receipt = {"receipt_id": f"hermes_tg_{uid}_{fingerprint}", "update_id": uid, "message_fingerprint": fingerprint, "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16], "outcome": metadata.get("outcome"), "route": metadata.get("route"), "delivered": delivered, "response_telegram_message_id": outgoing_message_id or metadata.get("product_evolution_message_id"), "created_work_order_id": metadata.get("work_order_id"), "approval_id": metadata.get("approval_id"), "campaign_id": metadata.get("campaign_id"), "correlation_id": f"{metadata.get('campaign_id')}:{uid}" if metadata.get("campaign_id") else None, "created_at": utc_now()}
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
