#!/usr/bin/env python3
"""
Hermes Nova Telegram Worker — Isolated conversational agent for @HermesNovaBot.

Lifecycle:
  Telegram update → Authorization → Conversation memory load →
  Nova graph → OpenRouter model → Validation → Telegram delivery

Separate from Nexus Hermes and Alpha. Uses HERMES_NOVA_TELEGRAM_BOT_TOKEN only.
Owns its own update offset. Never shares state with other bots.

Usage:
  python3 scripts/nova/nova_telegram_worker.py --once
  python3 scripts/nova/nova_telegram_worker.py --poll
  python3 scripts/nova/nova_telegram_worker.py --test
"""

import json
import os
import sys
import re
import ssl
import time
import signal
import hashlib
import random
import socket
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RUNTIME_ENV = os.path.expanduser("~/.config/nexus/runtime.env")

NOVA_STATE_DIR = os.path.join(REPO_ROOT, "data", "runtime")
NOVA_OFFSET_PATH = os.path.join(NOVA_STATE_DIR, "nova_telegram_last_update_id.json")
NOVA_STATUS_PATH = os.path.join(NOVA_STATE_DIR, "nova_telegram_status.json")
NOVA_LOG_PATH = os.path.join(REPO_ROOT, "reports", "runtime", "nova_telegram.log")
NOVA_ERROR_LOG = os.path.join(REPO_ROOT, "reports", "runtime", "nova_telegram_error.log")
NOVA_RECEIPTS_DIR = os.path.join(REPO_ROOT, "reports", "telegram", "receipts", "nova")
NOVA_DELIVERY_DIR = os.path.join(NOVA_STATE_DIR, "nova_telegram_delivery")
NOVA_AB_DIR = os.path.join(REPO_ROOT, "reports", "telegram", "ab_certification")
AB_CERTIFICATION_FLAG = "NOVA_TELEGRAM_AB_CERTIFICATION"
PRIMARY_RUNTIME_FLAG = "NOVA_PRIMARY_RUNTIME"
PRIMARY_RUNTIME_CUSTOM = "custom"
PRIMARY_RUNTIME_HERMES = "hermes"
PRIMARY_RUNTIME_ORACLE = "oracle_hermes"
HERMES_SHADOW_SCRIPT = os.path.join(REPO_ROOT, "scripts", "nova", "nova_hermes_shadow.py")
HERMES_SHADOW_PYTHON = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python")
HERMES_SHADOW_TIMEOUT = int(os.getenv("NOVA_HERMES_SHADOW_TIMEOUT_SECONDS", "180"))

# Agent Platform path
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from nexus_agent_platform.runtime.execution_telemetry import execution_run, stage_execution, telemetry_context
from nexus_agent_platform.control_object_resolver import (
    format_repair_status,
    get_repair,
    is_operational_control_intent,
    load_control_context,
    resolve_control_object,
    save_control_context,
)

# ─── SSL ────────────────────────────────────────────────

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ─── Config ─────────────────────────────────────────────

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_MAX_MSG = 4000
POLL_TIMEOUT = 30
HEARTBEAT_INTERVAL = 60
TELEGRAM_SEND_TIMEOUT = int(os.getenv("HERMES_NOVA_TELEGRAM_SEND_TIMEOUT_SECONDS", "20"))
TELEGRAM_SEND_ATTEMPTS = int(os.getenv("HERMES_NOVA_TELEGRAM_SEND_ATTEMPTS", "3"))
TELEGRAM_DELIVERY_EXPIRY_SECONDS = int(os.getenv("HERMES_NOVA_TELEGRAM_DELIVERY_EXPIRY_SECONDS", "86400"))

# ─── Runtime env loader ─────────────────────────────────

def load_runtime_env():
    """Load canonical runtime.env without printing secrets."""
    if not os.path.exists(RUNTIME_ENV):
        _log_error(f"Runtime env not found: {RUNTIME_ENV}")
        return {}
    env = {}
    with open(RUNTIME_ENV) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                val = val.strip()
                # Strip matching single or double quotes
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                env[key.strip()] = val
    return env

_ENV = None

def get_env():
    global _ENV
    if _ENV is None:
        _ENV = load_runtime_env()
        for k, v in _ENV.items():
            if k and v and k not in os.environ:
                os.environ[k] = v
    return _ENV


def _primary_runtime():
    """Return the explicitly selected primary runtime, failing closed."""
    value = get_env().get(PRIMARY_RUNTIME_FLAG, PRIMARY_RUNTIME_CUSTOM).strip().lower()
    if value not in {PRIMARY_RUNTIME_CUSTOM, PRIMARY_RUNTIME_HERMES, PRIMARY_RUNTIME_ORACLE}:
        raise RuntimeError(f"invalid {PRIMARY_RUNTIME_FLAG}={value!r}")
    return value

# ─── Logging ────────────────────────────────────────────

def _log(msg, path=None):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    target = path or NOVA_LOG_PATH
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a") as f:
        f.write(line + "\n")

def _log_error(msg):
    _log(f"ERROR: {msg}", NOVA_ERROR_LOG)
    _log(f"ERROR: {msg}")

# ─── Telegram API ───────────────────────────────────────

def _tg_api(method, params=None, token=None, timeout=20):
    """Call Telegram API. Returns JSON response or None."""
    env = get_env()
    if token is None:
        token = env.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")
    if not token:
        _log_error("HERMES_NOVA_TELEGRAM_BOT_TOKEN not set")
        return None

    url = TELEGRAM_API.format(token=token, method=method)
    try:
        if params:
            data = urllib.parse.urlencode(params).encode("utf-8")
            req = urllib.request.Request(url, data=data)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        _log_error(f"HTTP {e.code} calling {method}: {body[:200]}")
        return None
    except Exception as e:
        _log_error(f"Error calling {method}: {e}")
        return None


def _tg_send_attempt(chat_id, chunk, token=None, timeout=TELEGRAM_SEND_TIMEOUT):
    """Return structured send state; preserve the generic API helper contract."""
    env = get_env()
    token = token or env.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"ok": False, "retryable": False, "error": "telegram_token_missing"}
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    try:
        req = urllib.request.Request(url, data=urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode("utf-8"))
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("ok"):
            return {"ok": True, "message_id": body.get("result", {}).get("message_id")}
        error_code = int(body.get("error_code") or 0)
        return {"ok": False, "retryable": error_code in {408, 429, 500, 502, 503, 504}, "error": json.dumps(body)[:500], "retry_after": (body.get("parameters") or {}).get("retry_after")}
    except urllib.error.HTTPError as exc:
        retry_after = None
        try:
            retry_after = int(exc.headers.get("Retry-After")) if exc.headers.get("Retry-After") else None
        except (TypeError, ValueError):
            pass
        return {"ok": False, "retryable": exc.code in {408, 429, 500, 502, 503, 504}, "error": f"HTTP {exc.code}: {str(exc)[:300]}", "retry_after": retry_after}
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
        return {"ok": False, "retryable": True, "error": f"{type(exc).__name__}: {exc}"[:500]}


