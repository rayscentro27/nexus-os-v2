"""Durable, attributable AI-usage accounting for Nexus.

This is a bounded governance ledger, not a FinOps platform.  It extends the
existing runtime-telemetry package (same data tree, same 0600 append-only JSONL
convention, same redaction posture) with a dedicated store for *provider-call*
accounting that the process-lifecycle ``execution_telemetry`` store is not
shaped to hold (per-call token counts, cost class, fallback truth, provider
quota/alert state, retry-guard state).

Policy implemented here:

  NO_UNATTRIBUTED_AI_CALL
    Every recorded call must carry DEPARTMENT, AGENT, (JOB_ID or CASE_ID),
    PROVIDER, MODEL, ROUTING_REASON.  ``record_ai_usage`` raises
    ``UnattributedAICallError`` when attribution is incomplete unless the caller
    explicitly marks the record as an authorized lightweight health probe.

  Cost classes: FREE / INCLUDED_SUBSCRIPTION / PAID_METERED / UNKNOWN.
  Provider states: HEALTHY / WARNING / RATE_LIMITED / USAGE_LIMIT_REACHED / UNAVAILABLE.
  Alert levels: INFO(50) / WATCH(70) / WARNING(85) / CRITICAL(95) / EXHAUSTED(100).

Nothing here enables spend or a paid provider; it only records what happened.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from nexus_agent_platform.runtime.paths import nexus_data_path

EVENT_TYPE = "AI_USAGE"
ALERT_EVENT_TYPE = "AI_PROVIDER_ALERT"
SOURCE_TYPE = "ai_usage_ledger"
LEDGER_ENV = "NEXUS_AI_USAGE_LEDGER_PATH"

COST_CLASSES = frozenset({"FREE", "INCLUDED_SUBSCRIPTION", "PAID_METERED", "UNKNOWN"})
PROVIDER_STATUSES = frozenset({
    "HEALTHY", "WARNING", "RATE_LIMITED", "USAGE_LIMIT_REACHED", "UNAVAILABLE", "UNKNOWN",
})
# Numeric-capacity alert thresholds (Phase 6).
ALERT_THRESHOLDS = ((100, "EXHAUSTED"), (95, "CRITICAL"), (85, "WARNING"), (70, "WATCH"), (50, "INFO"))
ALERT_ORDER = {"NONE": 0, "INFO": 1, "WATCH": 2, "WARNING": 3, "CRITICAL": 4, "EXHAUSTED": 5}
# Provider states that mean "no numeric capacity but already out of capacity".
EXHAUSTION_STATES = frozenset({"USAGE_LIMIT_REACHED", "UNAVAILABLE"})

REQUIRED_ATTRIBUTION = ("DEPARTMENT", "AGENT", "PROVIDER", "MODEL", "ROUTING_REASON")
CODEX_CAPACITY_STATES = ("NORMAL", "WATCH", "RESTRICTED", "CRITICAL", "EXHAUSTED")
DEFAULT_BLOCK_SECONDS = 15 * 60

_SECRET_RE = (
    re.compile(r"sk-or-v1-[A-Za-z0-9]{10,}"),
    re.compile(r"\d{9,10}:[A-Za-z0-9_-]{35}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|authorization)\s*[=:]\s*\S+"),
)


class UnattributedAICallError(ValueError):
    """Raised when a provider call is recorded without required attribution."""


# --------------------------------------------------------------------------- paths
def ledger_store_path() -> Path:
    configured = os.environ.get(LEDGER_ENV)
    if configured:
        return Path(configured).expanduser()
    return nexus_data_path("runtime", "ai_usage", "ledger.jsonl")


def _state_path(name: str) -> Path:
    ledger = ledger_store_path()
    return ledger.parent / name


def _prepare(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    if not path.exists():
        path.touch(mode=0o600)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        text = value
        for pattern in _SECRET_RE:
            text = pattern.sub("[REDACTED]", text)
        return text[:500]
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value[:50]]
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now() -> str:
    return _now().isoformat()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# --------------------------------------------------------------------------- cost class
def cost_class_for(provider: str, model: str = "") -> str:
    p = (provider or "").strip().lower()
    m = (model or "").strip().lower()
    if p in ("openai-codex", "openai_codex", "codex"):
        return "INCLUDED_SUBSCRIPTION"
    if p == "openrouter":
        return "FREE" if m.endswith(":free") else "PAID_METERED"
    if p in ("", "unknown"):
        return "UNKNOWN"
    return "UNKNOWN"


# --------------------------------------------------------------------------- append / read
def _append(record: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or ledger_store_path()
    _prepare(target)
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return record


def read_ledger(path: Optional[Path] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    target = path or ledger_store_path()
    if not target.exists():
        return []
    out: List[Dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("SOURCE_TYPE") == SOURCE_TYPE:
                out.append(rec)
    return out[-limit:] if limit else out


# --------------------------------------------------------------------------- record (Phase 2/3/4/11)
def record_ai_usage(
    *,
    department: str,
    agent: str,
    provider: str,
    model: str,
    routing_reason: str,
    job_id: str = "",
    case_id: str = "",
    work_item_id: str = "",
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cached_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    estimated_cost: Optional[float] = None,
    actual_cost: Optional[float] = None,
    cost_class: str = "",
    fallback_used: bool = False,
    fallback_position: Optional[int] = None,
    request_duration_ms: Optional[int] = None,
    success: bool = True,
    failure_reason: str = "",
    provider_status: str = "UNKNOWN",
    quota_state: Any = "UNKNOWN",
    retry_number: Optional[int] = None,
    prior_failure_reason: str = "",
    token_data: str = "",
    probe: bool = False,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Record one attributable provider call (primary OR a distinct fallback attempt).

    Primary and fallback attempts must be recorded as SEPARATE events; do not
    collapse a Codex-429 + OpenRouter-success into one opaque record.
    """
    department = (department or "").strip().upper()
    agent = (agent or "").strip().upper()
    provider = (provider or "").strip()
    model = (model or "").strip()
    routing_reason = (routing_reason or "").strip()

    if not probe:
        missing = [k for k, v in {
            "DEPARTMENT": department, "AGENT": agent, "PROVIDER": provider,
            "MODEL": model, "ROUTING_REASON": routing_reason,
        }.items() if not v]
        if not (job_id or case_id):
            missing.append("JOB_ID_OR_CASE_ID")
        if missing:
            raise UnattributedAICallError(
                "NO_UNATTRIBUTED_AI_CALL: missing " + ",".join(missing)
            )

    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    if not token_data:
        token_data = "AVAILABLE" if total_tokens is not None else "UNAVAILABLE"
    if not cost_class:
        cost_class = cost_class_for(provider, model)
    if cost_class not in COST_CLASSES:
        cost_class = "UNKNOWN"
    if provider_status not in PROVIDER_STATUSES:
        provider_status = "UNKNOWN"
    if estimated_cost is None:
        estimated_cost = 0 if cost_class in ("FREE", "INCLUDED_SUBSCRIPTION") else None

    record = {
        "TIMESTAMP": _utc_now(),
        "EVENT_TYPE": EVENT_TYPE,
        "SOURCE_TYPE": SOURCE_TYPE,
        "EVENT_ID": f"aiu_{uuid.uuid4().hex}",
        "DEPARTMENT": department,
        "AGENT": agent,
        "JOB_ID": job_id or None,
        "CASE_ID": case_id or None,
        "WORK_ITEM_ID": work_item_id or None,
        "PROVIDER": provider,
        "MODEL": model,
        "INPUT_TOKENS": input_tokens,
        "OUTPUT_TOKENS": output_tokens,
        "CACHED_TOKENS": cached_tokens,
        "TOTAL_TOKENS": total_tokens,
        "TOKEN_DATA": token_data,
        "ESTIMATED_COST": estimated_cost,
        "ACTUAL_COST": actual_cost,
        "COST_CLASS": cost_class,
        "ROUTING_REASON": routing_reason,
        "FALLBACK_USED": bool(fallback_used),
        "FALLBACK_POSITION": fallback_position,
        "REQUEST_DURATION_MS": request_duration_ms,
        "SUCCESS": bool(success),
        "FAILURE_REASON": _redact(failure_reason) or None,
        "PROVIDER_STATUS": provider_status,
        "QUOTA_STATE": quota_state if quota_state not in (None, "") else "UNKNOWN",
        "RETRY_NUMBER": retry_number,
        "PRIOR_FAILURE_REASON": _redact(prior_failure_reason) or None,
        "PROBE": bool(probe),
    }
    _append(record, path)

    # A recorded exhaustion signal immediately updates provider-block + alert state.
    if provider_status in EXHAUSTION_STATES or (not success and _looks_exhausted(failure_reason)):
        note_provider_exhaustion(provider, reason=failure_reason or provider_status, path=path)
        raise_provider_alert(provider, provider_status="USAGE_LIMIT_REACHED",
                             reason=failure_reason or provider_status, path=path)
    return record


