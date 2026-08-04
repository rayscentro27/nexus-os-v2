#!/usr/bin/env python3
"""Canonical Nexus runtime environment loader.

Loads /Users/raymonddavis/.config/nexus/runtime.env without printing values.
Repository-local test env files are intentionally excluded unless a caller
explicitly loads them.
"""
from __future__ import annotations

import os
from pathlib import Path

CANONICAL_RUNTIME_ENV = Path("/Users/raymonddavis/.config/nexus/runtime.env")

ALIASES = {
    "NEXUS_TELEGRAM_BOT_TOKEN": "TELEGRAM_BOT_TOKEN",
    "OANDA_API_KEY": "OANDA_API_TOKEN",
    "RESEND_FROM": "RESEND_FROM_EMAIL",
    "EMAIL_FROM": "RESEND_FROM_EMAIL",
    "SUPABASE_ANON_KEY": "VITE_SUPABASE_ANON_KEY",
    "META_ACCESS_TOKEN": "META_PAGE_ACCESS_TOKEN",
}

SERVER_ONLY_PREFIXES = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "FIRECRAWL_API_KEY",
    "RESEND_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "ALPHA_TELEGRAM_BOT_TOKEN",
    "META_PAGE_ACCESS_TOKEN",
    "WHATSAPP_ACCESS_TOKEN",
    "OANDA_API_TOKEN",
    "OANDA_API_KEY",
    "NETLIFY_AUTH_TOKEN",
    "GITHUB_TOKEN",
)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if not key:
            continue
        values[key] = value.strip().strip("'").strip('"')
    return values


def apply_aliases(values: dict[str, str]) -> dict[str, str]:
    merged = dict(values)
    for alias, canonical in ALIASES.items():
        if not merged.get(canonical) and merged.get(alias):
            merged[canonical] = merged[alias]
    return merged


def load_runtime_env(*, override: bool = False) -> dict[str, str]:
    values = apply_aliases(parse_env_file(CANONICAL_RUNTIME_ENV))
    for key, value in values.items():
        if override or not os.environ.get(key):
            os.environ[key] = value
    return values


def presence_report(required: list[str]) -> list[dict[str, object]]:
    values = load_runtime_env()
    return [{"variable": key, "configured": bool(values.get(key) or os.environ.get(key))} for key in required]


def assert_no_frontend_secret_names(values: dict[str, str]) -> None:
    for key in values:
        if key.startswith("VITE_") and any(secret in key for secret in ("SECRET", "SERVICE", "TOKEN", "API_KEY")):
            raise ValueError(f"refusing frontend-style secret variable: {key}")
