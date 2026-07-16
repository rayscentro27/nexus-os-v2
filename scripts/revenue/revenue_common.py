#!/usr/bin/env python3
"""Shared fail-closed helpers for the synthetic revenue certification."""
from __future__ import annotations
import json, os, re, ssl, urllib.error, urllib.parse, urllib.request
from pathlib import Path
import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())
PERSONA_EMAIL = "nexus-persona-d-revenue@goclear.test"
SYNTHETIC_CLIENT_RE = re.compile(r"^gc_[0-9a-f]{32}$")

def envfile(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values

def settings() -> dict[str, str]:
    values = envfile(ROOT / ".env")
    values.update(envfile(ROOT / ".env.local"))
    values.update({k: v for k, v in os.environ.items() if v})
    return values

def rest(base: str, key: str, path: str, method: str = "GET", body=None, extra=None):
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers.update(extra or {})
    payload = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base.rstrip("/") + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=SSL, timeout=45) as response:
            raw = response.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Supabase request failed ({error.code}) for {method} {path.split('?')[0]}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Supabase request failed for {method} {path.split('?')[0]}") from error

def query(base: str, key: str, table: str, select: str, filters: dict[str, str] | None = None):
    params = [("select", select)] + list((filters or {}).items()) + [("limit", "1000")]
    return rest(base, key, f"/rest/v1/{table}?{urllib.parse.urlencode(params, safe='=,*()')}")

def require_synthetic_scope(row: dict, label: str = "Persona D"):
    if row.get("tenant_id") != "goclear" or not SYNTHETIC_CLIENT_RE.fullmatch(str(row.get("client_id") or "")):
        raise RuntimeError(f"{label} scope is not synthetic goclear data")

def safe_summary(value):
    if isinstance(value, dict):
        return {str(k): safe_summary(v) for k, v in value.items() if k not in {"password", "access_token", "refresh_token", "service_role", "payment_credentials", "security_code"}}
    if isinstance(value, list): return [safe_summary(v) for v in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    return str(value)

def print_json(value):
    print(json.dumps(safe_summary(value), indent=2, sort_keys=True))