def _delivery_path(update_id):
    return os.path.join(NOVA_DELIVERY_DIR, f"{update_id}.json")


def _load_delivery(update_id):
    try:
        with open(_delivery_path(update_id)) as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _update_already_delivered(update_id):
    """Return whether this Telegram update already has a final delivery.

    Poll offsets protect the normal path, but a replayed update can also reach
    ``process_message`` directly after a worker restart.  Check the durable
    delivery record before creating a mission or invoking Hermes so replay
    cannot duplicate work.  Pending records remain retryable.
    """
    record = _load_delivery(update_id)
    return bool(record and record.get("state") == "DELIVERED")


def _save_delivery(record):
    os.makedirs(NOVA_DELIVERY_DIR, exist_ok=True)
    path = _delivery_path(record["telegram_update_id"])
    temporary = path + ".tmp"
    with open(temporary, "w") as handle:
        json.dump(record, handle, indent=2)
    os.replace(temporary, path)
    return record


def _delivery_record(update_id, chat_id, response, hermes_run_id=None, mission_id=None):
    digest = hashlib.sha256(response.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    return {"telegram_update_id": update_id, "chat_id": chat_id, "hermes_run_id": hermes_run_id,
            "mission_id": mission_id, "response_id": digest[:24], "response_hash": digest,
            "response": response, "state": "NOT_ATTEMPTED", "attempt_count": 0,
            "last_error": None, "last_attempt_at": None, "message_ids": [],
            "created_at": now, "updated_at": now}


def _is_progress_only_response(response, tools):
    """Recognize an interim-looking model final that must not be delivered."""
    if tools or not isinstance(response, str):
        return False
    text = response.strip().lower()
    markers = (
        "please hold on",
        "one moment",
        "fetching current",
        "loading public_",
        "[loading",
        "[fetching",
    )
    return len(text) < 500 and any(marker in text for marker in markers)


def _deliver_response(update_id, chat_id, response, *, hermes_run_id=None, mission_id=None):
    """Deliver one composed response, recoverably and without rerunning Hermes."""
    record = _load_delivery(update_id) or _delivery_record(update_id, chat_id, response, hermes_run_id, mission_id)
    if record.get("state") == "DELIVERED":
        return record
    record.update({"response": response, "response_hash": hashlib.sha256(response.encode()).hexdigest(),
                   "updated_at": datetime.now(timezone.utc).isoformat()})
    chunks = _chunk_message(response)
    sent = list(record.get("message_ids") or [])
    last_error = None
    cycle_attempts = 0
    terminal_error = False
    for index, chunk in enumerate(chunks[len(sent):], start=len(sent)):
        chunk_ok = False
        for attempt in range(TELEGRAM_SEND_ATTEMPTS):
            cycle_attempts += 1
            record["state"] = "ATTEMPTING"
            record["attempt_count"] = int(record.get("attempt_count", 0)) + 1
            record["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            _save_delivery(record)
            outcome = _tg_send_attempt(chat_id, chunk)
            if outcome.get("ok") and outcome.get("message_id"):
                sent.append(outcome["message_id"])
                record["message_ids"] = sent
                chunk_ok = True
                _save_delivery(record)
                break
            last_error = outcome.get("error") or "telegram_send_failed"
            record["last_error"] = last_error
            if not outcome.get("retryable") or attempt + 1 >= TELEGRAM_SEND_ATTEMPTS:
                terminal_error = not outcome.get("retryable")
                break
            delay = outcome.get("retry_after") or min(8, 0.5 * (2 ** attempt)) + random.uniform(0, 0.25)
            time.sleep(delay)
        if not chunk_ok:
            expired = False
            try:
                created = datetime.fromisoformat(str(record.get("created_at", "")).replace("Z", "+00:00"))
                expired = (datetime.now(timezone.utc) - created).total_seconds() >= TELEGRAM_DELIVERY_EXPIRY_SECONDS
            except ValueError:
                pass
            record["state"] = "FAILED_TERMINAL" if terminal_error or expired else "FAILED_TRANSIENT"
            record["terminal_outcome"] = "TERMINAL_DELIVERY_FAILURE" if record["state"] == "FAILED_TERMINAL" else "DELIVERY_PENDING"
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            return _save_delivery(record)
    record["state"] = "DELIVERED"
    record["terminal_outcome"] = "DELIVERED"
    record["last_error"] = None
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    return _save_delivery(record)


def delivery_completeness_check():
    """Require every consumed response-producing mission to have a terminal delivery state."""
    failures = []
    if not os.path.isdir(NOVA_MISSIONS_DIR):
        return {"valid": True, "failures": failures}
    for name in os.listdir(NOVA_MISSIONS_DIR):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(NOVA_MISSIONS_DIR, name)) as handle:
                mission = json.load(handle)
        except (OSError, ValueError):
            continue
        if mission.get("status") not in {"RESPONSE_COMPOSED", "DELIVERY_PENDING", "DELIVERY_FAILED", "DELIVERED", "TERMINAL_DELIVERY_FAILURE"}:
            continue
        delivery = _load_delivery(mission.get("update_id"))
        if not delivery or delivery.get("state") not in {"DELIVERED", "FAILED_TERMINAL"}:
            failures.append(mission.get("update_id"))
    return {"valid": not failures, "failures": failures}


def _retry_pending_deliveries():
    """Retry only composed responses; never re-enter Hermes or resource tools."""
    recovered = 0
    if not os.path.isdir(NOVA_DELIVERY_DIR):
        return recovered
    for name in sorted(os.listdir(NOVA_DELIVERY_DIR)):
        if not name.endswith(".json"):
            continue
        try:
            update_id = int(name[:-5])
        except ValueError:
            continue
        record = _load_delivery(update_id)
        if not record or record.get("state") != "FAILED_TRANSIENT":
            continue
        delivered = _deliver_response(update_id, record.get("chat_id"), record.get("response", ""), hermes_run_id=record.get("hermes_run_id"), mission_id=record.get("mission_id"))
        if delivered.get("state") == "DELIVERED":
            recovered += 1
            mission_path = os.path.join(NOVA_MISSIONS_DIR, f"{record.get('mission_id')}.json")
            try:
                with open(mission_path) as handle:
                    mission = json.load(handle)
                update_mission(mission, "DELIVERED", {"response_message_ids": delivered.get("message_ids", [])})
            except (OSError, ValueError, TypeError):
                pass
    return recovered

def tg_send_message(chat_id, text, token=None, timeout=TELEGRAM_SEND_TIMEOUT):
    """Send a message, chunking if needed. Returns list of message IDs."""
    if not text:
        return []

    env = get_env()
    if token is None:
        token = env.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")

    chunks = _chunk_message(text)
    message_ids = []

    for chunk in chunks:
        outcome = _tg_send_attempt(chat_id, chunk, token=token, timeout=timeout)
        if outcome.get("ok") and outcome.get("message_id"):
            message_ids.append(outcome["message_id"])
        else:
            _log_error(f"Failed to send message to {chat_id}: {outcome.get('error')}")

    return message_ids


def _chunk_message(text):
    """Split long messages into Telegram-safe chunks."""
    if len(text) <= TELEGRAM_MAX_MSG:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > TELEGRAM_MAX_MSG - 100 and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def _response_integrity(response, response_type="conversation"):
    """Reject untyped internal scalars/raw structures before Telegram delivery."""
    value = str(response or "").strip()
    if not value:
        return None, "empty_response"
    # Internal capability envelopes are never user-facing, even when a model
    # or an older runtime returns one wrapped in prose. The graph should
    # intercept these; this final guard prevents accidental Telegram leakage.
    if "nova_capability_request" in value:
        return None, "raw_capability_request"
    if response_type != "user_numeric_answer" and re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", value):
        return None, "bare_internal_scalar"
    if response_type != "user_json_answer" and value[:1] in {"{", "["}:
        try:
            json.loads(value)
            return None, "raw_internal_json"
        except ValueError:
            pass
    return value, None

# ─── Offset Management ─────────────────────────────────

def load_offset():
    try:
        with open(NOVA_OFFSET_PATH) as f:
            data = json.load(f)
            return data.get("last_update_id", 0)
    except Exception:
        return 0


def save_offset(update_id):
    os.makedirs(os.path.dirname(NOVA_OFFSET_PATH), exist_ok=True)
    with open(NOVA_OFFSET_PATH, "w") as f:
        json.dump({
            "last_update_id": update_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)

# ─── Authorization ──────────────────────────────────────

def is_authorized(chat_id, user_id, username):
    """Check if this user is authorized to interact with Nova."""
    env = get_env()

    allowed_chat_ids = set()

    # Check HERMES_NOVA_CHAT_ID
    nova_chat = env.get("HERMES_NOVA_CHAT_ID", "")
    if nova_chat:
        for cid in nova_chat.split(","):
            cid = cid.strip()
            if cid:
                try:
                    allowed_chat_ids.add(int(cid))
                except ValueError:
                    pass

    # Also check TELEGRAM_CHAT_ID (Ray's private chat)
    ray_chat = env.get("TELEGRAM_CHAT_ID", "")
    if ray_chat:
        for cid in ray_chat.split(","):
            cid = cid.strip()
            if cid:
                try:
                    allowed_chat_ids.add(int(cid))
                except ValueError:
                    pass

    # Fallback: hardcoded Ray chat ID
    if 1288928049 not in allowed_chat_ids:
        allowed_chat_ids.add(1288928049)

    if chat_id in allowed_chat_ids:
        return True

    _log_error(f"Unauthorized access attempt: chat_id={chat_id} user_id={user_id} username={username}")
    return False

# ─── Mission Tracking ───────────────────────────────────

NOVA_MISSIONS_DIR = os.path.join(REPO_ROOT, "data", "nova", "missions")


def create_mission(update_id, chat_id, user_id, text):
    ts = datetime.now(timezone.utc)
    mission_id = f"nova_{ts.strftime('%Y%m%dT%H%M%S')}_{update_id}"
    mission = {
        "mission_id": mission_id,
        "update_id": update_id,
        "chat_id": chat_id,
        "masked_chat_id": f"***{str(chat_id)[-4:]}",
        "user_id": user_id,
        "original_message": text[:500],
        "status": "RECEIVED",
        "timestamps": {"received_at": ts.isoformat()},
        "response_mode": None,
        "model_used": None,
        "response_message_ids": [],
        "validation_error": None,
        "fallback_used": False,
        "correlation_id": f"tg-{update_id}-{hashlib.sha256(f'{chat_id}:{update_id}'.encode()).hexdigest()[:12]}",
    }
    os.makedirs(NOVA_MISSIONS_DIR, exist_ok=True)
    path = os.path.join(NOVA_MISSIONS_DIR, f"{mission_id}.json")
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)
    return mission


def update_mission(mission, status, extra=None):
    mission["status"] = status
    mission["timestamps"][f"{status.lower()}_at"] = datetime.now(timezone.utc).isoformat()
    if extra:
        mission.update(extra)
    path = os.path.join(NOVA_MISSIONS_DIR, f"{mission['mission_id']}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)
    return mission

# ─── Receipt Writing ────────────────────────────────────

def write_receipt(receipt_data):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rid = f"nova_{ts}"
    receipt_data["receipt_id"] = rid
    receipt_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    receipt_data["source"] = "nova_telegram_worker"
    os.makedirs(NOVA_RECEIPTS_DIR, exist_ok=True)
    path = os.path.join(NOVA_RECEIPTS_DIR, f"{rid}.json")
    with open(path, "w") as f:
        json.dump(receipt_data, f, indent=2)
    return receipt_data


def _ab_safe_text(value, limit=8000):
    """Bound A/B evidence and redact credential-shaped values."""
    text = str(value or "")[:limit]
    text = re.sub(r"(?i)(api[_ -]?key|token|secret|password)\s*[:=]\s*\S+", r"\1=<redacted>", text)
    return text


def _run_shadow_ab(update_id, message, chat_id, text, primary_run_id=None, primary_result=None, primary_response=None, primary_latency_ms=None):
    """Run the Hermes shadow silently through Hermes' supported interpreter."""
    if get_env().get(AB_CERTIFICATION_FLAG, "").lower() != "true":
        return None
    # Telegram update IDs are the certification idempotency key.  A retry of
    # the one-shot worker must not create a second shadow invocation.
    run_id = f"ab-shadow-{update_id}"
    receipt_path = os.path.join(NOVA_AB_DIR, f"{run_id}.json")
    try:
        with open(receipt_path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        pass
    session = f"nova-telegram-ab-{chat_id}"
    started = time.monotonic()
    primary_metadata = getattr(primary_result, "metadata", {}) or {}
    shadow = {
        "run_id": run_id,
        "primary_run_id": primary_run_id or f"custom-{update_id}",
        "shadow_run_id": run_id,
        "session_id": session,
        "update_id": update_id,
        "message_id": message.get("message_id") or update_id,
        "user_text": _ab_safe_text(text, 2000),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "custom": {
            "run_id": primary_run_id or f"custom-{update_id}",
            "model": primary_metadata.get("model_used", "unknown"),
            "resources_selected": primary_metadata.get("model_selected_capability"),
            "tools_executed": (primary_metadata.get("capability_result") or {}).get("capability"),
            "final_response": _ab_safe_text(primary_response),
            "latency_ms": primary_latency_ms,
            "error": primary_metadata.get("validation_error"),
        },
        "shadow": {"run_id": run_id, "model": get_env().get("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")},
        "shadow_telegram_send_count": 0,
        "primary_telegram_send_count": 1,
    }
    try:
        if not os.path.isfile(HERMES_SHADOW_SCRIPT):
            raise RuntimeError("shadow_script_missing")
        if not os.path.isfile(HERMES_SHADOW_PYTHON) or not os.access(HERMES_SHADOW_PYTHON, os.X_OK):
            raise RuntimeError("hermes_interpreter_missing")
        child_env = {
            "HOME": os.path.expanduser("~"),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "NOVA_RUNTIME_ENV": RUNTIME_ENV,
            "NOVA_HERMES_NATIVE_SHADOW": "true",
            "NOVA_HERMES_NATIVE_PRIMARY": "false",
            "PYTHONUNBUFFERED": "1",
            "NOVA_SHADOW_UPDATE_ID": str(update_id),
            "NOVA_SHADOW_MESSAGE_ID": str(message.get("message_id") or update_id),
            "NOVA_LANGFUSE_TRACE_ID": os.getenv("NOVA_LANGFUSE_TRACE_ID", ""),
            "NOVA_LANGFUSE_UPDATE_ID": str(update_id),
        }
        # Development-only bounded fault injection is inherited by the
        # already-isolated shadow process. It is intentionally opt-in and has
        # no effect in normal certification runs.
        for key in ("NOVA_SHADOW_FORCE_SEARXNG_FAILURE", "NOVA_SHADOW_FORCE_ALPHA_FAILURE"):
            if os.environ.get(key):
                child_env[key] = os.environ[key]
        completed = subprocess.run(
            [HERMES_SHADOW_PYTHON, HERMES_SHADOW_SCRIPT, text, "--session-id", session],
            cwd=REPO_ROOT,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=HERMES_SHADOW_TIMEOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(_ab_safe_text(completed.stderr or "shadow_process_failed", 500))
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            # Hermes may emit a bounded diagnostic line before its final JSON
            # envelope. Recover only a complete JSON object; do not treat
            # arbitrary stdout as a shadow result.
            result = None
            for line in reversed(completed.stdout.splitlines()):
                try:
                    candidate = json.loads(line)
                    if isinstance(candidate, dict):
                        result = candidate
                        break
                except json.JSONDecodeError:
                    continue
            if result is None:
                raise
        if not isinstance(result, dict):
            raise RuntimeError("shadow_result_not_object")
        messages = result.get("messages", []) if isinstance(result, dict) else []
        shadow["shadow"].update({
            "final_response": _ab_safe_text((result or {}).get("final_response")),
            "tools_executed": [m.get("name") or m.get("tool_name") for m in messages if m.get("role") == "tool"],
            "results": [_ab_safe_text(m.get("content"), 3000) for m in messages if m.get("role") == "tool"],
            "model": (result or {}).get("model", shadow["shadow"]["model"]),
            "error": None,
            "completed": (result or {}).get("completed"),
            "runtime_init": True,
            "model_init": True,
            "turn_contract": (result or {}).get("turn_contract"),
            "evidence_state": (result or {}).get("evidence_state"),
            "claim_validation": (result or {}).get("claim_validation"),
        })
    except Exception as exc:
        shadow["shadow"].update({"final_response": None, "tools_executed": [], "results": [], "error": type(exc).__name__ + ": " + str(exc)[:500], "runtime_init": False, "model_init": False})
    shadow["shadow"]["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    os.makedirs(NOVA_AB_DIR, exist_ok=True)
    with open(receipt_path, "w") as handle:
        json.dump(shadow, handle, indent=2)
    return shadow


def _run_hermes_primary(update_id, message, chat_id, text, primary_run_id=None):
    """Run the certified Hermes core for primary delivery."""
    run_id = f"hermes-primary-{update_id}"
    started = time.monotonic()
    session = f"nova-telegram-primary-{chat_id}"
    record = {"run_id": run_id, "primary_run_id": primary_run_id or run_id,
              "session_id": session, "update_id": update_id,
              "message_id": message.get("message_id") or update_id,
              "runtime": "hermes", "telegram_send_count": 0, "error": None}
    try:
        if not os.path.isfile(HERMES_SHADOW_SCRIPT):
            raise RuntimeError("hermes_runner_missing")
        if not os.path.isfile(HERMES_SHADOW_PYTHON) or not os.access(HERMES_SHADOW_PYTHON, os.X_OK):
            raise RuntimeError("hermes_interpreter_missing")
        child_env = {
            "HOME": os.path.expanduser("~"), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HERMES_HOME": os.getenv("NOVA_HERMES_HOME", os.path.join(REPO_ROOT, "config", "hermes", "nova-profile")),
            "NOVA_RUNTIME_ENV": RUNTIME_ENV, "NOVA_HERMES_NATIVE_SHADOW": "false",
            "NOVA_HERMES_NATIVE_PRIMARY": "true", "PYTHONUNBUFFERED": "1",
            "NOVA_PRIMARY_SESSION_ID": session, "NOVA_SHADOW_UPDATE_ID": str(update_id),
            "NOVA_SHADOW_MESSAGE_ID": str(message.get("message_id") or update_id),
        }
        for key in ("NOVA_SHADOW_FORCE_SEARXNG_FAILURE", "NOVA_SHADOW_FORCE_ALPHA_FAILURE"):
            if os.environ.get(key):
                child_env[key] = os.environ[key]
        subprocess_started = time.monotonic()
        completed = subprocess.run(
            [HERMES_SHADOW_PYTHON, HERMES_SHADOW_SCRIPT, text, "--session-id", session],
            cwd=REPO_ROOT, env=child_env, capture_output=True, text=True,
            timeout=HERMES_SHADOW_TIMEOUT, check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(_ab_safe_text(completed.stderr or "hermes_primary_failed", 500))
        result = None
        for line in reversed(completed.stdout.splitlines()):
            try:
                candidate = json.loads(line)
                if isinstance(candidate, dict):
                    result = candidate
                    break
            except json.JSONDecodeError:
                continue
        if not result:
            raise RuntimeError("hermes_primary_result_not_object")
        messages = result.get("messages", [])
        retry_count = 0
        if _is_progress_only_response(
            result.get("final_response"),
            [m.get("name") or m.get("tool_name") for m in messages if m.get("role") == "tool"],
        ):
            # Hermes occasionally emits progress prose as its terminal output
            # without executing the requested resource. Do not expose that as
            # the answer. Give the same native runtime one bounded retry; only
            # the completed answer is eligible for Telegram delivery.
            retry_count = 1
            retry = subprocess.run(
                [HERMES_SHADOW_PYTHON, HERMES_SHADOW_SCRIPT, text, "--session-id", session],
                cwd=REPO_ROOT, env=child_env, capture_output=True, text=True,
                timeout=HERMES_SHADOW_TIMEOUT, check=False,
            )
            retry_result = None
            for line in reversed(retry.stdout.splitlines()):
                try:
                    candidate = json.loads(line)
                    if isinstance(candidate, dict):
                        retry_result = candidate
                        break
                except json.JSONDecodeError:
                    continue
            if retry.returncode == 0 and retry_result:
                retry_messages = retry_result.get("messages", [])
                retry_tools = [m.get("name") or m.get("tool_name") for m in retry_messages if m.get("role") == "tool"]
                if not _is_progress_only_response(retry_result.get("final_response"), retry_tools):
                    result = retry_result
                    messages = retry_messages
            if _is_progress_only_response(
                result.get("final_response"),
                [m.get("name") or m.get("tool_name") for m in messages if m.get("role") == "tool"],
            ):
                raise RuntimeError("hermes_primary_incomplete_progress_response")
        child_telemetry = result.get("latency_telemetry") if isinstance(result.get("latency_telemetry"), dict) else {}
        record.update({
            "response": _ab_safe_text(result.get("final_response")),
            "model": result.get("model", get_env().get("HERMES_NOVA_MODEL", "openai/gpt-4o-mini")),
            "tools_executed": [m.get("name") or m.get("tool_name") for m in messages if m.get("role") == "tool"],
            "runtime_init": True, "model_init": True,
            "completed": bool(result.get("completed")),
            "retry_count": retry_count,
            "turn_contract": result.get("turn_contract"),
            "evidence_state": result.get("evidence_state"),
            "claim_validation": result.get("claim_validation"),
            "latency_telemetry": {
                **child_telemetry,
                "subprocess_elapsed_ms": round((time.monotonic() - subprocess_started) * 1000, 1),
                "subprocess_startup_ms": child_telemetry.get("hermes_init_ms"),
            },
        })
    except Exception as exc:
        record.update({"response": None, "tools_executed": [], "runtime_init": False,
                       "model_init": False, "completed": False,
                       "error": type(exc).__name__ + ": " + str(exc)[:500]})
    record["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    record.setdefault("latency_telemetry", {})["worker_total_ms"] = record["latency_ms"]
    return record


def _run_oracle_primary(update_id, message, chat_id, text, primary_run_id=None):
    """Run the fixed, governed Oracle Hermes 0.20.6 adapter."""
    from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes
    session = f"nova-telegram-primary-{chat_id}"
    started = time.monotonic()
    result = run_oracle_hermes(text, session, request_id=f"telegram-{update_id}",
                               timeout_seconds=HERMES_SHADOW_TIMEOUT)
    return {
        "run_id": f"oracle-hermes-primary-{update_id}",
        "primary_run_id": primary_run_id or f"oracle-hermes-primary-{update_id}",
        "session_id": session, "update_id": update_id,
        "message_id": message.get("message_id") or update_id,
        "runtime": "oracle_hermes", "runtime_host": result.runtime_host,
        "hermes_version": result.hermes_version, "profile": result.profile,
        "provider": result.provider, "model": result.model,
        "telegram_send_count": 0, "error": result.error,
        "response": result.response, "tools_executed": [],
        "runtime_init": result.status == "SUCCEEDED", "model_init": result.status == "SUCCEEDED",
        "completed": result.status == "SUCCEEDED", "latency_ms": result.latency_ms,
        "latency_telemetry": {"bridge_elapsed_ms": result.latency_ms,
                               "worker_total_ms": round((time.monotonic() - started) * 1000, 1)},
    }


def _complete_shadow_ab(shadow_record, primary_result=None, primary_response=None, primary_latency_ms=None):
    """Attach the eventual primary outcome to a pre-branch shadow receipt."""
    if not shadow_record:
        return
    path = os.path.join(NOVA_AB_DIR, f"{shadow_record['run_id']}.json")
    try:
        with open(path) as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        return
    metadata = getattr(primary_result, "metadata", {}) or {}
    record["primary_run_id"] = record.get("primary_run_id") or record.get("custom", {}).get("run_id")
    record["custom"] = {
        "run_id": record.get("primary_run_id") or f"custom-{record.get('update_id')}",
        "model": metadata.get("model_used", "unknown"),
        "resources_selected": metadata.get("model_selected_capability"),
        "tools_executed": (metadata.get("capability_result") or {}).get("capability"),
        "final_response": _ab_safe_text(primary_response),
        "latency_ms": primary_latency_ms,
        "error": metadata.get("validation_error"),
    }
    with open(path, "w") as handle:
        json.dump(record, handle, indent=2)


def _capability_receipt(result, update_id, conversation_id, final_response_id=None):
    """Return secret-free capability execution facts for the Nova receipt."""
    metadata = getattr(result, "metadata", {}) or {}
    selected = metadata.get("model_selected_capability") or {}
    capability_result = metadata.get("capability_result") or {}
    provenance = capability_result.get("provenance") or {}
    capability = selected.get("capability") or capability_result.get("query_type") or capability_result.get("capability")
    if not capability:
        return None
    status = capability_result.get("status") or provenance.get("status") or "unknown"
    is_truth = str(capability).lower() in {"get_live_capability_status", "capability_status"}
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": conversation_id,
        "telegram_update_id": update_id,
        "capability": capability,
        "requested_by_model": bool(selected),
        "boundary_validation": "validated" if selected.get("status") == "validated" else metadata.get("capability_gate", {}).get("decision", "not_model_requested"),
        "provider": provenance.get("provider") or provenance.get("service") or capability_result.get("planner_provider"),
        "execution_attempted": bool(metadata.get("capability_invocation_attempted") or capability_result),
        "execution_status": status,
        "failure_reason": capability_result.get("error") or capability_result.get("errors") or provenance.get("error"),
        "fallback_selected": metadata.get("fallback_used", False),
        "result_returned_to_model": bool(capability_result),
        "final_response_id": final_response_id,
        "capability_truth_called": is_truth,
        "capability_truth_result": status if is_truth else None,
        "capability_truth_source": (provenance.get("source") or provenance.get("source_type")) if is_truth else None,
        "capability_truth_freshness": provenance.get("freshness") if is_truth else None,
        "model_received": bool(capability_result),
    }

# ─── Single-Delivery Lock ───────────────────────────────

def _acquire_chat_lock(chat_id, *, wait_seconds=None):
    """Acquire a per-chat lock, waiting instead of dropping a Telegram update."""
    lock_dir = os.path.join(NOVA_STATE_DIR, "nova_locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, f"chat_{chat_id}.lock")
    wait_seconds = float(wait_seconds if wait_seconds is not None else os.getenv("NOVA_CHAT_LOCK_WAIT_SECONDS", "600"))
    deadline = time.monotonic() + max(1.0, wait_seconds)

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, f"{os.getpid()}\n".encode())
            os.close(fd)
            return lock_path
        except FileExistsError:
            owner_pid = None
            try:
                with open(lock_path, encoding="utf-8") as handle:
                    owner_pid = int(handle.read().strip().splitlines()[0])
            except (OSError, ValueError, IndexError):
                pass
            owner_alive = False
            if owner_pid == os.getpid():
                owner_alive = True
            elif owner_pid:
                try:
                    os.kill(owner_pid, 0)
                    owner_alive = True
                except OSError:
                    owner_alive = False
            if not owner_alive:
                try:
                    os.remove(lock_path)
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for Telegram chat lock {chat_id}")
            time.sleep(0.1)


def _release_chat_lock(chat_id):
    """Release the per-chat file lock."""
    lock_path = os.path.join(NOVA_STATE_DIR, "nova_locks", f"chat_{chat_id}.lock")
    try:
        os.remove(lock_path)
    except OSError:
        pass

# ─── Message Processing ─────────────────────────────────

def process_message(update):
    """Process a single incoming Telegram update through Nova."""
    message = update.get("message", {})
    chat = message.get("chat", {})
    user = message.get("from", {})
    chat_id = chat.get("id")
    user_id = user.get("id")
    username = user.get("username", "")
    text = message.get("text", "")
    update_id = update.get("update_id", 0)

    if not text or not chat_id:
        return False

    if _update_already_delivered(update_id):
        _log(f"Duplicate Telegram update suppressed: update={update_id}")
        return True

    base_metadata = {
        "update_id": update_id,
        "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16],
    }

    from langfuse_runtime import NovaTrace
    trace = NovaTrace(update_id=update_id, session_id=f"nova-telegram-primary-{chat_id}")
    trace.event("telegram.intake", {"runtime": "hermes", "agent": "nova"})
    os.environ["NOVA_LANGFUSE_TRACE_ID"] = trace.trace_id
    with execution_run(
        process_id="telegram_operator",
        process_name="Telegram Operator",
        worker_id="nova_telegram_worker",
        agent_id="hermes_nova",
        execution_type="telegram_update_run",
        source="scripts/nova/nova_telegram_worker.py:process_message",
        metadata=base_metadata,
    ) as run_id:
        with telemetry_context(parent_run_id=run_id, metadata=base_metadata):
            with stage_execution(
                stage="telegram_update_received",
                source="scripts/nova/nova_telegram_worker.py:process_message",
            ):
                pass
            trace.event("telegram.authorization", {"authorized": True})
            outcome = _process_message_inner(update, message, chat, user, chat_id, user_id, username, text, update_id, run_id, trace=trace)
            trace.finish({"runtime": "hermes", "delivery_visible": True, "outcome": outcome})
            return outcome


def _process_message_inner(update, message, chat, user, chat_id, user_id, username, text, update_id, primary_run_id=None, trace=None):
    _log(f"Incoming: update={update_id} chat={chat_id} user={username} text={text[:80]}")

    # Acquire per-chat lock to prevent duplicate delivery
    with stage_execution(
        stage="chat_lock",
        source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
    ):
        lock = _acquire_chat_lock(chat_id)
    if not lock:
        # _acquire_chat_lock either returns ownership or raises. Keep this
        # guard for test doubles and future lock implementations; never treat
        # contention as successful processing because the poller would then
        # advance past an unhandled Telegram update.
        raise RuntimeError(f"chat lock unavailable for update {update_id}")

    try:
        with stage_execution(
            stage="mission_create",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
        ):
            mission = create_mission(update_id, chat_id, user_id, text)

        with stage_execution(
            stage="authorization",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
        ):
            authorized = is_authorized(chat_id, user_id, username)

        if not authorized:
            update_mission(mission, "UNAUTHORIZED")
            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={"mission_id": mission["mission_id"], "unauthorized": True},
            ):
                tg_send_message(chat_id, "This bot is private. You are not authorized.")
            return True

        update_mission(mission, "AUTHORIZED")
        _update_status_field("last_incoming_message", datetime.now(timezone.utc).isoformat())

        primary_runtime = _primary_runtime()

        # In certification mode the shadow observes every authorized request
        # before any primary-only terminal branch (including governed object
        # resolution). It has no Telegram delivery path.
        ab_record = None
        if primary_runtime == PRIMARY_RUNTIME_CUSTOM:
            ab_record = _run_shadow_ab(update_id, message, chat_id, text, primary_run_id=primary_run_id)

        if primary_runtime in {PRIMARY_RUNTIME_HERMES, PRIMARY_RUNTIME_ORACLE}:
            if trace:
                trace.event("hermes.context_build", {
                    "session_id": f"nova-telegram-primary-{chat_id}",
                    "profile": "nova_nexus",
                    "runtime_host": "ORACLE" if primary_runtime == PRIMARY_RUNTIME_ORACLE else "MAC",
                })
            hermes_record = (
                _run_oracle_primary(update_id, message, chat_id, text, primary_run_id=primary_run_id)
                if primary_runtime == PRIMARY_RUNTIME_ORACLE
                else _run_hermes_primary(update_id, message, chat_id, text, primary_run_id=primary_run_id)
            )
            if trace:
                trace.event("hermes.generation", {"generation_type": "FINAL_SYNTHESIS_GENERATION", "model": hermes_record.get("model"), "tool_count": len(hermes_record.get("tools_executed", [])), "latency_ms": hermes_record.get("latency_ms")})
            response, blocked_reason = _response_integrity(hermes_record.get("response") or "", "conversation")
            if response is None:
                update_mission(mission, "DELIVERY_FAILED", {
                    "response_mode": "hermes_primary",
                    "model_used": hermes_record.get("model"),
                    "hermes_error": hermes_record.get("error") or blocked_reason,
                })
                return True
            update_mission(mission, "RESPONSE_COMPOSED", {
                "response_mode": "hermes_primary",
                "model_used": hermes_record.get("model"),
                "hermes_primary_run_id": hermes_record.get("run_id"),
            })
            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={"mission_id": mission["mission_id"], "runtime": "hermes_primary"},
            ):
                delivery = _deliver_response(update_id, chat_id, response, hermes_run_id=hermes_record.get("run_id"), mission_id=mission["mission_id"])
            if trace:
                trace.event("telegram.delivery", {"attempt_count": delivery.get("attempt_count"), "state": delivery.get("state"), "message_ids": delivery.get("message_ids", []), "last_error": delivery.get("last_error")})
            msg_ids = delivery.get("message_ids", [])
            hermes_record["telegram_send_count"] = len(msg_ids)
            write_receipt({
                "type": "nova_hermes_primary_response",
                "incoming_update_id": update_id,
                "outgoing_message_ids": msg_ids,
                "correlation_id": mission.get("correlation_id"),
                "primary_run_id": primary_run_id,
                "hermes_run_id": hermes_record.get("run_id"),
                "langfuse_trace_id": os.getenv("NOVA_LANGFUSE_TRACE_ID"),
                "session_id": hermes_record.get("session_id"),
                "model": hermes_record.get("model"),
                "runtime": hermes_record.get("runtime"),
                "runtime_host": hermes_record.get("runtime_host", "MAC"),
                "hermes_version": hermes_record.get("hermes_version", "0.14.0"),
                "profile": hermes_record.get("profile", "nova_nexus"),
                "provider": hermes_record.get("provider", "openrouter"),
                "latency_ms": hermes_record.get("latency_ms"),
                "tools_executed": hermes_record.get("tools_executed", []),
                "response": _ab_safe_text(response),
                "error": hermes_record.get("error"),
                "delivery": delivery,
                "claim_attribution": hermes_record.get("claim_attribution"),
                "runtime_init": hermes_record.get("runtime_init"),
                "model_init": hermes_record.get("model_init"),
            })
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else ("TERMINAL_DELIVERY_FAILURE" if delivery.get("state") == "FAILED_TERMINAL" else "DELIVERY_PENDING"), {"response_message_ids": msg_ids, "delivery_state": delivery.get("state"), "delivery_error": delivery.get("last_error")})
            return True

        # Explicit governed objects are resolved deterministically before the
        # conversational graph. This prevents Nova/Product Evolution fuzzy
        # routing from hiding an existing repair behind a generic mission
        # lookup. This read-only branch does not start engineering or create
        # any new object.
        control_context = load_control_context(chat_id)
        control = resolve_control_object(text, control_context)
        if is_operational_control_intent(text, control):
            if control.get("object_type") == "REPAIR":
                repair = get_repair(control.get("object_id") or control.get("repair_id"))
                response = format_repair_status(repair) if repair else "I couldn't retrieve the current Nexus state. The persisted repair was not found. No Nexus state was changed."
                outcome = "GOVERNED_REPAIR_RESOLVED" if repair else "REPAIR_NOT_FOUND"
                if repair:
                    save_control_context(chat_id, {**control, "repair_id": repair.get("repair_id"), "work_order_id": repair.get("work_order_id"), "run_id": repair.get("run_id")})
            elif control.get("object_type") in {"UNKNOWN_REPAIR", "UNKNOWN_WORK_ORDER"}:
                response = f"I could not find persisted {control.get('object_type', 'object').lower()} {control.get('object_id', '')}. No repair or mission was created."
                outcome = control.get("object_type")
            else:
                response = "I couldn't retrieve the current Nexus state. No state was changed."
                outcome = "OPERATIONAL_STATE_UNAVAILABLE"
            response, blocked_reason = _response_integrity(response, "operational_status")
            if response is None:
                response = "I couldn't produce a valid Nexus status response. No state was changed."
                outcome = "RESPONSE_INTEGRITY_BLOCKED"
            update_mission(mission, "RESPONSE_COMPOSED", {"response_mode": "governed_object_resolution", "control_object": control.get("object_type"), "outcome": outcome})
            msg_ids = tg_send_message(chat_id, response)
            _complete_shadow_ab(ab_record, primary_response=response, primary_latency_ms=0)
            update_mission(mission, "COMPLETED" if msg_ids else "DELIVERY_FAILED", {"response_message_ids": msg_ids})
            write_receipt({"type": "nova_governed_object_response", "object_type": control.get("object_type"), "object_id": control.get("object_id") or control.get("repair_id"), "outcome": outcome, "model_calls": 0, "correlation_id": mission.get("correlation_id"), "incoming_update_id": update_id, "outgoing_message_ids": msg_ids, "integrity_blocked": blocked_reason})
            return True

        with stage_execution(
            stage="graph_setup",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
        ):
            from nexus_agent_platform.agents.nova import (
                get_nova_graph, get_nova_otel, reset_memory, AGENT_ID, session_id,
            )
            from nexus_agent_platform.adapters.state_adapter import AgentState
            from nexus_agent_platform.flags import HERMES_NOVA_ENABLED

            if not HERMES_NOVA_ENABLED:
                graph = None
                otel = None
            else:
                graph = get_nova_graph()
                otel = get_nova_otel()

        if not HERMES_NOVA_ENABLED:
            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={"mission_id": mission["mission_id"], "disabled": True},
            ):
                tg_send_message(chat_id, "Nova is currently disabled. Try again later.")
            _complete_shadow_ab(ab_record, primary_response="Nova is currently disabled. Try again later.", primary_latency_ms=0)
            update_mission(mission, "DISABLED")
            return True

        state = AgentState(
            agent_id=AGENT_ID,
            mission_id=mission["mission_id"],
            user_message=text,
            metadata={
                "chat_id": chat_id,
                "conversation_id": session_id(chat_id),
                "message_id": message.get("message_id") or update_id,
                "user_id": user_id,
                "username": username,
                "source": "telegram",
                "nova_agent": True,
            },
        )

        t0 = time.monotonic()
        with stage_execution(
            stage="graph_invoke",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
            metadata={"mission_id": mission["mission_id"]},
        ):
            result = graph.invoke(state)
        latency_ms = round((time.monotonic() - t0) * 1000, 1)

        response, blocked_reason = _response_integrity(result.assistant_response or "", result.metadata.get("response_type", "conversation"))
        if response is None:
            _log(f"Response integrity blocked: update={update_id} reason={blocked_reason}")
            write_receipt({"type": "nova_response_integrity_blocked", "incoming_update_id": update_id, "correlation_id": mission.get("correlation_id"), "reason": blocked_reason, "model_calls": 1})
            response = "I couldn't produce a meaningful response to that request. Please try again."

        if result.metadata.get("reset_requested"):
            reset_memory(chat_id)
            _log(f"Memory reset for chat {chat_id}")

        if ab_record:
            _complete_shadow_ab(ab_record, result, response, latency_ms)
            update_mission(mission, "SHADOW_RECORDED", {
                "ab_run_id": ab_record.get("run_id"),
                "shadow_telegram_send_count": 0,
            })

        if otel.is_enabled:
            otel.record_generation(
                name=f"nova_conversation_{mission['mission_id']}",
                model=result.metadata.get("model_used", "unknown"),
                input_text=text[:200],
                output_text=response[:200],
                metadata={
                    "response_mode": result.metadata.get("response_mode"),
                    "model": result.metadata.get("model_used"),
                    "provider": result.metadata.get("model_provider"),
                    "latency_ms": latency_ms,
                    "validation_error": result.metadata.get("validation_error"),
                    "fallback_used": result.metadata.get("fallback_used", False),
                    "conversation_turns": result.metadata.get("conversation_turns", 0),
                },
            )
            otel.flush()

        if response:
            update_mission(mission, "RESPONSE_COMPOSED", {
                "response_mode": result.metadata.get("response_mode"),
                "model_used": result.metadata.get("model_used"),
                "fallback_used": result.metadata.get("fallback_used", False),
            })

            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={
                    "mission_id": mission["mission_id"],
                    "response_chars": len(response),
                    "chunk_count": len(_chunk_message(response)),
                },
            ):
                msg_ids = tg_send_message(chat_id, response)
            if msg_ids:
                update_mission(mission, "COMPLETED", {
                    "response_message_ids": msg_ids,
                })
                write_receipt({
                    "type": "nova_response",
                    "response_mode": result.metadata.get("response_mode"),
                    "model": result.metadata.get("model_used"),
                    "latency_ms": latency_ms,
                    "turns": result.metadata.get("conversation_turns", 0),
                    "incoming_update_id": update_id,
                    "outgoing_message_ids": msg_ids,
                    "correlation_id": mission.get("correlation_id"),
                    "model_calls": 1,
                    "capability_telemetry": _capability_receipt(
                        result, update_id, result.metadata.get("conversation_id", session_id(chat_id)),
                        msg_ids[0] if msg_ids else None,
                    ),
                })
                _log(f"Nova delivered: mission={mission['mission_id']} latency={latency_ms}ms")
            else:
                update_mission(mission, "DELIVERY_FAILED")
                _log_error(f"Delivery failed: mission={mission['mission_id']}")
        else:
            update_mission(mission, "EMPTY_RESPONSE")
            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={"mission_id": mission["mission_id"], "fallback_empty_response": True},
            ):
                tg_send_message(chat_id, "I'm not sure what to say. Could you try again?")

    except Exception as exc:
        _log_error(f"Nova processing error: {exc}")
        with stage_execution(
            stage="telegram_send",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
            metadata={"error_type": exc.__class__.__name__},
        ):
            tg_send_message(chat_id, "I hit a snag processing that. Give me another try.")
    finally:
        _release_chat_lock(chat_id)

    return True

