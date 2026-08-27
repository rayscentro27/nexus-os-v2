"""Canonical, redacted credential identity and health control plane."""
from __future__ import annotations
import json, os, re, subprocess, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/nexus_credential_registry.json"
RUNTIME_ENV = Path.home() / ".config/nexus/runtime.env"
SOURCE_ORDER = ("PROCESS_ENV", "CANONICAL_RUNTIME_ENV", "LEGACY_ENV", "MACOS_KEYCHAIN", "NETLIFY_ENV", "SUPABASE_SECRET", "CLOUDFLARE_SECRET")
ENV_FILES = (RUNTIME_ENV, ROOT / ".env.local", ROOT / ".env", ROOT / ".env.nexus.recovered.local", Path.home() / "nexuslive/.env", Path.home() / "nexus/.env")

def _load() -> list[dict[str, Any]]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["credentials"]

def _parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file(): return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1); value = value.strip().strip("'\"")
            if key.strip() and value: values[key.strip()] = value
    return values

def generate_credential_display_name(*, provider: str, purpose: str, environment: str, runtime: str = "macmini", major: int = 1, unique_id: str | None = None) -> str:
    if environment not in {"prod", "test", "dev", "practice", "canary"}: raise ValueError("invalid environment")
    normalized = lambda value: re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    name = f"nexus-{environment}-{normalized(provider)}-{normalized(purpose)}-{normalized(runtime)}-v{int(major)}"
    return f"{name}-{normalized(unique_id)}" if unique_id else name

def registry_entry(credential_id: str) -> dict[str, Any]:
    for entry in _load():
        if entry["credential_id"] == credential_id: return entry
    raise KeyError(credential_id)

def _source_values() -> dict[str, dict[str, str]]:
    result = {"PROCESS_ENV": dict(os.environ)}
    result["CANONICAL_RUNTIME_ENV"] = _parse(RUNTIME_ENV)
    for path in ENV_FILES[1:]: result[f"LEGACY_ENV:{path}"] = _parse(path)
    return result

def resolve(credential_id: str, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    entry = registry_entry(credential_id); sources = _source_values();
    if environ is not None: sources["PROCESS_ENV"] = dict(environ)
    components = {}
    for component, canonical in entry["canonical_aliases"].items():
        aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
        found: list[dict[str, str]] = []
        for source, values in sources.items():
            for alias in aliases:
                if values.get(alias): found.append({"source": source.split(":", 1)[0], "alias": alias})
        found.sort(key=lambda row: (SOURCE_ORDER.index(row["source"]) if row["source"] in SOURCE_ORDER else 99, aliases.index(row["alias"])))
        components[component] = {"canonical_alias": canonical, "accepted_aliases": aliases, "found": found, "selected": found[0] if found else None}
    present = all(item["selected"] for item in components.values())
    return {"credential_id": credential_id, "provider": entry["provider"], "purpose": entry["purpose"], "environment": entry["environment"], "canonical_aliases": entry["canonical_aliases"], "legacy_aliases": entry.get("legacy_aliases", {}), "provider_display_name": entry["provider_display_name"], "components": components, "source_precedence": list(SOURCE_ORDER), "source_found": sorted({item["selected"]["source"] for item in components.values() if item["selected"]}), "authenticated": "UNKNOWN", "result": "AVAILABLE" if present else "MISSING", "values_included": False}

def apply_to_process(credential_id: str) -> dict[str, Any]:
    """Map the selected legacy value into the canonical provider env name in memory only."""
    entry = registry_entry(credential_id); sources = _source_values(); applied = []
    for component, canonical in entry["canonical_aliases"].items():
        aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
        for source in SOURCE_ORDER:
            values = sources.get(source, {})
            alias = next((candidate for candidate in aliases if values.get(candidate)), None)
            if alias:
                os.environ[canonical] = values[alias]
                # Provider adapters may still read a legacy name during the
                # compatibility window; this is process memory only.
                for compatibility_alias in aliases[1:]:
                    os.environ.setdefault(compatibility_alias, values[alias])
                applied.append(component); break
    return {"credential_id": credential_id, "components_applied": applied, "values_included": False}

def catalog() -> dict[str, Any]:
    records = [resolve(entry["credential_id"]) for entry in _load()]
    for record in records:
        entry = registry_entry(record["credential_id"])
        health = {"status":"NOT_RUN","http_status":None}
        if record["credential_id"] == "credential.brave.web_search.prod.v1" and record["result"] == "AVAILABLE":
            apply_to_process(record["credential_id"])
            key = os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
            if key:
                try:
                    request = urllib.request.Request("https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q":"Nexus credential canary","count":1}), headers={"Accept":"application/json","X-Subscription-Token":key})
                    with urllib.request.urlopen(request, timeout=10) as response: health = {"status":"PASS","http_status":response.status}
                except urllib.error.HTTPError as exc: health = {"status":"AUTH_REQUIRED" if exc.code in {401,402,403} else "DEGRADED","http_status":exc.code}
                except Exception: health = {"status":"DEGRADED","http_status":None}
        result = record["result"]
        if health["status"] == "AUTH_REQUIRED": result = "AUTH_REQUIRED"
        record.update({"last_health_check": health, "authenticated":"YES" if health["status"] == "PASS" else ("NO" if health["status"] == "AUTH_REQUIRED" else "UNKNOWN"), "result":result, "permissions_scopes": [], "expiry_known": "NO", "rotation_due": "UNKNOWN", "capabilities": entry.get("capabilities", []), "authority": entry.get("authority")})
    return {"schema_version":"nexus.credential-catalog.v1", "generated_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "raw_values_included":False, "credentials":records}

def write_reports() -> dict[str, Any]:
    report = catalog(); target = ROOT / "reports/runtime"; target.mkdir(parents=True, exist_ok=True)
    (target / "nexus_credential_catalog_latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Nexus Credential Catalog", "", "Redacted identity inventory; secret values are never written.", "", "| Identity | Provider | Components | Sources | Result |", "|---|---|---|---|---|"]
    for row in report["credentials"]:
        components = ", ".join(f"{key}:{'PRESENT' if value['selected'] else 'MISSING'}" for key, value in row["components"].items())
        lines.append(f"| {row['credential_id']} | {row['provider']} | {components} | {', '.join(row['source_found']) or 'none'} | {row['result']} |")
    (target / "nexus_credential_catalog_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__": print(json.dumps(write_reports(), indent=2))
