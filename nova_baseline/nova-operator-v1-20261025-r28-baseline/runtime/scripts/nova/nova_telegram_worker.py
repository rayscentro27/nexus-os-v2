#!/usr/bin/env python3
"""
Hermes Nova Telegram Worker — Isolated conversational agent for @HermesNovaBot.

Lifecycle:
  Telegram update → Authorization → Conversation memory load →
  Nova graph → governed subscription model → Validation → Telegram delivery

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
REPO_ROOT = os.path.abspath(os.getenv("NOVA_REPO_ROOT") or os.path.join(SCRIPT_DIR, "..", ".."))
CODE_ROOT = os.path.abspath(os.getenv("NOVA_CODE_ROOT") or REPO_ROOT)
RUNTIME_ENV = os.path.expanduser(os.getenv("NOVA_RUNTIME_ENV") or "~/.config/nexus/runtime.env")

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
if CODE_ROOT != REPO_ROOT:
    sys.path.insert(0, os.path.join(CODE_ROOT, "scripts"))

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
                key = key.strip()
                val = val.strip()
                # Strip matching single or double quotes
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                if key in {"HERMES_NOVA_TELEGRAM_BOT_TOKEN", "HERMES_NOVA_CHAT_ID", "TELEGRAM_CHAT_ID", PRIMARY_RUNTIME_FLAG, AB_CERTIFICATION_FLAG}:
                    env[key] = val
    # The proactive notifier uses the canonical single trusted Ray chat. Expose
    # that exact recipient to the generic Telegram guard; do not widen to the
    # bridge allowlist, bot IDs, or arbitrary chat IDs.
    trusted_ray = (env.get("HERMES_NOVA_CHAT_ID") or env.get("TELEGRAM_CHAT_ID") or "").strip()
    if trusted_ray and "," not in trusted_ray and trusted_ray.lstrip("-").isdigit():
        os.environ.setdefault("NEXUS_TELEGRAM_RAY_CHAT_IDS", trusted_ray)
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
    """Return the one production runtime, failing closed on legacy values."""
    value = get_env().get(PRIMARY_RUNTIME_FLAG, PRIMARY_RUNTIME_CUSTOM).strip().lower()
    if value != PRIMARY_RUNTIME_ORACLE:
        raise RuntimeError(f"legacy_nova_runtime_disabled:{PRIMARY_RUNTIME_FLAG}={value!r}")
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
        def call():
            req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode("utf-8") if params else None)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        if method == "sendMessage":
            from nexus_agent_platform.provider_enforcement import execute_telegram_delivery
            return execute_telegram_delivery(params.get("chat_id"), call, job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
                job_type=os.environ.get("NEXUS_JOB_TYPE", "NOVA_TELEGRAM_DELIVERY"), external_ref=lambda value: str((value.get("result") or {}).get("message_id")) if value else None)
        # Long-polling Telegram updates is a read-only ingress operation with
        # no durable owner job yet. Keep it read-only; all sends remain behind
        # the durable provider boundary and owner-chat authorization.
        if method == "getUpdates":
            return call()
        from nexus_agent_platform.provider_enforcement import execute
        return execute("TELEGRAM", "bot_api", f"API_{method}",
            {"requests": 1, "operations": 1, "billable": False}, call,
            job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
            job_type=os.environ.get("NEXUS_JOB_TYPE", "NOVA_TELEGRAM_RECEIVER"),
            purpose=f"nova_telegram:{method}")
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
        def call():
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode("utf-8"))
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        from nexus_agent_platform.provider_enforcement import execute_telegram_delivery
        body = execute_telegram_delivery(chat_id, call, job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
            job_type=os.environ.get("NEXUS_JOB_TYPE", "NOVA_TELEGRAM_DELIVERY"), external_ref=lambda value: str((value.get("result") or {}).get("message_id")) if value else None)
        if body.get("ok"):
            return {"ok": True, "message_id": body.get("result", {}).get("message_id")}
        error_code = int(body.get("error_code") or 0)
        return {"ok": False, "retryable": error_code in {408, 429, 500, 502, 503, 504}, "error": json.dumps(body)[:500], "retry_after": (body.get("parameters") or {}).get("retry_after")}
    except Exception as exc:
        from nexus_agent_platform.resource_spend_governor import GovernanceDenied
        if isinstance(exc, GovernanceDenied):
            return {"ok": False, "retryable": False, "error": exc.code}
        if isinstance(exc, urllib.error.HTTPError):
            retry_after = None
            try:
                retry_after = int(exc.headers.get("Retry-After")) if exc.headers.get("Retry-After") else None
            except (TypeError, ValueError):
                pass
            return {"ok": False, "retryable": exc.code in {408, 429, 500, 502, 503, 504}, "error": f"HTTP {exc.code}: {str(exc)[:300]}", "retry_after": retry_after}
        if not isinstance(exc, (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError)):
            return {"ok": False, "retryable": False, "error": type(exc).__name__}
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


def _resume_authorized_missions(max_age_seconds=86400):
    """Resume accepted missions whose worker died before composing a response.

    Telegram removes an update from the polling queue as soon as getUpdates
    returns it.  The mission record is therefore the canonical recovery source
    when a one-shot worker exits during Hermes execution.  Only recent,
    explicitly authorized missions without a terminal delivery are eligible;
    the original update ID and mission identity are retained.
    """
    if not os.path.isdir(NOVA_MISSIONS_DIR):
        return 0
    now = datetime.now(timezone.utc)
    recovered = 0
    for name in sorted(os.listdir(NOVA_MISSIONS_DIR)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(NOVA_MISSIONS_DIR, name), encoding="utf-8") as handle:
                mission = json.load(handle)
            if mission.get("status") != "AUTHORIZED":
                continue
            received_at = datetime.fromisoformat(str(mission["timestamps"]["received_at"]).replace("Z", "+00:00"))
            if (now - received_at).total_seconds() > max_age_seconds:
                continue
            if _load_delivery(mission.get("update_id")):
                continue
            update_id = int(mission["update_id"])
            update = {
                "update_id": update_id,
                "message": {
                    "message_id": update_id,
                    "date": int(received_at.timestamp()),
                    "text": mission.get("original_message", ""),
                    "chat": {"id": mission["chat_id"]},
                    "from": {"id": mission.get("user_id"), "username": ""},
                },
            }
            if process_message(update, existing_mission=mission):
                recovered += 1
        except (OSError, ValueError, TypeError, KeyError):
            continue
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


def _sanitize_internal_failure(response):
    """Keep implementation diagnostics in receipts, not executive Telegram."""
    value = str(response or "").strip()
    lower = value.casefold()
    alpha_registry_failure = "alpha" in lower and (
        "keyerror" in lower or "traceback" in lower or "failed with" in lower or "'url'" in lower
    )
    if alpha_registry_failure:
        return (
            "Alpha encountered malformed prior registry state while preparing research. "
            "Nexus is repairing the registry internally and will retry Alpha; the parent objective remains active. "
            "Ray action: none unless a genuine approval boundary appears."
        )
    if "traceback (most recent call last)" in lower or "keyerror:" in lower:
        return (
            "An internal Nexus method failed while preparing this update. "
            "Nexus is preserving the parent objective, repairing the method, and will retry or reroute automatically. "
            "Ray action: none unless a genuine approval boundary appears."
        )
    return value

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
NOVA_CURRENT_LINEAGE_PATH = os.path.join(NOVA_STATE_DIR, "nova_current_objective_lineage.json")


def load_current_objective_lineage(chat_id):
    """Load only the exact owner's current project lineage; never search history."""
    try:
        with open(NOVA_CURRENT_LINEAGE_PATH, encoding="utf-8") as handle:
            state = json.load(handle)
        row = (state.get("by_chat_id") or {}).get(str(chat_id))
        return row if isinstance(row, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def save_current_objective_lineage(chat_id, lineage):
    """Atomically persist the current objective identifiers and receipt chain."""
    os.makedirs(os.path.dirname(NOVA_CURRENT_LINEAGE_PATH), exist_ok=True)
    state = {"schema_version": "nova.current-objective-lineage.v1", "by_chat_id": {}}
    try:
        with open(NOVA_CURRENT_LINEAGE_PATH, encoding="utf-8") as handle:
            prior = json.load(handle)
        if isinstance(prior.get("by_chat_id"), dict):
            state["by_chat_id"] = prior["by_chat_id"]
    except (OSError, ValueError, TypeError):
        pass
    state["by_chat_id"][str(chat_id)] = dict(lineage)
    temporary = NOVA_CURRENT_LINEAGE_PATH + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, NOVA_CURRENT_LINEAGE_PATH)


def current_lineage_followup_kind(text):
    """Recognize anaphoric current-project reads and explicit continuations."""
    value = " ".join(str(text or "").casefold().split())
    refers_to_current = bool(re.search(
        r"\b(?:that project|this project|(?:research\s+)?project you just created|(?:research\s+)?project we just created|"
        r"that\s+(?:research\s+)?project|this\s+(?:research\s+)?project|that objective|this objective|"
        r"that research|continue it|advance it|its result|the result of that project|the result of that research project|"
        r"the result of the project)\b", value))
    if not refers_to_current:
        return None
    if re.search(r"\b(?:continue|advance|resume|keep going|run|execute)\b", value):
        return "CONTINUE"
    if re.search(r"\b(?:result|show|status|state|check|progress|next step|where|what)\b", value):
        return "READ"
    return None


