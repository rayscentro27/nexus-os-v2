"""Minimal Supabase REST access for the commerce funnel.

anon role: what the public storefront can do (insert-only, RLS-scoped).
service role: Nexus-side reads/verified writes. Keys are read from the runtime
env file and never printed or persisted.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

RUNTIME_ENV = Path.home() / ".config/nexus/runtime.env"


def _env() -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in RUNTIME_ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.replace("export ", "").strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def config() -> dict[str, str]:
    e = _env()
    return {"url": (e.get("SUPABASE_URL") or e.get("VITE_SUPABASE_URL") or "").rstrip("/"),
            "anon": e.get("VITE_SUPABASE_ANON_KEY", ""), "service": e.get("SUPABASE_SERVICE_ROLE_KEY", "")}


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def call(method: str, path: str, body: Any = None, *, role: str = "anon", prefer: str = "return=minimal") -> tuple[int, Any]:
    cfg = config()
    key = cfg["anon"] if role == "anon" else cfg["service"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(f"{cfg['url']}/rest/v1/{path}", data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=25) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read() or b"{}")
        except ValueError:
            detail = {}
        return e.code, {"code": detail.get("code"), "message": str(detail.get("message", ""))[:160]}