# ─── Runtime Status ─────────────────────────────────────

def write_status(pid, state, extra=None):
    status = {
        "service": "nova_telegram_worker",
        "state": state,
        "pid": pid,
        "heartbeat": datetime.now(timezone.utc).isoformat(),
        "bot_identity": {
            "name": "Hermes Nova",
            "agent": "hermes_nova",
        },
        "polling_mode": "long_poll",
        "last_update_id": load_offset(),
    }
    if extra:
        status.update(extra)
    os.makedirs(os.path.dirname(NOVA_STATUS_PATH), exist_ok=True)
    with open(NOVA_STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)


def _update_status_field(key, value):
    try:
        with open(NOVA_STATUS_PATH) as f:
            status = json.load(f)
    except Exception:
        status = {"service": "nova_telegram_worker", "pid": os.getpid()}
    status[key] = value
    status["heartbeat"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(NOVA_STATUS_PATH), exist_ok=True)
    with open(NOVA_STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)

# ─── Main Loops ─────────────────────────────────────────

def run_once():
    """Single polling cycle."""
    _log("Nova worker: --once cycle starting")
    with execution_run(
        process_id="telegram_operator",
        process_name="Telegram Operator",
        worker_id="nova_telegram_worker",
        agent_id="hermes_nova",
        execution_type="worker_poll",
        source="scripts/nova/nova_telegram_worker.py:run_once",
        metadata={"mode": "once"},
    ):
        write_status(os.getpid(), "RUNNING")

        recovered_deliveries = _retry_pending_deliveries()
        if recovered_deliveries:
            _log(f"Nova worker: recovered {recovered_deliveries} pending deliveries")

        offset = load_offset()
        result = _tg_api("getUpdates", {"offset": offset + 1, "limit": 10, "timeout": 0})

        if not result or not result.get("ok"):
            _log_error(f"getUpdates failed: {result}")
            write_status(os.getpid(), "API_ERROR")
            return "API_ERROR"

        updates = result.get("result", [])
        if not updates:
            _log("Nova worker: no new updates")
            write_status(os.getpid(), "IDLE")
            return "NO_UPDATES"

        processed = 0

        for update in updates:
            uid = update.get("update_id", 0)
            try:
                if process_message(update):
                    # Save offset immediately after each successful message
                    save_offset(uid)
                    processed += 1
            except Exception as e:
                _log_error(f"Error processing update {uid}: {e}")

        _log(f"Nova worker: processed {processed} updates")
        write_status(os.getpid(), "IDLE")
        return f"PROCESSED {processed}"


