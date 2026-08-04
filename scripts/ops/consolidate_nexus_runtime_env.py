#!/usr/bin/env python3
"""Recover, validate, and consolidate Nexus runtime credentials.

Outputs are masked. The canonical runtime file is outside Git:
/Users/raymonddavis/.config/nexus/runtime.env
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import plistlib
import shlex
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nexus_runtime_env import ALIASES, CANONICAL_RUNTIME_ENV, assert_no_frontend_secret_names, parse_env_file

ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "reports" / "runtime" / "nexus_environment_source_inventory.json"
REPORT_MD = ROOT / "reports" / "runtime" / "nexus_environment_source_inventory.md"

TARGET_KEYS = [
    "TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN", "ALPHA_TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "RESEND_API_KEY", "RESEND_FROM_EMAIL", "RESEND_FROM", "EMAIL_FROM",
    "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "VITE_STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET",
    "SUPABASE_URL", "VITE_SUPABASE_URL", "SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    "OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY", "YOUTUBE_API_KEY",
    "META_ACCESS_TOKEN", "META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_BUSINESS_ACCOUNT_ID", "WHATSAPP_VERIFY_TOKEN",
    "OANDA_API_TOKEN", "OANDA_API_KEY", "OANDA_ACCOUNT_ID", "OANDA_ENVIRONMENT",
    "NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID", "GITHUB_TOKEN", "FIRECRAWL_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
]

CANONICAL_KEYS = [
    "SUPABASE_URL", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
    "OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY", "YOUTUBE_API_KEY",
    "TELEGRAM_BOT_TOKEN", "ALPHA_TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "RESEND_API_KEY", "RESEND_FROM_EMAIL",
    "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET",
    "META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_BUSINESS_ACCOUNT_ID", "WHATSAPP_VERIFY_TOKEN",
    "OANDA_API_TOKEN", "OANDA_ACCOUNT_ID", "OANDA_ENVIRONMENT",
    "NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID", "GITHUB_TOKEN", "FIRECRAWL_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def file_mode(path: Path) -> str:
    try:
        return oct(path.stat().st_mode & 0o777)
    except OSError:
        return "unknown"


def env_files() -> list[Path]:
    roots = [
        Path("/Users/raymonddavis/nexus-os-v2"),
        *sorted(Path("/Users/raymonddavis").glob("nexus-os-v2*")),
        Path("/Users/raymonddavis/nexus-ai"),
        Path("/Users/raymonddavis/nexuslive"),
        Path("/Users/raymonddavis/nexus-hermes-runtime"),
        Path("/Users/raymonddavis/.config"),
    ]
    seen: set[Path] = set()
    out: list[Path] = []
    skip_dirs = {
        "node_modules", "dist", ".git", "test-results", "playwright-report", "__pycache__",
        "reports", "data", "logs", ".venv", "venv", "site-packages", "DerivedData",
    }
    for root in roots:
        if not root.exists() or root in seen:
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.endswith(".app")]
            for name in filenames:
                if name in {".env", ".env.local", ".env.production", ".env.development", ".env.test", ".env.e2e.local", "runtime.env"} or name.startswith(".env.") or name.endswith(".env"):
                    out.append(Path(dirpath) / name)
        seen.add(root)
    return sorted(set(out))


def plist_sources() -> list[tuple[Path, dict[str, str]]]:
    rows = []
    for path in sorted(Path("/Users/raymonddavis/Library/LaunchAgents").glob("*.plist*")):
        try:
            with path.open("rb") as fh:
                data = plistlib.load(fh)
            env = data.get("EnvironmentVariables") or {}
            if isinstance(env, dict):
                rows.append((path, {str(k): str(v) for k, v in env.items()}))
        except Exception:
            continue
    return rows


def collect_candidates() -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = {k: [] for k in TARGET_KEYS}
    for path in env_files():
        values = parse_env_file(path)
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            mtime = None
        for key, value in values.items():
            if key in TARGET_KEYS and value:
                candidates.setdefault(key, []).append({"source": str(path), "mechanism": "env_file", "mtime": mtime, "mode": file_mode(path), "value": value})
    for path, values in plist_sources():
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            mtime = None
        for key, value in values.items():
            if key in TARGET_KEYS and value:
                candidates.setdefault(key, []).append({"source": str(path), "mechanism": "launchd_plist", "mtime": mtime, "mode": file_mode(path), "value": value})
    try:
        pref = json.loads((Path.home() / "Library/Preferences/netlify/config.json").read_text())
        user_id = pref.get("userId") or next(iter(pref.get("users", {})))
        token = pref.get("users", {}).get(user_id, {}).get("auth", {}).get("token")
        if token:
            candidates.setdefault("NETLIFY_AUTH_TOKEN", []).append({"source": "~/Library/Preferences/netlify/config.json", "mechanism": "netlify_cli", "mtime": None, "mode": file_mode(Path.home() / "Library/Preferences/netlify/config.json"), "value": token})
        state = json.loads((Path("/Users/raymonddavis/nexus-os-v2/.netlify/state.json")).read_text())
        site_id = state.get("siteId")
        if site_id:
            candidates.setdefault("NETLIFY_SITE_ID", []).append({"source": "/Users/raymonddavis/nexus-os-v2/.netlify/state.json", "mechanism": "netlify_state", "mtime": None, "mode": file_mode(Path("/Users/raymonddavis/nexus-os-v2/.netlify/state.json")), "value": site_id})
    except Exception:
        pass
    return candidates


def http_json(method: str, url: str, headers: dict[str, str] | None = None, body: Any = None, timeout: int = 20) -> tuple[bool, int | None, Any, str | None]:
    data = json.dumps(body).encode() if body is not None else None
    request_headers = {"User-Agent": "nexus-os-v2/1.0", **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        import certifi  # type: ignore
        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            raw = resp.read().decode(errors="ignore")
            try:
                return True, resp.status, json.loads(raw) if raw else {}, None
            except json.JSONDecodeError:
                return True, resp.status, raw[:500], None
    except urllib.error.HTTPError as exc:
        return False, exc.code, {}, f"HTTP_{exc.code}"
    except Exception as exc:
        return False, None, {}, exc.__class__.__name__


def first_value(selected: dict[str, str], candidates: dict[str, list[dict[str, Any]]], *keys: str) -> str | None:
    for key in keys:
        if selected.get(key):
            return selected[key]
        rows = candidates.get(key) or []
        if rows:
            return rows[0]["value"]
    return None


def validate_candidates(candidates: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {}
    def add(key: str, row: dict[str, Any], ok: bool, status: str, meta: dict[str, Any] | None = None) -> None:
        results.setdefault(key, []).append({
            "source": row["source"], "mechanism": row["mechanism"], "fingerprint": fingerprint(row["value"]),
            "valid": ok, "status": status, "meta": meta or {},
        })
    for key in ("TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN", "ALPHA_TELEGRAM_BOT_TOKEN"):
        for row in candidates.get(key, []):
            ok, code, data, err = http_json("GET", f"https://api.telegram.org/bot{row['value']}/getMe")
            result = data.get("result", {}) if isinstance(data, dict) else {}
            username = result.get("username")
            status = "VALID" if ok and data.get("ok") else err or f"HTTP_{code}"
            add(key, row, bool(ok and data.get("ok")), status, {"bot_id_hash": fingerprint(str(result.get("id", ""))) if result.get("id") else None, "username": username, "first_name": result.get("first_name")})
    for key in ("RESEND_API_KEY",):
        for row in candidates.get(key, []):
            ok, code, data, err = http_json("GET", "https://api.resend.com/domains", {"authorization": f"Bearer {row['value']}"})
            domains = data.get("data", []) if isinstance(data, dict) else []
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"domains_seen": len(domains)})
    for key in ("OPENROUTER_API_KEY",):
        for row in candidates.get(key, []):
            ok, code, data, err = http_json("GET", "https://openrouter.ai/api/v1/models", {"authorization": f"Bearer {row['value']}"})
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"models_seen": len(data.get("data", [])) if isinstance(data, dict) else None})
    for key in ("GROQ_API_KEY",):
        for row in candidates.get(key, []):
            ok, code, data, err = http_json("GET", "https://api.groq.com/openai/v1/models", {"authorization": f"Bearer {row['value']}"})
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"models_seen": len(data.get("data", [])) if isinstance(data, dict) else None})
    for key in ("BRAVE_SEARCH_API_KEY",):
        for row in candidates.get(key, []):
            ok, code, data, err = http_json("GET", "https://api.search.brave.com/res/v1/web/search?q=nexus%20runtime%20credential%20probe&count=1", {"x-subscription-token": row["value"], "accept": "application/json"})
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"results_seen": len(((data.get("web") or {}).get("results") or [])) if isinstance(data, dict) else None})
    for key in ("YOUTUBE_API_KEY",):
        for row in candidates.get(key, []):
            url = "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=1&q=business%20credit&key=" + urllib.parse.quote(row["value"])
            ok, code, data, err = http_json("GET", url)
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"items_seen": len(data.get("items", [])) if isinstance(data, dict) else None})
    for key in ("STRIPE_SECRET_KEY",):
        for row in candidates.get(key, []):
            auth = base64.b64encode(f"{row['value']}:".encode()).decode()
            ok, code, data, err = http_json("GET", "https://api.stripe.com/v1/balance", {"authorization": f"Basic {auth}"})
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"livemode": data.get("livemode") if isinstance(data, dict) else None})
    for key in ("META_PAGE_ACCESS_TOKEN", "META_ACCESS_TOKEN"):
        for row in candidates.get(key, []):
            ok, code, data, err = http_json("GET", f"https://graph.facebook.com/v20.0/me?access_token={urllib.parse.quote(row['value'])}")
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"identity_present": bool(isinstance(data, dict) and data.get("id"))})
    for key in ("OANDA_API_TOKEN", "OANDA_API_KEY"):
        for row in candidates.get(key, []):
            acct = first_value({}, candidates, "OANDA_ACCOUNT_ID")
            if not acct:
                add(key, row, False, "MISSING_ACCOUNT_ID")
                continue
            ok, code, data, err = http_json("GET", f"https://api-fxpractice.oanda.com/v3/accounts/{urllib.parse.quote(acct, safe='')}/summary", {"authorization": f"Bearer {row['value']}", "Accept-Datetime-Format": "RFC3339"})
            add(key, row, ok, "VALID" if ok else err or f"HTTP_{code}", {"practice": True, "account_hash": fingerprint(acct)})
    return results


def choose_value(key: str, candidates: dict[str, list[dict[str, Any]]], validations: dict[str, list[dict[str, Any]]]) -> str | None:
    rows = candidates.get(key) or []
    if not rows:
        return None
    valid_fps = [r["fingerprint"] for r in validations.get(key, []) if r.get("valid")]
    if valid_fps:
        for row in rows:
            if fingerprint(row["value"]) in valid_fps:
                return row["value"]
    if validations.get(key):
        return None
    trusted = [r for r in rows if "/Users/raymonddavis/nexus-os-v2/.env" in r["source"] or "/Users/raymonddavis/.config/nexus/runtime.env" in r["source"]]
    picked = sorted(trusted or rows, key=lambda r: r.get("mtime") or "", reverse=True)[0]
    return picked["value"]


def write_runtime_env(selected: dict[str, str]) -> None:
    assert_no_frontend_secret_names({k: v for k, v in selected.items() if k not in {"VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY", "VITE_STRIPE_PUBLISHABLE_KEY"}})
    CANONICAL_RUNTIME_ENV.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(CANONICAL_RUNTIME_ENV.parent, 0o700)
    lines = ["# Nexus canonical runtime environment", f"# Generated {now()}", "# Secret values intentionally omitted from reports."]
    for key in CANONICAL_KEYS:
        value = selected.get(key)
        if value:
            lines.append(f"{key}={shlex.quote(value)}")
    CANONICAL_RUNTIME_ENV.write_text("\n".join(lines) + "\n")
    os.chmod(CANONICAL_RUNTIME_ENV, 0o600)


def write_reports(candidates: dict[str, list[dict[str, Any]]], validations: dict[str, list[dict[str, Any]]], selected: dict[str, str]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    inventory = []
    for key in TARGET_KEYS:
        rows = []
        for row in candidates.get(key, []):
            rows.append({
                "source": row["source"], "mechanism": row["mechanism"], "mode": row["mode"], "mtime": row["mtime"],
                "fingerprint": fingerprint(row["value"]), "selected": selected.get(key) == row["value"],
            })
        fps = {r["fingerprint"] for r in rows}
        inventory.append({
            "variable": key,
            "present": bool(rows),
            "selected": bool(selected.get(key)),
            "selected_fingerprint": fingerprint(selected[key]) if selected.get(key) else None,
            "sources": rows,
            "duplicate_sources": len(rows),
            "alias_target": ALIASES.get(key),
            "alias_conflict": bool(ALIASES.get(key) and selected.get(key) and selected.get(ALIASES[key]) and selected[key] != selected[ALIASES[key]]),
            "provider_validation": validations.get(key, []),
            "currently_loaded": bool(os.environ.get(key)),
        })
    payload = {"generated_at": now(), "canonical_runtime_env": str(CANONICAL_RUNTIME_ENV), "runtime_env_mode": oct(CANONICAL_RUNTIME_ENV.stat().st_mode & 0o777) if CANONICAL_RUNTIME_ENV.exists() else None, "runtime_dir_mode": oct(CANONICAL_RUNTIME_ENV.parent.stat().st_mode & 0o777) if CANONICAL_RUNTIME_ENV.parent.exists() else None, "variables": inventory}
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    lines = ["# Nexus Environment Source Inventory", "", f"Generated: {payload['generated_at']}", f"Canonical runtime file: `{CANONICAL_RUNTIME_ENV}`", ""]
    lines.append("| Variable | Present | Selected | Sources | Validation |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for item in inventory:
        statuses = sorted({v.get("status", "") for v in item["provider_validation"] if v.get("status")})
        lines.append(f"| `{item['variable']}` | {item['present']} | {item['selected']} | {item['duplicate_sources']} | {', '.join(statuses) or 'not probed'} |")
    REPORT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    candidates = collect_candidates()
    validations = validate_candidates(candidates)
    selected: dict[str, str] = {}
    for key in CANONICAL_KEYS:
        value = choose_value(key, candidates, validations)
        if value:
            selected[key] = value
    # Alias-derived canonical values.
    for alias, canonical in ALIASES.items():
        if not selected.get(canonical):
            value = choose_value(alias, candidates, validations)
            if value:
                selected[canonical] = value
    if selected.get("SUPABASE_URL") and not selected.get("VITE_SUPABASE_URL"):
        selected["VITE_SUPABASE_URL"] = selected["SUPABASE_URL"]
    if selected.get("VITE_SUPABASE_ANON_KEY") and not selected.get("SUPABASE_ANON_KEY"):
        selected["SUPABASE_ANON_KEY"] = selected["VITE_SUPABASE_ANON_KEY"]
    write_runtime_env(selected)
    write_reports(candidates, validations, selected)
    print(json.dumps({
        "canonical_runtime_file_created": CANONICAL_RUNTIME_ENV.exists(),
        "runtime_dir_mode": oct(CANONICAL_RUNTIME_ENV.parent.stat().st_mode & 0o777),
        "runtime_file_mode": oct(CANONICAL_RUNTIME_ENV.stat().st_mode & 0o777),
        "variables_selected": len(selected),
        "variables_with_sources": sum(1 for rows in candidates.values() if rows),
        "validations_passed": sum(1 for rows in validations.values() for row in rows if row.get("valid")),
        "validations_failed": sum(1 for rows in validations.values() for row in rows if not row.get("valid")),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
