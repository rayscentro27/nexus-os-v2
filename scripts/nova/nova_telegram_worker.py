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
NOVA_CONTEXT_DIR = os.path.join(NOVA_STATE_DIR, "nova_context_snapshots")
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


def _previous_delivered_turn(chat_id, before_update_id):
    """Read the latest delivered exchange for this exact chat, never memory search."""
    try:
        candidate_ids = sorted((int(name[:-5]) for name in os.listdir(NOVA_DELIVERY_DIR)
                                if name.endswith(".json") and name[:-5].isdigit()
                                and int(name[:-5]) < int(before_update_id)), reverse=True)
    except (OSError, TypeError, ValueError):
        return None
    for previous_id in candidate_ids:
        delivery = _load_delivery(previous_id) or {}
        if str(delivery.get("chat_id")) != str(chat_id) or delivery.get("state") != "DELIVERED":
            continue
        mission = {}
        mission_id = str(delivery.get("mission_id") or "")
        if mission_id:
            try:
                with open(os.path.join(NOVA_MISSIONS_DIR, f"{mission_id}.json"), encoding="utf-8") as handle:
                    mission = json.load(handle)
            except (OSError, ValueError):
                mission = {}
        answer = str(delivery.get("response") or "").strip()
        if answer:
            return {"update_id": previous_id, "user_text": str(mission.get("original_message") or ""),
                    "assistant_text": answer[:4000], "mission_id": mission_id or None}
    return None


