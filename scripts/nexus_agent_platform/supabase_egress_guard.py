"""Local, bounded Supabase REST egress accounting (no request values or secrets)."""
from __future__ import annotations

import json
import os
import fcntl
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "data" / "runtime" / "supabase_egress_guard.json"
LARGE_RESPONSE_BYTES = 1_000_000
CONTROL_PLANE_RESPONSE_WARNING_BYTES = 256_000
SAFE_MODE_STATE = ROOT / "data" / "runtime" / "supabase_egress_safe_mode.json"
WAKE_BUDGET_STATE = ROOT / "data" / "runtime" / "research_sources_wake_budget.json"
SYSTEMS_INCIDENTS = ROOT / "data" / "runtime" / "systems_workflow_runs.jsonl"
MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE = 20
JOB_EGRESS_DIR = ROOT / "data" / "runtime" / "job_egress"
JOB_MAX_REQUESTS = 120
JOB_MAX_RESPONSE_BYTES = 2_000_000
_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_LOCK = threading.RLock()
_CACHE_MAX_ENTRIES = 32
_CACHE_MAX_BYTES = 1_000_000
_CACHE_ALLOWED_PREFIXES = ("template:", "settings:", "provider:", "environment:", "capability:", "scheduler:")


class ResearchSourcesBurstExceeded(RuntimeError):
    """The current wake exhausted its measured research_sources request budget."""


class LargeControlPlaneQueryBlocked(RuntimeError):
    """A full proactive-memory payload query is broader than the safe contract."""


class JobEgressBudgetExceeded(RuntimeError):
    """One bounded worker exceeded its job-scoped Supabase budget."""


def job_egress_snapshot(job_id: str) -> dict:
    if not job_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in job_id):
        return {}
    try:
        return json.loads((JOB_EGRESS_DIR / f"{job_id}.json").read_text())
    except (OSError, ValueError):
        return {"job_id": job_id, "request_count": 0, "response_bytes": 0, "retry_count": 0,
                "largest_response": 0, "endpoint_counts": {}}


