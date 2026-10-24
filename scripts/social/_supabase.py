"""Shared service-role Supabase REST helper for Nexus OS v2 social scripts.

Server/script-side only. Loads .env, uses SUPABASE_SERVICE_ROLE_KEY. Never prints secrets.
On macOS, run scripts with: SSL_CERT_FILE="$(python3 -m certifi)" python3 <script>
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
import sys
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from nexus_runtime_env import load_runtime_env  # noqa: E402

try:
    import certifi  # type: ignore
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except Exception:
    pass


def load_env() -> dict:
    env = {}
    allowed = {"SUPABASE_URL", "VITE_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                key = k.strip()
                if key in allowed:
                    env[key] = v.strip().strip('"').strip("'")
    env.update(load_runtime_env())
    return env


ENV = load_env()
URL = (ENV.get("SUPABASE_URL") or ENV.get("VITE_SUPABASE_URL") or "").rstrip("/")
KEY = ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")


def configured() -> bool:
    return bool(URL and KEY)


def _redact(text: str) -> str:
    if KEY and text:
        text = text.replace(KEY, "<redacted>")
    return text


def rest(method: str, path: str, body=None, prefer: str | None = None):
    """Return (status, parsed_or_text). Errors return (code, redacted_text)."""
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{URL}/rest/v1/{path}", data=data, method=method, headers=headers)
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from nexus_agent_platform.supabase_egress_guard import record_request, safe_mode_enabled, preflight_request, read_bounded_response, JobEgressBudgetExceeded
        max_retries = 0 if safe_mode_enabled() else max(0, min(1, int(os.environ.get("NEXUS_SUPABASE_MAX_RETRIES", "1"))))
    except Exception:
        from nexus_agent_platform.supabase_egress_guard import record_request, preflight_request, read_bounded_response, JobEgressBudgetExceeded
        max_retries = 0
    idempotent = method.upper() in {"GET", "HEAD", "OPTIONS", "PATCH"} or (method.upper() == "POST" and "on_conflict=" in path)
    attempt = 0
    while True:
        preflight_request(method, path, body)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw_bytes = read_bounded_response(r, method, path)
                raw = raw_bytes.decode(errors="ignore")
                parsed = json.loads(raw) if raw else None
                record_request(method, path, r.status, len(raw_bytes), rows=len(parsed) if isinstance(parsed, list) else 0, retries=attempt, trace=False)
                return r.status, parsed
        except JobEgressBudgetExceeded:
            raise
        except urllib.error.HTTPError as e:
            error_bytes = read_bounded_response(e, method, path)
            record_request(method, path, e.code, len(error_bytes), retries=attempt, trace=False)
            if idempotent and attempt < max_retries and e.code in {408, 429, 500, 502, 503, 504, 522}:
                attempt += 1
                time.sleep(min(2 ** attempt, 2))
                continue
            return e.code, _redact(error_bytes.decode(errors="ignore"))[:300]
        except Exception as e:  # noqa: BLE001
            record_request(method, path, 0, 0, retries=attempt, trace=False)
            if idempotent and attempt < max_retries:
                attempt += 1
                time.sleep(min(2 ** attempt, 2))
                continue
            return 0, _redact(str(e))[:300]


def get(table: str, query: str = ""):
    return rest("GET", f"{table}?{query}" if query else table)


def insert(table: str, rows, prefer="return=representation"):
    return rest("POST", table, body=rows if isinstance(rows, list) else [rows], prefer=prefer)


def update(table: str, query: str, patch: dict):
    return rest("PATCH", f"{table}?{query}", body=patch, prefer="return=minimal")


def event(lane: str, action: str, status: str, title: str, summary: str = "",
          payload: dict | None = None, approval_id: str | None = None, job_id: str | None = None):
    row = {"lane": lane, "source": action, "action": action, "status": status,
           "title": title, "summary": summary, "payload": payload or {}}
    if approval_id:
        row["approval_id"] = approval_id
    if job_id:
        row["job_id"] = job_id
    insert("nexus_events", row, prefer="return=minimal")


def health(component: str, status: str, summary: str = ""):
    insert("system_health", {"component": component, "status": status, "summary": summary},
           prefer="return=minimal")


def q(value: str) -> str:
    return urllib.parse.quote(value, safe="")