def _context_snapshot(update_id, chat_id, user_id, text, lineage=None):
    """Build and persist a bounded context authority snapshot before routing."""
    from nova.context_authority import resolve_context
    from nova import operator_v1
    previous = _previous_delivered_turn(chat_id, update_id) or {}
    try:
        active = operator_v1.status_read(None, owner_id=str(user_id), exclude_mission_id="")
        if active is None:
            active = {"status": "CURRENT_STATE_UNAVAILABLE"}
    except Exception as exc:
        active = {"status": "CURRENT_STATE_UNAVAILABLE", "error": type(exc).__name__}
    try:
        completed = operator_v1.recent_completed_status(str(user_id))
    except Exception:
        completed = None
    authoritative = completed
    # If the previous delivered answer named a completed mission, bind this
    # turn to that exact durable snapshot. Never recover its current/final state
    # by searching old event wording or Hermes session memory.
    previous_text = str(previous.get("assistant_text") or "")
    named_mission = re.search(r"\b(?:nova_)?\d{8}T\d{6}_\d+\b", previous_text)
    if named_mission:
        candidate_id = named_mission.group(0)
        if not candidate_id.startswith("nova_"):
            candidate_id = "nova_" + candidate_id
        try:
            candidate = operator_v1.get_authoritative_mission_snapshot(candidate_id, owner_id=str(user_id))
            if candidate and candidate.get("success_verified"):
                authoritative = {**candidate, "mission_success_verified": True}
                if completed and completed.get("mission_id") == candidate_id:
                    authoritative["objective"] = completed.get("objective")
        except Exception:
            pass
    def compact_mission(value):
        if not isinstance(value, dict):
            return None
        current_step = value.get("current_step")
        if isinstance(current_step, dict):
            current_step = {key: current_step.get(key) for key in ("step_id", "goal", "status", "sequence")}
        return {key: value.get(key) for key in ("mission_id", "objective", "status", "mission_success_verified",
                "completed_at", "updated_at", "current_step", "last_action", "next_step", "waiting_on",
                "recovery_state", "read_only", "no_mutation", "success_verified", "terminal_reason",
                "final_outcome", "success_condition", "success_evidence", "final_entity_state",
                "source_of_truth", "active", "historical_problem_events") if key in value} | {
                    **({"current_step": current_step} if current_step is not None else {}),
                    **({"entity_lineage": value.get("entity_lineage", [])[:8]} if isinstance(value.get("entity_lineage"), list) else {})}
    active = compact_mission(active)
    completed = compact_mission(completed)
    authoritative = compact_mission(authoritative)
    thread = {"previous_user_text": previous.get("user_text"), "previous_assistant_text": previous.get("assistant_text")} if previous else None
    resolution = resolve_context(text, previous_turn=previous, active_mission=active,
        recent_completed_mission=completed, authoritative_mission_snapshot=authoritative,
        thread_context=thread, entity_lineage=lineage or {})
    snapshot = {
        "message_id": str(update_id), "current_text": str(text)[:3000],
        "previous_user_text": previous.get("user_text"),
        "previous_assistant_text": previous.get("assistant_text"),
        "previous_update_id": previous.get("update_id"),
        "active_mission_id": active.get("mission_id") if active else None,
        "active_mission": active,
        "last_completed_mission_id": completed.get("mission_id") if completed else None,
        "last_completed_mission": completed,
        "authoritative_mission_snapshot": authoritative,
        "thread_objective": thread,
        "resolved_referent": resolution.get("resolved_referent"),
        "resolution_source": resolution.get("context_source"),
        "resolution_priority": resolution.get("context_priority"),
        "reference_type": resolution.get("reference_type"),
    }
    try:
        os.makedirs(NOVA_CONTEXT_DIR, exist_ok=True)
        with open(os.path.join(NOVA_CONTEXT_DIR, f"{update_id}.json"), "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2, default=str)
    except OSError as exc:
        _log(f"Context snapshot persistence unavailable: {type(exc).__name__}")
    return snapshot


def _authoritative_mission_answer(snapshot):
    """Render narrow mission-state answers directly from the read-only snapshot."""
    if not isinstance(snapshot, dict):
        return None
    reference_type = str(snapshot.get("reference_type") or "")
    active = snapshot.get("active_mission") or {}
    completed = snapshot.get("last_completed_mission") or {}
    authoritative = snapshot.get("authoritative_mission_snapshot") or completed
    if reference_type == "CURRENT_STATE":
        if str(active.get("status") or "").upper() == "NO_ACTIVE_MISSION":
            return "I don't currently have an active mission."
        if active.get("mission_id"):
            step = active.get("current_step") or {}
            current_step = step.get("goal") if isinstance(step, dict) else step
            suffix = f" Current step: {current_step}." if current_step else ""
            return f"I'm working on {active.get('objective') or active['mission_id']} (mission {active['mission_id']}; status {active.get('status')}).{suffix}"
        return None
    if reference_type == "RECENT_COMPLETED_WORK" and completed.get("success_verified"):
        entity = completed.get("final_entity_state") or {}
        if entity.get("entity_type") == "RESEARCH_CASE":
            outcome = (f"The same Research case {entity.get('entity_id')} reached {entity.get('status')}: "
                f"{entity.get('source_count')} sources, {entity.get('synthesis_count')} syntheses, "
                f"{entity.get('open_question_count')} open questions, and a persisted {entity.get('recommendation')} recommendation.")
        else:
            outcome = str(completed.get("final_outcome") or "The requested final state was independently verified.")
        return (f"The last verified completed mission was {completed.get('mission_id')}: "
            f"{completed.get('objective')} Final outcome: {outcome} "
            f"The mission success condition was: {completed.get('success_condition')}")
    if reference_type == "COMPLETION_EXPLANATION" and authoritative.get("success_verified"):
        entity = authoritative.get("final_entity_state") or {}
        evidence = authoritative.get("success_evidence") or {}
        if entity.get("entity_type") == "RESEARCH_CASE":
            return (f"It was considered complete because the mission's success condition was independently verified on the same case {entity.get('entity_id')}: "
                f"{entity.get('status')}, {entity.get('source_count')} sources, {entity.get('synthesis_count')} syntheses, "
                f"{entity.get('open_question_count')} open questions, and a persisted {entity.get('recommendation')} recommendation. "
                "The earlier worker failure remains historical evidence; its original Python exception was not captured, and that missing exception was not claimed as resolved.")
        return (f"It was considered complete because the persisted success condition was verified: "
            f"{authoritative.get('success_condition')} Final outcome: {authoritative.get('final_outcome')}")
    if reference_type == "HISTORICAL_MISSION_EVENTS" and authoritative.get("mission_id"):
        events = authoritative.get("historical_problem_events") or []
        evidence = authoritative.get("success_evidence") or {}
        if events:
            history = ", ".join(dict.fromkeys(str(event.get("event_type")) for event in events))
            outcome = "It later reached a verified completed state." if authoritative.get("success_verified") else "Its current terminal state is not verified as complete."
            detail = authoritative.get("final_outcome") or ""
            return (f"Yes. Its history includes {history}. {detail} {outcome} "
                f"The final state is {authoritative.get('status')}; earlier failures are historical, not the final status.").strip()
        return ("I found no recorded failure, recovery, capability-gap, or blocked events for that mission. "
            f"Its authoritative status is {authoritative.get('status')}.")
    return None


def _wave1_route_decision(text, snapshot):
    """Resolve only R24.current and R24.last_completed through the prepared switch.

    The legacy response renderer and authoritative read data remain unchanged.
    A canonical decision failure falls back to that same read-only renderer for
    this update and is logged for immediate config rollback/diagnosis.
    """
    reference = str((snapshot or {}).get("reference_type") or "")
    route_id = {"CURRENT_STATE": "R24.current",
                "RECENT_COMPLETED_WORK": "R24.last_completed"}.get(reference)
    if not route_id:
        return None, None, False, None
    try:
        from nova.operator_cutover_switch import read_route_mode
        mode = read_route_mode(route_id)
    except Exception as exc:
        _log(f"WAVE1_SWITCH_READ_FAILED route={route_id} error={type(exc).__name__}; using legacy handler")
        return route_id, "LEGACY_LIVE", False, None
    if mode == "LEGACY_LIVE":
        return route_id, mode, False, None
    active = snapshot.get("active_mission") or {}
    completed = snapshot.get("last_completed_mission") or {}
    previous = {"user_text": snapshot.get("previous_user_text"),
                "assistant_text": snapshot.get("previous_assistant_text"),
                "update_id": snapshot.get("previous_update_id")}
    try:
        from nova import operator_v1
        decision = operator_v1.decide_read_only_route(
            text, active_mission=active, completed_mission=completed,
            previous_turn=previous, entity_lineage={},
            route_id=route_id, shadow_only=(mode == "SHADOW"),
        )
        decision = dict(decision)
        valid = (decision.get("ACTION_CLASS") == "READ"
                 and decision.get("MISSION_REQUIRED") is False
                 and decision.get("CREATE_NEW_ENTITY") is False
                 and decision.get("SIDE_EFFECTS") == 0
                 and decision.get("ROUTE_ID") == route_id
                 and decision.get("DECISION_OWNER") == ("NOVA_OPERATOR" if mode == "CANONICAL" else "SHADOW")
                 and decision.get("SHADOW_ONLY") is (mode != "CANONICAL"))
        if route_id == "R24.current":
            valid = valid and decision.get("CURRENT_STATE") == str(active.get("status") or "")
        else:
            valid = (valid and decision.get("TARGET_ENTITY_ID") == completed.get("mission_id")
                     and decision.get("FINAL_STATE") == "COMPLETE"
                     and bool(completed.get("success_verified")))
        _log(f"WAVE1_DECISION route={route_id} mode={mode} owner={'CANONICAL_OPERATOR' if mode == 'CANONICAL' and valid else 'SHADOW_ONLY' if mode == 'SHADOW' else 'LEGACY_FALLBACK'} decision={decision.get('ACTION_CLASS')} valid={valid}")
        return route_id, mode, bool(mode == "CANONICAL" and valid), decision
    except Exception as exc:
        _log(f"WAVE1_OPERATOR_DECISION_FAILED route={route_id} mode={mode} error={type(exc).__name__}; using legacy handler")
        return route_id, mode, False, None


def _operator_read_only_answer(decision, snapshot):
    """Use the Operator's canonical read decision, then the existing renderer adapter."""
    if not isinstance(decision, dict):
        return None
    if (decision.get("DECISION_OWNER") != "NOVA_OPERATOR"
            or decision.get("SHADOW_ONLY") is not False
            or decision.get("ACTION_CLASS") != "READ"
            or decision.get("MISSION_REQUIRED") is not False
            or decision.get("CREATE_NEW_ENTITY") is not False
            or decision.get("SIDE_EFFECTS") != 0):
        return None
    route_id = decision.get("ROUTE_ID")
    active = (snapshot or {}).get("active_mission") or {}
    completed = (snapshot or {}).get("last_completed_mission") or {}
    if route_id == "R24.current":
        if decision.get("CURRENT_STATE") != str(active.get("status") or ""):
            return None
    elif route_id == "R24.last_completed":
        if (decision.get("TARGET_ENTITY_ID") != completed.get("mission_id")
                or decision.get("FINAL_STATE") != "COMPLETE"
                or not completed.get("success_verified")):
            return None
    else:
        return None
    # Response wording and source records remain the established read-only adapter.
    return _authoritative_mission_answer(snapshot)


def _wave2_action_route(text, lineage, previous_turn=None):
    """Resolve bounded internal note/file CRUD routes under a per-route switch."""
    try:
        from nova.operator_shadow import decide_wave2_action
        from nova.operator_cutover_switch import read_route_mode
        decision = decide_wave2_action(text, lineage=lineage or {}, previous_turn=previous_turn or {})
        if not decision:
            return None, None, None, False
        route_id = str(decision.get("ROUTE_ID") or "")
        if isinstance(lineage, dict):
            decision["CREATED_BY_STEP"] = lineage.get("created_by_step")
            decision["PARENT_ENTITY_IF_ANY"] = lineage.get("parent_entity_id")
        mode = read_route_mode(route_id)
        route_modes = {f"{decision.get('ENTITY_TYPE')}_{('READ' if action == 'VERIFY_ABSENT' else action)}": read_route_mode(
            f"{decision.get('ENTITY_TYPE')}_{('READ' if action == 'VERIFY_ABSENT' else action)}")
            for action in decision.get("ACTION_SEQUENCE", [decision.get("ACTION_CLASS")])}
        exact = (decision.get("DECISION_OWNER") == "NOVA_OPERATOR"
                 and decision.get("ENTITY_TYPE") in {"NOTE", "FILE"}
                 and decision.get("ACTION_CLASS") in {"CREATE", "READ", "UPDATE", "DELETE"}
                 and decision.get("SIDE_EFFECTS") == 0)
        canonical = bool(exact and route_modes and all(value == "CANONICAL" for value in route_modes.values()))
        if mode == "SHADOW" or any(value == "SHADOW" for value in route_modes.values()):
            decision = {**decision, "DECISION_OWNER": "SHADOW", "SHADOW_ONLY": True}
        _log(f"WAVE2_DECISION route={route_id} mode={mode} sequence_modes={route_modes} owner={'CANONICAL_OPERATOR' if canonical else decision.get('DECISION_OWNER')} action={decision.get('ACTION_CLASS')} entity={decision.get('ENTITY_ID') or 'NEW'} exact={exact}")
        return route_id, mode, decision, canonical
    except Exception as exc:
        _log(f"WAVE2_SWITCH_OR_DECISION_FAILED error={type(exc).__name__}; existing route retained")
        return None, None, None, False


def _wave3_case_resolution_route(text, lineage, context_snapshot, owner_id=None):
    """Resolve an existing Research case under Wave 3 decision-only switches.

    This helper never calls MCP or creates Operator work. Research writes and
    continuation execution remain on their existing routes in this phase.
    """
    try:
        from nova.operator_shadow import decide_research_case_resolution
        from nova.operator_cutover_switch import read_route_mode
        snapshot = context_snapshot if isinstance(context_snapshot, dict) else {}
        active = snapshot.get("active_mission") if isinstance(snapshot.get("active_mission"), dict) else {}
        previous = {key: snapshot.get(f"previous_{key}") for key in ("user_text", "assistant_text")}
        previous["update_id"] = snapshot.get("previous_update_id")
        decision = decide_research_case_resolution(
            text, lineage=lineage or {}, previous_turn=previous,
            active_mission=active,
        )
        if not decision:
            return None, None, None, False
        route_modes = {route: read_route_mode(route) for route in decision["ROUTE_IDS"]}
        mode = "CANONICAL" if all(value == "CANONICAL" for value in route_modes.values()) else (
            "SHADOW" if any(value == "SHADOW" for value in route_modes.values()) else "LEGACY_LIVE")
        if mode != "LEGACY_LIVE" and decision.get("DECISION") == "UNRESOLVED" and owner_id is not None:
            # Final-priority resolution uses only the exact durable Research
            # lineage ledger; multiple distinct cases remain unresolved.
            from nova import operator_v1
            durable = operator_v1.recent_research_case_lineage(str(owner_id))
            if durable and durable.get("case_id"):
                resolution_lineage = dict(lineage or {})
                resolution_lineage["research_case_id"] = durable["case_id"]
                resolution_lineage["research_case_lineage"] = durable
                decision = decide_research_case_resolution(
                    text, lineage=resolution_lineage, previous_turn=previous,
                    active_mission=active,
                )
            elif durable and durable.get("resolution_status") == "AMBIGUOUS":
                decision = {**decision, "DECISION": "UNRESOLVED",
                            "RESOLUTION_SOURCE": "AMBIGUOUS_DURABLE_RESEARCH_LINEAGE",
                            "AMBIGUOUS_CASE_IDS": durable.get("ambiguous_case_ids", [])}
        if mode != "LEGACY_LIVE" and decision.get("TARGET_ENTITY_ID") and owner_id is not None:
            from nova import operator_v1
            exact_lineage = operator_v1.recent_research_case_lineage(
                str(owner_id), case_id=str(decision["TARGET_ENTITY_ID"]))
            if exact_lineage and all(exact_lineage.get(key) for key in
                    ("case_id", "objective_id", "project_id", "durable_job_id")):
                decision = {**decision, "RESEARCH_LINEAGE": exact_lineage}
            else:
                decision = {**decision, "RESEARCH_LINEAGE_ERROR": "EXACT_RESEARCH_LINEAGE_INCOMPLETE"}
        decision = dict(decision)
        decision["ROUTE_MODES"] = route_modes
        decision["ROUTE_MODE"] = mode
        decision["SHADOW_ONLY"] = mode != "CANONICAL"
        canonical = bool(mode == "CANONICAL" and decision.get("DECISION") == "READ_CASE"
                         and decision.get("TARGET_ENTITY_ID") and decision.get("SIDE_EFFECTS") == 0
                         and isinstance(decision.get("RESEARCH_LINEAGE"), dict))
        _log("WAVE3_CASE_RESOLUTION " + json.dumps({
            "mode": mode, "decision": decision.get("DECISION"),
            "target_case": decision.get("TARGET_ENTITY_ID"),
            "resolution_source": decision.get("RESOLUTION_SOURCE"),
            "side_effects": decision.get("SIDE_EFFECTS"),
        }, ensure_ascii=False, sort_keys=True))
        return mode, decision, route_modes, canonical
    except Exception as exc:
        _log(f"WAVE3_CASE_RESOLUTION_FAILED error={type(exc).__name__}; existing route retained")
        return None, None, None, False


def _wave3_research_controller_catalog(live_catalog):
    """Restrict canonical R15 execution to the production-bound Room controller."""
    contracts = {
        "nexus_get_research_controller_status": ("READ", {"case_id", "objective_id", "project_id", "durable_job_id"}),
        "nexus_get_research_controller_open_questions": ("READ", {"case_id", "objective_id", "project_id", "durable_job_id"}),
        "nexus_get_research_controller_results": ("READ", {"case_id", "objective_id", "project_id", "durable_job_id"}),
        "nexus_research_controller_continue": ("WRITE", {"case_id", "objective_id", "project_id", "durable_job_id", "instruction"}),
        "nexus_research_controller_advisor_request": ("WRITE", {"case_id", "objective_id", "project_id", "durable_job_id", "question"}),
    }
    selected = []
    for name, (expected_class, required) in contracts.items():
        row = next((item for item in live_catalog if item.get("tool_name") == name
                    and item.get("source_id") == "nexus_mcp_remote"), None)
        schema = row.get("input_schema") if isinstance(row, dict) else None
        properties = schema.get("properties") if isinstance(schema, dict) else None
        if (not row or row.get("capability_id") != f"mcp:nexus_mcp_remote:{name}"
                or not row.get("authorized") or row.get("read_write_class") != expected_class
                or not isinstance(properties, dict) or not required.issubset(properties)):
            raise RuntimeError("WAVE3_RESEARCH_ROOM_CONTROLLER_CONTRACT_MISSING:" + name)
        selected.append(row)
    return selected


def _wave3_operator_mission_for_case(operator_module, owner_id, lineage):
    """Resume an Operator mission only when its exact Research case matches.

    Chat context can contain unrelated note/file/project IDs from earlier
    turns. Those must never cause a Research continuation to attach to an
    unrelated mission that happens to own one of those stale entities.
    """
    case_id = lineage.get("case_id") if isinstance(lineage, dict) else None
    if not case_id:
        return None
    return operator_module.mission_for_entity(str(owner_id), [str(case_id)])


def _wave3_explicit_research_lineage(text):
    """Read a fully explicit exact lineage tuple from a bounded canary/request."""
    value = str(text or "")
    aliases = {
        "case_id": r"(?:CASE_ID|case_id)",
        "objective_id": r"(?:OBJECTIVE_ID|objective_id)",
        "project_id": r"(?:PROJECT_ID|project_id)",
        "durable_job_id": r"(?:DURABLE_JOB_ID|JOB_ID|durable_job_id|job_id)",
    }
    result = {}
    for key, label in aliases.items():
        match = re.search(r"\b" + label + r"\s*[:=]\s*([A-Za-z0-9_.:-]{4,160})", value)
        if not match:
            return None
        result[key] = match.group(1)
    if (not re.fullmatch(r"rcase_[A-Za-z0-9_.:-]{4,120}", result["case_id"], re.I)
            or not result["objective_id"].startswith("nova_research_")
            or not result["project_id"].startswith("nova_research_work_")
            or not result["durable_job_id"].startswith("job_")):
        return None
    return result


def _wave3_research_continuation_decision(text, resolution, *, owner_id=None):
    """Make a read-only Operator continuation decision for one exact case.

    This selects and verifies the target case, reads its current snapshot, and
    chooses the next approved capability. It never executes that capability;
    the existing Operator mission runner remains responsible for governed
    execution and postcondition verification.
    """
    if not isinstance(resolution, dict) or resolution.get("DECISION") != "CONTINUE_EXISTING_CASE":
        return None, None, None, False
    try:
        from nova.operator_cutover_switch import read_route_mode
        from nova.operator_shadow import plan_research_continuation
        from nova import operator_v1
        from nova.nexus_mcp_status import call_mcp_tool

        route_modes = {
            "R13.continue_vs_new": read_route_mode("R13.continue_vs_new"),
            "R15.research_continue": read_route_mode("R15.research_continue"),
        }
        mode = ("CANONICAL" if all(value == "CANONICAL" for value in route_modes.values())
                else "SHADOW" if any(value == "SHADOW" for value in route_modes.values())
                else "LEGACY_LIVE")
        if mode == "LEGACY_LIVE":
            return mode, None, route_modes, False

        if mode == "SHADOW":
            decision = {"TARGET_ENTITY_TYPE": "RESEARCH_CASE",
                        "TARGET_ENTITY_ID": resolution.get("TARGET_ENTITY_ID"),
                        "ACTION_CLASS": "SHADOW_DECISION_REQUIRES_CASE_SNAPSHOT",
                        "CREATE_NEW_ENTITY": False, "DECISION_OWNER": "SHADOW",
                        "SIDE_EFFECTS": 0, "EXECUTION_PERFORMED": False,
                        "ROUTE_MODES": route_modes, "ROUTE_MODE": mode}
            return mode, decision, route_modes, False

        case_id = str(resolution.get("TARGET_ENTITY_ID") or "")
        exact = resolution.get("RESEARCH_LINEAGE") if isinstance(resolution.get("RESEARCH_LINEAGE"), dict) else None
        if not isinstance(exact, dict) or any(not exact.get(key) for key in
                ("case_id", "objective_id", "project_id", "durable_job_id")):
            explicit = _wave3_explicit_research_lineage(text)
            exact = explicit if explicit and explicit.get("case_id") == case_id else None
        if not exact and owner_id is not None and case_id:
            exact = operator_v1.recent_research_case_lineage(str(owner_id), case_id=case_id)
        required = ("case_id", "objective_id", "project_id", "durable_job_id")
        if not isinstance(exact, dict) or any(not exact.get(key) for key in required):
            decision = {"TARGET_ENTITY_TYPE": "RESEARCH_CASE", "TARGET_ENTITY_ID": case_id or None,
                        "ACTION_CLASS": "CAPABILITY_PREFLIGHT_REQUIRED", "CREATE_NEW_ENTITY": False,
                        "DECISION_OWNER": "NOVA_OPERATOR", "SIDE_EFFECTS": 0,
                        "EXECUTION_PERFORMED": False, "ERROR_CODE": "EXACT_RESEARCH_LINEAGE_INCOMPLETE",
                        "SUCCESS_CONDITION": "Continue only the same exact case after objective, project, and job lineage are verified."}
            return mode, decision, route_modes, False

        snapshot, tool_count = call_mcp_tool("nexus_get_research_case", {
            "case_id": exact["case_id"], "objective_id": exact["objective_id"],
            "project_id": exact["project_id"], "durable_job_id": exact["durable_job_id"],
        })
        if (snapshot.get("status") != "ok" or snapshot.get("read_only") is not True
                or snapshot.get("no_mutation") is not True
                or any(str(snapshot.get(key) or "") != str(exact[key]) for key in required)):
            decision = {"TARGET_ENTITY_TYPE": "RESEARCH_CASE", "TARGET_ENTITY_ID": case_id,
                        "ACTION_CLASS": "CASE_READBACK_REQUIRED", "CREATE_NEW_ENTITY": False,
                        "DECISION_OWNER": "NOVA_OPERATOR", "SIDE_EFFECTS": 0,
                        "EXECUTION_PERFORMED": False, "ERROR_CODE": "EXACT_CASE_READBACK_FAILED"}
            return mode, decision, route_modes, False

        catalog = operator_v1.discover_catalog(force=True)
        approved = {str(row.get("capability_id")) for row in catalog
                    if row.get("authorized") and row.get("source_id") == "nexus_mcp_remote"}
        case_state = snapshot.get("case_state") if isinstance(snapshot.get("case_state"), dict) else {}
        folded = str(text or "").casefold()
        decision = plan_research_continuation(
            case_id=exact["case_id"], objective_id=exact["objective_id"],
            project_id=exact["project_id"], durable_job_id=exact["durable_job_id"],
            case_state=case_state, approved_capability_ids=approved,
            worker_failure=bool(re.search(r"\b(?:worker|execution|source)\s+(?:failed|failure)|failed\s+(?:worker|execution|source)\b", folded)),
            receipt_missing_source_exists=bool(re.search(r"\bmissing\s+(?:the\s+)?receipt\b", folded)),
            outside_review_requested=bool(re.search(r"\b(?:outside review|outside reviewer|external advisor|advisor review)\b", folded)),
        )
        decision.update({"DECISION_OWNER": "NOVA_OPERATOR", "ROUTE_MODES": route_modes,
                         "ROUTE_MODE": mode, "READ_TOOL_COUNT": tool_count,
                         "READ_ONLY": True, "NO_MUTATION": True,
                         "RESEARCH_LINEAGE": {key: exact[key] for key in required},
                         "CASE_STATE_SNAPSHOT": case_state,
                         "CAPABILITY_DISCOVERY_COUNT": len(approved)})
        canonical = bool(mode == "CANONICAL" and decision.get("TARGET_ENTITY_ID") == exact["case_id"]
                         and decision.get("SIDE_EFFECTS") == 0 and not decision.get("UNKNOWN_CAPABILITY_IDS"))
        _log("WAVE3_CONTINUATION_DECISION " + json.dumps({
            "mode": mode, "action": decision.get("ACTION_CLASS"),
            "case": decision.get("TARGET_ENTITY_ID"), "capabilities": decision.get("SELECTED_CAPABILITY_IDS"),
            "side_effects": decision.get("SIDE_EFFECTS"), "read_tools": tool_count,
        }, ensure_ascii=False, sort_keys=True))
        return mode, decision, route_modes, canonical
    except Exception as exc:
        _log(f"WAVE3_CONTINUATION_DECISION_FAILED error={type(exc).__name__}; existing execution route retained")
        return None, None, None, False


def _wave3_case_resolution_answer(decision, case_snapshot):
    """Render a no-mutation resolution only after exact Research case readback."""
    if not isinstance(decision, dict) or decision.get("DECISION") != "READ_CASE":
        return None
    if (decision.get("DECISION_OWNER") != "NOVA_OPERATOR"
            or decision.get("SHADOW_ONLY") is not False
            or decision.get("SIDE_EFFECTS") != 0
            or decision.get("CREATE_NEW_ENTITY") is not False):
        return None
    case_id = str(decision.get("TARGET_ENTITY_ID") or "")
    if not re.fullmatch(r"rcase_[A-Za-z0-9_.:-]{4,120}", case_id, re.I):
        return None
    if not isinstance(case_snapshot, dict) or case_snapshot.get("status") != "ok":
        return None
    if (case_snapshot.get("case_id") != case_id or case_snapshot.get("read_only") is not True
            or case_snapshot.get("no_mutation") is not True or case_snapshot.get("error")):
        return None
    case_state = case_snapshot.get("case_state") if isinstance(case_snapshot.get("case_state"), dict) else {}
    if not case_state.get("status"):
        return None
    open_questions = case_state.get("open_questions") if isinstance(case_state.get("open_questions"), list) else []
    synthesis_count = len(case_state.get("syntheses") or []) if isinstance(case_state.get("syntheses"), list) else None
    source_count = len(case_state.get("sources") or []) if isinstance(case_state.get("sources"), list) else None
    return (f"The existing Research case resolved from this conversation is {case_id}. "
            f"Its verified current case status is {case_state['status']}; it has {len(open_questions)} open questions"
            f"{', ' + str(source_count) + ' sources' if source_count is not None else ''}"
            f"{', ' + str(synthesis_count) + ' syntheses' if synthesis_count is not None else ''}. "
            "This was a read-only continuity check; no objective, project, job, or case was created, and no Research execution was started.")


def _wave2_new_entity_sequence(decision):
    """A create-first graph owns its later pronouns within this request."""
    if not isinstance(decision, dict):
        return False
    actions = decision.get("ACTION_SEQUENCE") or [decision.get("ACTION_CLASS")]
    return bool(decision.get("CREATE_NEW_ENTITY") and actions and actions[0] == "CREATE")


def _wave2_result_envelope(decision, operator_result, receipt_id=None):
    """Normalize Operator outcome to the bounded Wave 2 action contract."""
    decision = decision if isinstance(decision, dict) else {}
    operator_result = operator_result if isinstance(operator_result, dict) else {}
    final = operator_result.get("final_result") if isinstance(operator_result.get("final_result"), dict) else {}
    entities = operator_result.get("entities") if isinstance(operator_result.get("entities"), dict) else {}
    entity_type = str(decision.get("ENTITY_TYPE") or "")
    entity_id = decision.get("ENTITY_ID")
    if entity_type == "NOTE":
        entity_id = entities.get("note_id") or entity_id
    elif entity_type == "FILE":
        entity_id = entities.get("file_id") or entity_id

    def find_key(value, key):
        if isinstance(value, dict):
            if value.get(key) is not None:
                return value[key]
            for child in value.values():
                found = find_key(child, key)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = find_key(child, key)
                if found is not None:
                    return found
        return None

    evidence = final.get("mission_success_evidence") if isinstance(final.get("mission_success_evidence"), dict) else {}
    completed_steps = final.get("completed_steps") if isinstance(final.get("completed_steps"), list) else []
    version_hash = find_key(evidence, "sha256") or find_key(evidence, "previous_sha256")
    if not version_hash:
        version_hash = next((value for row in reversed(completed_steps)
                             if (value := (find_key(row, "previous_sha256") or find_key(row, "sha256")))), None)
    write_step = next((row for row in completed_steps if "nexus_write_workspace_artifact" in
                       str(row.get("capability_id") or "")), None)
    created_by_step = (write_step or {}).get("step_id")
    verified = bool(operator_result.get("status") == "COMPLETE"
                    and final.get("mission_success_verified") is True
                    and final.get("all_postconditions_verified") is True
                    and version_hash and evidence.get("verified_at"))
    succeeded = bool(verified and entity_id)
    return {
        "ACTION_SUCCEEDED": succeeded,
        "ENTITY_TYPE": entity_type,
        "ENTITY_ID": str(entity_id) if entity_id else None,
        "RESULT": final if final else {"status": operator_result.get("status")},
        "RECEIPT_ID": receipt_id,
        "POSTCONDITION_VERIFIED": verified,
        "MISSION_ID": operator_result.get("mission_id"),
        "CREATED_BY_STEP": created_by_step or decision.get("CREATED_BY_STEP"),
        "CURRENT_VERSION_OR_HASH": version_hash,
        "PARENT_ENTITY_IF_ANY": decision.get("PARENT_ENTITY_IF_ANY"),
        "LAST_VERIFIED_AT": evidence.get("verified_at"),
        "ERROR_CODE": None if succeeded else str(operator_result.get("failure") or operator_result.get("error") or
                                                    ("POSTCONDITION_NOT_VERIFIED" if operator_result.get("status") == "COMPLETE" else "OPERATOR_ACTION_INCOMPLETE")),
        "SOURCE": "NOVA_OPERATOR",
    }


def _wave2_crud_plan(decision, text, update_id):
    """Build a bounded exact-entity Operator plan for the requested CRUD sequence."""
    kind = str(decision.get("ENTITY_TYPE") or "")
    actions = list(decision.get("ACTION_SEQUENCE") or [decision.get("ACTION_CLASS")])
    if kind not in {"NOTE", "FILE"} or not actions or any(
            action not in {"CREATE", "READ", "UPDATE", "DELETE", "VERIFY_ABSENT"} for action in actions):
        raise ValueError("WAVE2_CRUD_SEQUENCE_INVALID")
    quoted = [" ".join(match.group(2).split())[:4000] for match in re.finditer(
        r"(['\"“])(.*?)\1", str(text or ""), re.S)]
    content_actions = [action for action in actions if action in {"CREATE", "UPDATE"}]
    content_for_action = dict(zip(content_actions, quoted))
    path = str(decision.get("ENTITY_ID") or "")
    if "CREATE" in actions:
        if "CREATE" != actions[0]:
            raise ValueError("WAVE2_CREATE_MUST_PRECEDE_ENTITY_MUTATION")
        if "CREATE" not in content_for_action:
            raise ValueError("WAVE2_CREATE_REQUIRES_EXACT_QUOTED_CONTENT")
        if kind == "NOTE":
            path = f"reports/nova_internal/nova_note_{int(update_id)}.md"
        else:
            named = re.search(r"\b(?:called|named)\s+([A-Za-z0-9][A-Za-z0-9_.-]{0,100})", str(text), re.I)
            filename = named.group(1) if named else f"nova_file_{int(update_id)}.txt"
            if filename in {".", ".."} or "/" in filename or "\\" in filename:
                raise ValueError("WAVE2_FILE_NAME_MUST_BE_A_BOUNDED_BASENAME")
            path = f"reports/nova_internal/{filename}"
    if not path.startswith("reports/nova_internal/"):
        raise ValueError("WAVE2_EXACT_BOUNDED_ENTITY_PATH_REQUIRED")

    tool_ids = {
        "CREATE": "mcp:nexus_mcp_remote:nexus_write_workspace_artifact",
        "READ": "mcp:nexus_mcp_remote:nexus_read_workspace_file",
        "UPDATE": "mcp:nexus_mcp_remote:nexus_update_workspace_artifact",
        "DELETE": "mcp:nexus_mcp_remote:nexus_delete_workspace_artifact",
        "VERIFY_ABSENT": "mcp:nexus_mcp_remote:nexus_read_workspace_file",
    }
    steps = []
    sequence = 0
    last_content = None
    current_sha_ref = None
    entity_field = "note_id" if kind == "NOTE" else "file_id"

    def add(action, goal, arguments, verification=None):
        nonlocal sequence
        sequence += 1
        row = {"step_id": f"crud_{sequence}_{action.casefold()}", "goal": goal,
               "capability_id": tool_ids[action], "arguments": arguments,
               "depends_on": [], "expected_postcondition": goal,
               "alternate_capability_ids": [], "boundary": None}
        if verification is not None:
            row["verification"] = verification
        steps.append(row)
        return sequence

    for action in actions:
        exact_read = {"relative_path": path}
        if action == "CREATE":
            last_content = content_for_action[action]
            add("CREATE", f"Create exactly one bounded {kind} at its assigned path without overwriting.",
                {"relative_path": path, "content": last_content},
                {"capability_id": tool_ids["READ"], "arguments": exact_read,
                 "assertion": {"equals": {"path": "content", "value": last_content}}})
        elif action == "READ":
            add("READ", f"Read the same exact {kind} entity.", exact_read,
                {"capability_id": tool_ids["READ"], "arguments": exact_read,
                 "assertion": {"equals": {"path": "status", "value": "ok"}}})
        elif action == "UPDATE":
            if "UPDATE" not in content_for_action:
                raise ValueError("WAVE2_UPDATE_REQUIRES_EXACT_QUOTED_CONTENT")
            pre_read = add("READ", f"Read the exact {kind} before same-entity update.", exact_read,
                {"capability_id": tool_ids["READ"], "arguments": exact_read,
                 "assertion": {"equals": {"path": "status", "value": "ok"}}})
            last_content = content_for_action[action]
            ref = f"{{{{step{pre_read}.result_data.sha256}}}}"
            add("UPDATE", f"Update only the existing {kind} with its current SHA-256 guard.",
                {"relative_path": path, entity_field: path, "content": last_content,
                 "expected_sha256": ref},
                {"capability_id": tool_ids["READ"], "arguments": exact_read,
                 "assertion": {"equals": {"path": "content", "value": last_content}}})
        elif action == "DELETE":
            pre_read = add("READ", f"Read the exact {kind} before same-entity delete.", exact_read,
                {"capability_id": tool_ids["READ"], "arguments": exact_read,
                 "assertion": {"equals": {"path": "status", "value": "ok"}}})
            ref = f"{{{{step{pre_read}.result_data.sha256}}}}"
            add("DELETE", f"Delete only the exact existing {kind} with its current SHA-256 guard.",
                {"relative_path": path, entity_field: path, "expected_sha256": ref},
                {"capability_id": tool_ids["READ"], "arguments": exact_read,
                 "assertion": {"not_found": True}})
        elif action == "VERIFY_ABSENT":
            add("VERIFY_ABSENT", f"Independently verify the same {kind} path is absent after deletion.",
                exact_read, {"capability_id": tool_ids["READ"], "arguments": exact_read,
                            "assertion": {"not_found": True}})
    final_action = actions[-1]
    if final_action in {"DELETE", "VERIFY_ABSENT"}:
        assertion = {"not_found": True}
    elif final_action in {"CREATE", "UPDATE"}:
        assertion = {"equals": {"path": "content", "value": last_content}}
    else:
        assertion = {"equals": {"path": "status", "value": "ok"}}
    plan = {"steps": steps, "capability_gap": None,
            "mission_success_condition": {"description": f"The requested {kind} CRUD sequence is independently verified on the same exact path {path}.",
                "verification": {"capability_id": tool_ids["READ"], "arguments": {"relative_path": path},
                                 "assertion": assertion}}}
    return plan, path, content_for_action


def _deliver_authoritative_mission_answer(update_id, chat_id, response):
    """Deliver a read-only status answer under the narrow Ray owner-reply policy.

    This establishes per-update governance/correlation context only; it does
    not create an Operator mission or a Nexus work item.
    """
    update_scope = f"nova-telegram-update-{update_id}"
    context = _set_owner_turn_governance_context(
        {"mission_id": update_scope, "correlation_id": update_scope},
        delivery_update_id=update_id,
        delivery_job_type="NOVA_TELEGRAM_STATUS_REPLY",
    )
    try:
        return _deliver_response(update_id, chat_id, response)
    finally:
        _restore_owner_turn_governance_context(context)


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


def current_lineage_followup_kind(text, lineage=None):
    """Recognize exact current-entity references without historical search."""
    value = " ".join(str(text or "").casefold().split())
    if not isinstance(lineage, dict) or not any(lineage.get(key) for key in (
            "objective_id", "project_id", "job_id", "case_id", "note_id", "file_id", "event_id", "result_id")):
        return None
    refers_to_current = bool(re.search(
        r"(?:\b(?:that|this)\s+(?:(?:same|current|existing|previous|just-opened)\s+)*(?:research\s+)?(?:project|objective|job|case|note|file|document|event|result)|"
        r"\b(?:that|this|the)\s+(?:(?:same|existing|prior|previous|current)\s+)+research\b|"
        r"\b(?:research\s+)?(?:project|objective|job|case|note|file|document|event)\s+(?:you|we)\s+just\s+"
        r"(?:created|made|started|updated|saved|opened|fixed|repaired)|\bthe\s+result\s+of\s+(?:that|the)\s+"
        r"(?:research\s+)?(?:project|objective|job|case)|\bthat\s+research|\bits\s+result)\b", value))
    if not refers_to_current and lineage:
        has_entity = any(lineage.get(key) for key in ("objective_id", "project_id", "job_id", "case_id", "note_id", "file_id", "event_id", "result_id"))
        refers_to_current = has_entity and bool(re.search(
            r"\b(?:it|that|that one|the same one)\b|\bshow me (?:the )?result\b", value))
    if not refers_to_current:
        return None
    if re.search(r"\b(?:continue|advance|resume|keep going|keep the same|keep working|answer|gather|synthesize|run|execute|also check|also verify|also review|also investigate|also research|also compare)\b", value):
        return "CONTINUE"
    if re.search(r"\b(?:result|show|status|state|check|progress|next step|where|what)\b", value):
        return "READ"
    return None


def current_lineage_reference(text, lineage=None):
    """Whether natural language refers to the exact active entity bundle."""
    if not isinstance(lineage, dict) or not any(lineage.get(key) for key in (
            "objective_id", "project_id", "job_id", "case_id", "note_id", "file_id", "event_id", "result_id")):
        return False
    value = " ".join(str(text or "").casefold().split())
    return bool(re.search(
        r"\b(?:that|this|it|those|the same)\s+(?:(?:same|current|existing|previous|just-opened)\s+)*(?:research\s+)?(?:case|project|objective|job|note|file|document|event|result)\b|"
        r"\b(?:that|this|the)\s+(?:(?:same|existing|prior|previous|current)\s+)+research\b|"
        r"\b(?:research\s+)?(?:case|project|objective|job|note|file|document|event)\s+(?:you|we)\s+just\s+"
        r"(?:created|made|started|updated|saved|opened|fixed|repaired)\b|"
        r"\b(?:continue|advance|resume|keep going|show me|delete|update|read|check|fix|repair|retry)\s+"
        r"(?:it|that|that one|the same one|the result)\b|\bwhat happened with (?:it|that|the same)\b|"
        r"\bshow me (?:the )?result\b", value))


def _operator_route_gate(actionable_request, text, lineage, followup_kind):
    """Evaluate Operator routing after computing the current-entity reference."""
    lineage_reference = current_lineage_reference(text, lineage)
    should_route = bool(actionable_request or (lineage and (followup_kind or lineage_reference)))
    return should_route, lineage_reference


def _legacy_research_assignment_owns_intake(semantic, *, continuation_canonical=False):
    """Honor R14 for new Research assignment intake without affecting continuation.

    The generic actionable-request gate predates the per-route switch and would
    otherwise intercept new Research assignments even while R14 is
    LEGACY_LIVE. Wave 3 continuation remains governed separately by R15.
    """
    if continuation_canonical or not isinstance(semantic, dict):
        return False
    if (
        semantic.get("execution_mode") == "RESEARCH_ROOM_MODE"
        or semantic.get("intent") == "RESEARCH_ROOM_REQUEST"
    ):
        return False
    if str(semantic.get("department") or "").upper() != "RESEARCH":
        return False
    if str(semantic.get("intent") or "").upper() not in {
        "RESEARCH_REQUEST", "RESEARCH_MISSION", "RESEARCH_RUNTIME_INSPECTION", "DEPARTMENT_ASSIGNMENT"
    }:
        return False
    try:
        from nova.operator_cutover_switch import read_route_mode
        return read_route_mode("R14.research_assignment") == "LEGACY_LIVE"
    except Exception as exc:
        _log(f"R14_SWITCH_READ_FAILED error={type(exc).__name__}; preserving legacy Research intake")
        return True


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


def _exact_research_status_response(job_id, *, include_internal_receipts=False):
    """Read and render one exact existing durable job; never create work."""
    from nova.nexus_mcp_status import call_exact_job_status, render_exact_job_status

    result, tool_count = call_exact_job_status(job_id)
    if result.get("status") != "ok":
        return (f"RESEARCH_JOB_ID={job_id}\nJOB_STATUS=NOT_FOUND\n"
                "I could not find that exact job in the live durable store. No objective or job was created.",
                tool_count, result)
    job = result.get("job") if isinstance(result.get("job"), dict) else {}
    return render_exact_job_status(result, include_internal_receipts=include_internal_receipts), tool_count, result


def _existing_job_operational_diagnostic(chat_id, semantic):
    """Read one exact current job and report any executor evidence or gap.

    This path is deliberately read-only. It never enqueues replacement work or
    claims that a worker/service was repaired without a durable action receipt.
    """
    from nova.nexus_mcp_status import call_exact_job_status, call_mcp_tool

    lineage = load_current_objective_lineage(chat_id) or {}
    job_id = str(semantic.get("job_id") or lineage.get("job_id") or "").strip()
    if not job_id:
        return {
            "response": (
                "I could not resolve an exact existing job from this chat's current lineage. "
                "I did not search historical jobs or create new work.\n"
                "MISSING_CAPABILITY=exact current-job lineage\n"
                "MISSING_TOOL_OR_ACTION=none; a receipt-backed current job reference is required\n"
                "CURRENT_JOB_ID=UNKNOWN\nNEW_JOB_CREATED=NO"
            ),
            "job_id": None, "status": "CURRENT_JOB_NOT_FOUND", "tool_count": 0,
            "missing": ["exact current-job lineage"],
        }

    exact, tool_count = call_exact_job_status(job_id)
    if exact.get("status") != "ok":
        return {
            "response": (
                f"I could not read the exact linked job {job_id} from the durable job store. "
                "I did not substitute a historical job or create another one.\n"
                f"MISSING_CAPABILITY=exact durable-job status read\nCURRENT_JOB_ID={job_id}\n"
                "NEW_JOB_CREATED=NO"
            ),
            "job_id": job_id, "status": "EXACT_JOB_READ_FAILED", "tool_count": tool_count,
            "missing": ["exact durable-job status read"],
        }

    job = exact.get("job") if isinstance(exact.get("job"), dict) else {}
    queue_read = call_mcp_tool("nexus_get_research_queue", {})[0]
    health_read = call_mcp_tool("nexus_get_system_health", {})[0]
    health_data = health_read.get("data") if isinstance(health_read.get("data"), dict) else {}
    process_states = health_data.get("process_states") if isinstance(health_data.get("process_states"), list) else []
    executor_rows = [row for row in process_states if isinstance(row, dict) and
                     re.search(r"research.*(?:worker|dispatcher|scheduler)|(?:worker|dispatcher|scheduler).*research",
                               str(row.get("process_id") or "") + " " + str(row.get("service") or ""), re.I)]
    queue_data = queue_read.get("data") if isinstance(queue_read.get("data"), dict) else {}
    queue_summary = queue_data.get("queue_summary") if isinstance(queue_data.get("queue_summary"), dict) else {}

    state = str(job.get("state") or "UNKNOWN").upper()
    attempts = int(job.get("attempt_count") or 0)
    recorded_claim = str(job.get("claimed_by") or "")
    claimed_by = recorded_claim if state in {"CLAIMED", "RUNNING"} and recorded_claim else "NONE"
    executor = str((executor_rows[0].get("process_id") if executor_rows else "") or "UNKNOWN")
    executor_state = str((executor_rows[0].get("state") if executor_rows else "") or "UNKNOWN")
    heartbeat = str((executor_rows[0].get("last_run_at") if executor_rows else "") or "UNKNOWN")
    missing = []
    if not executor_rows:
        missing.extend([
            "nexus_get_research_executor_health (worker/scheduler heartbeat and RESEARCH_INTAKE subscription)",
            "nexus_read_research_executor_logs (claim/routing errors)",
            "nexus_repair_research_dispatcher (governed source-filter/service configuration repair)",
        ])
    if state in {"CLAIMED", "RUNNING"} and claimed_by != "NONE":
        status_text = f"The exact job {job_id} is {state} and claimed by {claimed_by}."
    elif state == "READY" and attempts == 0 and claimed_by == "NONE":
        status_text = f"The exact job {job_id} remains READY with zero attempts and no worker claim."
    else:
        status_text = f"The exact job {job_id} is {state}; attempts={attempts}; claimed_by={claimed_by}."
    if executor_rows:
        executor_text = f"Executor evidence: {executor} state={executor_state}, last heartbeat={heartbeat}."
        missing_text = ""
    else:
        executor_text = "The available system-health read contains no Research worker or dispatcher heartbeat/log record."
        missing_text = (
            "\nMISSING_CAPABILITY=Research executor/dispatcher health, logs, and governed configuration repair"
            "\nMISSING_TOOL_OR_ACTION=" + "; ".join(missing)
            + "\nREQUIRED_SCOPE=read-only executor heartbeat/log inspection and narrowly scoped control of the existing dispatcher source filter"
            + "\nWHY_REQUIRED=The current MCP surface exposes exact job, aggregate queue, and general system-health reads, but no Research executor heartbeat/log query or dispatcher configuration action."
        )
    response = (
        status_text + "\n"
        f"JOB_TYPE={job.get('job_type') or 'UNKNOWN'}\nATTEMPT_COUNT={attempts}\nCLAIMED_BY={claimed_by}\n"
        f"LAST_CLAIMED_BY={recorded_claim or 'UNKNOWN'}\nSTARTED_AT={job.get('started_at') or 'UNKNOWN'}\n"
        f"LAST_ERROR_CODE={job.get('last_error_code') or 'NONE'}\n"
        f"LAST_ERROR_SUMMARY={str(job.get('last_error_summary') or 'NONE')[:700]}\n"
        f"QUEUE_READY_COUNT={queue_summary.get('by_status', {}).get('QUEUED', 'UNKNOWN')}\n"
        f"DISPATCHER_RUNNING={executor_state if executor_rows else 'UNKNOWN'}\n"
        f"LAST_HEARTBEAT={heartbeat}\nNEW_JOB_CREATED=NO\nREPAIR_EXECUTED=NO\n"
        + executor_text + missing_text
    )
    return {"response": response, "job_id": job_id, "status": state, "attempt_count": attempts,
            "claimed_by": claimed_by, "tool_count": tool_count, "queue_status": queue_data.get("current_health"),
            "last_claimed_by": recorded_claim, "started_at": job.get("started_at"),
            "last_error_code": job.get("last_error_code"),
            "last_error_summary": str(job.get("last_error_summary") or "")[:700],
            "executor": executor, "executor_state": executor_state, "last_heartbeat": heartbeat,
            "missing": missing}


def dispatch_objective_assignment(mission, text, department, requested_intent=None, followup_department=""):
    """Create and persist one governed department link before any success reply."""
    from nova.nexus_mcp_status import (
        assign_department_task, build_assignment_linkage, render_assignment_ack,
    )
    objective_id = str(mission.get("nova_objective_id") or mission.get("root_objective_id")
                       or mission.get("mission_id") or "")
    parent_request_id = str(mission.get("parent_request_id") or objective_id)
    # Hard guard: Research Room requests must NEVER fall through to legacy dispatch or durable job creation
    if (
        str(department).upper() == "RESEARCH"
        and (
            str(requested_intent or "").upper() == "RESEARCH_ROOM_REQUEST"
            or (isinstance(mission, dict) and mission.get("primary_mode") == "RESEARCH_ROOM_MODE")
            or bool(re.search(r"\b(?:create (?:a )?(?:new )?research room|open (?:a )?(?:new )?research room|research room)\b", str(text or ""), re.I))
        )
    ):
        raise RuntimeError("LEGACY_RESEARCH_DISPATCH_FORBIDDEN: Research Room requests must never be dispatched to legacy durable research.")
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


def record_approved_mcp_result(update_id, mission, route, response):
    """Persist an MCP write receipt only when Hermes returns the tool receipt."""
    if not route or route.get("read_write_class") != "WRITE":
        return None
    text = str(response or "")
    receipt_match = re.search(r"\b(?:TOOL_)?RECEIPT_ID\s*[:=]\s*([A-Za-z0-9_.:-]{6,160})", text, re.I)
    resource_match = re.search(r"\b(?:RESOURCE_ID|NOTE_ID|PROJECT_ID|JOB_ID|FILE_ID|EVENT_ID)\s*[:=]\s*([A-Za-z0-9_.:-]{3,160})", text, re.I)
    if not receipt_match:
        return None
    receipt = write_receipt({"type": "nova_approved_mcp_action", "incoming_update_id": update_id,
        "mission_id": mission.get("mission_id"), "mcp_server": route.get("server_id"),
        "tool_name": route.get("name"), "resource_id": resource_match.group(1) if resource_match else None,
        "action_type": route.get("read_write_class"), "policy_decision": (route.get("policy") or {}).get("decision"),
        "tool_receipt_id": receipt_match.group(1), "result_status": "TOOL_RECEIPT_RETURNED",
        "action_completed": True})
    update_mission(mission, "APPROVED_MCP_ACTION_RECEIPTED", {
        "action_completed": True, "read_only": False, "mcp_server": route.get("server_id"),
        "mcp_tool": route.get("name"), "tool_receipt_id": receipt_match.group(1),
        "resource_id": resource_match.group(1) if resource_match else None,
        "normalized_receipt_id": receipt["receipt_id"]})
    chat_id = mission.get("chat_id")
    if chat_id is not None and resource_match:
        lineage = load_current_objective_lineage(chat_id) or {}
        lineage["current_mcp_object"] = {"telegram_update_id": update_id,
            "mission_id": mission.get("mission_id"), "server_id": route.get("server_id"),
            "tool_name": route.get("name"), "resource_id": resource_match.group(1),
            "tool_receipt_id": receipt_match.group(1), "receipt_id": receipt["receipt_id"],
            "updated_at": receipt["timestamp"]}
        save_current_objective_lineage(chat_id, lineage)
    return receipt


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
                    "response": "The bounded artifact writer does not overwrite files. The objective remains active while Nova evaluates an approved update path; nothing changed."}
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