def _update_job_egress(*, method: str, path: str, response_bytes: int = 0, retries: int = 0, preflight: bool = False) -> None:
    job_id = os.environ.get("NEXUS_DURABLE_JOB_ID", "")
    if not job_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in job_id): return
    JOB_EGRESS_DIR.mkdir(parents=True, exist_ok=True)
    target = JOB_EGRESS_DIR / f"{job_id}.json"
    with (JOB_EGRESS_DIR / f"{job_id}.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = job_egress_snapshot(job_id)
        state.setdefault("request_count", 0); state.setdefault("response_bytes", 0)
        state.setdefault("retry_count", 0); state.setdefault("largest_response", 0)
        state.setdefault("endpoint_counts", {})
        if preflight:
            request_budget=JOB_MAX_REQUESTS; response_budget=JOB_MAX_RESPONSE_BYTES
            try:
                budget=json.loads(os.environ.get("NEXUS_JOB_BUDGET","{}"))
                request_budget=min(request_budget,max(1,int(budget.get("max_requests",request_budget))))
                response_budget=min(response_budget,max(1,int(budget.get("max_response_bytes",response_budget))))
            except (ValueError,TypeError): pass
            if int(state["request_count"]) >= request_budget or int(state["response_bytes"]) >= response_budget:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                raise JobEgressBudgetExceeded(f"JOB_EGRESS_BUDGET_EXCEEDED:{job_id}")
            state["request_count"] += 1
            endpoint = urlsplit(path).path.rstrip("/").split("/")[-1][:100] or "unknown"
            state["endpoint_counts"][endpoint] = int(state["endpoint_counts"].get(endpoint, 0)) + 1
        else:
            size = max(0, int(response_bytes)); state["response_bytes"] += size
            state["largest_response"] = max(int(state["largest_response"]), size)
            state["retry_count"] += max(0, int(retries))
            endpoint = urlsplit(path).path.rstrip("/").split("/")[-1][:100] or "unknown"
            response_budget=JOB_MAX_RESPONSE_BYTES
            try: response_budget=min(response_budget,max(1,int(json.loads(os.environ.get("NEXUS_JOB_BUDGET","{}")).get("max_response_bytes",response_budget))))
            except (ValueError,TypeError): pass
            if state["response_bytes"] > response_budget or size > response_budget:
                state["budget_exceeded"] = True
                try:
                    with SYSTEMS_INCIDENTS.open("a", encoding="utf-8") as incident_file:
                        incident_file.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "component": "JOB_SCOPED_SUPABASE_EGRESS", "status": "DEGRADED", "job_id": job_id, "endpoint": endpoint, "response_bytes": size, "next_workflow": "DURABLE_JOB_EGRESS_RECOVERY"}, separators=(",", ":")) + "\n")
                except OSError: pass
        fd, tmp = tempfile.mkstemp(prefix="job-egress-", suffix=".tmp", dir=JOB_EGRESS_DIR)
        try:
            with os.fdopen(fd, "w") as output: json.dump(state, output, separators=(",", ":"))
            os.chmod(tmp, 0o600); os.replace(tmp, target)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="research-budget-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, separators=(",", ":"))
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def preflight_request(method: str, path: str) -> None:
    """Trace and enforce the evidence-based research_sources budget per wake.

    The lock file is shared across forked heartbeat workers, so independent
    child processes consume the same wake allowance atomically.
    """
    _update_job_egress(method=method, path=path, preflight=True)
    parsed = urlsplit(path)
    table = parsed.path.rstrip("/").split("/")[-1]
    if table == "research_proactive_memory":
        params = parse_qs(parsed.query)
        fields = [field.strip().split(":", 1)[-1] for field in params.get("select", [""])[0].split(",")]
        if "payload" in fields:
            limit = params.get("limit", [""])[0]
            bounded_limit = limit.isdigit() and 0 < int(limit) <= 100
            exact_id = any(value.startswith("eq.") for value in params.get("memory_id", []))
            case_filter = any(value.startswith("in.(RESEARCH_CASE,PROACTIVE_RESEARCH_CASE)")
                              for value in params.get("memory_kind", []))
            if not bounded_limit or not (exact_id and int(limit) <= 1 or case_filter):
                raise LargeControlPlaneQueryBlocked("unbounded research_proactive_memory payload read blocked")
    if table != "research_sources":
        return
    from nexus_agent_platform.research_sources_trace import trace_request
    trace = trace_request(method, path) or {}
    wake_id = os.environ.get("NEXUS_WAKE_ID", "").strip()
    if not wake_id or len(wake_id) > 96:
        return
    caller = f"{str(trace.get('caller_module') or 'unknown')}.{str(trace.get('caller_function') or 'unknown')}"[:180]
    limit = max(1, int(os.environ.get("NEXUS_RESEARCH_SOURCES_MAX_CALLS_PER_WAKE",
                                     MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE)))
    WAKE_BUDGET_STATE.parent.mkdir(parents=True, exist_ok=True)
    with WAKE_BUDGET_STATE.open("a+", encoding="utf-8") as handle:
        os.chmod(WAKE_BUDGET_STATE, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        try: state = json.loads(handle.read() or "{}")
        except (ValueError, TypeError): state = {}
        wakes = state.get("wakes") if isinstance(state.get("wakes"), dict) else {}
        entry = wakes.setdefault(wake_id, {"calls": 0, "blocked": 0, "callers": {}, "incident_emitted": False})
        if int(entry.get("calls", 0)) >= limit:
            entry["blocked"] = int(entry.get("blocked", 0)) + 1
            entry.setdefault("blocked_callers", {})[caller] = int(entry.get("blocked_callers", {}).get(caller, 0)) + 1
            state["wakes"] = dict(list(wakes.items())[-16:])
            handle.seek(0); handle.truncate(); json.dump(state, handle, separators=(",", ":")); handle.flush(); os.fsync(handle.fileno())
            should_emit = not entry.get("incident_emitted")
            entry["incident_emitted"] = True
            # Persist the incident marker after first-writer selection.
            handle.seek(0); handle.truncate(); json.dump(state, handle, separators=(",", ":")); handle.flush(); os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            if should_emit:
                try:
                    SYSTEMS_INCIDENTS.parent.mkdir(parents=True, exist_ok=True)
                    incident = {"at": datetime.now(timezone.utc).isoformat(), "component": "SUPABASE_RESEARCH_SOURCES_BURST_GUARD",
                                "status": "DEGRADED", "wake_id": wake_id, "allowed_calls": limit,
                                "attempted_call": int(entry["calls"]) + int(entry["blocked"]),
                                "caller_breakdown": entry.get("callers", {}),
                                "blocked_caller_breakdown": entry.get("blocked_callers", {}),
                                "next_workflow": "SUPABASE_EGRESS_BURST_RECOVERY"}
                    with SYSTEMS_INCIDENTS.open("a", encoding="utf-8") as out:
                        out.write(json.dumps(incident, separators=(",", ":")) + "\n")
                except OSError:
                    pass
            raise ResearchSourcesBurstExceeded(f"research_sources wake budget exceeded ({limit})")
        entry["calls"] = int(entry.get("calls", 0)) + 1
        entry.setdefault("callers", {})[caller] = int(entry.get("callers", {}).get(caller, 0)) + 1
        state["wakes"] = dict(list(wakes.items())[-16:])
        handle.seek(0); handle.truncate(); json.dump(state, handle, separators=(",", ":")); handle.flush(); os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def safe_mode_enabled() -> bool:
    try:
        state = json.loads(SAFE_MODE_STATE.read_text())
        return bool(state.get("enabled"))
    except (OSError, ValueError, TypeError):
        return os.environ.get("SUPABASE_EGRESS_SAFE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def set_safe_mode(enabled: bool, *, reason: str = "operator_or_systems") -> dict:
    state = {"enabled": bool(enabled), "changed_at": datetime.now(timezone.utc).isoformat(),
             "reason": str(reason)[:120]}
    SAFE_MODE_STATE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="egress-mode-", suffix=".tmp", dir=SAFE_MODE_STATE.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream, separators=(",", ":"))
        os.chmod(temp, 0o600)
        os.replace(temp, SAFE_MODE_STATE)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    if enabled:
        invalidate_cache()
    return state


def invalidate_cache(prefix: str | None = None) -> None:
    with _CACHE_LOCK:
        if prefix is None:
            _CACHE.clear()
        else:
            for key in list(_CACHE):
                if key.startswith(prefix): _CACHE.pop(key, None)


def cached_static(key: str, loader, *, ttl_seconds: int = 300):
    """Small process-local cache for explicitly approved non-PII configuration."""
    if not key.startswith(_CACHE_ALLOWED_PREFIXES):
        raise ValueError("CACHE_KEY_NOT_ALLOWLISTED")
    ttl = max(1, min(int(ttl_seconds), 3600))
    now = time.monotonic()
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item and item[0] > now:
            _record_cache(True)
            return item[1]
    value = loader()
    try:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
    except (TypeError, ValueError):
        return value
    if len(encoded) <= _CACHE_MAX_BYTES:
        with _CACHE_LOCK:
            while len(_CACHE) >= _CACHE_MAX_ENTRIES:
                _CACHE.pop(next(iter(_CACHE)))
            _CACHE[key] = (now + ttl, value)
    _record_cache(False)
    return value


def _record_cache(hit: bool) -> None:
    try:
        data = snapshot()
        data["cache_lookups"] = int(data.get("cache_lookups", 0)) + 1
        data["cache_hits"] = int(data.get("cache_hits", 0)) + int(hit)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix="egress-", suffix=".tmp", dir=STATE.parent)
        try:
            with os.fdopen(fd, "w") as stream: json.dump(data, stream, separators=(",", ":"))
            os.replace(temp, STATE)
        finally:
            if os.path.exists(temp): os.unlink(temp)
    except Exception:
        pass


