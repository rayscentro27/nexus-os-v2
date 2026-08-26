"""Redacted integration and credential discovery for governed Nexus adapters.

This module answers whether a credential identity is present and where it was
found. It never returns or persists secret values. Provider API calls belong to
the owning adapter after this resolver has selected a source.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ENV = Path.home() / ".config/nexus/runtime.env"

IDENTITIES: dict[str, tuple[str, ...]] = {
    "credential.telegram.hermes.bot.v1": (
        "TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN", "HERMES_TELEGRAM_BOT_TOKEN",
    ),
    "credential.telegram.hermes.chat.v1": (
        "TELEGRAM_ALLOWED_CHAT_IDS", "NEXUS_TELEGRAM_ALLOWED_CHAT_IDS", "TELEGRAM_CHAT_ID",
    ),
    "credential.cloudflare.voice.management.v1": (
        "CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_TOKEN",
        "NEXUS_CLOUDFLARE_TOKEN", "VOICE_CLOUDFLARE_API_TOKEN",
    ),
    "credential.cloudflare.voice.service_auth.v1": (
        "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN",
    ),
    "credential.netlify.release.v1": ("NETLIFY_AUTH_TOKEN",),
    "credential.supabase.admin.v1": (
        "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_URL",
    ),
}

COMPONENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "credential.cloudflare.voice.service_auth.v1": {
        "client_id": ("CF_ACCESS_CLIENT_ID",),
        "client_secret": ("CF_ACCESS_CLIENT_SECRET",),
        "origin": ("VOICE_ACCESS_ORIGIN",),
    },
    "credential.telegram.hermes.bot.v1": {
        "bot_token": ("TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN", "HERMES_TELEGRAM_BOT_TOKEN"),
        "authorized_chat_ids": ("TELEGRAM_ALLOWED_CHAT_IDS", "NEXUS_TELEGRAM_ALLOWED_CHAT_IDS", "TELEGRAM_CHAT_ID"),
    },
    "credential.supabase.admin.v1": {
        "url": ("SUPABASE_URL", "VITE_SUPABASE_URL"),
        "service_role_key": ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY"),
    },
}


@dataclass(frozen=True)
class Discovery:
    identity: str
    provider: str
    aliases: tuple[str, ...]
    present_aliases: tuple[str, ...]
    sources: tuple[str, ...]
    status: str

    def safe(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "provider": self.provider,
            "aliases": list(self.aliases),
            "present_aliases": list(self.present_aliases),
            "sources": list(self.sources),
            "status": self.status,
            "values_included": False,
        }


def _dotenv(path: Path) -> Mapping[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("\"'")
        if key.strip() and value:
            values[key.strip()] = value
    return values


def discover(identity: str, *, environ: Mapping[str, str] | None = None) -> Discovery:
    aliases = IDENTITIES.get(identity, ())
    env = dict(environ or os.environ)
    present: dict[str, list[str]] = {}
    for alias in aliases:
        if env.get(alias):
            present.setdefault(alias, []).append("process")
        for path, source_name in ((RUNTIME_ENV, "canonical_runtime_env"), (ROOT / ".env.local", ".env.local"), (ROOT / ".env", ".env")):
            filename = source_name
            if _dotenv(path).get(alias):
                present.setdefault(alias, []).append(filename)
    present_aliases = tuple(present)
    sources = tuple(sorted({source for rows in present.values() for source in rows}))
    if not aliases:
        status = "UNKNOWN_IDENTITY"
    elif present_aliases:
        status = "SOURCE_FOUND" if len(present_aliases) == 1 else "ALIAS_MAPPED"
    else:
        status = "ABSENT"
    provider = identity.split(".")[1] if "." in identity else "UNKNOWN"
    return Discovery(identity, provider, aliases, present_aliases, sources, status)


def resolve_all() -> dict[str, Any]:
    result = {identity: discover(identity).safe() for identity in IDENTITIES}
    for identity, components in COMPONENTS.items():
        resolved: dict[str, Any] = {}
        complete = True
        for component, aliases in components.items():
            found = discover(identity)
            chosen = [alias for alias in aliases if alias in found.present_aliases]
            resolved[component] = {"aliases": list(aliases), "present_aliases": chosen, "status": "PRESENT" if chosen else "ABSENT"}
            complete = complete and bool(chosen)
        result[identity]["components"] = resolved
        result[identity]["status"] = "COMPLETE" if complete else result[identity]["status"]
    return result


def safe_runtime_facts() -> dict[str, Any]:
    """Return non-secret discovery facts needed by release diagnostics."""
    return {
        "wrangler": {
            "path": shutil.which("wrangler") or None,
            "installed_on_path": bool(shutil.which("wrangler")),
        },
        "identities": resolve_all(),
        "secret_values_included": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(safe_runtime_facts(), indent=2, sort_keys=True))