def run_poll():
    """Persistent long-polling mode."""
    _log("Nova worker: entering persistent long-poll mode")
    write_status(os.getpid(), "STARTING")

    running = True
    def _handle_signal(sig, frame):
        nonlocal running
        _log(f"Nova worker: received signal {sig}, shutting down")
        running = False
        write_status(os.getpid(), "STOPPING")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    last_heartbeat = time.time()

    while running:
        try:
            now = time.time()
            if now - last_heartbeat > HEARTBEAT_INTERVAL:
                write_status(os.getpid(), "ALIVE")
                last_heartbeat = now

            offset = load_offset()
            result = _tg_api("getUpdates", {
                "offset": offset + 1,
                "limit": 10,
                "timeout": POLL_TIMEOUT,
            }, timeout=POLL_TIMEOUT + 10)

            if not result or not result.get("ok"):
                _log_error(f"Poll error: {result}")
                write_status(os.getpid(), "POLL_ERROR")
                time.sleep(5)
                continue

            updates = result.get("result", [])
            if not updates:
                continue

            max_update_id = offset
            processed = 0

            for update in updates:
                uid = update.get("update_id", 0)
                try:
                    if process_message(update):
                        if uid > max_update_id:
                            max_update_id = uid
                        processed += 1
                except Exception as e:
                    _log_error(f"Error processing update {uid}: {e}")

            if max_update_id > offset:
                save_offset(max_update_id)

            if processed > 0:
                _log(f"Poll cycle: processed {processed} updates")
                write_status(os.getpid(), "ACTIVE")

        except Exception as e:
            err_msg = str(e)
            if "timed out" in err_msg.lower():
                continue
            _log_error(f"Poll loop error: {e}")
            write_status(os.getpid(), "ERROR")
            time.sleep(5)

    write_status(os.getpid(), "STOPPED")
    _log("Nova worker: stopped")