def _day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def record_request(method: str, path: str, status: int, response_bytes: int,
                   *, rows: int = 0, retries: int = 0, cache_hit: bool = False,
                   trace: bool = True) -> None:
    """Aggregate safe counters by endpoint/table. Never store URL parameters."""
    try: _update_job_egress(method=method, path=path, response_bytes=response_bytes, retries=retries)
    except Exception: pass
    try:
        # Central attribution covers guarded Supabase clients beyond the shared
        # script and feeder adapters. This is local-only and query-value safe.
        if trace:
            from nexus_agent_platform.research_sources_trace import trace_request
            trace_request(method, path)
        parsed = urlsplit(path)
        table = parsed.path.rstrip("/").split("/")[-1][:100] or "unknown"
        select = parse_qs(parsed.query).get("select", [""])[0]
        field_count = 0 if select in ("", "*") else min(100, len(select.split(",")))
        STATE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(STATE.read_text())
        except (OSError, ValueError):
            data = {"day": _day(), "request_count": 0, "approx_bytes": 0,
                    "large_query_count": 0, "retry_count": 0, "cache_hits": 0,
                    "cache_lookups": 0, "status_counts": {}, "http_522_count": 0, "endpoints": {}}
        if data.get("day") != _day():
            data = {"day": _day(), "request_count": 0, "approx_bytes": 0,
                    "large_query_count": 0, "retry_count": 0, "cache_hits": 0,
                    "cache_lookups": 0, "status_counts": {}, "http_522_count": 0, "endpoints": {}}
        size = max(0, int(response_bytes))
        data["request_count"] += 1
        data["approx_bytes"] += size
        data["large_query_count"] += int(size >= LARGE_RESPONSE_BYTES)
        data["retry_count"] += max(0, int(retries))
        data["cache_lookups"] += 1
        data["cache_hits"] += int(cache_hit)
        status_key = f"{int(status) // 100}xx" if int(status) > 0 else "000"
        status_counts = data.setdefault("status_counts", {})
        status_counts[status_key] = int(status_counts.get(status_key, 0)) + 1
        data["http_522_count"] = int(data.get("http_522_count", 0)) + int(int(status) == 522)
        endpoints = data.setdefault("endpoints", {})
        entry = endpoints.setdefault(table, {"calls": 0, "rows": 0, "approx_bytes": 0,
                                             "selected_field_count": field_count,
                                             "max_response_bytes": 0,
                                             "last_status": 0, "last_at": None})
        if table == "research_proactive_memory":
            params = parse_qs(parsed.query)
            selected = [item.split(":", 1)[0].strip()[:64]
                        for item in params.get("select", [""])[0].split(",")[:50]]
            filters = []
            for key, values in params.items():
                if key in {"select", "order", "limit", "offset", "on_conflict", "columns"}:
                    continue
                operator = (values[0].split(".", 1)[0] if values and "." in values[0] else "eq")[:20]
                filters.append({"field": key[:64], "operator": operator})
            shape = {"method": str(method).upper()[:10], "selected_fields": selected,
                     "filters": filters[:20], "limit": params.get("limit", [None])[0],
                     "order": params.get("order", [None])[0]}
            entry["last_query_shape"] = shape
            shapes = entry.setdefault("query_shapes", {})
            shape_key = json.dumps(shape, sort_keys=True, separators=(",", ":"))
            shapes[shape_key] = int(shapes.get(shape_key, 0)) + 1
            if len(shapes) > 8:
                for old_shape in list(shapes)[:-8]:
                    shapes.pop(old_shape, None)
        entry["calls"] += 1
        entry["rows"] += max(0, int(rows))
        entry["approx_bytes"] += size
        entry["max_response_bytes"] = max(int(entry.get("max_response_bytes", 0)), size)
        entry["last_status"] = int(status)
        entry["last_at"] = datetime.now(timezone.utc).isoformat()
        # Cap endpoint cardinality so this local guard cannot grow without bound.
        if len(endpoints) > 40:
            keep = sorted(endpoints.items(), key=lambda item: item[1].get("last_at") or "", reverse=True)[:40]
            data["endpoints"] = dict(keep)
        total_bytes = data["approx_bytes"]
        elevated = int(os.environ.get("NEXUS_SUPABASE_EGRESS_ELEVATED_BYTES", 100_000_000))
        high = int(os.environ.get("NEXUS_SUPABASE_EGRESS_HIGH_BYTES", 500_000_000))
        critical = int(os.environ.get("NEXUS_SUPABASE_EGRESS_CRITICAL_BYTES", 1_000_000_000))
        data["thresholds_bytes"] = {"elevated": elevated, "high": high, "critical": critical}
        data["state"] = ("CRITICAL" if total_bytes >= critical else
                         "HIGH" if total_bytes >= high else
                         "ELEVATED" if total_bytes >= elevated else "NORMAL")
        large_control_response = table == "research_proactive_memory" and size > CONTROL_PLANE_RESPONSE_WARNING_BYTES
        if large_control_response:
            data["large_control_plane_response_count"] = int(data.get("large_control_plane_response_count", 0)) + 1
            data["largest_control_plane_response_bytes"] = max(
                int(data.get("largest_control_plane_response_bytes", 0)), size
            )
        fd, temp_name = tempfile.mkstemp(prefix="egress-", suffix=".tmp", dir=STATE.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, separators=(",", ":"))
            os.replace(temp_name, STATE)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        if large_control_response:
            try:
                SYSTEMS_INCIDENTS.parent.mkdir(parents=True, exist_ok=True)
                incident = {"at": datetime.now(timezone.utc).isoformat(),
                            "component": "SUPABASE_LARGE_CONTROL_RESPONSE", "status": "DEGRADED",
                            "endpoint": table, "response_bytes": size,
                            "warning_threshold_bytes": CONTROL_PLANE_RESPONSE_WARNING_BYTES,
                            "next_workflow": "SUPABASE_EGRESS_LARGE_CONTROL_RESPONSE_RECOVERY"}
                with SYSTEMS_INCIDENTS.open("a", encoding="utf-8") as out:
                    out.write(json.dumps(incident, separators=(",", ":")) + "\n")
            except OSError:
                pass
    except Exception:
        # Telemetry must never interrupt authoritative workflow processing.
        return


def snapshot() -> dict:
    try:
        data = json.loads(STATE.read_text())
        if data.get("day") == _day():
            return data
    except (OSError, ValueError):
        pass
    return {"day": _day(), "state": "NORMAL", "request_count": 0, "approx_bytes": 0,
            "large_query_count": 0, "retry_count": 0, "cache_hits": 0,
            "cache_lookups": 0, "endpoints": {}}
