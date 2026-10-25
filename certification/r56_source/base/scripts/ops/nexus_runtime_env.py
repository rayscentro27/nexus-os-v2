#!/usr/bin/env python3
"""Canonical Nexus runtime environment loader.

Loads /Users/raymonddavis/.config/nexus/runtime.env without printing values.
Repository-local test env files are intentionally excluded unless a caller
explicitly loads them.
"""
from __future__ import annotations

import os
import inspect
import json
import re
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

SENSITIVE_NAME_RE = re.compile(r"(?:TOKEN|API[_-]?KEY|SECRET|PASSWORD|CREDENTIAL|PRIVATE[_-]?KEY|ACCESS[_-]?KEY)", re.I)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CALLER_SECRET_ALLOWLIST = {
    "scripts/activation/youtube_engine_common.py": {"YOUTUBE_API_KEY", "YOUTUBE_DATA_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_API_KEY"},
    # Alpha research may retrieve governed external sources, but persistence is
    # delegated to the durable-job backend. It must not load Supabase service role.
    "scripts/alpha/alpha_live_research.py": {"OPENROUTER_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY", "YOUTUBE_API_KEY"},
    "scripts/nexus_agent_platform/research/semantic_intelligence.py": {"OPENROUTER_API_KEY"},
    "scripts/nexus_agent_platform/alpha_model_review.py": {"OPENROUTER_API_KEY"},
    "scripts/nexus_agent_platform/research_ai_orchestrator.py": {"OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"},
    "scripts/nexus_agent_platform/marketing_ai_orchestrator.py": {"OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"},
    "scripts/nexus_agent_platform/durable_jobs.py": {"SUPABASE_SERVICE_ROLE_KEY"},
    # The provider governor must resolve the same hosted policy store as the
    # durable job queue. Loading only the service key left SUPABASE_URL unset
    # in fresh worker processes, which silently selected the fail-closed local
    # policy database and denied otherwise-authorized V6 zero-cost research.
    "scripts/nexus_agent_platform/resource_spend_governor.py": {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"},
    "scripts/nexus_agent_platform/feeder_runtime.py": {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"},
    # Research parent handoff writes use the existing governed handoff table.
    # Keep credentials scoped to this one persistence adapter so an otherwise
    # valid Research handoff is not misreported as an unavailable store.
    "scripts/operations/nexus_handoff.py": {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"},
    "scripts/nexus_agent_platform/systems_workflow.py": {"SUPABASE_SERVICE_ROLE_KEY"},
    "scripts/nexus_agent_platform/phase15/live_research.py": {"OPENROUTER_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY"},
    "scripts/nexus_agent_platform/phase15/common.py": {"OPENROUTER_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY"},
    "scripts/social/_supabase.py": {"SUPABASE_URL", "VITE_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"},
    "scripts/trading/oanda_demo_common.py": {"OANDA_API_TOKEN", "OANDA_API_KEY"},
    "scripts/trading/alpaca_options_capability_check.py": {"ALPACA_API_KEY", "ALPACA_SECRET_KEY"},
    "scripts/trading/nexus_oanda_practice_engine.py": {"OANDA_API_TOKEN", "OANDA_API_KEY"},
    "scripts/trading/run_oanda_demo_readonly_check.py": {"OANDA_API_TOKEN", "OANDA_API_KEY"},
    "scripts/trading/audit_oanda_vibe_trading.py": {"OANDA_API_TOKEN", "OANDA_API_KEY"},
}


def _sensitive_names() -> set[str]:
    names: set[str] = set()
    registry_path = _REPO_ROOT / "configs/nexus_credential_registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for item in registry.get("credentials", []):
            names.update(value for value in item.get("canonical_aliases", {}).values() if isinstance(value, str))
            for aliases in item.get("legacy_aliases", {}).values():
                if isinstance(aliases, list):
                    names.update(value for value in aliases if isinstance(value, str))
    except (OSError, ValueError, TypeError):
        pass
    return names


def parse_env_file(path: Path, *, allowed_sensitive_keys: set[str] | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    allowed = allowed_sensitive_keys or set()
    sensitive = _sensitive_names()
    try:
        stream = path.open(encoding="utf-8", errors="ignore")
    except OSError:
        return values
    with stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            if not key:
                continue
            if (key in sensitive or SENSITIVE_NAME_RE.search(key)) and key not in allowed:
                continue
            values[key] = value.strip().strip("'").strip('"')
    return values


def apply_aliases(values: dict[str, str]) -> dict[str, str]:
    merged = dict(values)
    for alias, canonical in ALIASES.items():
        if not merged.get(canonical) and merged.get(alias):
            merged[canonical] = merged[alias]
    return merged


def load_runtime_env(*, override: bool = False, allowed_keys: set[str] | tuple[str, ...] | None = None) -> dict[str, str]:
    """Load only caller-approved sensitive settings.

    Non-secret operational settings remain available. Sensitive values are
    deny-by-default and require a per-caller allowlist or explicit argument.
    """
    if allowed_keys is None:
        frame = inspect.currentframe()
        caller = Path(frame.f_back.f_code.co_filename).resolve() if frame and frame.f_back else Path()
        try:
            relative = caller.relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            relative = ""
        allowed = set(_CALLER_SECRET_ALLOWLIST.get(relative, set()))
    else:
        allowed = set(allowed_keys)
    aliases = {alias: canonical for alias, canonical in ALIASES.items()}
    allowed = allowed | {alias for alias, canonical in aliases.items() if canonical in allowed}
    values = apply_aliases(parse_env_file(CANONICAL_RUNTIME_ENV, allowed_sensitive_keys=allowed))
    filtered = values
    for key, value in filtered.items():
        if override or not os.environ.get(key):
            os.environ[key] = value
    return filtered


def presence_report(required: list[str]) -> list[dict[str, object]]:
    requested = set(required)
    configured: set[str] = set()
    try:
        with CANONICAL_RUNTIME_ENV.open(encoding="utf-8", errors="ignore") as stream:
            for raw in stream:
                key, separator, value = raw.partition("=")
                normalized = key.strip().removeprefix("export ").strip()
                if separator and normalized in requested and value.strip():
                    configured.add(normalized)
    except OSError:
        pass
    return [{"variable": key, "configured": key in configured or bool(os.environ.get(key))} for key in required]


def assert_no_frontend_secret_names(values: dict[str, str]) -> None:
    for key in values:
        if key.startswith("VITE_") and any(secret in key for secret in ("SECRET", "SERVICE", "TOKEN", "API_KEY")):
            raise ValueError(f"refusing frontend-style secret variable: {key}")