def _run_oracle_primary(update_id, message, chat_id, text, primary_run_id=None, mcp_action_route=None,
                       context_snapshot=None):
    """Run the fixed, governed Oracle Hermes 0.20.6 adapter."""
    from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes
    session = f"nova-telegram-primary-{chat_id}"
    started = time.monotonic()
    from nova.context_authority import render_context_block
    pre_context = render_context_block(context_snapshot or {
        "message_id": str(update_id), "current_text": str(text)[:3000],
        "resolution_source": "CURRENT_USER_MESSAGE", "resolution_priority": 1,
        "reference_type": "GENERAL"})
    if mcp_action_route:
        current = load_current_objective_lineage(chat_id) or {}
        obj = current.get("current_mcp_object") or {}
        if obj.get("server_id") == mcp_action_route.get("server_id"):
            pre_context += ("\n\nCURRENT APPROVED MCP OBJECT LINEAGE (exact current object; do not substitute history):\n"
                            + json.dumps(obj, ensure_ascii=False))
    result = run_oracle_hermes(text, session, request_id=f"telegram-{update_id}",
                               timeout_seconds=HERMES_SHADOW_TIMEOUT, pre_context=pre_context)
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


def _acceptance_record_fields(update_id, trace):
    """Join only the exact update's persisted context, mission, and delivery."""
    delivery = _load_delivery(update_id) or {}
    mission_id = str(delivery.get("mission_id") or "")
    mission = {}
    if mission_id and re.fullmatch(r"[A-Za-z0-9_-]{1,120}", mission_id):
        try:
            with open(os.path.join(NOVA_MISSIONS_DIR, mission_id + ".json"), encoding="utf-8") as handle:
                mission = json.load(handle)
        except (OSError, ValueError):
            mission = {}
    context = {}
    try:
        with open(os.path.join(NOVA_CONTEXT_DIR, f"{update_id}.json"), encoding="utf-8") as handle:
            context = json.load(handle)
    except (OSError, ValueError):
        context = {}

    def value_from_events(*keys):
        for event in reversed(trace.events):
            metadata = event.get("metadata") if isinstance(event, dict) else None
            if not isinstance(metadata, dict):
                continue
            for key in keys:
                if metadata.get(key) not in (None, ""):
                    return metadata[key]
        return None

    def collect_named(value, names, depth=0):
        found = []
        if depth > 6:
            return found
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in names and child not in (None, ""):
                    items = child if isinstance(child, list) else [child]
                    found.extend(str(item)[:200] for item in items if isinstance(item, (str, int)))
                elif isinstance(child, (dict, list)):
                    found.extend(collect_named(child, names, depth + 1))
        elif isinstance(value, list):
            for child in value[:100]:
                found.extend(collect_named(child, names, depth + 1))
        return list(dict.fromkeys(found))[:50]

    referent = context.get("resolved_referent")
    if isinstance(referent, dict):
        referent_id = next((referent.get(key) for key in
            ("result_id", "mission_id", "job_id", "case_id", "objective_id", "project_id", "id")
            if referent.get(key)), None)
    else:
        referent_id = referent if isinstance(referent, (str, int)) else None

    capabilities = collect_named(mission, {"capability_id", "selected_capability", "tool_name"})
    capabilities.extend(collect_named({"events": trace.events}, {"resolved_capability", "tool_names"}))
    capabilities = list(dict.fromkeys(capabilities))[:50]
    job_ids = collect_named(mission, {"job_id", "durable_job_id"})
    # The owner-turn mission ID is deliberately not reported as a durable job.
    job_ids = [job for job in job_ids if job != mission_id]
    receipts = collect_named(mission, {"receipt_id", "tool_receipt_id", "nexus_receipt_id", "receipt_ids"})
    provenance = collect_named(mission, {"provenance_ref", "provenance_refs", "evidence_ref", "evidence_refs", "source_refs"})
    response = str(delivery.get("response") or "")
    for receipt in re.findall(r"(?:Gateway receipt ID|Systems receipt ID|Receipt ID)[:=\s]+([A-Za-z0-9_.:-]+)", response, re.I):
        receipts.append(receipt)
    for source in re.findall(r"\[evidence:\s*([^\]]+)\]", response, re.I):
        provenance.append(source)
    receipts = list(dict.fromkeys(receipts))[:50]
    provenance = list(dict.fromkeys(provenance))[:50]
    tools = value_from_events("tool_names") or []
    if isinstance(tools, str):
        tools = [tools]
    engine_call_count = value_from_events("engine_call_count")
    if engine_call_count is None:
        engine_call_count = len(tools)
    intent = value_from_events("intent_class") or mission.get("semantic_intent") or "UNCLASSIFIED"
    casual = str(intent).upper() in {"CASUAL_CONVERSATION", "GREETING", "SMALL_TALK", "GENERAL_CONVERSATION"}
    objective_created = value_from_events("new_objective_created")
    job_created = value_from_events("new_job_created")
    mutation_count = value_from_events("mutation_count", "mutations_performed")
    if casual:
        objective_created = objective_created or "NO"
        job_created = job_created or "NO"
        mutation_count = 0 if mutation_count is None else mutation_count
        engine_call_count = 0 if engine_call_count is None else engine_call_count
    return {
        "intent_class": intent,
        "resolved_capability": capabilities,
        "resolved_engine": value_from_events("resolved_engine") or ("GOVERNED_CAPABILITY" if tools else "NONE"),
        "operation_class": value_from_events("operation_class") or mission.get("response_mode") or "UNCLASSIFIED",
        "used_existing_verified_result": value_from_events("used_existing_verified_result"),
        "referent_result_id": value_from_events("referent_result_id") or referent_id,
        "request_id": value_from_events("request_id") or mission.get("request_id") or f"telegram-{update_id}",
        "correlation_id": mission.get("correlation_id") or value_from_events("correlation_id"),
        "engine_call_count": engine_call_count,
        "job_id": (job_ids[0] if job_ids else None),
        "new_objective_created": objective_created,
        "new_job_created": job_created,
        "mutation_count": mutation_count,
        "approval_required": value_from_events("approval_required"),
        "receipt_ids": receipts,
        "provenance_refs": provenance,
        "delivery_state": delivery.get("state"),
        "telegram_message_id": delivery.get("message_ids") or [],
        "mission_id": mission_id or None,
    }

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
            if trace.acceptance_session_id:
                # Capture only this completed update's durable delivery/context
                # joins. This is observational and runs after the response path.
                delivery_record = _load_delivery(update_id) or {}
                trace.record_acceptance_turn(
                    user_message=text,
                    nova_response=str(delivery_record.get("response") or ""),
                    fields=_acceptance_record_fields(update_id, trace),
                )
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
        lineage = load_current_objective_lineage(chat_id)
        # The JSON per-chat pointer is a cache. Refresh it from the durable
        # Operator lineage before deciding whether this is a follow-up; the
        # cache can lag a newly opened Research case by one turn.
        from nova import operator_v1
        try:
            durable_lineage = operator_v1.current_entity_lineage(str(user_id))
        except Exception as exc:
            durable_lineage = None
            _log(f"Durable Operator lineage lookup unavailable: {type(exc).__name__}")
        if durable_lineage:
            lineage = {**(lineage or {}), **durable_lineage}
        context_snapshot = _context_snapshot(update_id, chat_id, user_id, text, lineage=lineage)
        wave3_mode, wave3_decision, wave3_modes, wave3_canonical = _wave3_case_resolution_route(
            text, lineage, context_snapshot, owner_id=user_id)
        if wave3_canonical:
            # Wave 3's first cutover is resolution-only. The authoritative
            # decision selects the exact entity; the existing governed READ
            # adapter independently verifies current case status. No Research
            # write, continuation, or job/case creation is possible here.
            exact = wave3_decision.get("RESEARCH_LINEAGE") or {}
            try:
                from nova.nexus_mcp_status import call_mcp_tool
                case_snapshot, case_tool_count = call_mcp_tool("nexus_get_research_case", {
                    "case_id": exact.get("case_id"), "objective_id": exact.get("objective_id"),
                    "project_id": exact.get("project_id"), "durable_job_id": exact.get("durable_job_id"),
                })
                response = _wave3_case_resolution_answer(wave3_decision, case_snapshot)
                _log(f"WAVE3_CASE_READ case={exact.get('case_id')} tools={case_tool_count} status={case_snapshot.get('status')}")
            except Exception as exc:
                response = None
                _log(f"WAVE3_CASE_READ_FAILED case={exact.get('case_id')} error={type(exc).__name__}")
            if not response:
                response = (f"I resolved the existing Research case {wave3_decision.get('TARGET_ENTITY_ID')}, "
                    "but its current state could not be independently verified. I did not continue or change Research work, "
                    "and no new objective, project, job, or case was created.")
            _log(f"ROUTE_TRACE update={update_id} route=R13.case_resolution mode={wave3_mode} authority=CANONICAL_OPERATOR execution=NONE")
            delivery = _deliver_authoritative_mission_answer(update_id, chat_id, response)
            _log(f"Wave 3 case resolution delivered update={update_id} delivery={delivery.get('state')} case={wave3_decision.get('TARGET_ENTITY_ID')}")
            return True
        route_id = None
        route_mode = None
        canonical_owner = False
        decision = None
        if context_snapshot.get("reference_type") in {"CURRENT_STATE", "RECENT_COMPLETED_WORK"}:
            route_id, route_mode, canonical_owner, decision = _wave1_route_decision(text, context_snapshot)
            authoritative_answer = (_operator_read_only_answer(decision, context_snapshot)
                                    if canonical_owner else None)
            if authoritative_answer is None:
                if canonical_owner:
                    canonical_owner = False
                    _log(f"WAVE1_OPERATOR_RENDER_FAILED route={route_id}; using legacy renderer")
                authoritative_answer = _authoritative_mission_answer(context_snapshot)
        else:
            authoritative_answer = _authoritative_mission_answer(context_snapshot)
        if authoritative_answer:
            if route_id:
                _log(f"ROUTE_TRACE update={update_id} route={route_id} mode={route_mode} authority={'CANONICAL_OPERATOR' if canonical_owner else 'LEGACY_LIVE'} data=AUTHORITATIVE_OPERATOR_SNAPSHOT")
            delivery = _deliver_authoritative_mission_answer(update_id, chat_id, authoritative_answer)
            _log(f"Authoritative mission-state response update={update_id} ref={context_snapshot.get('reference_type')} route={route_id or 'NON_WAVE1'} delivery={delivery.get('state')}")
            return True
        semantic = resolve_owner_request(text, context=lineage)
        followup_kind = current_lineage_followup_kind(text, lineage)
        wave3_continuation_mode, wave3_continuation_decision, wave3_continuation_modes, wave3_continuation_canonical = (
            _wave3_research_continuation_decision(text, wave3_decision, owner_id=user_id))
        if wave3_continuation_mode == "CANONICAL" and not wave3_continuation_canonical:
            response = ("I resolved the Research continuation request, but the exact existing case and its linked "
                        "objective, project, and job could not all be verified through the read-only Research contract. "
                        "I did not start or create Research work.")
            _log("ROUTE_TRACE update=%s route=R15.research_continue mode=CANONICAL authority=NOVA_OPERATOR execution=NONE lineage_verified=NO" % update_id)
            _deliver_authoritative_mission_answer(update_id, chat_id, response)
            return True
        if wave3_continuation_canonical:
            exact = wave3_continuation_decision.get("RESEARCH_LINEAGE") or {}
            lineage = {**(lineage or {}), "case_id": exact.get("case_id"),
                       "objective_id": exact.get("objective_id"), "project_id": exact.get("project_id"),
                       "job_id": exact.get("durable_job_id"), "durable_job_id": exact.get("durable_job_id")}
        wave2_route, wave2_mode, wave2_decision, wave2_canonical = _wave2_action_route(
            text, lineage, previous_turn={"entity_ids": lineage or {}})
        wave2_new_entity_sequence = _wave2_new_entity_sequence(wave2_decision)
        if wave2_new_entity_sequence or semantic.get("intent") == "RESEARCH_ROOM_REQUEST" or semantic.get("execution_mode") == "RESEARCH_ROOM_MODE":
            # Pronouns later in a create-first compound request refer to its
            # newly created entity, not the prior turn's durable lineage.
            followup_kind = None

        # Nova Operator v1 owns actionable objectives before legacy handlers.
        # It plans from live approved schemas, executes through the existing
        # MCP governance boundary, and persists each step/verification. If the
        # planner itself is unavailable before execution begins, the existing
        # governed dispatcher remains a recorded alternate path.
        should_route_operator, lineage_reference = _operator_route_gate(
            operator_v1.actionable(text, semantic.get("intent")), text, lineage, followup_kind)
        if _legacy_research_assignment_owns_intake(
                semantic, continuation_canonical=wave3_continuation_canonical):
            should_route_operator = False
            _log(f"ROUTE_TRACE update={update_id} route=R14.research_assignment mode=LEGACY_LIVE authority=LEGACY_INTAKE")
        if semantic.get("intent") == "RESEARCH_ROOM_REQUEST" or semantic.get("execution_mode") == "RESEARCH_ROOM_MODE":
            should_route_operator = False
            _log(f"ROUTE_TRACE update={update_id} route=research_room_request mode=RESEARCH_ROOM authority=RESEARCH_ROOM_INTAKE")
        if wave3_continuation_canonical:
            should_route_operator = True
            lineage_reference = "R15_RESEARCH_CASE_CONTINUATION"
        if wave2_canonical:
            should_route_operator = True
        if should_route_operator:
            mission = mission_override or create_mission(update_id, chat_id, user_id, text)
            governance_context = _set_owner_turn_governance_context(mission, delivery_update_id=update_id)
            update_mission(mission, "AUTHORIZED", {"operator_v1": True,
                "operator_original_objective_id": mission.get("nova_objective_id") or mission.get("root_objective_id"),
                "wave3_research_continuation_decision": wave3_continuation_decision,
                "wave3_research_continuation_routes": wave3_continuation_modes})
            if lineage and (followup_kind or lineage_reference or wave3_continuation_canonical) and not wave2_new_entity_sequence:
                mission["current_objective_lineage"] = lineage
            if lineage_reference and lineage and not wave2_new_entity_sequence:
                try:
                    if wave3_continuation_canonical:
                        operator_owner_mission = _wave3_operator_mission_for_case(
                            operator_v1, user_id, lineage)
                    else:
                        exact_entities = [lineage.get(key) for key in ("objective_id", "project_id", "job_id", "case_id", "note_id", "file_id", "event_id") if lineage.get(key)]
                        operator_owner_mission = operator_v1.mission_for_entity(str(user_id), exact_entities)
                    if operator_owner_mission:
                        mission["operator_mission_id"] = operator_owner_mission
                except Exception as exc:
                    _log(f"Operator lineage lookup unavailable: {type(exc).__name__}")
            try:
                operator_text = text
                operator_catalog = None
                operator_planner = None
                if wave3_continuation_canonical:
                    selected = wave3_continuation_decision.get("SELECTED_CAPABILITY_IDS") or []
                    operator_text = (
                        "Nova Operator canonical Research continuation decision: preserve the exact existing "
                        f"RESEARCH_CASE and objective/project/job lineage {json.dumps(wave3_continuation_decision.get('RESEARCH_LINEAGE'), sort_keys=True)}. "
                        f"Current read-only case assessment selected ACTION_CLASS={wave3_continuation_decision.get('ACTION_CLASS')}, "
                        f"approved next-capability candidates={json.dumps(selected)}; "
                        f"success condition={wave3_continuation_decision.get('SUCCESS_CONDITION')}. "
                        "Use only the Research Room controller MCP capabilities for Research execution, status, Advisor/challenger review, and results. "
                        "Do NOT call nexus_continue_research_case, nexus_continue_research, nexus_assign_research, or the legacy notebook worker for this R15 continuation. "
                        "Re-read the same production case after each controller turn; "
                        "do not create a replacement case/objective/project, and do not declare completion while required questions remain. "
                        "Original Ray request: " + text)
                    operator_catalog = _wave3_research_controller_catalog(
                        operator_v1.discover_catalog(force=True))
                if wave2_canonical:
                    # Preflight the full shared NOTE/FILE CRUD family before
                    # executing any Wave 2 action; the plan is exact-path and
                    # ordered so each later verb retains the same entity.
                    live_catalog = operator_v1.discover_catalog(force=True)
                    preflight = operator_v1.workspace_crud_family_preflight(live_catalog)
                    if preflight.get("status") != "PASS":
                        raise RuntimeError("WAVE2_CRUD_FAMILY_PREFLIGHT_FAILED:" + _json(preflight)[:400])
                    allowed_tools = {"nexus_read_workspace_file", "nexus_write_workspace_artifact",
                                     "nexus_update_workspace_artifact", "nexus_delete_workspace_artifact"}
                    plan, exact_path, _ = _wave2_crud_plan(wave2_decision, text, update_id)
                    action_graph = " -> ".join(wave2_decision.get("ACTION_SEQUENCE") or
                                                [wave2_decision["ACTION_CLASS"]])
                    create_scope = "Create a new" if wave2_new_entity_sequence else "Continue the exact existing"
                    operator_text = (f"{create_scope} {wave2_decision['ENTITY_TYPE']} entity for this bounded "
                        f"CRUD request. Execute ordered action graph {action_graph}; bind later actions to the "
                        f"entity created or selected inside this request. Original request: {text}")
                    operator_planner = lambda _prompt, _plan=plan: json.dumps(_plan, ensure_ascii=False)
                    operator_catalog = [row for row in live_catalog if row.get("tool_name") in allowed_tools
                                        and row.get("source_id") == "nexus_mcp_remote"]
                    by_tool = {str(row.get("tool_name")): row for row in operator_catalog}
                    if not allowed_tools.issubset(by_tool):
                        raise RuntimeError("WAVE2_COMPLETE_CRUD_CAPABILITY_FAMILY_REQUIRED")
                    expected_classes = {"nexus_read_workspace_file": "READ",
                        "nexus_write_workspace_artifact": "WRITE",
                        "nexus_update_workspace_artifact": "WRITE",
                        "nexus_delete_workspace_artifact": "WRITE"}
                    for tool_name in allowed_tools:
                        row = by_tool[tool_name]
                        if (row.get("capability_id") != f"mcp:nexus_mcp_remote:{tool_name}"
                                or row.get("read_write_class") != expected_classes[tool_name]
                                or row.get("source_id") != "nexus_mcp_remote"
                                or not row.get("authorized")):
                            raise RuntimeError("WAVE2_APPROVED_WORKSPACE_CAPABILITY_CONTRACT_MISMATCH")
                operator_result = operator_v1.run_objective(
                    mission, operator_text, semantic,
                    owner_authorized=True,
                    **({"catalog": operator_catalog} if operator_catalog is not None else {}),
                    **({"planner": operator_planner} if operator_planner is not None else {}),
                )
            except Exception as exc:
                operator_result = {"handled": False, "mission_id": mission.get("operator_mission_id") or mission["mission_id"],
                                   "status": "FAILED_INTERNAL", "error": f"{type(exc).__name__}:{str(exc)[:220]}"}
                _log_error(f"Nova Operator failed before a verified route: {type(exc).__name__}: {str(exc)[:220]}")
            if operator_result.get("handled"):
                operator_status = str(operator_result.get("status") or "FAILED_INTERNAL")
                wave2_envelope = None
                if operator_status == "COMPLETE":
                    response = str(operator_result.get("response") or "Objective complete; verification evidence is persisted.")
                    operator_receipt = write_receipt({
                        "type": "nova_operator_objective_complete", "incoming_update_id": update_id,
                        "mission_id": mission["mission_id"], "operator_mission_id": operator_result.get("mission_id"),
                        "objective_id": mission.get("nova_objective_id") or mission.get("root_objective_id"),
                        "step_count": operator_result.get("step_count"), "entities": operator_result.get("entities", {}),
                        "final_evidence": operator_result.get("final_result"), "action_completed": True,
                    })
                    if wave2_canonical:
                        wave2_envelope = _wave2_result_envelope(
                            wave2_decision, operator_result, operator_receipt.get("receipt_id"))
                        if not wave2_envelope.get("ACTION_SUCCEEDED"):
                            operator_status = "RECOVERING"
                            response = ("ACTION_COMPLETED=NO\nRECOVERY_REQUIRED=YES\n"
                                "The action lacks a verified exact entity, content hash, or postcondition timestamp. "
                                "The same mission is retained for recovery; no completion is claimed.")
                            try:
                                operator_v1._mission_state(operator_result.get("mission_id"), "RECOVERING", {
                                    "same_mission": True, "wave2_result": wave2_envelope,
                                    "completion_rejected": True, "retryable": True})
                            except Exception as exc:
                                _log_error(f"Wave 2 completion downgrade failed: {type(exc).__name__}")
                    update_mission(mission, "OPERATOR_" + operator_status, {
                        "operator_mission_id": operator_result.get("mission_id"), "operator_status": operator_status,
                        "operator_receipt_id": operator_receipt["receipt_id"], "operator_entities": operator_result.get("entities", {}),
                        "action_completed": bool(wave2_envelope.get("ACTION_SUCCEEDED")) if wave2_envelope else True,
                        "wave2_result": wave2_envelope, "read_only": False,
                    })
                    entities = operator_result.get("entities") or {}
                    if entities:
                        current = dict(lineage or {})
                        current.update({key: value for key, value in entities.items() if value})
                        current.update({"telegram_update_id": update_id, "mission_id": mission["mission_id"],
                                        "operator_mission_id": operator_result.get("mission_id"),
                                        "operator_receipt_id": operator_receipt["receipt_id"],
                                        "updated_at": datetime.now(timezone.utc).isoformat()})
                        if wave2_envelope:
                            current.update({key: value for key, value in {
                                "entity_type": wave2_envelope.get("ENTITY_TYPE"),
                                "created_by_step": wave2_envelope.get("CREATED_BY_STEP"),
                                "entity_version_or_hash": wave2_envelope.get("CURRENT_VERSION_OR_HASH"),
                                "last_verified_at": wave2_envelope.get("LAST_VERIFIED_AT"),
                            }.items() if value is not None})
                        save_current_objective_lineage(chat_id, current)
                else:
                    response = str(operator_result.get("response") or "The objective remains open; no completion is claimed.")
                    if wave2_canonical:
                        wave2_envelope = _wave2_result_envelope(wave2_decision, operator_result)
                    update_mission(mission, "OPERATOR_" + operator_status, {
                        "operator_mission_id": operator_result.get("mission_id"), "operator_status": operator_status,
                        "operator_failure": operator_result.get("failure") or operator_result.get("error"),
                        "action_completed": False, "wave2_result": wave2_envelope, "read_only": False,
                    })
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
                update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                    "response_mode": "nova_operator_v1", "operator_mission_id": operator_result.get("mission_id"),
                    "response_message_ids": delivery.get("message_ids", []),
                    "operator_status": operator_status,
                })
                return True
            # No operator tool was called when planning failed. Preserve the
            # same Telegram mission and continue through the established
            # semantic/Nexus route as an alternate executor.
            if wave2_canonical:
                response = ("ACTION_COMPLETED=NO\nRECOVERY_REQUIRED=YES\n"
                    "The canonical Operator could not complete the bounded note action with its approved workspace adapter. "
                    "The same mission is retained for recovery; no legacy writer was invoked.")
                update_mission(mission, "OPERATOR_WAVE2_RECOVERY_REQUIRED", {
                    "wave2_route_id": wave2_route, "operator_mission_id": operator_result.get("mission_id"),
                    "operator_failure": operator_result.get("failure") or operator_result.get("error"),
                    "same_mission": True, "no_legacy_fallback": True, "action_completed": False,
                })
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
                update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                    "response_mode": "nova_operator_wave2_recovery", "response_message_ids": delivery.get("message_ids", [])})
                return True
            try:
                operator_v1.note_existing_route_fallback(
                    str(operator_result.get("mission_id") or mission["mission_id"]), semantic,
                    str(operator_result.get("error") or "planner did not return an executable plan"))
            except Exception:
                pass
            if lineage and (followup_kind or lineage_reference):
                # Exact current-entity actions cannot fall through to a legacy
                # project/department assignment route. Keep the Operator
                # mission active for capability-compatible recovery instead.
                response = ("The same current Research case remains active. I could not select a case-compatible "
                    "execution capability on this attempt, so I did not create or substitute a job, project, or case. "
                    "The Operator is retaining the original case lineage for recovery.")
                update_mission(mission, "OPERATOR_ENTITY_ROUTE_RECOVERING", {
                    "operator_mission_id": operator_result.get("mission_id"),
                    "resolved_entity_type": (lineage.get("case_entity") or {}).get("entity_type") or "RESEARCH_CASE",
                    "resolved_entity_id": lineage.get("case_id"), "no_new_entity_created": True,
                    "semantic_fallback_blocked": True,
                })
                delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
                update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                    "response_mode": "nova_operator_entity_route_recovery",
                    "response_message_ids": delivery.get("message_ids", []),
                })
                return True
            mission_override = mission
        if followup_kind:
            mission = mission_override or create_mission(update_id, chat_id, user_id, text)
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
                    from nova.nexus_mcp_status import internal_receipt_requested
                    response, tool_count, live_result = _exact_research_status_response(
                        job_id, include_internal_receipts=internal_receipt_requested(text))
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
                from nova.nexus_mcp_status import internal_receipt_requested
                response, tool_count, live_result = _exact_research_status_response(
                    job_id, include_internal_receipts=internal_receipt_requested(text))
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
        semantic = resolve_owner_request(text, context=lineage)
        mcp_action_route = None
        if semantic.get("intent") in {"CAPABILITY_QUERY", "COMMUNICATION_ACTION", "BROWSER_ACTION",
                                      "FILE_OR_DOCUMENT_ACTION", "CODE_OR_SYSTEM_ACTION",
                                      "ACTION_NOT_AVAILABLE", "UNKNOWN_OR_AMBIGUOUS"}:
            try:
                from nova.approved_mcp_registry import resolve_approved_mcp_tool_request
                mcp_action_route = resolve_approved_mcp_tool_request(
                    text, owner_authorized=(int(chat_id) == 1288928049 and int(user_id) == 1288928049))
            except Exception as exc:
                _log(f"Approved MCP tool discovery unavailable: {type(exc).__name__}")
            if mcp_action_route:
                semantic = {"intent": "APPROVED_MCP_ACTION", "executor": "hermes_approved_mcp_tool",
                    "mcp_server": mcp_action_route.get("server_id"),
                    "mcp_tool": mcp_action_route.get("name"),
                    "mcp_policy": mcp_action_route.get("policy"), "confidence": 1.0}
        from nexus_agent_platform.workflow_execution import nova_execution_plan
        execution_plan = nova_execution_plan(semantic)
        update_mission(mission, "EXECUTION_CLASSIFIED", {
            "semantic_intent": semantic.get("intent"),
            "execution_plan": execution_plan,
            "model_call_required": execution_plan["model_call_required"],
            "mcp_action_route": ({k: mcp_action_route.get(k) for k in
                ("server_id", "name", "read_write_class", "cost_class", "policy")}
                if mcp_action_route else None),
        })
        if semantic.get("intent") == "APPROVED_MCP_ACTION" and (semantic.get("mcp_policy") or {}).get("decision") != "ALLOW":
            decision = semantic.get("mcp_policy") or {}
            response = (f"The objective is waiting at a governance boundary: {decision.get('decision', 'DENY')} "
                        f"({decision.get('reason', 'POLICY_UNAVAILABLE')}). Nothing was changed."
                        if decision.get("decision") == "APPROVAL_REQUIRED" else
                        "The objective remains active while Nova evaluates another approved route. Nothing was changed, and no action is claimed.")
            update_mission(mission, "WAITING_FOR_APPROVAL" if decision.get("decision") == "APPROVAL_REQUIRED" else "OPERATOR_RECOVERING", {"action_completed": False,
                "read_only": False, "mcp_action_route": semantic, "side_effects": False})
            write_receipt({"type": "nova_approved_mcp_action_blocked", "incoming_update_id": update_id,
                "mission_id": mission["mission_id"], "server_id": semantic.get("mcp_server"),
                "tool_name": semantic.get("mcp_tool"), "policy_decision": decision.get("decision"),
                "result_status": decision.get("reason"), "action_completed": False})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED",
                {"response_message_ids": delivery.get("message_ids", []), "action_completed": False})
            return True
        if semantic.get("intent") == "ACTION_NOT_AVAILABLE":
            response = ("Nova has not verified that all execution paths are exhausted. The objective remains active in recovery; "
                        "nothing was created, changed, sent, or scheduled, and no completion is claimed.")
            update_mission(mission, "OPERATOR_RECOVERING", {"action_completed": False, "read_only": False,
                "semantic_route": semantic, "side_effects": False})
            write_receipt({"type": "nova_operator_recovery_pending", "incoming_update_id": update_id,
                "mission_id": mission["mission_id"], "action_completed": False, "side_effects": False})
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_message_ids": delivery.get("message_ids", []), "action_completed": False})
            return True
        if semantic.get("intent") == "NEXUS_OPERATIONAL_DIAGNOSTIC_AND_REPAIR":
            try:
                diagnostic = _existing_job_operational_diagnostic(chat_id, semantic)
                response = diagnostic["response"]
                diagnostic_receipt = write_receipt({
                    "type": "nova_existing_job_operational_diagnostic",
                    "incoming_update_id": update_id, "mission_id": mission["mission_id"],
                    "job_id": diagnostic.get("job_id"), "job_state": diagnostic.get("status"),
                    "attempt_count": diagnostic.get("attempt_count"),
                    "claimed_by": diagnostic.get("claimed_by"),
                    "tool_count": diagnostic.get("tool_count"),
                    "read_only": True, "job_created": False, "repair_executed": False,
                    "missing_capabilities": diagnostic.get("missing", []),
                    "historical_substitution": False,
                })
                update_mission(mission, "OPERATIONAL_DIAGNOSTIC_READ", {
                    "response_mode": "existing_job_operational_diagnostic",
                    "semantic_route": semantic, "target_job_id": diagnostic.get("job_id"),
                    "target_job_state": diagnostic.get("status"),
                    "target_job_attempt_count": diagnostic.get("attempt_count"),
                    "target_job_claimed_by": diagnostic.get("claimed_by"),
                    "new_job_created": False, "repair_executed": False,
                    "diagnostic_receipt_id": diagnostic_receipt["receipt_id"],
                    "missing_capabilities": diagnostic.get("missing", []),
                })
            except Exception as exc:
                error_type = type(exc).__name__
                _log_error(f"Existing-job operational diagnostic failed: {error_type}: {str(exc)[:180]}")
                response = (
                    "I couldn't complete the read-only diagnosis of the exact current job. "
                    "I did not create another job or substitute historical work.\n"
                    "MISSING_CAPABILITY=existing-job executor diagnostics\n"
                    "MISSING_TOOL_OR_ACTION=nexus_get_research_executor_health and nexus_read_research_executor_logs\n"
                    f"CURRENT_JOB_ID={(load_current_objective_lineage(chat_id) or {}).get('job_id') or 'UNKNOWN'}\n"
                    f"DIAGNOSTIC_ERROR={error_type}\nNEW_JOB_CREATED=NO"
                )
                update_mission(mission, "OPERATIONAL_DIAGNOSTIC_FAILED", {
                    "response_mode": "existing_job_operational_diagnostic",
                    "error_type": error_type, "new_job_created": False,
                    "action_completed": False,
                })
            delivery = _deliver_response(update_id, chat_id, response, mission_id=mission["mission_id"])
            update_mission(mission, "DELIVERED" if delivery.get("state") == "DELIVERED" else "DELIVERY_FAILED", {
                "response_mode": "existing_job_operational_diagnostic",
                "response_message_ids": delivery.get("message_ids", []),
                "new_job_created": False, "repair_executed": False,
            })
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
                    call_exact_job_status, call_status_tool, internal_receipt_requested, render_exact_job_status,
                    render_status_result,
                )
                linked_assignment = find_linked_objective_assignment(text, chat_id=chat_id)
                if linked_assignment:
                    live_result, tool_count = call_exact_job_status(linked_assignment["job_id"])
                    tool_name = "nexus_get_durable_jobs"
                    response = render_exact_job_status(
                        live_result, include_internal_receipts=internal_receipt_requested(text))
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
            if (
                semantic.get("execution_mode") == "RESEARCH_ROOM_MODE"
                or semantic.get("intent") == "RESEARCH_ROOM_REQUEST"
                or bool(re.search(r"\b(?:create (?:a )?(?:new )?research room|open (?:a )?(?:new )?research room|research room)\b", text, re.I))
            ):
                _log(f"LEGACY_RESEARCH_DISPATCH_BLOCKED update={update_id} intent={semantic.get('intent')} mode={semantic.get('execution_mode')}")
                raise RuntimeError("LEGACY_RESEARCH_DISPATCH_FORBIDDEN: Research Room requests must never be dispatched to legacy durable research.")
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
                          "response": "The Google action was not safely matched to a supported operation. The objective remains active for capability recovery; nothing was changed or sent."}
                write_receipt({"type": "nova_google_action_recovery_pending", "incoming_update_id": update_id,
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
            response = action.get("response") or "The file action remains active for capability recovery. Nothing was changed."
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
            response = ("The objective remains active in capability recovery. Nova has not exhausted alternate tools or safe capability acquisition, "
                        "so I cannot claim it is unavailable. Nothing was changed, sent, or scheduled.")
            update_mission(mission, "OPERATOR_RECOVERING", {"action_completed": False, "read_only": False,
                "semantic_route": semantic, "side_effects": False})
            write_receipt({"type": "nova_operator_recovery_pending", "incoming_update_id": update_id,
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
                _run_oracle_primary(update_id, message, chat_id, text, primary_run_id=primary_run_id,
                                    mcp_action_route=mcp_action_route, context_snapshot=context_snapshot)
                if primary_runtime == PRIMARY_RUNTIME_ORACLE
                else _run_hermes_primary(update_id, message, chat_id, text, primary_run_id=primary_run_id)
            )
            approved_mcp_receipt = None
            if mcp_action_route and mcp_action_route.get("read_write_class") == "WRITE" and hermes_record.get("response"):
                approved_mcp_receipt = record_approved_mcp_result(
                    update_id, mission, mcp_action_route, hermes_record.get("response"))
                if not approved_mcp_receipt:
                    hermes_record["response"] = (
                        "ACTION_COMPLETED=NO. I could not verify a receipt from the approved MCP tool, "
                        "so I cannot claim the write succeeded. The tool outcome may need a read-only check.")
                    hermes_record["tools_executed"] = []
                    update_mission(mission, "APPROVED_MCP_ACTION_UNVERIFIED", {
                        "action_completed": False, "read_only": False,
                        "mcp_server": mcp_action_route.get("server_id"),
                        "mcp_tool": mcp_action_route.get("name"),
                        "policy_decision": (mcp_action_route.get("policy") or {}).get("decision")})
                else:
                    hermes_record["tools_executed"] = [f"{mcp_action_route.get('server_id')}.{mcp_action_route.get('name')}"]
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
            if "mission" not in locals():
                mission = mission_override or create_mission(update_id, chat_id, user_id, text)
            if governance_context is None:
                governance_context = _set_owner_turn_governance_context(
                    mission, delivery_update_id=update_id)
            update_mission(mission, "TURN_FAILED", {
                "error_type": type(exc).__name__, "error_message": str(exc)[:500],
                "work_acceptance": "UNKNOWN_UNLESS_DURABLE_JOB_READ_CONFIRMS",
            })
        except Exception:
            pass
        try:
            with stage_execution(
                stage="telegram_send",
                source="scripts/nova/nova_telegram_worker.py:_process_message_inner",
                metadata={"error_type": exc.__class__.__name__, "mission_id": mission.get("mission_id")},
            ):
                delivery = _deliver_response(
                    update_id, chat_id,
                    "I couldn't complete that request because one of my execution steps failed. I haven't confirmed whether Nexus accepted any work, so I won't claim it ran. Your request is still in this conversation; I'll verify durable state before retrying, and you don't need to restate it.",
                    mission_id=mission.get("mission_id"),
                )
            if delivery.get("state") != "DELIVERED":
                _log_error(f"Failure notice delivery did not complete: {delivery.get('last_error') or delivery.get('state')}")
        except Exception as delivery_exc:
            _log_error(f"Failure notice delivery error: {type(delivery_exc).__name__}: {str(delivery_exc)[:300]}")
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
        _process_proactive_communications()

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


def _process_proactive_communications():
    """Check the existing event outbox from the existing Telegram worker."""
    try:
        from proactive_communications import process_once
        proactive = process_once()
        if proactive.get("status") not in {"NO_SEND", "SUPPRESSED"}:
            _log(f"Nova worker: proactive communication {proactive.get('status')}")
    except Exception as exc:
        # Notification errors are observability only; they never affect
        # Research state or the Telegram polling loop.
        _log_error(f"Proactive communication unavailable: {type(exc).__name__}")


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

    _process_proactive_communications()

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
                _process_proactive_communications()
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

            _process_proactive_communications()

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