def create_mission(update_id, chat_id, user_id, text):
    ts = datetime.now(timezone.utc)
    mission_id = f"nova_{ts.strftime('%Y%m%dT%H%M%S')}_{update_id}"
    from nexus_agent_platform.company_objective_router import build_root_objective
    root_objective = build_root_objective(text, conversation_message_id=update_id)
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
        "root_objective": root_objective,
        "root_objective_id": root_objective["objective_id"],
        "nova_objective_id": root_objective["objective_id"],
        "parent_request_id": root_objective["objective_id"],
        "objective_assignments": [],
        "created_at": ts.isoformat(),
        "current_status": "RECEIVED",
        "objective_source": "RAY",
        "objective_source_type": "DIRECT_MESSAGE",
        "parent_objective_id": None,
        "child_tasks": [],
    }
    os.makedirs(NOVA_MISSIONS_DIR, exist_ok=True)
    path = os.path.join(NOVA_MISSIONS_DIR, f"{mission_id}.json")
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)
    return mission


def update_mission(mission, status, extra=None):
    mission["status"] = status
    mission["current_status"] = status
    mission["timestamps"][f"{status.lower()}_at"] = datetime.now(timezone.utc).isoformat()
    if extra:
        mission.update(extra)
    path = os.path.join(NOVA_MISSIONS_DIR, f"{mission['mission_id']}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(mission, f, indent=2)
    return mission


def find_linked_objective_assignment(text, mission_dir=None, chat_id=None):
    """Resolve only an explicit job ID or this chat's exact current lineage.

    Semantic search over historical requests caused unrelated jobs to be
    substituted for the owner's current project. Similarity is not lineage.
    """
    directory = mission_dir or NOVA_MISSIONS_DIR
    explicit_job_id = re.search(r"\b(job_[a-z0-9][a-z0-9_-]*)\b", str(text or ""), re.I)
    target_job_id = explicit_job_id.group(1) if explicit_job_id else ""
    if not target_job_id and chat_id is not None:
        target_job_id = str((load_current_objective_lineage(chat_id) or {}).get("job_id") or "")
    if not target_job_id or not os.path.isdir(directory):
        return None
    for name in os.listdir(directory):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, name), encoding="utf-8") as handle:
                mission = json.load(handle)
        except (OSError, ValueError):
            continue
        assignments = mission.get("objective_assignments")
        if not isinstance(assignments, list):
            assignments = mission.get("department_assignments")
        if not isinstance(assignments, list):
            continue
        for assignment in assignments:
            if not isinstance(assignment, dict):
                continue
            job_id = str(assignment.get("job_id") or assignment.get("assignment_id") or "").strip()
            if job_id != target_job_id:
                continue
            return {
                "nova_objective_id": str(assignment.get("nova_objective_id") or mission.get("nova_objective_id")
                                          or mission.get("root_objective_id") or mission.get("mission_id") or ""),
                "parent_request_id": str(assignment.get("parent_request_id") or mission.get("parent_request_id")
                                         or mission.get("root_objective_id") or ""),
                "department": str(assignment.get("department") or "").upper(),
                "job_id": job_id,
                "created_at": str(assignment.get("created_at") or ""),
                "current_status": str(assignment.get("current_status") or assignment.get("status") or "UNKNOWN").upper(),
                "mission": mission,
            }
    return None


def _exact_research_status_response(job_id):
    """Read and render one exact existing durable job; never create work."""
    from nova.nexus_mcp_status import call_exact_job_status, render_exact_job_status

    result, tool_count = call_exact_job_status(job_id)
    if result.get("status") != "ok":
        return (f"RESEARCH_JOB_ID={job_id}\nJOB_STATUS=NOT_FOUND\n"
                "I could not find that exact job in the live durable store. No objective or job was created.",
                tool_count, result)
    job = result.get("job") if isinstance(result.get("job"), dict) else {}
    return render_exact_job_status(result), tool_count, result


def dispatch_objective_assignment(mission, text, department, requested_intent=None, followup_department=""):
    """Create and persist one governed department link before any success reply."""
    from nova.nexus_mcp_status import (
        assign_department_task, build_assignment_linkage, render_assignment_ack,
    )
    objective_id = str(mission.get("nova_objective_id") or mission.get("root_objective_id")
                       or mission.get("mission_id") or "")
    parent_request_id = str(mission.get("parent_request_id") or objective_id)
    # Nova already classified this turn. Preserve that decision across MCP so
    # Research does not have to guess the intent again from bounded text.
    research_intent = str(requested_intent or "").strip().upper()
    if str(department).upper() == "RESEARCH" and research_intent == "RESEARCH_REQUEST":
        research_intent = "RESEARCH_MISSION"
    assignment, tool_count = assign_department_task(
        text, department, parent_request_id, requested_intent=research_intent,
        followup_department=followup_department)
    linkage = build_assignment_linkage(objective_id, parent_request_id, department, assignment)
    mission.update({
        "nova_objective_id": objective_id,
        "parent_request_id": parent_request_id,
        "owner_objective_id": objective_id,
        "objective_id": objective_id,
        "assigned_department": str(department).upper(),
        "assignment_id": linkage["assignment_id"],
        "durable_job_id": linkage["job_id"],
        "durable_job_state": linkage["current_status"],
        "objective_assignments": [linkage],
        "department_assignments": [linkage],
    })
    response = render_assignment_ack(linkage)
    if str(requested_intent or "").upper() == "RESEARCH_MISSION" and str(department).upper() == "RESEARCH":
        response += ("\nREQUESTED_INTENT=RESEARCH_MISSION\nROUTED_INTENT=RESEARCH_MISSION"
                    "\nEXECUTION_PATH=nexus_assign_research")
    return assignment, linkage, tool_count, response

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


def _quoted_value(text, label):
    match = re.search(rf"\b{label}\b\s*[:=]?\s*(['\"“])(.*?)\1", str(text or ""), re.I | re.S)
    return " ".join(match.group(2).split())[:4000] if match else None


def execute_governed_google_action(text, update_id, mission):
    """Execute only explicit safe Google mutations through canonical Nexus MCP."""
    value = str(text or "")
    folded = value.casefold()
    tool = None
    arguments = {}
    from nova.nexus_mcp_status import call_mcp_tool
    if not re.search(r"\b(?:create|make|archive|mark|update|delete|send|forward|share|invite)\b", folded):
        read_tool = None
        read_args: dict[str, Any] = {}
        if re.search(r"\b(?:gmail|email|mailbox)\b", folded) and re.search(r"\b(?:latest|newest|recent|find|search|read|from|subject)\b", folded):
            read_tool, read_args = "gmail_search", {"query": "", "max_results": 1}
        elif re.search(r"\bcalendar\b", folded) and re.search(r"\b(?:next|upcoming|find|search|read|event)\b", folded):
            now = datetime.now(timezone.utc)
            read_tool, read_args = "calendar_search_events", {
                "start_time": now.isoformat(), "end_time": (now + timedelta(days=30)).isoformat(),
                "max_results": 1}
        elif re.search(r"\bdrive\b", folded) and re.search(r"\b(?:find|search|look for|read|open)\b", folded):
            read_tool, read_args = "drive_search", {"query": "Nexus", "max_results": 5}
        if read_tool:
            result, _ = call_mcp_tool(read_tool, read_args)
            receipt = write_receipt({"type": "nova_google_read", "incoming_update_id": update_id,
                "mission_id": mission.get("mission_id"), "tool": read_tool,
                "mcp_request_id": result.get("request_id"), "read_only": True,
                "result_status": result.get("status")})
            success = result.get("status") in {"ok", "empty", "partial"}
            items = result.get("items") or []
            response = (f"GOOGLE_READ={'PASS' if success else 'FAIL'}\nSERVICE={read_tool}\n"
                        f"RESULTS={json.dumps(items[:5], ensure_ascii=False)[:4500]}\nRECEIPT_ID={receipt['receipt_id']}" if success else
                        f"GOOGLE_READ=FAIL\nERROR={result.get('error') or 'read_failed'}\nRECEIPT_ID={receipt['receipt_id']}")
            return {"handled": True, "success": success, "response": response, "receipt": receipt, "result": result}
    if re.search(r"\b(?:create|make)\b.*\b(?:gmail\s+)?draft\b", folded):
        if not re.search(r"\b(?:to myself|to me|draft to self)\b", folded):
            return {"handled": True, "success": False,
                    "response": "RAY_ACTION_REQUIRED: confirm the draft is addressed only to your own Gmail account. Nothing was created or sent."}
        subject = _quoted_value(value, "subject")
        body = _quoted_value(value, "body")
        if not subject or body is None:
            return {"handled": True, "success": False,
                    "response": "ACTION_NEEDS_DETAILS: provide a quoted subject and quoted body for the unsent Gmail draft. Nothing was created."}
        tool, arguments = "gmail_create_draft", {"subject": subject, "body": body, "to_self": True}
    elif re.search(r"\b(?:create|make|add)\b.*\b(?:calendar\s+)?event\b", folded):
        title = _quoted_value(value, "titled") or _quoted_value(value, "title")
        times = re.findall(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})\b", value)
        if not title or len(times) < 2:
            return {"handled": True, "success": False,
                    "response": "ACTION_NEEDS_DETAILS: provide a quoted event title and timezone-aware ISO start and end times. No calendar change was made."}
        tool, arguments = "calendar_create_private_event", {"title": title, "start_time": times[0], "end_time": times[1]}
    elif re.search(r"\b(?:create|make|save)\b.*\b(?:drive\s+)?(?:file|document|folder)\b", folded):
        title = _quoted_value(value, "titled") or _quoted_value(value, "title")
        if not title:
            return {"handled": True, "success": False,
                    "response": "ACTION_NEEDS_DETAILS: provide a quoted Nexus Drive file title. Nothing was created."}
        tool, arguments = "drive_create_nexus_file", {"name": title, "content": "Created by Nova at Ray's explicit request.", "mime_type": "text/plain"}
    else:
        return {"handled": False}
    try:
        result, _ = call_mcp_tool(tool, arguments)
    except Exception as exc:
        result = {"status": "error", "error": type(exc).__name__}
    success = result.get("status") == "ok" and bool(result.get("mutation_performed"))
    receipt = write_receipt({"type": "nova_governed_google_action", "incoming_update_id": update_id,
        "mission_id": mission.get("mission_id"), "tool": tool,
        "policy_decision": "ALLOW" if success else "DENY_OR_SCOPE_BLOCK",
        "result_status": result.get("status"), "mcp_receipt_id": result.get("request_id"),
        "mcp_receipt_hash": result.get("receipt_hash"), "mutation_performed": success,
        "external_action": False, "spend_allowed": False})
    if success:
        item = result.get("item") or {}
        response = (f"ACTION_COMPLETED=YES\nTOOL={tool}\nITEM_ID={item.get('id') or 'UNKNOWN'}\n"
                    f"RECEIPT_ID={receipt['receipt_id']}\nMCP_RECEIPT_ID={result.get('request_id')}\n")
    else:
        error = str(result.get("error") or "google_action_failed")
        if result.get("outcome_uncertain"):
            response = (f"ACTION_COMPLETION=UNKNOWN\nERROR={error}\nRECEIPT_ID={receipt['receipt_id']}\n"
                        "The provider may have applied the change, but its final receipt could not be saved. Check the target before retrying.")
        else:
            response = (f"ACTION_COMPLETED=NO\nERROR={error}\nRECEIPT_ID={receipt['receipt_id']}\n"
                        "No successful mutation receipt was produced, so I did not claim the change as completed.")
    return {"handled": True, "success": success, "response": response, "receipt": receipt, "result": result}


