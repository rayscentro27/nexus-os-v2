"""Shared service-role Supabase REST helper for Nexus OS v2 social scripts.

Server/script-side only. Loads .env, uses SUPABASE_SERVICE_ROLE_KEY. Never prints secrets.
On macOS, run scripts with: SSL_CERT_FILE="$(python3 -m certifi)" python3 <script>
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root


def load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
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
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode(errors="ignore")
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, _redact(e.read().decode(errors="ignore"))[:300]
    except Exception as e:  # noqa: BLE001
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