def _looks_exhausted(reason: str) -> bool:
    r = (reason or "").lower()
    return any(tok in r for tok in ("429", "usage_limit", "rate limit", "rate_limit", "quota", "insufficient_quota", "overloaded"))


# ----------------------------------------------------------------- Nova turn helper (Phase 3)
def record_nova_turn(
    *,
    job_id: str,
    primary_provider: str,
    primary_model: str,
    primary_success: bool,
    fallback_provider: str = "",
    fallback_model: str = "",
    fallback_tokens: Optional[Dict[str, int]] = None,
    primary_failure_reason: str = "",
    routing_reason: str = "NOVA_CONVERSATION",
    path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Record a Nova/Hermes conversational turn as distinct attempts.

    Preserves provider-specific truth: the failed Codex primary and the
    successful OpenRouter-free fallback are two events, not one.
    """
    events: List[Dict[str, Any]] = []
    if not primary_success:
        events.append(record_ai_usage(
            department="NOVA", agent="HERMES", job_id=job_id,
            provider=primary_provider, model=primary_model,
            routing_reason=routing_reason, success=False,
            failure_reason=primary_failure_reason or "primary_provider_failed",
            provider_status="USAGE_LIMIT_REACHED" if _looks_exhausted(primary_failure_reason) else "UNAVAILABLE",
            fallback_used=False, path=path,
        ))
    else:
        events.append(record_ai_usage(
            department="NOVA", agent="HERMES", job_id=job_id,
            provider=primary_provider, model=primary_model,
            routing_reason=routing_reason, success=True,
            provider_status="HEALTHY", fallback_used=False, path=path,
        ))
    if fallback_provider:
        tk = fallback_tokens or {}
        events.append(record_ai_usage(
            department="NOVA", agent="HERMES", job_id=job_id,
            provider=fallback_provider, model=fallback_model,
            routing_reason=f"FALLBACK_AFTER_PRIMARY:{primary_provider}",
            input_tokens=tk.get("input"), output_tokens=tk.get("output"),
            cached_tokens=tk.get("cache_read"), total_tokens=tk.get("total"),
            success=True, provider_status="HEALTHY",
            fallback_used=True, fallback_position=1, path=path,
        ))
    return events


# --------------------------------------------------------------------------- alerts (Phase 6)
def classify_alert(percent: Optional[float]) -> str:
    if percent is None:
        return "NONE"
    for threshold, level in ALERT_THRESHOLDS:
        if percent >= threshold:
            return level
    return "NONE"


def _alert_state(path: Optional[Path] = None) -> Dict[str, Any]:
    p = _state_path("provider_alert_state.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            return {}
    return {}


def _write_alert_state(state: Dict[str, Any]) -> None:
    p = _state_path("provider_alert_state.json")
    _prepare(p)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(p)


def raise_provider_alert(
    provider: str,
    *,
    percent: Optional[float] = None,
    provider_status: str = "",
    reason: str = "",
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Emit a durable, deduplicated provider alert.

    Numeric capacity -> threshold level.  No numeric capacity but a
    429/usage_limit/unavailable signal -> EXHAUSTED.  Repeated identical state
    is deduplicated: no second durable alert until the level materially changes.
    """
    provider = (provider or "").strip()
    level = classify_alert(percent)
    if provider_status in EXHAUSTION_STATES and ALERT_ORDER[level] < ALERT_ORDER["EXHAUSTED"]:
        level = "EXHAUSTED"
    if level == "NONE":
        return {"raised": False, "alert_level": "NONE", "deduped": False, "provider": provider}

    state = _alert_state()
    prior = (state.get(provider) or {}).get("alert_level", "NONE")
    if prior == level:
        return {"raised": False, "alert_level": level, "deduped": True, "provider": provider}

    alert = {
        "TIMESTAMP": _utc_now(),
        "EVENT_TYPE": ALERT_EVENT_TYPE,
        "SOURCE_TYPE": SOURCE_TYPE,
        "EVENT_ID": f"alr_{uuid.uuid4().hex}",
        "PROVIDER": provider,
        "ALERT_LEVEL": level,
        "CAPACITY_PERCENT": percent,
        "PROVIDER_STATUS": provider_status or "UNKNOWN",
        "REASON": _redact(reason) or None,
        "VISIBLE_TO": ["SYSTEMS", "NOVA", "RAY"],
    }
    _append(alert, path)
    state[provider] = {"alert_level": level, "at": alert["TIMESTAMP"]}
    _write_alert_state(state)
    return {"raised": True, "alert_level": level, "deduped": False, "provider": provider}


def clear_provider_alert(provider: str) -> None:
    state = _alert_state()
    if provider in state:
        del state[provider]
        _write_alert_state(state)


# ------------------------------------------------------- retry / provider-block guard (Phase 8)
def _block_state() -> Dict[str, Any]:
    p = _state_path("provider_block_state.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            return {}
    return {}


def _write_block_state(state: Dict[str, Any]) -> None:
    p = _state_path("provider_block_state.json")
    _prepare(p)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(p)


def note_provider_exhaustion(
    provider: str,
    *,
    reason: str = "",
    resume_after: Optional[str] = None,
    block_seconds: int = DEFAULT_BLOCK_SECONDS,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Mark a provider blocked so repeated identical attempts are deferred."""
    provider = (provider or "").strip()
    resume = resume_after or (_now() + timedelta(seconds=block_seconds)).isoformat()
    state = _block_state()
    state[provider] = {"blocked": True, "reason": _redact(reason), "resume_after": resume,
                       "blocked_at": _utc_now()}
    _write_block_state(state)
    return state[provider]


def clear_provider_block(provider: str) -> None:
    state = _block_state()
    if provider in state:
        del state[provider]
        _write_block_state(state)


def provider_blocked(provider: str) -> Dict[str, Any]:
    entry = _block_state().get((provider or "").strip())
    if not entry or not entry.get("blocked"):
        return {"blocked": False}
    resume = _parse_dt(entry.get("resume_after"))
    if resume and _now() >= resume:
        return {"blocked": False, "expired": True, "resume_after": entry.get("resume_after")}
    return {"blocked": True, "reason": entry.get("reason"), "resume_after": entry.get("resume_after")}


def should_defer_retry(
    job_id: str,
    provider: str,
    model: str = "",
    *,
    prior_failure_reason: str = "",
) -> Dict[str, Any]:
    """Provider-safety guard: should this repeated attempt be deferred?

    Returns a decision dict.  When deferred, the caller must preserve the
    job/case and NOT immediately re-hit the provider.  This is not a Research
    redesign; it only stops uncontrolled identical retries at exhaustion.
    """
    block = provider_blocked(provider)
    if block.get("blocked"):
        return {
            "defer": True, "reason": "PROVIDER_BLOCKED",
            "provider": provider, "job_id": job_id, "model": model,
            "resume_after": block.get("resume_after"),
            "action": "RETRY_DEFERRED", "case_preserved": True,
            "prior_failure_reason": prior_failure_reason or block.get("reason"),
        }
    return {"defer": False, "reason": "PROVIDER_AVAILABLE", "provider": provider,
            "job_id": job_id, "model": model, "action": "PROCEED", "case_preserved": True}


# --------------------------------------------------------- Codex capacity governance (Phase 7)
def set_codex_capacity_state(state: str, *, reason: str = "") -> Dict[str, Any]:
    state = (state or "").strip().upper()
    if state not in CODEX_CAPACITY_STATES:
        raise ValueError(f"invalid codex capacity state: {state}")
    p = _state_path("codex_capacity_state.json")
    _prepare(p)
    payload = {"CODEX_CAPACITY_STATE": state, "REASON": _redact(reason), "UPDATED_AT": _utc_now(),
               "POLICY": {
                   "NORMAL": "normal existing behavior",
                   "WATCH": "flag elevated consumption",
                   "RESTRICTED": "noncritical Research candidates for cheaper routing after Research optimization is certified",
                   "CRITICAL": "preserve Codex for Nova/Hermes + genuinely high-value/TIER-3 work",
                   "EXHAUSTED": "Nova uses approved free fallback; Research preserves cases and does not retry Codex blindly",
               }}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(p)
    return payload


def get_codex_capacity_state() -> Dict[str, Any]:
    p = _state_path("codex_capacity_state.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            pass
    # Derive from observed provider health when no explicit state is set.
    health = provider_health()
    codex = health.get("openai-codex", {})
    derived = "EXHAUSTED" if codex.get("status") in EXHAUSTION_STATES else "NORMAL"
    return {"CODEX_CAPACITY_STATE": derived, "REASON": "derived_from_observed_provider_health",
            "UPDATED_AT": None, "DERIVED": True}


# --------------------------------------------------------------------------- health / summary
def provider_health(events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Latest observed status per provider from recent ledger events + block state."""
    evs = events if events is not None else read_ledger()
    latest: Dict[str, Dict[str, Any]] = {}
    for rec in evs:
        if rec.get("EVENT_TYPE") != EVENT_TYPE:
            continue
        provider = rec.get("PROVIDER")
        if not provider:
            continue
        ts = rec.get("TIMESTAMP") or ""
        cur = latest.get(provider)
        if cur is None or ts >= cur.get("_ts", ""):
            latest[provider] = {
                "status": rec.get("PROVIDER_STATUS", "UNKNOWN"),
                "quota_state": rec.get("QUOTA_STATE", "UNKNOWN"),
                "cost_class": rec.get("COST_CLASS", "UNKNOWN"),
                "last_success": rec.get("SUCCESS"),
                "_ts": ts,
            }
    blocks = _block_state()
    for provider, info in latest.items():
        b = provider_blocked(provider)
        info["blocked"] = bool(b.get("blocked"))
        info["resume_after"] = b.get("resume_after")
        info.pop("_ts", None)
    return latest


def _phoenix_day_start(now: Optional[datetime] = None) -> datetime:
    current = now or _now()
    phoenix = current.astimezone(timezone(timedelta(hours=-7)))
    midnight = phoenix.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc)


def _window_start(window: str, now: Optional[datetime] = None) -> Optional[datetime]:
    current = now or _now()
    w = (window or "today").lower()
    if w in ("today", "day", "since_midnight"):
        return _phoenix_day_start(current)
    if w in ("last_7_days", "7d", "week", "weekly"):
        return current - timedelta(days=7)
    if w in ("all", ""):
        return None
    return _phoenix_day_start(current)


def usage_summary(window: str = "today", now: Optional[datetime] = None) -> Dict[str, Any]:
    """Compact, Nova-readable usage summary for a window (Phase 9/10)."""
    current = now or _now()
    start = _window_start(window, current)
    evs = read_ledger()
    usage = [e for e in evs if e.get("EVENT_TYPE") == EVENT_TYPE]
    if start:
        usage = [e for e in usage if (_parse_dt(e.get("TIMESTAMP")) or current) >= start]

    req_by_dept: Dict[str, int] = {}
    req_by_provider: Dict[str, int] = {}
    tok_by_dept: Dict[str, int] = {}
    tok_by_provider: Dict[str, int] = {}
    job_tokens: Dict[str, int] = {}
    failed = fallback = retries = 0
    for e in usage:
        dept = e.get("DEPARTMENT") or "UNKNOWN"
        prov = e.get("PROVIDER") or "UNKNOWN"
        req_by_dept[dept] = req_by_dept.get(dept, 0) + 1
        req_by_provider[prov] = req_by_provider.get(prov, 0) + 1
        tot = e.get("TOTAL_TOKENS")
        if isinstance(tot, int):
            tok_by_dept[dept] = tok_by_dept.get(dept, 0) + tot
            tok_by_provider[prov] = tok_by_provider.get(prov, 0) + tot
            jid = e.get("JOB_ID") or e.get("CASE_ID") or "UNATTRIBUTED"
            job_tokens[jid] = job_tokens.get(jid, 0) + tot
        if not e.get("SUCCESS"):
            failed += 1
        if e.get("FALLBACK_USED"):
            fallback += 1
        if isinstance(e.get("RETRY_NUMBER"), int) and e["RETRY_NUMBER"] > 0:
            retries += 1

    top5 = sorted(job_tokens.items(), key=lambda kv: kv[1], reverse=True)[:5]
    alert_events = [e for e in evs if e.get("EVENT_TYPE") == ALERT_EVENT_TYPE]
    current_alert = "NONE"
    state = _alert_state()
    for info in state.values():
        if ALERT_ORDER.get(info.get("alert_level", "NONE"), 0) > ALERT_ORDER.get(current_alert, 0):
            current_alert = info.get("alert_level", "NONE")

    return {
        "WINDOW": window,
        "WINDOW_START": start.isoformat() if start else None,
        "WINDOW_END": current.isoformat(),
        "REQUESTS_BY_DEPARTMENT": req_by_dept,
        "REQUESTS_BY_PROVIDER": req_by_provider,
        "TOKENS_BY_DEPARTMENT": tok_by_dept,
        "TOKENS_BY_PROVIDER": tok_by_provider,
        "FAILED_PROVIDER_CALLS": failed,
        "FALLBACK_CALLS": fallback,
        "RETRIES": retries,
        "TOP_5_JOBS_BY_USAGE": [{"JOB_OR_CASE": k, "TOTAL_TOKENS": v} for k, v in top5],
        "CURRENT_PROVIDER_HEALTH": provider_health(evs),
        "CURRENT_ALERT_LEVEL": current_alert,
        "CODEX_CAPACITY_STATE": get_codex_capacity_state().get("CODEX_CAPACITY_STATE"),
        "TOTAL_REQUESTS": len(usage),
        "COST_CLASS_LEGEND": {
            "openai-codex": "INCLUDED_SUBSCRIPTION",
            "openrouter :free": "FREE",
            "openrouter paid": "PAID_METERED (DISABLED)",
        },
        "PRE_INSTRUMENTATION_TOKEN_TOTALS": "UNAVAILABLE",
        "OPENROUTER_PAID_ENABLED": "NO",
        "SOURCE_TYPE": SOURCE_TYPE,
    }