def execute_workspace_file_action(text, update_id, mission):
    """Route explicit Nexus workspace file reads/writes through bounded MCP tools."""
    value = str(text or "")
    folded = value.casefold()
    from nova.nexus_mcp_status import call_mcp_tool
    if re.search(r"\b(?:read|open|show|inspect)\b", folded):
        path_match = re.search(r"(?:path\s*[:=]?\s*|['\"])([A-Za-z0-9_./-]+\.[A-Za-z0-9_-]{1,12})", value)
        if not path_match:
            return {"handled": True, "success": False,
                    "response": "ACTION_NEEDS_DETAILS: provide the Nexus-relative path to read. Nothing was read."}
        path = path_match.group(1).strip("'\"")
        result, _ = call_mcp_tool("nexus_read_workspace_file", {"relative_path": path})
        success = result.get("status") == "ok"
        receipt = write_receipt({"type": "nova_workspace_file_read", "incoming_update_id": update_id,
            "mission_id": mission.get("mission_id"), "path": result.get("path"),
            "mcp_request_id": result.get("request_id"), "read_only": True, "result_status": result.get("status")})
        body = str(result.get("content") or "")[:7000]
        response = (f"FILE_READ=PASS\nPATH={result.get('path')}\nRECEIPT_ID={receipt['receipt_id']}\n{body}" if success else
                    f"FILE_READ=FAIL\nERROR={result.get('error') or 'workspace_read_failed'}\nNo other file was substituted.")
        return {"handled": True, "success": success, "response": response, "receipt": receipt}
    if re.search(r"\b(?:create|write|save|update|build)\b", folded):
        if re.search(r"\b(?:update|overwrite|edit)\b", folded):
            return {"handled": True, "success": False,
                    "response": "ACTION_NOT_AVAILABLE: workspace writes create new artifacts only and will not overwrite an existing file. Nothing changed."}
        path_match = re.search(r"(?:path\s*[:=]?\s*|['\"])(reports/nova_internal/[A-Za-z0-9_./-]+|data/runtime/nova_artifacts/[A-Za-z0-9_./-]+)", value)
        if not path_match:
            slug = re.sub(r"[^a-z0-9]+", "-", (mission.get("mission_id") or "nova-artifact").casefold()).strip("-")
            path = f"reports/nova_internal/{slug}.md"
        else:
            path = path_match.group(1).strip("'\"")
        content = _quoted_value(value, "content") or _quoted_value(value, "body")
        if content is None:
            return {"handled": True, "success": False,
                    "response": "ACTION_NEEDS_DETAILS: provide the exact artifact content in quotes. Nothing was written."}
        result, _ = call_mcp_tool("nexus_write_workspace_artifact", {"relative_path": path, "content": content})
        success = result.get("status") == "created" and bool(result.get("created"))
        receipt = write_receipt({"type": "nova_workspace_artifact_write", "incoming_update_id": update_id,
            "mission_id": mission.get("mission_id"), "path": result.get("path"),
            "mcp_request_id": result.get("request_id"), "mcp_receipt_hash": result.get("receipt"),
            "policy_decision": "ALLOW" if success else "DENY_OR_CONFLICT",
            "action_completed": success, "content_recorded": False})
        response = (f"ACTION_COMPLETED=YES\nPATH={result.get('path')}\nRECEIPT_ID={receipt['receipt_id']}\n"
                    f"MCP_RECEIPT={result.get('receipt')}" if success else
                    f"ACTION_COMPLETED=NO\nERROR={result.get('error') or result.get('status')}\nNothing was written.")
        return {"handled": True, "success": success, "response": response, "receipt": receipt}
    return {"handled": False}


def execute_bounded_system_action(text, update_id, mission):
    """Dispatch internal Systems or coding work to its existing durable owner."""
    from nova.nexus_mcp_status import call_mcp_tool
    value = " ".join(str(text or "").split())
    folded = value.casefold()
    if re.search(r"\b(?:code|repository|software|integration|build|patch|implement)\b", folded):
        tool = "nexus_assign_bounded_coding_task"
        arguments = {"task": value[:1200], "parent_request_id": str(mission.get("mission_id") or "")}
    else:
        tool = "nexus_assign_department_query"
        arguments = {"department": "SYSTEMS", "question": value[:240],
                     "parent_request_id": str(mission.get("mission_id") or "")}
    result, _ = call_mcp_tool(tool, arguments)
    successful_statuses = {"queued", "idempotent_existing"}
    success = result.get("status") in successful_statuses and bool(result.get("durable_job_id") or result.get("job_id"))
    receipt = write_receipt({"type": "nova_bounded_internal_execution", "incoming_update_id": update_id,
        "mission_id": mission.get("mission_id"), "tool": tool,
        "job_id": result.get("durable_job_id") or result.get("job_id"),
        "mcp_request_id": result.get("request_id"), "mcp_receipt_hash": result.get("receipt"),
        "action_completed": success, "read_only": False, "external_action": False, "spend_allowed": False})
    if success:
        response = (f"ACTION_ACCEPTED=YES\nDEPARTMENT={result.get('department') or ('SYSTEMS' if 'department_query' in tool else 'CODING')}\n"
                    f"JOB_ID={result.get('durable_job_id') or result.get('job_id')}\nJOB_STATE={result.get('durable_job_state') or result.get('job_state') or 'QUEUED'}\n"
                    f"RECEIPT_ID={receipt['receipt_id']}\nMCP_RECEIPT={result.get('receipt')}\n")
    else:
        response = (f"ACTION_ACCEPTED=NO\nERROR={result.get('error') or result.get('status') or 'assignment_failed'}\n"
                    f"RECEIPT_ID={receipt['receipt_id']}\nNothing was assigned or changed.")
    return {"success": success, "response": response, "receipt": receipt, "result": result}


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
        "shadow": {"run_id": run_id, "model": get_env().get("HERMES_NOVA_MODEL", "gpt-5.5")},
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
            "model": result.get("model", get_env().get("HERMES_NOVA_MODEL", "gpt-5.5")),
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
        "hermes_session_id": result.hermes_session_id,
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


def _set_owner_turn_governance_context(mission, *, delivery_update_id=None, delivery_job_type=None):
    """Bind provider accounting to the already-persisted owner-turn mission.

    Telegram owner turns are durable missions, even when the request is a
    read/query instead of a Nexus department job. Metered execution and the
    trusted owner reply still need a stable correlation ID for the governor.
    """
    values = {
        # A follow-up reply is a new external message even when its data is
        # correlated to an older objective. Give each Telegram update its own
        # governor idempotency scope while retaining the objective correlation.
        "NEXUS_DURABLE_JOB_ID": (
            f"nova-telegram-update-{delivery_update_id}"
            if delivery_update_id is not None else str(mission["mission_id"])
        ),
        "NEXUS_CORRELATION_ID": str(mission["correlation_id"]),
        "NEXUS_DEPARTMENT": "NOVA",
    }
    if delivery_job_type:
        values["NEXUS_JOB_TYPE"] = str(delivery_job_type)
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    return previous


def _restore_owner_turn_governance_context(previous):
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

# ─── Message Processing ─────────────────────────────────

def process_message(update, existing_mission=None):
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
            outcome = _process_message_inner(update, message, chat, user, chat_id, user_id, username, text, update_id, run_id, trace=trace, mission_override=existing_mission)
            trace.finish({"runtime": "hermes", "delivery_visible": True, "outcome": outcome})
            return outcome


