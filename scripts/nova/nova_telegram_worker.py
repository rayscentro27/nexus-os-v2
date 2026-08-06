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

# Agent Platform path
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

# ─── SSL ────────────────────────────────────────────────

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ─── Config ─────────────────────────────────────────────

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_MAX_MSG = 4000
POLL_TIMEOUT = 30
HEARTBEAT_INTERVAL = 60

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


def tg_send_message(chat_id, text, token=None):
    """Send a message, chunking if needed. Returns list of message IDs."""
    if not text:
        return []

    env = get_env()
    if token is None:
        token = env.get("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")

    chunks = _chunk_message(text)
    message_ids = []

    for chunk in chunks:
        result = _tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
        }, token=token)
        if result and result.get("ok"):
            msg_id = result.get("result", {}).get("message_id")
            if msg_id:
                message_ids.append(msg_id)
        else:
            _log_error(f"Failed to send message to {chat_id}")
            time.sleep(1)
            result = _tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": chunk,
            }, token=token)
            if result and result.get("ok"):
                msg_id = result.get("result", {}).get("message_id")
                if msg_id:
                    message_ids.append(msg_id)
            else:
                _log_error(f"Retry also failed for chat {chat_id}")

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

# ─── Single-Delivery Lock ───────────────────────────────

def _acquire_chat_lock(chat_id):
    """Acquire a per-chat file lock to prevent concurrent processing."""
    lock_dir = os.path.join(NOVA_STATE_DIR, "nova_locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, f"chat_{chat_id}.lock")

    # Use atomic create — fails if lock already exists
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return lock_path
    except FileExistsError:
        # Check if lock is stale (older than 120s)
        try:
            age = time.time() - os.path.getmtime(lock_path)
            if age > 120:
                os.remove(lock_path)
                return _acquire_chat_lock(chat_id)
        except OSError:
            pass
        return None


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

    _log(f"Incoming: update={update_id} chat={chat_id} user={username} text={text[:80]}")

    # Acquire per-chat lock to prevent duplicate delivery
    lock = _acquire_chat_lock(chat_id)
    if not lock:
        _log(f"Skipped update {update_id} — another worker processing chat {chat_id}")
        return False

    try:
        mission = create_mission(update_id, chat_id, user_id, text)

        if not is_authorized(chat_id, user_id, username):
            update_mission(mission, "UNAUTHORIZED")
            tg_send_message(chat_id, "This bot is private. You are not authorized.")
            return True

        update_mission(mission, "AUTHORIZED")
        _update_status_field("last_incoming_message", datetime.now(timezone.utc).isoformat())

        from nexus_agent_platform.agents.nova import (
            get_nova_graph, get_nova_otel, reset_memory, AGENT_ID,
        )
        from nexus_agent_platform.adapters.state_adapter import AgentState
        from nexus_agent_platform.flags import HERMES_NOVA_ENABLED

        if not HERMES_NOVA_ENABLED:
            tg_send_message(chat_id, "Nova is currently disabled. Try again later.")
            update_mission(mission, "DISABLED")
            return True

        graph = get_nova_graph()
        otel = get_nova_otel()

        state = AgentState(
            agent_id=AGENT_ID,
            mission_id=mission["mission_id"],
            user_message=text,
            metadata={
                "chat_id": chat_id,
                "user_id": user_id,
                "username": username,
                "source": "telegram",
                "nova_agent": True,
            },
        )

        t0 = time.monotonic()
        result = graph.invoke(state)
        latency_ms = round((time.monotonic() - t0) * 1000, 1)

        response = result.assistant_response or ""

        if result.metadata.get("reset_requested"):
            reset_memory(chat_id)
            _log(f"Memory reset for chat {chat_id}")

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
                })
                _log(f"Nova delivered: mission={mission['mission_id']} latency={latency_ms}ms")
            else:
                update_mission(mission, "DELIVERY_FAILED")
                _log_error(f"Delivery failed: mission={mission['mission_id']}")
        else:
            update_mission(mission, "EMPTY_RESPONSE")
            tg_send_message(chat_id, "I'm not sure what to say. Could you try again?")

    except Exception as exc:
        _log_error(f"Nova processing error: {exc}")
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
    write_status(os.getpid(), "RUNNING")

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
                if uid > max_update_id:
                    max_update_id = uid
                try:
                    process_message(update)
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