def run_test():
    """Test mode: validate configuration and connectivity."""
    print("Hermes Nova Telegram Worker — Test Mode")
    print("=" * 40)

    env = get_env()
    token = env.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")
    print(f"Token present: {'YES' if token else 'NO'}")

    if not token:
        print("FATAL: HERMES_NOVA_TELEGRAM_BOT_TOKEN not set")
        return False

    # getMe
    result = _tg_api("getMe")
    if result and result.get("ok"):
        bot = result["result"]
        print(f"Bot name: {bot.get('first_name')}")
        print(f"Bot username: @{bot.get('username')}")
        print(f"Bot ID: {bot.get('id')}")
    else:
        print(f"FATAL: getMe failed: {result}")
        return False

    # getWebhookInfo
    wh = _tg_api("getWebhookInfo")
    if wh and wh.get("ok"):
        info = wh["result"]
        print(f"Webhook URL: {info.get('url') or '(none — polling mode)'}")
        print(f"Pending updates: {info.get('pending_update_count', 0)}")

    # Check offset
    offset = load_offset()
    print(f"Current offset: {offset}")

    # Check model
    model = env.get("HERMES_NOVA_MODEL", "openai/gpt-4o-mini (default)")
    print(f"Model: {model}")

    # Check OpenRouter key
    api_key = env.get("OPENROUTER_API_KEY", "")
    print(f"OpenRouter key present: {'YES' if api_key else 'NO'}")

    # Check authorization
    print(f"Ray chat ID: 1288928049")
    print(f"Authorized: {is_authorized(1288928049, 1288928049, 'rayscentro')}")

    # Check graph
    try:
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        print(f"Nova graph: compiled={graph._compiled} enabled={graph.is_enabled}")
    except Exception as e:
        print(f"Nova graph: FAILED ({e})")

    print("\nTest PASSED — Nova worker is ready to run.")
    return True


def main():
    args = sys.argv[1:]

    if "--test" in args:
        success = run_test()
        sys.exit(0 if success else 1)
    elif "--once" in args:
        result = run_once()
        print(f"Nova worker: {result}")
    elif "--poll" in args:
        run_poll()
    else:
        print("Usage: nova_telegram_worker.py [--once | --poll | --test]")


if __name__ == "__main__":
    main()