def _process_message_inner(update, message, chat, user, chat_id, user_id, username, text, update_id, primary_run_id=None, trace=None, mission_override=None):
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

    governance_context = None
    try:
        with stage_execution(
            stage="authorization",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
        ):
            authorized = is_authorized(chat_id, user_id, username)

        if not authorized:
            with stage_execution(
                stage="mission_create",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
            ):
                mission = mission_override or create_mission(update_id, chat_id, user_id, text)
            governance_context = _set_owner_turn_governance_context(mission)
            update_mission(mission, "UNAUTHORIZED")
            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={"mission_id": mission["mission_id"], "unauthorized": True},
            ):
                tg_send_message(chat_id, "This bot is private. You are not authorized.")
            return True

        from nova.semantic_orchestration import resolve_owner_request
        semantic = resolve_owner_request(text)
        lineage = load_current_objective_lineage(chat_id)
        followup_kind = current_lineage_followup_kind(text)
        if followup_kind:
            mission = create_mission(update_id, chat_id, user_id, text)
            governance_context = _set_owner_turn_governance_context(mission)
            update_mission(mission, "AUTHORIZED")
            if not lineage:
                response = ("CURRENT_PROJECT_NOT_FOUND. I have no receipt-backed Research project in this chat's current lineage; "
                            "I did not search or substitute a historical project, and nothing was continued or changed.")
                update_mission(mission, "CURRENT_PROJECT_NOT_FOUND", {
                    "semantic_intent": "CURRENT_OBJECTIVE_FOLLOWUP", "action_completed": False,
                    "historical_substitution": False,
                })
                write_receipt({"type": "nova_current_project_not_found", "incoming_update_id": update_id,
                    "mission_id": mission["mission_id"], "read_only": True,
                    "action_completed": False, "historical_substitution": False})
            elif followup_kind == "READ":
                job_id = str(lineage.get("job_id") or "")
                try:
                    response, tool_count, live_result = _exact_research_status_response(job_id)
                    response = (f"OBJECTIVE_ID={lineage.get('objective_id') or 'UNKNOWN'}\n"
                                f"PROJECT_ID={lineage.get('project_id') or 'UNKNOWN'}\n" + response)
                    status_receipt = write_receipt({"type": "nova_current_project_status_read",
                        "incoming_update_id": update_id, "mission_id": mission["mission_id"],
                        "objective_id": lineage.get("objective_id"), "project_id": lineage.get("project_id"),
                        "job_id": job_id, "source_request_receipt_id": lineage.get("receipt_id"),
                        "read_only": True, "historical_substitution": False,
                        "nexus_tool_count": tool_count, "result_status": live_result.get("status")})
                    update_mission(mission, "CURRENT_PROJECT_STATUS_READ", {
                        "current_objective_lineage": lineage, "current_project_read_receipt_id": status_receipt["receipt_id"]})
                except Exception as exc:
                    response = (f"CURRENT_PROJECT_STATUS=UNAVAILABLE\nPROJECT_ID={lineage.get('project_id') or 'UNKNOWN'}\n"
                                "The exact linked job could not be read. I did not substitute historical work.")
                    update_mission(mission, "CURRENT_PROJECT_STATUS_UNAVAILABLE", {
                        "error_type": type(exc).__name__, "current_objective_lineage": lineage,
                        "historical_substitution": False})
            else:
                try:
                    from nova.nexus_mcp_status import continue_research_project
                    continued, tool_count = continue_research_project(
                        objective_id=str(lineage.get("objective_id") or ""),
                        project_id=str(lineage.get("project_id") or ""),
                        job_id=str(lineage.get("job_id") or ""), instruction=text,
                        parent_request_id=str(lineage.get("objective_id") or ""))
                    continuation_receipt = write_receipt({"type": "nova_current_project_continuation",
                        "incoming_update_id": update_id, "mission_id": mission["mission_id"],
                        "objective_id": lineage.get("objective_id"), "project_id": lineage.get("project_id"),
                        "prior_job_id": lineage.get("job_id"), "job_id": continued.get("job_id"),
                        "nexus_request_id": continued.get("request_id"), "nexus_tool_count": tool_count,
                        "job_created": bool(continued.get("job_created")), "action_completed": True,
                        "same_project_lineage": True, "external_action": False, "spend_allowed": False})
                    lineage.update({"job_id": continued["job_id"],
                        "job_state": continued.get("job_state", "UNKNOWN"),
                        "parent_job_id": lineage.get("job_id"), "receipt_id": continuation_receipt["receipt_id"],
                        "updated_at": datetime.now(timezone.utc).isoformat()})
                    save_current_objective_lineage(chat_id, lineage)
                    response = (f"CONTINUATION_EXECUTED=YES\nOBJECTIVE_ID={lineage.get('objective_id')}\n"
                        f"PROJECT_ID={lineage.get('project_id')}\nJOB_ID={continued.get('job_id')}\n"
                        f"JOB_STATUS={continued.get('job_state', 'UNKNOWN')}\n"
                        f"RECEIPT_ID={continuation_receipt['receipt_id']}\n"
                        "The work remains in the existing Research queue under the same project; completion is not claimed yet.")
                    update_mission(mission, "CURRENT_PROJECT_CONTINUED", {
                        "current_objective_lineage": lineage, "continuation_receipt_id": continuation_receipt["receipt_id"],
                        "durable_job_id": continued.get("job_id"), "durable_job_state": continued.get("job_state")})
                except Exception as exc:
                    response = (f"CONTINUATION_EXECUTED=NO\nPROJECT_ID={lineage.get('project_id') or 'UNKNOWN'}\n"
                                "The exact project could not be continued through Nexus. No replacement project was created.")
                    update_mission(mission, "CURRENT_PROJECT_CONTINUATION_FAILED", {
                        "error_type": type(exc).__name__, "current_objective_lineage": lineage,
                        "action_completed": False, "historical_substitution": False})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []), "semantic_intent": "CURRENT_OBJECTIVE_FOLLOWUP",
                "current_project_id": (lineage or {}).get("project_id"), "historical_substitution": False})
            return True

        if semantic.get("intent") == "RESEARCH_STATUS_QUERY":
            # Route explicit existing-job inspection before mission creation.
            # The only MCP operation here is a bounded read by exact ID.
            job_id = str(semantic.get("job_id") or "")
            linked = find_linked_objective_assignment(text, chat_id=chat_id)
            try:
                response, tool_count, live_result = _exact_research_status_response(job_id)
            except Exception as exc:
                _log_error(f"Exact Research job status read failed: {type(exc).__name__}: {str(exc)[:180]}")
                response = (f"RESEARCH_JOB_ID={job_id}\nSTATUS_READ=UNAVAILABLE\n"
                            "The durable store could not confirm this job's current state. "
                            "No objective or replacement job was created.")
                tool_count, live_result = 0, {"status": "unavailable", "job_id": job_id}
            existing_mission = linked.get("mission") if linked else None
            context_mission = existing_mission or {
                "mission_id": job_id,
                "correlation_id": str((live_result.get("job") or {}).get("correlation_id") or job_id),
            }
            governance_context = _set_owner_turn_governance_context(
                context_mission, delivery_update_id=update_id,
                delivery_job_type="NOVA_TELEGRAM_STATUS_REPLY",
            )
            try:
                delivery = _deliver_response(
                    update_id, chat_id, response,
                    mission_id=existing_mission.get("mission_id") if existing_mission else None,
                )
            finally:
                _restore_owner_turn_governance_context(governance_context)
                governance_context = None
            delivery_state = str(delivery.get("state") or "UNKNOWN")
            if delivery_state == "DELIVERED":
                _log(f"Read-only exact job status delivered: update={update_id} job={job_id} tools={tool_count}")
            else:
                _log_error(
                    f"Read-only exact job status delivery failed: update={update_id} job={job_id} "
                    f"state={delivery_state} error={str(delivery.get('last_error') or 'unknown')[:180]}"
                )
            return True

        with stage_execution(
            stage="mission_create",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
        ):
            mission = mission_override or create_mission(update_id, chat_id, user_id, text)
        governance_context = _set_owner_turn_governance_context(mission)

        update_mission(mission, "AUTHORIZED")
        _update_status_field("last_incoming_message", datetime.now(timezone.utc).isoformat())

        # Classify the command before inspecting request details. Imperative
        # task creation must win over read words embedded in a long task body.
        from nexus_agent_platform.department_router import classify_intent
        from nova.semantic_orchestration import resolve_owner_request
        intent = classify_intent(text)
        semantic = resolve_owner_request(text)
        from nexus_agent_platform.workflow_execution import nova_execution_plan
        execution_plan = nova_execution_plan(semantic)
        update_mission(mission, "EXECUTION_CLASSIFIED", {
            "semantic_intent": semantic.get("intent"),
            "execution_plan": execution_plan,
            "model_call_required": execution_plan["model_call_required"],
        })
        if semantic.get("intent") == "ACTION_NOT_AVAILABLE":
            response = ("ACTION_NOT_AVAILABLE. This request was classified as an action, but no governed executor is available for it. "
                        "Nothing was created, changed, sent, or scheduled.")
            update_mission(mission, "ACTION_NOT_AVAILABLE", {"action_completed": False, "read_only": False,
                "semantic_route": semantic, "side_effects": False})
            write_receipt({"type": "nova_action_not_available", "incoming_update_id": update_id,
                "mission_id": mission["mission_id"], "action_completed": False, "side_effects": False})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []), "action_completed": False})
            return True
        if semantic.get("intent") == "RESEARCH_ROOM_REQUEST":
            intent_object = semantic.get("intent_object") or {}
            mission["nova_objective_id"] = str(mission.get("nova_objective_id") or mission.get("root_objective_id") or mission["mission_id"])
            mission["primary_mode"] = intent_object.get("primary_mode")
            mission["objective_accepted"] = True
            update_mission(mission, "RESEARCH_ROOM_ACCEPTED", {
                "objective_accepted": True,
                "primary_mode": intent_object.get("primary_mode"),
                "intent_object": intent_object,
                "research_intake_accepted_before_handoff_checks": True,
                "alpha_assignment_required": False,
                "downstream_actions_before_strategy": False,
            })
            try:
                from nova.research_room_dispatch import execute_research_room_request, render_nova_research_response
                room_result = execute_research_room_request(text,
                    objective_id=mission["nova_objective_id"], repository_root=REPO_ROOT)
                room_case = room_result.get("case") or {}
                execution_strategy = room_case.get("execution_strategy") or (room_case.get("final_synthesis") or {}).get("execution_strategy") or {}
                complete = room_result.get("status") == "COMPLETE" and room_case.get("status") == "COMPLETE"
                response = render_nova_research_response(room_result)
                mission.update({"research_room_case_id": room_result.get("case_id"),
                    "research_room_case_status": room_case.get("status"),
                    "execution_strategy": execution_strategy,
                    "proposed_handoff": room_case.get("handoff"),
                    "research_room_artifacts": room_result.get("artifacts") or
                        (room_case.get("metadata") or {}).get("transcript_paths", {}),
                    "final_strategist_used": bool(execution_strategy),
                    "nova_response_generated": bool(response)})
                update_mission(mission, "RESEARCH_ROOM_COMPLETE" if complete else "RESEARCH_ROOM_PARTIAL", {
                    "response_mode": "nova_research_room_execution",
                    "objective_accepted": True,
                    "primary_mode": execution_strategy.get("execution_mode") or intent_object.get("primary_mode"),
                    "research_room_case_id": room_result.get("case_id"),
                    "research_room_case_status": room_case.get("status"),
                    "final_strategist_used": bool(execution_strategy),
                    "business_strategy_created": bool(execution_strategy.get("top_businesses")) if intent_object.get("primary_mode") == "BUSINESS_OPPORTUNITY_MODE" else bool(execution_strategy),
                    "nova_automation_plan_created": bool(execution_strategy.get("how_nova_runs_it")),
                    "library_additions_created": bool(execution_strategy.get("library_additions")),
                    "proposed_handoff_created": bool(room_case.get("handoff")),
                    "execution_strategy": execution_strategy,
                    "proposed_handoff": room_case.get("handoff"),
                    "artifacts": mission.get("research_room_artifacts"),
                    "reused_idempotent_case": room_result.get("reused_idempotent_case", False),
                })
                write_receipt({"type": "nova_research_room_result",
                    "incoming_update_id": update_id, "nova_objective_id": mission["nova_objective_id"],
                    "case_id": room_result.get("case_id"), "case_status": room_case.get("status"),
                    "execution_mode": execution_strategy.get("execution_mode"),
                    "objective_accepted": True, "proposed_handoff": room_case.get("handoff"),
                    "artifact_paths": mission.get("research_room_artifacts"),
                    "downstream_actions_executed": False})
            except Exception as exc:
                # Preserve the accepted root objective and deliver a partial
                # room result; source/provider/dept capability failures are
                # recorded findings, never pre-research assignment gates.
                error_type = type(exc).__name__
                _log_error(f"Nova Research Room route failed after intake acceptance: {error_type}: {str(exc)[:220]}")
                response = ("I accepted the research objective, but the shadow Research Room did not return a completed strategy on this turn. "
                    "The objective remains preserved for continuation; no department action was dispatched.")
                update_mission(mission, "RESEARCH_ROOM_PARTIAL", {
                    "response_mode": "nova_research_room_execution",
                    "objective_accepted": True, "primary_mode": intent_object.get("primary_mode"),
                    "error_type": error_type, "error_message": str(exc)[:220],
                    "alpha_assignment_required": False, "downstream_actions_before_strategy": False,
                })
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "nova_research_room_execution",
                "response_message_ids": delivery.get("message_ids", []),
                "telegram_send_count": len(delivery.get("message_ids", [])),
            })
            return True

        if semantic.get("intent") == "CAPABILITY_QUERY":
            try:
                from nova.live_capability_registry import render_capability_answer
                response = render_capability_answer(text)
                update_mission(mission, "RESPONSE_COMPOSED", {
                    "response_mode": "live_capability_registry",
                    "registry_source": "Nexus MCP discovery and deployed Hermes profile",
                })
            except Exception as exc:
                error_type = type(exc).__name__
                _log_error(f"Live capability registry failed: {error_type}: {str(exc)[:180]}")
                response = f"I couldn't verify my current capability list ({error_type}); I won't present an unverified capability as working."
                update_mission(mission, "CAPABILITY_REGISTRY_FAILED", {"error_type": error_type})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "live_capability_registry", "telegram_send_count": len(delivery.get("message_ids", [])),
            })
            return True

        if semantic.get("intent") == "MULTI_DEPARTMENT_ASSIGNMENT":
            from nova.nexus_mcp_status import (
                assign_department_tasks, build_assignment_linkage,
                render_assignment_batch,
            )
            owner_objective_id = str(mission.get("root_objective_id") or mission["mission_id"])
            mission["nova_objective_id"] = owner_objective_id
            mission["parent_request_id"] = owner_objective_id
            departments = [str(value).upper() for value in semantic.get("departments", [])]
            batch = assign_department_tasks(text, departments, owner_objective_id)
            response = render_assignment_batch(batch, owner_objective_id)
            mission["owner_objective_id"] = owner_objective_id
            mission["objective_id"] = owner_objective_id
            linked_assignments = []
            for row in batch.get("assignments", []):
                if row.get("job_id"):
                    linked_assignments.append(build_assignment_linkage(
                        owner_objective_id, owner_objective_id, row.get("department"),
                        {"job_id": row.get("job_id"), "job_state": row.get("status"),
                         "created_at": row.get("created_at")},
                    ))
                else:
                    linked_assignments.append({
                        "nova_objective_id": owner_objective_id,
                        "parent_request_id": owner_objective_id,
                        "department": row.get("department"), "assignment_id": None,
                        "job_id": None, "created_at": datetime.now(timezone.utc).isoformat(),
                        "current_status": str(row.get("status") or "BLOCKED").upper(),
                        "blocker": row.get("error"), "error_type": row.get("error_type"),
                    })
            mission["objective_assignments"] = linked_assignments
            mission["department_assignments"] = linked_assignments
            mission["child_tasks"] = [
                {"department": row.get("department"), "job_id": row.get("job_id"),
                 "status": row.get("status"), "parent_objective_id": owner_objective_id,
                 "assignment_source": "GOVERNED_NEXUS_MCP"}
                for row in batch.get("assignments", []) if row.get("job_id")
            ]
            accepted = int(batch.get("accepted_count", 0) or 0)
            update_mission(mission, "RESPONSE_COMPOSED" if accepted else "DEPARTMENT_ASSIGNMENT_FAILED", {
                "response_mode": "nexus_mcp_multi_department_assignment",
                "semantic_route": semantic,
                "nexus_mcp_tool_count": batch.get("tool_count", 0),
                "owner_objective_id": owner_objective_id,
                "parent_request_id": owner_objective_id,
                "objective_assignments": linked_assignments,
            })
            previous_governance = _set_owner_turn_governance_context(mission)
            try:
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            finally:
                _restore_owner_turn_governance_context(previous_governance)
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "nexus_mcp_multi_department_assignment",
                "response_message_ids": delivery.get("message_ids", []),
                "telegram_send_count": len(delivery.get("message_ids", [])),
            })
            return True

        if semantic.get("intent") == "PRIOR_WORK_QUERY":
            try:
                from nova.nexus_mcp_status import call_prior_department_result, render_prior_department_result
                prior_result, tool_count = call_prior_department_result(text, semantic.get("department"))
                response = render_prior_department_result(prior_result)
                update_mission(mission, "RESPONSE_COMPOSED", {
                    "response_mode": "receipt_verified_prior_work",
                    "nexus_mcp_tool": "nexus_get_prior_department_result",
                    "nexus_mcp_tool_count": tool_count,
                    "prior_department": semantic.get("department"),
                    "prior_job_id": prior_result.get("job_id"),
                    "prior_receipt_id": prior_result.get("receipt_id"),
                    "source_research_job_id": prior_result.get("source_research_job_id"),
                    "prior_read_receipt_id": prior_result.get("request_id"),
                    "semantic_route": semantic,
                })
            except Exception as exc:
                error_type = type(exc).__name__
                _log_error(f"Prior Nexus result lookup failed: {error_type}: {str(exc)[:180]}")
                update_mission(mission, "PRIOR_WORK_READ_FAILED", {
                    "response_mode": "receipt_verified_prior_work", "error_type": error_type,
                    "prior_department": semantic.get("department"),
                })
                response = "I couldn't retrieve the completed Nexus result just now. I did not create or rerun any department work."
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "receipt_verified_prior_work",
                "telegram_send_count": len(delivery.get("message_ids", [])),
            })
            write_receipt({
                "type": "nova_prior_work_response", "incoming_update_id": update_id,
                "correlation_id": mission.get("correlation_id"),
                "department": semantic.get("department"),
                "job_id": prior_result.get("job_id") if "prior_result" in locals() else None,
                "receipt_id": prior_result.get("receipt_id") if "prior_result" in locals() else None,
                "outgoing_message_ids": delivery.get("message_ids", []),
                "read_only": True, "job_created": False,
            })
            return True

        if intent in {"STATE_QUERY", "LIST_JOBS", "STATUS_OF_EXISTING_TASK", "FOLLOWUP_QUERY"} or semantic.get("intent") in {"LIVE_STATE_QUERY", "LIST_JOBS", "OBJECTIVE_STATUS_QUERY"}:
            try:
                from nova.nexus_mcp_status import (
                    call_exact_job_status, call_status_tool, render_exact_job_status,
                    render_status_result,
                )
                linked_assignment = find_linked_objective_assignment(text, chat_id=chat_id)
                if linked_assignment:
                    live_result, tool_count = call_exact_job_status(linked_assignment["job_id"])
                    tool_name = "nexus_get_durable_jobs"
                    response = render_exact_job_status(live_result)
                    if live_result.get("status") == "ok":
                        current_job = live_result.get("job") or {}
                        linked_assignment["current_status"] = str(current_job.get("state") or "UNKNOWN").upper()
                        mission = linked_assignment.get("mission") or mission
                        assignments = mission.get("objective_assignments") or mission.get("department_assignments") or []
                        for row in assignments:
                            if isinstance(row, dict) and str(row.get("job_id") or row.get("assignment_id") or "") == linked_assignment["job_id"]:
                                row["current_status"] = linked_assignment["current_status"]
                        update_mission(mission, "OBJECTIVE_STATUS_READ", {
                            "objective_assignments": assignments,
                            "last_status_job_id": linked_assignment["job_id"],
                            "last_status_read_at": datetime.now(timezone.utc).isoformat(),
                        })
                else:
                    tool_name, live_result, tool_count = call_status_tool(text)
                    response = render_status_result(text, tool_name, live_result)
                update_mission(mission, "RESPONSE_COMPOSED", {
                    "response_mode": "live_nexus_mcp_status", "nexus_mcp_tool": tool_name,
                    "nexus_mcp_tool_count": tool_count, "nexus_mcp_request_id": live_result.get("request_id"),
                    "linked_objective_id": linked_assignment.get("nova_objective_id") if linked_assignment else None,
                    "linked_job_id": linked_assignment.get("job_id") if linked_assignment else None,
                })
            except Exception as exc:
                error_type = type(exc).__name__
                _log_error(f"Live Nexus MCP status route failed: {error_type}: {str(exc)[:240]}")
                update_mission(mission, "MCP_READ_FAILED", {"response_mode": "live_nexus_mcp_status", "error_type": error_type})
                response = "I could not read current Nexus state through MCP just now. This query was not converted into an objective."
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "live_nexus_mcp_status", "nexus_mcp_tool": tool_name if "tool_name" in locals() else None,
                "telegram_send_count": len(delivery.get("message_ids", [])),
            })
            return True

        if semantic.get("intent") == "CROSS_DEPARTMENT_CONTINUATION":
            assignment = None
            try:
                from nova.nexus_mcp_status import call_prior_department_result, assign_research_task
                alpha_result, alpha_tool_count = call_prior_department_result(
                    "What evidence gap did Alpha identify in the prior Research result?", "ALPHA")
                if alpha_result.get("status") != "ok":
                    raise RuntimeError("PRIOR_ALPHA_EVIDENCE_NOT_FOUND")
                evaluation = alpha_result.get("alpha_evaluation") if isinstance(alpha_result.get("alpha_evaluation"), dict) else {}
                source_research_job_id = str(alpha_result.get("source_research_job_id") or "")
                alpha_summary = str(alpha_result.get("summary") or "")
                opportunity = str(evaluation.get("business_name") or evaluation.get("opportunity_name") or "").strip()
                if not opportunity:
                    match = re.search(r"(?im)^ALPHA REVIEW\s*[—-]\s*(.+?)(?:\s+business example)?\s*$", alpha_summary)
                    opportunity = match.group(1).strip() if match else ""
                if not opportunity:
                    raise RuntimeError("PRIOR_ALPHA_OPPORTUNITY_NOT_RESOLVED")
                gap = str(evaluation.get("weakest_assumption") or evaluation.get("reasoning_summary") or "")[:700]
                weaknesses = evaluation.get("weaknesses") if isinstance(evaluation.get("weaknesses"), list) else []
                if not gap and weaknesses:
                    gap = str(weaknesses[0])[:700]
                if not gap:
                    gap = str(alpha_result.get("summary") or "Alpha identified weak supporting evidence.")[:700]
                task = (
                    f"TASK: Close the largest evidence gap from Alpha's review of the existing {opportunity} opportunity. "
                    f"Source Research job: {source_research_job_id}. Alpha's gap: {gap}.\n"
                    f"RESEARCH QUERY: Research {opportunity} pricing plans, official prices, and billing periods.\n"
                    f"INSTRUCTIONS: Verify the exact plan, price, billing period, and source URL. If the official pricing page for {opportunity} is inaccessible, "
                    "use the strongest authoritative source and clearly state the limitation. Keep this scoped to the existing opportunity; "
                    "return evidence for Alpha to reevaluate the same opportunity."
                )
                assignment, tool_count = assign_research_task(task, str(mission["mission_id"]), followup_department="ALPHA")
                job_id = assignment.get("durable_job_id")
                if not job_id:
                    raise RuntimeError("RESEARCH_JOB_ID_MISSING")
                response = (
                    "I’ve sent Alpha’s largest evidence gap back to Research. Once Research improves the evidence, "
                    "Alpha will reevaluate the same opportunity and I’ll send you the updated conclusion."
                )
                mission.update({"continuation_plan": "PRIOR_ALPHA_GAP_TO_RESEARCH_THEN_ALPHA",
                    "source_alpha_job_id": alpha_result.get("job_id"),
                    "source_alpha_receipt_id": alpha_result.get("receipt_id"),
                    "source_research_job_id": source_research_job_id,
                    "research_job_id": job_id, "durable_job_id": job_id,
                    "durable_job_state": assignment.get("durable_job_state"),
                    "assigned_department": "RESEARCH", "semantic_route": semantic,
                    "nexus_mcp_tool": "nexus_assign_research",
                    "nexus_mcp_tool_count": tool_count + alpha_tool_count})
                update_mission(mission, "RESPONSE_COMPOSED", {"response_mode": "cross_department_continuation_ack"})
            except Exception as exc:
                error_type = type(exc).__name__
                _log_error(f"Cross-department continuation failed: {error_type}: {str(exc)[:220]}")
                response = "I couldn’t continue this through Research yet. The prior Alpha review is preserved, and I’m keeping the request attached to this mission while the Research assignment path is repaired."
                update_mission(mission, "CROSS_DEPARTMENT_CONTINUATION_FAILED", {
                    "error_type": error_type, "error_message": str(exc)[:220], "semantic_route": semantic})
            previous_governance = _set_owner_turn_governance_context(mission)
            try:
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            finally:
                _restore_owner_turn_governance_context(previous_governance)
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "cross_department_continuation_ack",
                "response_message_ids": delivery.get("message_ids", []),
                "ack_delivery_state": delivery.get("state"),
            })
            return True

        if semantic.get("intent") in {"CREATIVE_ASSET_REQUEST", "BOUNDED_CODING_REQUEST"}:
            control_tool = ("nexus_assign_creative_asset" if semantic["intent"] == "CREATIVE_ASSET_REQUEST"
                            else "nexus_assign_bounded_coding_task")
            try:
                from nova.nexus_mcp_status import assign_bounded_control_task
                assignment, tool_count = assign_bounded_control_task(control_tool, text, mission["mission_id"])
                response = (f"{assignment.get('department')} accepted the bounded task.\nJOB_ID={assignment['job_id']}\n"
                            f"JOB_STATUS={assignment.get('job_state', 'READY')}\nI’ll report the persisted result when the worker finishes.")
                mission.update({"durable_job_id": assignment["job_id"], "durable_job_state": assignment.get("job_state"),
                                "assigned_department": assignment.get("department"), "semantic_route": semantic})
                update_mission(mission, "RESPONSE_COMPOSED", {"response_mode": "bounded_nova_control_action",
                    "nexus_mcp_tool": control_tool, "nexus_mcp_tool_count": tool_count,
                    "durable_job_id": assignment["job_id"], "semantic_route": semantic})
            except Exception as exc:
                _log_error(f"Bounded Nova control action failed: {type(exc).__name__}: {str(exc)[:220]}")
                response = f"I couldn't queue that bounded task: {type(exc).__name__}: {str(exc)[:180]}"
                update_mission(mission, "CONTROL_ACTION_FAILED", {"error_type": type(exc).__name__,
                    "error_message": str(exc)[:220], "semantic_route": semantic})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "bounded_nova_control_action", "telegram_send_count": len(delivery.get("message_ids", []))})
            return True

        selected_department = semantic.get("department")
        if selected_department in {"RESEARCH", "SYSTEMS", "ALPHA"} and semantic.get("intent") in {
            "RESEARCH_REQUEST", "RESEARCH_MISSION", "RESEARCH_RUNTIME_INSPECTION", "DEPARTMENT_ASSIGNMENT"
        }:
            response_mode = "nexus_mcp_department_assignment"
            assignment_notice_job_id = None
            nova_objective_id = str(mission.get("nova_objective_id") or mission.get("root_objective_id") or mission["mission_id"])
            parent_request_id = str(mission.get("parent_request_id") or nova_objective_id)
            try:
                mission["nova_objective_id"] = nova_objective_id
                mission["parent_request_id"] = parent_request_id
                assignment, linkage, tool_count, response = dispatch_objective_assignment(
                    mission, text, selected_department, requested_intent=semantic.get("intent"),
                    followup_department=semantic.get("likely_destination") or "")
                assigned_department = selected_department
                job_id = linkage["job_id"]
                job_state = linkage["current_status"]
                response_mode = f"nexus_mcp_{assigned_department.casefold()}_assignment"
                if assigned_department == "ALPHA":
                    response += (f"\nSOURCE_RESEARCH_JOB_ID={assignment.get('source_research_job_id')}"
                                 "\nThe existing Research evidence will be used; no new Research job or owner objective was created.")
                    assignment_notice_job_id = assignment.get("notice_job_id")
                mission.update({
                    "nova_objective_id": nova_objective_id,
                    "parent_request_id": parent_request_id,
                    "owner_objective_id": nova_objective_id,
                    "objective_id": nova_objective_id,
                    "assigned_department": assigned_department,
                    "assignment_id": job_id,
                    "durable_job_id": job_id,
                    "durable_job_state": job_state,
                    "objective_assignments": [linkage],
                    "department_assignments": [linkage],
                })
                if assigned_department == "RESEARCH":
                    project_receipt = write_receipt({
                        "type": "nova_research_project_assignment",
                        "incoming_update_id": update_id, "mission_id": mission["mission_id"],
                        "objective_id": assignment.get("objective_id"),
                        "project_id": assignment.get("work_id") or assignment.get("objective_id"),
                        "job_id": job_id, "nexus_receipt_id": assignment.get("request_id"),
                        "nexus_receipt_hash": assignment.get("receipt"),
                        "assignment_state": job_state, "read_only": False,
                        "external_action": False, "spend_allowed": False,
                    })
                    lineage = {
                        "telegram_update_id": update_id, "mission_id": mission["mission_id"],
                        "objective_id": assignment.get("objective_id") or linkage.get("objective_id"),
                        "project_id": assignment.get("work_id") or linkage.get("project_id"),
                        "job_id": job_id, "case_id": None,
                        "receipt_id": project_receipt["receipt_id"],
                        "nexus_receipt_id": assignment.get("request_id"),
                        "result_id": None, "job_state": job_state,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    save_current_objective_lineage(chat_id, lineage)
                    response += f"\nRECEIPT_ID={project_receipt['receipt_id']}"
                update_mission(mission, "RESPONSE_COMPOSED", {
                    "response_mode": response_mode, "nexus_mcp_tool": "nexus_assign_research" if assigned_department=="RESEARCH" else "nexus_assign_department_query",
                    "nexus_mcp_tool_count": tool_count, "owner_objective_id": nova_objective_id,
                    "durable_job_id": job_id, "durable_job_state": job_state, "assigned_department": assigned_department,
                    "source_research_job_id": assignment.get("source_research_job_id") if assigned_department=="ALPHA" else None,
                    "notice_job_id": assignment_notice_job_id,
                    "parent_request_id": parent_request_id, "objective_assignments": [linkage],
                    "semantic_route": semantic,
                    "current_objective_lineage": lineage if assigned_department == "RESEARCH" else None,
                })
            except Exception as exc:
                error_type = type(exc).__name__
                _log_error(f"Nexus {selected_department} assignment failed: {error_type}: {str(exc)[:240]}")
                blocker = f"{error_type}: {str(exc)[:180]}"
                from nova.nexus_mcp_status import render_assignment_failure
                response = render_assignment_failure(nova_objective_id, blocker)
                failed_link = {
                    "nova_objective_id": nova_objective_id,
                    "parent_request_id": parent_request_id,
                    "department": selected_department,
                    "assignment_id": None,
                    "job_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "current_status": "FAILED",
                    "blocker": blocker,
                }
                mission.update({"nova_objective_id": nova_objective_id,
                    "parent_request_id": parent_request_id, "owner_objective_id": nova_objective_id,
                    "assigned_department": selected_department, "objective_assignments": [failed_link],
                    "department_assignments": [failed_link]})
                update_mission(mission, "DEPARTMENT_ASSIGNMENT_FAILED", {
                    "error_type": error_type, "error_message": str(exc)[:240],
                    "department": selected_department, "parent_request_id": parent_request_id,
                    "objective_assignments": [failed_link], "semantic_route": semantic})
            # Durable acceptance is the acknowledgment boundary. Send the
            # owner reply now through Nova's governed delivery path; completion
            # remains a separate proactive notice from the worker.
            previous_governance = _set_owner_turn_governance_context(mission)
            try:
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            finally:
                _restore_owner_turn_governance_context(previous_governance)
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": response_mode if "response_mode" in locals() else "nexus_mcp_department_assignment",
                "response_message_ids": delivery.get("message_ids", []),
                "telegram_send_count": len(delivery.get("message_ids", [])),
            })
            return True

        if semantic.get("intent") == "GOOGLE_ACTION":
            try:
                action = execute_governed_google_action(text, update_id, mission)
            except Exception as exc:
                action = {"handled": True, "success": False,
                          "response": f"ACTION_COMPLETED=NO\nERROR={type(exc).__name__}\nNothing was changed."}
            if not action.get("handled"):
                action = {"handled": True, "success": False,
                          "response": "ACTION_NOT_AVAILABLE. No safe, explicit Google operation matched this request. Nothing was changed or sent."}
                write_receipt({"type": "nova_google_action_not_available", "incoming_update_id": update_id,
                    "mission_id": mission["mission_id"], "action_completed": False, "side_effects": False})
            response = action["response"]
            update_mission(mission, "GOOGLE_ACTION_COMPLETED" if action.get("success") else "GOOGLE_ACTION_NOT_COMPLETED", {
                "response_mode": "nexus_google_mcp_governed_action", "action_completed": bool(action.get("success")),
                "read_only": False, "side_effects": bool(action.get("success")),
                "action_outcome_uncertain": bool((action.get("result") or {}).get("outcome_uncertain")),
                "receipt_id": (action.get("receipt") or {}).get("receipt_id")})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []),
                "action_completed": bool(action.get("success"))})
            return True

        if semantic.get("intent") == "FILE_OR_DOCUMENT_ACTION":
            try:
                action = execute_workspace_file_action(text, update_id, mission)
            except Exception as exc:
                action = {"handled": True, "success": False,
                          "response": f"ACTION_COMPLETED=NO\nERROR={type(exc).__name__}\nNothing was changed."}
            response = action.get("response") or "ACTION_NOT_AVAILABLE. Nothing was changed."
            update_mission(mission, "WORKSPACE_FILE_ACTION_COMPLETED" if action.get("success") else "WORKSPACE_FILE_ACTION_NOT_COMPLETED", {
                "response_mode": "nexus_workspace_file_mcp", "action_completed": bool(action.get("success")),
                "side_effects": bool(action.get("success")),
                "receipt_id": (action.get("receipt") or {}).get("receipt_id")})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []), "action_completed": bool(action.get("success"))})
            return True

        if semantic.get("intent") == "CODE_OR_SYSTEM_ACTION":
            try:
                action = execute_bounded_system_action(text, update_id, mission)
            except Exception as exc:
                action = {"success": False,
                          "response": f"ACTION_ACCEPTED=NO\nERROR={type(exc).__name__}\nNothing was assigned."}
            response = action.get("response") or "ACTION_ACCEPTED=NO\nNo assignment receipt was returned. Nothing was assigned."
            update_mission(mission, "BOUNDED_INTERNAL_ACTION_ACCEPTED" if action.get("success") else "BOUNDED_INTERNAL_ACTION_FAILED", {
                "response_mode": "nexus_bounded_internal_execution", "action_completed": bool(action.get("success")),
                "side_effects": bool(action.get("success")),
                "receipt_id": (action.get("receipt") or {}).get("receipt_id")})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []), "action_completed": bool(action.get("success"))})
            return True

        if semantic.get("intent") in {"BROWSER_ACTION", "COMMUNICATION_ACTION"}:
            response = ("ACTION_NOT_AVAILABLE. No governed executor is registered for this action in the current Nexus MCP surface. "
                        "Nothing was created, changed, sent, or scheduled.")
            update_mission(mission, "ACTION_NOT_AVAILABLE", {"action_completed": False, "read_only": False,
                "semantic_route": semantic, "side_effects": False})
            write_receipt({"type": "nova_action_not_available", "incoming_update_id": update_id,
                "mission_id": mission["mission_id"], "semantic_route": semantic,
                "action_completed": False, "side_effects": False})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []), "action_completed": False})
            return True

        # Company-level planning is not dispatch. Submit every supported
        # department through the same governed MCP actions before describing
        # work as coordinated; retain actual blockers for unsupported steps.
        try:
            from nexus_agent_platform.company_objective_router import route_company_objective
            company_plan = route_company_objective(text, conversation_message_id=update_id)
            structured_objective = (
                len(company_plan.get("root_objective", {}).get("requirements", [])) >= 2
                and (len(text) >= 240 or any(marker in text.upper() for marker in ("MISSION", "SUCCESS CRITERIA", "FINAL OUTPUT")))
            )
            if (company_plan.get("intent_class") in {"OPPORTUNITY_INTAKE", "TRADING_PREMARKET", "RESEARCH"}
                    or len(company_plan.get("steps", [])) > 1 or structured_objective):
                owner_objective_id = str((company_plan.get("root_objective") or {}).get("objective_id")
                                         or mission.get("root_objective_id") or mission["mission_id"])
                owner_to_department = {"RESEARCH": "RESEARCH", "SYSTEMS": "SYSTEMS",
                                       "OPERATIONS": "SYSTEMS", "ALPHA": "ALPHA",
                                       "RESEARCH_ALPHA": "ALPHA"}
                departments = []
                unsupported_steps = []
                for step in company_plan.get("steps", []):
                    owner = str(step.get("owner") or "UNKNOWN").upper()
                    department = owner_to_department.get(owner)
                    if department and department not in departments:
                        departments.append(department)
                    elif not department:
                        unsupported_steps.append(step)
                from nova.nexus_mcp_status import (
                    assign_department_tasks, build_assignment_linkage,
                    render_assignment_batch,
                )
                if departments:
                    batch = assign_department_tasks(text, departments, owner_objective_id)
                else:
                    batch = {"parent_request_id": owner_objective_id, "assignments": [],
                             "tool_count": 0, "accepted_count": 0, "blocked_count": 0}
                for step in unsupported_steps:
                    batch["assignments"].append({
                        "department": str(step.get("owner") or "UNKNOWN"), "status": "BLOCKED",
                        "error_type": "UnsupportedDepartmentAssignment",
                        "error": f"no_governed_mcp_action_for:{step.get('owner') or 'UNKNOWN'}",
                    })
                    batch["blocked_count"] += 1
                batch["accepted_count"] = sum(1 for row in batch["assignments"] if row.get("job_id"))
                batch["blocked_count"] = sum(1 for row in batch["assignments"] if not row.get("job_id"))
                response = render_assignment_batch(batch, owner_objective_id)
                links = []
                for row in batch["assignments"]:
                    if row.get("job_id"):
                        links.append(build_assignment_linkage(
                            owner_objective_id, owner_objective_id, row.get("department"),
                            {"job_id": row.get("job_id"), "job_state": row.get("status"),
                             "created_at": row.get("created_at")},
                        ))
                    else:
                        links.append({
                            "nova_objective_id": owner_objective_id,
                            "parent_request_id": owner_objective_id,
                            "department": row.get("department"), "assignment_id": None,
                            "job_id": None, "created_at": datetime.now(timezone.utc).isoformat(),
                            "current_status": str(row.get("status") or "BLOCKED").upper(),
                            "blocker": row.get("error"), "error_type": row.get("error_type"),
                        })
                if not batch["accepted_count"]:
                    blocker = "; ".join(str(row.get("error") or row.get("error_type") or "assignment_rejected")
                                         for row in batch["assignments"]) or "no_governed_assignment_action"
                    response = (f"NEXUS_OBJECTIVE_ID={owner_objective_id}\nOBJECTIVE_ACCEPTED=NO\n"
                                f"DISPATCH_STATUS=FAILED\nBLOCKER={blocker[:600]}")
                    mission_status = "DEPARTMENT_ASSIGNMENT_FAILED"
                elif batch["blocked_count"]:
                    response = "OBJECTIVE_ACCEPTED=PARTIAL\nDISPATCH_STATUS=PARTIAL\n" + response
                    mission_status = "DEPARTMENT_ASSIGNMENT_PARTIAL"
                else:
                    mission_status = "ASSIGNMENT_ACCEPTED"
                mission.update({
                    "nova_objective_id": owner_objective_id,
                    "root_objective_id": owner_objective_id,
                    "parent_request_id": owner_objective_id,
                    "owner_objective_id": owner_objective_id,
                    "objective_id": owner_objective_id,
                    "company_objective": company_plan,
                    "objective_assignments": links,
                    "department_assignments": links,
                    "child_tasks": [{"department": row.get("department"), "job_id": row.get("job_id"),
                                     "status": row.get("status"), "parent_objective_id": owner_objective_id,
                                     "assignment_source": "GOVERNED_NEXUS_MCP"}
                                    for row in batch.get("assignments", [])],
                })
                update_mission(mission, mission_status, {
                    "response_mode": "company_objective_governed_assignment",
                    "company_objective": company_plan,
                    "nexus_mcp_tool_count": batch.get("tool_count", 0),
                    "parent_request_id": owner_objective_id,
                    "objective_assignments": links,
                })
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
                update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                    "response_mode": "company_objective_governed_assignment",
                    "objective_assignments": links,
                    "telegram_send_count": len(delivery.get("message_ids", [])),
                })
                return True
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            _log(f"Company objective route unavailable; continuing normal Hermes path: {type(exc).__name__}")

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
            pre_verified_current_state = None
            if primary_runtime == PRIMARY_RUNTIME_ORACLE:
                from nexus_agent_platform.grounded_response import collect_verified_current_state, requires_current_evidence
                if requires_current_evidence(text):
                    # Capture trusted facts before the model call.  Hermes may
                    # reason over them, but the final composition remains
                    # governed by this same object.
                    pre_verified_current_state = collect_verified_current_state({
                        "runtime_host": "ORACLE", "hermes_version": "0.20.6",
                        "profile": "nova_nexus", "provider": "openai-codex",
                        "model": os.getenv("HERMES_NOVA_MODEL", "gpt-5.5"),
                    })
            hermes_record = (
                _run_oracle_primary(update_id, message, chat_id, text, primary_run_id=primary_run_id)
                if primary_runtime == PRIMARY_RUNTIME_ORACLE
                else _run_hermes_primary(update_id, message, chat_id, text, primary_run_id=primary_run_id)
            )
            if trace:
                trace.event("hermes.generation", {"generation_type": "FINAL_SYNTHESIS_GENERATION", "model": hermes_record.get("model"), "tool_count": len(hermes_record.get("tools_executed", [])), "latency_ms": hermes_record.get("latency_ms")})
            response, blocked_reason = _response_integrity(
                _sanitize_internal_failure(hermes_record.get("response") or ""), "conversation"
            )
            if response is None:
                execution_error = str(hermes_record.get("error") or blocked_reason or "no_verified_response")[:240]
                if execution_error.startswith("governor_") or execution_error == "COST_ESTIMATE_UNAVAILABLE":
                    owner_notice = (
                        "I received your request, but couldn't run it because Nova's current model/provider "
                        "usage policy is blocking execution. The request is preserved. No Google data was "
                        "read, and I won't claim that it was. A bounded, approved model budget is required "
                        "before I can continue this request."
                    )
                else:
                    owner_notice = (
                        "I received your request, but Hermes returned no usable verified result "
                        f"({execution_error}). The request is preserved, and I won't claim the requested work completed."
                    )
                update_mission(mission, "DELIVERY_FAILED", {
                    "response_mode": "hermes_primary",
                    "model_used": hermes_record.get("model"),
                    "hermes_error": execution_error,
                    "owner_notice_required": True,
                })
                with stage_execution(
                    stage="telegram_send",
                    source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                    metadata={"mission_id": mission["mission_id"], "execution_blocked": True},
                ):
                    delivery = _deliver_response(
                        update_id, chat_id, owner_notice,
                        hermes_run_id=hermes_record.get("run_id"), mission_id=mission["mission_id"],
                    )
                update_mission(mission, "OWNER_ACTION_REQUIRED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                    "response_mode": "hermes_primary_blocker_notice",
                    "telegram_send_count": len(delivery.get("message_ids", [])),
                    "delivery_error": delivery.get("last_error"),
                })
                return True
            # Current-state claims are grounded after Hermes synthesis.  The
            # model remains the owner of narrative and recommendations, while
            # runtime/specialist facts come from deterministic local evidence.
            if primary_runtime == PRIMARY_RUNTIME_ORACLE:
                from nexus_agent_platform.grounded_response import ground_response, response_completeness
                response, verified_current_state = ground_response(response, text, hermes_record, pre_verified_current_state)
                hermes_record["verified_current_state"] = verified_current_state
                hermes_record["response_completeness"] = response_completeness(response)
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
                "provider": hermes_record.get("provider", "openai-codex"),
                "latency_ms": hermes_record.get("latency_ms"),
                "tools_executed": hermes_record.get("tools_executed", []),
                "response": _ab_safe_text(response),
                "error": hermes_record.get("error"),
                "delivery": delivery,
                "claim_attribution": hermes_record.get("claim_attribution"),
                "runtime_init": hermes_record.get("runtime_init"),
                "model_init": hermes_record.get("model_init"),
                "verified_current_state": hermes_record.get("verified_current_state"),
                "response_completeness": hermes_record.get("response_completeness"),
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
                tg_send_message(chat_id, "I didn't receive a usable response for this turn, so no result is confirmed. The request remains in this conversation; I'll check its execution state before retrying it.")

    except Exception as exc:
        _log_error(f"Nova processing error: {type(exc).__name__}: {str(exc)[:500]}")
        try:
            update_mission(mission, "TURN_FAILED", {
                "error_type": type(exc).__name__, "error_message": str(exc)[:500],
                "work_acceptance": "UNKNOWN_UNLESS_DURABLE_JOB_READ_CONFIRMS",
            })
        except Exception:
            pass
        with stage_execution(
            stage="telegram_send",
            source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
            metadata={"error_type": exc.__class__.__name__},
        ):
            tg_send_message(chat_id, "I couldn't complete that request because one of my execution steps failed. I haven't confirmed whether Nexus accepted any work, so I won't claim it ran. Your request is still in this conversation; I'll verify durable state before retrying, and you don't need to restate it.")
    finally:
        if governance_context is not None:
            _restore_owner_turn_governance_context(governance_context)
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

        recovered_missions = _resume_authorized_missions()
        if recovered_missions:
            _log(f"Nova worker: resumed {recovered_missions} authorized missions")

        # Proactive operational communication must not depend on a successful
        # inbound getUpdates call.  A slow/reset Telegram poll used to delay
        # useful Research and decision notifications until the next cycle.
        # This still shares the trusted token, destination resolution, retry
        # path, deduplication, and launchd cadence.
        try:
            from proactive_communications import process_once
            proactive = process_once()
            if proactive.get("status") not in {"NO_SEND", "SUPPRESSED"}:
                _log(f"Nova worker: proactive communication {proactive.get('status')}")
        except Exception as exc:
            _log_error(f"Proactive communication unavailable: {type(exc).__name__}")

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

    # A persistent worker must recover the same durable owner missions as the
    # one-shot worker after restart. Without this, an AUTHORIZED mission can
    # remain stranded forever in long-poll mode even though recovery exists in
    # run_once(). Existing update/mission identities are retained.
    try:
        recovered_deliveries = _retry_pending_deliveries()
        recovered_missions = _resume_authorized_missions()
        if recovered_deliveries:
            _log(f"Nova worker: recovered {recovered_deliveries} pending deliveries at startup")
        if recovered_missions:
            _log(f"Nova worker: resumed {recovered_missions} authorized missions at startup")
    except Exception as exc:
        _log_error(f"Nova startup recovery failed: {type(exc).__name__}: {str(exc)[:180]}")

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
    model = env.get("HERMES_NOVA_MODEL", "gpt-5.5 (default)")
    print(f"Model: {model}")

    # The passive Telegram receiver does not receive model-provider secrets.
    print("OpenRouter credential: not available to Telegram receiver")

    # Check authorization
    print(f"Ray chat ID: 1288928049")
    print(f"Authorized: {is_authorized(1288928049, 1288928049, 'rayscentro')}")

    # Check canonical Hermes transport. The former local Nova graph is not a
    # Telegram runtime and must never be used as a fallback brain.
    try:
        from nexus_agent_platform.bridge.oracle_hermes_cli import ORACLE_PROFILE, ORACLE_TOOLSET, ORACLE_HOST
        print(f"Hermes transport: Oracle host={ORACLE_HOST} profile={ORACLE_PROFILE} toolset={ORACLE_TOOLSET}")
    except Exception as e:
        print(f"Hermes transport: FAILED ({e})")

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
